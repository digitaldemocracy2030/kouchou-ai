import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import ValidationError

from src.config import settings
from src.schemas.public_report_result import PublicReportResult
from src.schemas.report import PublicReport, ReportStatus, ReportVisibility
from src.schemas.visualization_config import DEFAULT_REPORT_DISPLAY_CONFIG, parse_saved_visualization_config
from src.services.report_status import load_status_as_reports
from src.utils.slug_utils import validate_slug

logger = logging.getLogger("uvicorn")

router = APIRouter()

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


def _read_public_result_file(public_path: Path, result_path: Path) -> dict | None:
    """``public_result.json`` を読む。無い・壊れている・結果より古い場合は None。

    集計は結果と公開用を同時に書くので、公開用の方が古いのは、公開用を書かない経路
    （この仕組みより前の版など）で結果だけが書き直された場合。そのときは結果から作り直す。
    """
    if not public_path.exists():
        return None
    try:
        if result_path.exists() and public_path.stat().st_mtime < result_path.stat().st_mtime:
            logger.warning(f"{public_path} is older than {result_path.name}; rebuilding from the result")
            return None
        with open(public_path, encoding="utf-8") as f:
            public_result = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to read {public_path}; rebuilding from the result: {e}")
        return None
    return public_result if isinstance(public_result, dict) else None


def _load_validated_report_result(slug: str) -> dict:
    """公開用レポート結果（docs/development/public-result.md の契約）を返す。

    ``public_result.json`` を優先して読み、無いレポート（この仕組みより前に作られたもの）は
    ``hierarchical_result.json`` から analysis-core の ``build_public_result`` で同じ形へ変換する。
    どちらの経路でも、ホワイトリストにない項目（再分析用の設定など）は返さない。
    """
    from analysis_core.public_result import PUBLIC_RESULT_FILENAME, RESULT_FILENAME, build_public_result

    report_dir = settings.REPORT_DIR / slug
    result_path = report_dir / RESULT_FILENAME
    report_result = _read_public_result_file(report_dir / PUBLIC_RESULT_FILENAME, result_path)
    if report_result is None:
        if not result_path.exists():
            logger.warning(f"Public report result for {slug} is unreadable and {RESULT_FILENAME} is missing")
            raise HTTPException(status_code=500, detail="Invalid report data")
        with open(result_path, encoding="utf-8") as f:
            report_result = build_public_result(json.load(f))

    try:
        PublicReportResult.model_validate(report_result)
    except ValidationError as e:
        logger.warning(f"Invalid public report result for {slug}: {e}")
        raise HTTPException(status_code=500, detail="Invalid report data") from e

    return report_result


async def verify_public_api_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key != settings.PUBLIC_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


@router.get("/reports", dependencies=[Depends(verify_public_api_key)])
async def reports() -> list[PublicReport]:
    all_reports = load_status_as_reports()
    # 公開用の項目だけに絞る（複製元の slug や管理用の情報を返さない）
    return [
        PublicReport.from_report(report)
        for report in all_reports
        if report.status == ReportStatus.READY and report.is_publicly_visible
    ]


@router.get("/reports/{slug}")
async def report(slug: str, api_key: str = Depends(verify_public_api_key)) -> dict:
    """公開可能なレポートの公開用レポート結果に、公開範囲と可視化設定を添えて返す。

    可視化設定は古い密度項目だけを読み込み時に補正する。
    """
    validate_slug(slug)
    report_dir = settings.REPORT_DIR / slug
    all_reports = load_status_as_reports()
    target_report_status = next((report for report in all_reports if report.slug == slug), None)

    if target_report_status is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if target_report_status.status != ReportStatus.READY:
        raise HTTPException(status_code=404, detail="Report is not ready")
    if target_report_status.visibility == ReportVisibility.PRIVATE:
        raise HTTPException(status_code=404, detail="Report is private")
    if not (report_dir / "hierarchical_result.json").exists() and not (report_dir / "public_result.json").exists():
        raise HTTPException(status_code=404, detail="Report not found")

    report_result = _load_validated_report_result(slug)

    # レポートにvisibilityを追加
    report_result["visibility"] = target_report_status.visibility.value

    # 可視化設定をマージ（存在する場合）
    # snake_case JSONをpydanticで検証し、camelCaseに変換して返す
    visualization_config_path = settings.REPORT_DIR / slug / "visualization_config.json"
    if visualization_config_path.exists():
        try:
            with open(visualization_config_path, encoding="utf-8") as f:
                raw_config = json.load(f)
            # pydanticで検証（snake_case/camelCase両対応、populate_by_name=True）
            validated_config = parse_saved_visualization_config(raw_config)
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
