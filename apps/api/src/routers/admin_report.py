import json

import openai

try:  # pragma: no cover - optional dependency
    from google.api_core import exceptions as google_exceptions
except Exception:  # pragma: no cover
    google_exceptions = None

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Security
from fastapi.responses import FileResponse, ORJSONResponse
from fastapi.security.api_key import APIKeyHeader

from src.config import settings
from src.core.exceptions import (
    ClusterCSVParseError,
    ClusterFileNotFound,
    ConfigFileNotFound,
    ConfigJSONParseError,
)
from src.repositories.cluster_repository import ClusterRepository
from src.repositories.config_repository import ConfigRepository
from src.schemas.admin_report import ReportDuplicateRequest, ReportInput, ReportVisibilityUpdate
from src.schemas.cluster import ClusterResponse, ClusterUpdate
from src.schemas.report import Report, ReportStatus
from src.schemas.report_config import ReportConfigUpdate
from src.schemas.visualization_config import ReportDisplayConfig
from src.services.llm_models import get_models_by_provider
from src.services.llm_pricing import LLMPricing
from src.services.report_duplicate import duplicate_report
from src.services.report_launcher import execute_aggregation, launch_report_generation
from src.services.report_status import (
    add_analysis_data,
    invalidate_report_cache,
    load_status_as_reports,
    set_status,
    update_report_config,
    update_report_visibility_state,
)
from src.utils.logger import setup_logger
from src.utils.slug_utils import validate_slug

slogger = setup_logger()
router = APIRouter()

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


async def verify_admin_api_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


def validate_path_within_report_dir(path) -> None:
    """Validate that resolved path is within REPORT_DIR.

    Args:
        path: The path to validate

    Raises:
        HTTPException: If path escapes REPORT_DIR
    """
    try:
        resolved = path.resolve()
        report_dir_resolved = settings.REPORT_DIR.resolve()
        if not str(resolved).startswith(str(report_dir_resolved)):
            raise HTTPException(status_code=400, detail="Invalid path")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path") from None


@router.get("/admin/reports")
async def get_reports(api_key: str = Depends(verify_admin_api_key)) -> list[Report]:
    return list(map(add_analysis_data, load_status_as_reports()))


