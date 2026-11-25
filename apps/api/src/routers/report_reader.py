import json
from math import isfinite
from secrets import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, Security
from fastapi.security import APIKeyHeader

from src.config import settings
from src.schemas.report import Report, ReportStatus
from src.schemas.report_reader import REPORT_READER_PATH, ReportList, ReportProgress, ReportStep, ReportSummary
from src.services.report_launcher import UPLOAD_FAILED_ERROR
from src.services.report_status import load_status_as_reports
from src.utils.slug_utils import validate_slug

NO_STORE = {"Cache-Control": "no-store"}
reader_header = APIKeyHeader(name="x-api-key", scheme_name="ReportReaderKey", auto_error=False)


def require_reader_key(response: Response, api_key: Annotated[str | None, Security(reader_header)]) -> None:
    configured = settings.REPORT_READER_API_KEY
    expected = configured.get_secret_value().strip() if configured else ""
    if not expected or expected in {settings.ADMIN_API_KEY, settings.PUBLIC_API_KEY}:
        raise HTTPException(status_code=404, detail="Report reader API is disabled", headers=NO_STORE)
    if api_key is None or not compare_digest(api_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid report reader API key", headers=NO_STORE)
    response.headers.update(NO_STORE)


router = APIRouter(prefix=REPORT_READER_PATH, tags=["report reader"], dependencies=[Depends(require_reader_key)])


@router.get("")
def list_reports(status: ReportStatus | None = None) -> ReportList:
    return ReportList(
        reports=[
            ReportSummary(
                slug=report.slug,
                title=report.title,
                created_at=report.created_at,
                status=report.status,
                visibility=report.visibility,
            )
            for report in load_status_as_reports()
            if status is None or report.status == status
        ]
    )


def _current_step(report: Report) -> ReportStep | None:
    expected_status = {ReportStatus.PROCESSING: "running", ReportStatus.ERROR: "error"}.get(report.status)
    if expected_status is None:
        return None

    try:
        report_root = settings.REPORT_DIR.resolve()
        path = (report_root / report.slug / "hierarchical_status.json").resolve()
        if not path.is_relative_to(report_root):
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RuntimeError):
        # 古いレポートや起動直後には、工程のファイルを読めないことがある。
        return None

    if not isinstance(data, dict) or data.get("status") != expected_status or data.get("error") == UPLOAD_FAILED_ERROR:
        return None
    try:
        return ReportStep(data.get("current_job"))
    except ValueError:
        return None


@router.get("/{slug}/status")
def get_report_status(slug: str) -> ReportProgress:
    validate_slug(slug)
    report = next((report for report in load_status_as_reports() if report.slug == slug), None)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found", headers=NO_STORE)

    cost = report.estimated_cost
    return ReportProgress(
        slug=report.slug,
        status=report.status,
        current_step=_current_step(report),
        estimated_cost_usd=cost if cost is not None and isfinite(cost) and cost >= 0 else None,
    )
