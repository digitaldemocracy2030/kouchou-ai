import json
import os

import openai
from broadlistening.pipeline.services.llm import LLM_PROVIDERS, get_available_models
from fastapi import APIRouter, Depends, HTTPException, Query, Security
from fastapi.responses import FileResponse, ORJSONResponse
from fastapi.security.api_key import APIKeyHeader

from src.config import settings
from src.schemas.admin_report import ReportInput, ReportMetadataUpdate
from src.schemas.report import Report, ReportStatus
from src.services.report_launcher import launch_report_generation
from src.services.report_status import (
    load_status_as_reports,
    set_status,
    toggle_report_public_state,
    update_report_metadata,
)
from src.utils.logger import setup_logger

slogger = setup_logger()
router = APIRouter()

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


async def verify_admin_api_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


@router.get("/admin/reports")
async def get_reports(api_key: str = Depends(verify_admin_api_key)) -> list[Report]:
    return load_status_as_reports()


@router.post("/admin/reports", status_code=202)
async def create_report(report: ReportInput, api_key: str = Depends(verify_admin_api_key)) -> ORJSONResponse:
    try:
        launch_report_generation(report)
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


@router.get("/admin/comments/{slug}/csv")
async def download_comments_csv(slug: str, api_key: str = Depends(verify_admin_api_key)) -> FileResponse:
    csv_path = settings.REPORT_DIR / slug / "final_result_with_comments.csv"
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="CSV file not found")
    return FileResponse(path=str(csv_path), media_type="text/csv", filename=f"kouchou_{slug}.csv")


@router.get("/admin/reports/{slug}/status/step-json", dependencies=[Depends(verify_admin_api_key)])
async def get_current_step(slug: str) -> dict:
    status_file = settings.REPORT_DIR / slug / "hierarchical_status.json"
    try:
        # ステータスファイルが存在しない場合は "loading" を返す
        if not status_file.exists():
            return {"current_step": "loading"}

        with open(status_file) as f:
            status = json.load(f)

        # error キーが存在する場合はエラーとみなす
        if "error" in status:
            return {"current_step": "error"}

        # 全体のステータスが "completed" なら、current_step も "completed" とする
        if status.get("status") == "completed":
            return {"current_step": "completed"}

        # current_job キーが存在しない場合も "loading" とみなす
        if "current_job" not in status:
            return {"current_step": "loading"}

        # current_job が空文字列の場合も "loading" とする
        if not status.get("current_job"):
            return {"current_step": "loading"}

        # 有効な current_job を返す
        return {"current_step": status.get("current_job", "unknown")}
    except Exception:
        return {"current_step": "error"}