@router.post("/admin/reports", status_code=202)
async def create_report(
    report: ReportInput, request: Request, api_key: str = Depends(verify_admin_api_key)
) -> ORJSONResponse:
    try:
        user_api_key = request.headers.get("x-user-api-key")
        launch_report_generation(report, user_api_key)
        return ORJSONResponse(
            content=None,
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except ValueError as e:
        slogger.error(f"ValueError: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        slogger.error(f"Exception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/admin/reports/{slug}/duplicate", status_code=202)
async def duplicate_report_endpoint(
    slug: str,
    payload: ReportDuplicateRequest,
    request: Request,
    api_key: str = Depends(verify_admin_api_key),
) -> ORJSONResponse:
    try:
        validate_slug(slug)
        if payload.new_slug and payload.new_slug.strip():
            validate_slug(payload.new_slug)

        # source status check
        reports = load_status_as_reports(include_deleted=True)
        source_report = next((r for r in reports if r.slug == slug), None)
        if source_report is None:
            raise HTTPException(status_code=404, detail="Source report not found")
        if source_report.status == ReportStatus.DELETED:
            raise HTTPException(status_code=409, detail="Source report is deleted")
        if source_report.status not in (ReportStatus.READY, ReportStatus.ERROR):
            raise HTTPException(status_code=409, detail="Source report is not duplicatable")

        user_api_key = request.headers.get("x-user-api-key")
        new_slug = duplicate_report(slug, payload, user_api_key)

        return ORJSONResponse(
            content={
                "success": True,
                "report": {
                    "slug": new_slug,
                    "status": "processing",
                },
            },
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except HTTPException:
        raise
    except ValueError as e:
        slogger.error(f"ValueError: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        slogger.error(f"Exception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/admin/comments/{slug}/csv")
async def download_comments_csv(slug: str, api_key: str = Depends(verify_admin_api_key)) -> FileResponse:
    validate_slug(slug)
    csv_path = settings.REPORT_DIR / slug / "final_result_with_comments.csv"
    validate_path_within_report_dir(csv_path)
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="CSV file not found")
    return FileResponse(path=str(csv_path), media_type="text/csv", filename=f"kouchou_{slug}.csv")


@router.get("/admin/reports/{slug}/json")
async def download_report_json(slug: str, api_key: str = Depends(verify_admin_api_key)) -> FileResponse:
    validate_slug(slug)
    json_path = settings.REPORT_DIR / slug / "hierarchical_result.json"
    validate_path_within_report_dir(json_path)
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="JSON file not found")
    return FileResponse(path=str(json_path), media_type="application/json", filename=f"kouchou_{slug}.json")


@router.get("/admin/reports/{slug}/status/step-json", dependencies=[Depends(verify_admin_api_key)])
async def get_current_step(slug: str) -> dict:
    validate_slug(slug)
    status_file = settings.REPORT_DIR / slug / "hierarchical_status.json"
    try:
        # ステータスファイルが存在しない場合は "loading" を返す
        if not status_file.exists():
            return {"current_step": "loading"}

        with open(status_file) as f:
            status = json.load(f)

        response = {
            "status": status.get("status", "running"),
            "current_step": status.get("current_job", "loading"),
            "token_usage": status.get("total_token_usage", 0),
            "token_usage_input": status.get("token_usage_input", 0),
            "token_usage_output": status.get("token_usage_output", 0),
            "estimated_cost": status.get("estimated_cost", 0.0),
            "provider": status.get("provider"),
            "model": status.get("model"),
        }

        # 全体のステータスが "completed" なら、current_step も "completed" とする
        if status.get("status") == "completed":
            response["current_step"] = "completed"
            return response

        # current_job が空文字列の場合も "loading" とする
        if not status.get("current_job"):
            response["current_step"] = "loading"
            return response

        # 有効な current_job を返す
        response["current_step"] = status.get("current_job", "unknown")
        return response
    except Exception as e:
        slogger.error(f"Error in get_current_step: {e}")
        return {
            "current_step": "error",
            "token_usage": 0,
            "token_usage_input": 0,
            "token_usage_output": 0,
            "estimated_cost": 0.0,
            "provider": None,
            "model": None,
        }


@router.delete("/admin/reports/{slug}")
async def delete_report(slug: str, api_key: str = Depends(verify_admin_api_key)) -> ORJSONResponse:
    validate_slug(slug)
    try:
        set_status(slug, ReportStatus.DELETED.value)
        return ORJSONResponse(
            content={"message": f"Report {slug} marked as deleted"},
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except ConfigFileNotFound as e:
        slogger.error(f"ConfigFileNotFound: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ConfigJSONParseError as e:
        slogger.error(f"ConfigJSONParseError: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        slogger.error(f"Exception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.patch("/admin/reports/{slug}/visibility")
async def update_report_visibility(
    slug: str, visibility_update: ReportVisibilityUpdate, api_key: str = Depends(verify_admin_api_key)
) -> dict:
    validate_slug(slug)
    try:
        visibility = update_report_visibility_state(slug, visibility_update.visibility)

        return {"success": True, "visibility": visibility}
    except ValueError as e:
        slogger.error(f"ValueError: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ConfigFileNotFound as e:
        slogger.error(f"ConfigFileNotFound: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ConfigJSONParseError as e:
        slogger.error(f"ConfigJSONParseError: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        slogger.error(f"Exception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.patch("/admin/reports/{slug}/config")
async def update_report_config_endpoint(
    slug: str, config: ReportConfigUpdate, api_key: str = Depends(verify_admin_api_key)
) -> dict:
    """レポートのメタデータ（タイトル、説明）を更新するエンドポイント

    Args:
        slug: レポートのスラッグ
        config: 更新するレポートの設定
        api_key: 管理者APIキー

    Returns:
        更新後のレポート情報
    """
    validate_slug(slug)
    try:
        # 中間ファイル（config.json）を更新
        config_repo = ConfigRepository(slug)
        is_updated = config_repo.update_json(config)
        if not is_updated:
            raise Exception(f"Failed to update config json for {slug}")

        is_aggregation_executed = execute_aggregation(slug)
        if not is_aggregation_executed:
            raise Exception(f"Failed to execute aggregation for {slug}")

        # report_status.json を更新
        updated_report = update_report_config(
            slug=slug,
            updated_config=config,
        )
        return {
            "success": True,
            "report": updated_report,
        }
    except ValueError as e:
        slogger.error(f"ValueError: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        slogger.error(f"Exception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/admin/reports/{slug}/config")
async def get_report_config_endpoint(slug: str, api_key: str = Depends(verify_admin_api_key)) -> dict:
    """レポートの設定(config.json)を取得するエンドポイント"""
    validate_slug(slug)
    try:
        config_repo = ConfigRepository(slug)
        config = config_repo.read_from_json()
        return {"config": config.model_dump()}
    except ConfigFileNotFound as e:
        slogger.error(f"ConfigFileNotFound: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ConfigJSONParseError as e:
        slogger.error(f"ConfigJSONParseError: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        slogger.error(f"Exception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/admin/reports/{slug}/cluster-labels")
async def get_clusters(slug: str, api_key: str = Depends(verify_admin_api_key)) -> dict[str, list[ClusterResponse]]:
    validate_slug(slug)
    try:
        repo = ClusterRepository(slug)
        return {
            "clusters": repo.read_from_csv(),
        }
    # FIXME: エラーハンドリングが肥大化してきた段階で、ハンドリング処理をhandler/middlewareに切り出す
    except ClusterFileNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ClusterCSVParseError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.patch("/admin/reports/{slug}/cluster-label")
async def update_cluster_label(
    slug: str, updated_cluster: ClusterUpdate, api_key: str = Depends(verify_admin_api_key)
) -> dict[str, bool]:
    validate_slug(slug)
    # FIXME: error handlingを共通化するタイミングで、error handlingを切り出す
    # issue: https://github.com/digitaldemocracy2030/kouchou-ai/issues/546
    repo = ClusterRepository(slug)
    is_csv_updated = repo.update_csv(updated_cluster)
    if not is_csv_updated:
        raise HTTPException(status_code=500, detail="意見グループの更新に失敗しました")

    # aggregation を実行
    is_aggregation_executed = execute_aggregation(slug)
    if not is_aggregation_executed:
        raise HTTPException(status_code=500, detail="意見グループ更新の集計に失敗しました")

    invalidate_report_cache(slug)

    return {"success": True}


@router.get("/admin/reports/{slug}/visualization-config")
async def get_visualization_config(slug: str, api_key: str = Depends(verify_admin_api_key)) -> dict:
    """レポートの可視化設定を取得するエンドポイント

    Args:
        slug: レポートのスラッグ
        api_key: 管理者APIキー

    Returns:
        可視化設定
    """
    validate_slug(slug)
    visualization_config_path = settings.REPORT_DIR / slug / "visualization_config.json"
    if not visualization_config_path.exists():
        return {"visualizationConfig": None}

    try:
        with open(visualization_config_path) as f:
            raw_config = json.load(f)
        validated_config = ReportDisplayConfig.model_validate(raw_config)
        return {"visualizationConfig": validated_config.model_dump(by_alias=True)}
    except Exception as e:
        slogger.error(f"Error reading visualization config: {e}")
        return {"visualizationConfig": None}


@router.patch("/admin/reports/{slug}/visualization-config")
async def update_visualization_config(
    slug: str, config: ReportDisplayConfig, api_key: str = Depends(verify_admin_api_key)
) -> dict:
    """レポートの可視化設定を更新するエンドポイント

    Args:
        slug: レポートのスラッグ
        config: 更新する可視化設定
        api_key: 管理者APIキー

    Returns:
        更新後の可視化設定
    """
    validate_slug(slug)
    try:
        report_dir = settings.REPORT_DIR / slug
        if not report_dir.exists():
            raise HTTPException(status_code=404, detail=f"Report {slug} not found")

        visualization_config_path = report_dir / "visualization_config.json"

        # snake_caseで保存（Pydanticのデフォルト）
        with open(visualization_config_path, mode="w", encoding="utf-8") as f:
            json.dump(config.model_dump(), f, ensure_ascii=False, indent=2)

        invalidate_report_cache(slug)

        return {
            "success": True,
            "visualizationConfig": config.model_dump(by_alias=True),
        }
    except HTTPException:
        raise
    except Exception as e:
        slogger.error(f"Error updating visualization config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/admin/models")
async def get_models(
    provider: str = Query(..., description="LLMプロバイダー名 (openai, azure, openrouter, gemini, local)"),
    address: str | None = Query(None, description="LocalLLM用アドレス（例: 127.0.0.1:1234）"),
    api_key: str = Depends(verify_admin_api_key),
) -> list[dict[str, str]]:
    """指定されたプロバイダーのモデルリストを取得するエンドポイント

    Args:
        provider: LLMプロバイダー名（openai, azure, openrouter, gemini, local）
        address: LocalLLM用アドレス（localプロバイダーの場合のみ使用、例: 127.0.0.1:1234）
        api_key: 管理者APIキー

    Returns:
        モデルリスト（value, labelのリスト）
    """
    try:
        models = await get_models_by_provider(provider, address)
        return models
    except ValueError as e:
        slogger.error(f"ValueError: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        slogger.error(f"Exception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/admin/environment/verify")
async def verify_api_key(
    provider: str = Query("openai"),
    api_key: str = Depends(verify_admin_api_key),
) -> dict:
    """Verify the API key for the specified provider by making a simple chat request."""

    from broadlistening.pipeline.services.llm import request_to_chat_ai

    try:
        test_messages = [
            {"role": "system", "content": "This is a test message to verify API key."},
            {"role": "user", "content": "Hello"},
        ]

        model_map = {
            "openai": "gpt-4o-mini",
            "azure": "gpt-4o-mini",
            "openrouter": "openai/gpt-4o-mini-2024-07-18",
            "gemini": "gemini-2.5-flash",
        }
        model = model_map.get(provider, "gpt-4o-mini")

        _ = request_to_chat_ai(
            messages=test_messages,
            model=model,
            provider=provider,
        )

        return {
            "success": True,
            "message": "APIキーは有効です",
            "error_detail": None,
            "error_type": None,
        }

    except openai.AuthenticationError as e:
        return {
            "success": False,
            "message": "認証エラー: APIキーが無効または期限切れです",
            "error_detail": str(e),
            "error_type": "authentication_error",
        }
    except openai.RateLimitError as e:
        error_str = str(e).lower()
        if "insufficient_quota" in error_str or "quota exceeded" in error_str:
            return {
                "success": False,
                "message": "残高不足エラー: APIキーのデポジット残高が不足しています。残高を追加してください。",
                "error_detail": str(e),
                "error_type": "insufficient_quota",
            }
        return {
            "success": False,
            "message": "レート制限エラー: APIリクエストの制限を超えました。しばらく待ってから再試行してください。",
            "error_detail": str(e),
            "error_type": "rate_limit_error",
        }
    except Exception as e:
        if google_exceptions is not None and isinstance(e, google_exceptions.Unauthenticated):
            return {
                "success": False,
                "message": "認証エラー: APIキーが無効または期限切れです",
                "error_detail": str(e),
                "error_type": "authentication_error",
            }
        if google_exceptions is not None and isinstance(e, google_exceptions.ResourceExhausted):
            return {
                "success": False,
                "message": "レート制限エラー: APIリクエストの制限を超えました。しばらく待ってから再試行してください。",
                "error_detail": str(e),
                "error_type": "rate_limit_error",
            }
        return {
            "success": False,
            "message": f"エラーが発生しました: {str(e)}",
            "error_detail": str(e),
            "error_type": "unknown_error",
        }


@router.get("/admin/llm-pricing")
async def get_llm_pricing(api_key: str = Depends(verify_admin_api_key)) -> dict:
    """LLMの価格情報を取得するエンドポイント

    Returns:
        dict: プロバイダーとモデルごとの価格情報
    """
    try:
        return LLMPricing.PRICING
    except Exception as e:
        slogger.error(f"Exception in get_llm_pricing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e
