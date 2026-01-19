import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from src.config import settings
from src.schemas.report import Report, ReportStatus, ReportVisibility
from src.services.report_status import load_status_as_reports

logger = logging.getLogger("uvicorn")

router = APIRouter()

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


async def verify_public_api_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key != settings.PUBLIC_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


@router.get("/reports", dependencies=[Depends(verify_public_api_key)])
async def reports() -> list[Report]:
    all_reports = load_status_as_reports()
    ready_reports = [
        report for report in all_reports if report.status == ReportStatus.READY and report.is_publicly_visible
    ]
    return ready_reports


@router.get("/reports/{slug}")
async def report(slug: str, api_key: str = Depends(verify_public_api_key)) -> dict:
    report_path = settings.REPORT_DIR / slug / "hierarchical_result.json"
    all_reports = load_status_as_reports()
    target_report_status = next((report for report in all_reports if report.slug == slug), None)

    if target_report_status is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if target_report_status.status != ReportStatus.READY:
        raise HTTPException(status_code=404, detail="Report is not ready")
    if target_report_status.visibility == ReportVisibility.PRIVATE:
        raise HTTPException(status_code=404, detail="Report is private")
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    with open(report_path) as f:
        report_result = json.load(f)

    # レポートにvisibilityを追加
    report_result["visibility"] = target_report_status.visibility.value

    return report_result


@router.get("/test-error")
async def test_error():
    logger.info("This is a test log message")
    raise ValueError("Test error to check logging")
