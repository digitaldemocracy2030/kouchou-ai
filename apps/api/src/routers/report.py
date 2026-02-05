import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import ValidationError

from src.config import settings
from src.schemas.report import Report, ReportStatus, ReportVisibility
from src.schemas.visualization_config import DEFAULT_REPORT_DISPLAY_CONFIG, ReportDisplayConfig
from src.services.report_status import load_status_as_reports
from src.utils.slug_utils import validate_slug

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
    validate_slug(slug)
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

    # 可視化設定をマージ（存在する場合）
    # snake_case JSONをpydanticで検証し、camelCaseに変換して返す
    visualization_config_path = settings.REPORT_DIR / slug / "visualization_config.json"
    if visualization_config_path.exists():
        try:
            with open(visualization_config_path) as f:
                raw_config = json.load(f)
            # pydanticで検証（snake_case/camelCase両対応、populate_by_name=True）
            validated_config = ReportDisplayConfig.model_validate(raw_config)
            # camelCaseで出力（by_alias=True）
            report_result["visualizationConfig"] = validated_config.model_dump(by_alias=True)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load visualization config for {slug}: {e}")
        except ValidationError as e:
            logger.warning(f"Invalid visualization config for {slug}, using default: {e}")
            report_result["visualizationConfig"] = DEFAULT_REPORT_DISPLAY_CONFIG.model_dump(by_alias=True)

    return report_result


@router.get("/test-error")
async def test_error():
    logger.info("This is a test log message")
    raise ValueError("Test error to check logging")