@router.delete("/admin/reports/{slug}")
async def delete_report(slug: str, api_key: str = Depends(verify_admin_api_key)) -> ORJSONResponse:
    try:
        set_status(slug, ReportStatus.DELETED.value)
        return ORJSONResponse(
            content={"message": f"Report {slug} marked as deleted"},
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except ValueError as e:
        slogger.error(f"ValueError: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        slogger.error(f"Exception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.patch("/admin/reports/{slug}/visibility")
async def update_report_visibility(slug: str, api_key: str = Depends(verify_admin_api_key)) -> dict:
    try:
        is_public = toggle_report_public_state(slug)

        return {"success": True, "isPublic": is_public}
    except ValueError as e:
        slogger.error(f"ValueError: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        slogger.error(f"Exception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.patch("/admin/reports/{slug}/metadata")
async def update_report_metadata_endpoint(
    slug: str, metadata: ReportMetadataUpdate, api_key: str = Depends(verify_admin_api_key)
) -> dict:
    """レポートのメタデータ（タイトル、説明）を更新するエンドポイント

    Args:
        slug: レポートのスラッグ
        metadata: 更新するメタデータ
        api_key: 管理者APIキー

    Returns:
        更新後のレポート情報
    """
    try:
        updated_report = update_report_metadata(
            slug=slug,
            title=metadata.title or "",
            description=metadata.description or "",
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


@router.get("/admin/models")
async def get_models(
    provider: str = Query(..., description="LLMプロバイダー名"),
    address: str | None = Query(None, description="LocalLLM用アドレス（例: 127.0.0.1:1234）"),
    api_key: str = Depends(verify_admin_api_key),
) -> list[dict[str, str]]:
    """指定されたプロバイダーのモデルリストを取得するエンドポイント

    Args:
        provider: LLMプロバイダー名（openai, azure, openrouter, local）
        address: LocalLLM用アドレス（localプロバイダーの場合のみ使用、例: 127.0.0.1:1234）
        api_key: 管理者APIキー

    Returns:
        モデルリスト（value, labelのリスト）
    """
    try:
        models_dict = get_available_models(provider, address)
        return models_dict["available"]
    except ValueError as e:
        slogger.error(f"ValueError: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        slogger.error(f"Exception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/admin/environment/verify-chatgpt")
async def verify_chatgpt_api_key(api_key: str = Depends(verify_admin_api_key)) -> dict:
    """Verify the ChatGPT API key configuration by making a simple chat request.

    Checks both OpenAI and Azure OpenAI configurations based on the USE_AZURE setting.
    Makes a simple chat request to verify the API key is valid and properly configured.

    Returns:
        dict: Status of the verification and any error messages in Japanese
    """
    from broadlistening.pipeline.services.llm import request_to_chat_openai

    try:
        use_azure = os.getenv("USE_AZURE", "false").lower() == "true"

        test_messages = [
            {"role": "system", "content": "This is a test message to verify API key."},
            {"role": "user", "content": "Hello"},
        ]

        _ = request_to_chat_openai(
            messages=test_messages,
            model="gpt-4o-mini",
        )

        return {
            "success": True,
            "message": "ChatGPT API キーは有効です",
            "error_detail": None,
            "error_type": None,
            "use_azure": use_azure,
        }

    except openai.AuthenticationError as e:
        return {
            "success": False,
            "message": "認証エラー: APIキーが無効または期限切れです",
            "error_detail": str(e),
            "error_type": "authentication_error",
            "use_azure": use_azure,
        }
    except openai.RateLimitError as e:
        error_str = str(e).lower()
        if "insufficient_quota" in error_str or "quota exceeded" in error_str:
            return {
                "success": False,
                "message": "残高不足エラー: APIキーのデポジット残高が不足しています。残高を追加してください。",
                "error_detail": str(e),
                "error_type": "insufficient_quota",
                "use_azure": use_azure,
            }
        return {
            "success": False,
            "message": "レート制限エラー: APIリクエストの制限を超えました。しばらく待ってから再試行してください。",
            "error_detail": str(e),
            "error_type": "rate_limit_error",
            "use_azure": use_azure,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"エラーが発生しました: {str(e)}",
            "error_detail": str(e),
            "error_type": "unknown_error",
            "use_azure": use_azure,
        }


@router.get("/admin/environment/verify-llm-provider")
async def verify_llm_provider(provider: str | None = None, api_key: str = Depends(verify_admin_api_key)):
    """LLM プロバイダーの接続を検証するエンドポイント

    Args:
        provider: 検証するプロバイダー（指定がない場合は現在の設定を使用）

    Returns:
        dict: 検証結果、利用可能なモデル、エラーメッセージなど
    """
    try:
        from broadlistening.pipeline.services.llm import DEFAULT_PROVIDER

        current_provider = DEFAULT_PROVIDER
        provider_to_check = provider or current_provider

        if provider_to_check not in LLM_PROVIDERS:
            return {
                "success": False,
                "message": f"Invalid provider: {provider_to_check}",
                "current_provider": current_provider,
                "available_models": [],
                "supported_models": [],
            }

        models = get_available_models(provider_to_check)

        return {
            "success": True,
            "message": f"{provider_to_check.capitalize()} connection verified successfully",
            "current_provider": current_provider,
            "available_models": models["available"],
            "supported_models": models["supported"],
        }

    except openai.AuthenticationError as e:
        return {
            "success": False,
            "message": f"Authentication failed: {str(e)}",
            "current_provider": provider or DEFAULT_PROVIDER,
            "available_models": [],
            "supported_models": [],
        }
    except openai.RateLimitError as e:
        error_str = str(e).lower()
        if "insufficient_quota" in error_str or "quota exceeded" in error_str:
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "error_type": "insufficient_quota",
                "current_provider": provider or DEFAULT_PROVIDER,
                "available_models": [],
                "supported_models": [],
            }
        return {
            "success": False,
            "message": f"Rate limit exceeded: {str(e)}",
            "current_provider": provider or DEFAULT_PROVIDER,
            "available_models": [],
            "supported_models": [],
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "current_provider": provider or DEFAULT_PROVIDER,
            "available_models": [],
            "supported_models": [],
        }
