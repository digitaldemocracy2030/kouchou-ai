"""
LLMモデルリスト取得サービス
"""

import os

import httpx
from openai import OpenAI

from src.services.model_catalog import enrich_models, models_for_provider
from src.utils.logger import setup_logger

slogger = setup_logger()


async def get_openai_models() -> list[dict]:
    return models_for_provider("openai")


async def get_azure_models() -> list[dict]:
    return models_for_provider("azure")


async def get_gemini_models() -> list[dict]:
    """Google Geminiのモデルリストを取得"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return models_for_provider("gemini")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://generativelanguage.googleapis.com/v1/models",
                params={"key": api_key},
            )

            if response.status_code != 200:
                slogger.error(f"Gemini API error: {response.status_code}")
                raise ValueError("Failed to fetch models from Gemini API")

            data = response.json()

            if not data or not isinstance(data.get("models"), list):
                slogger.error("Invalid response format from Gemini API")
                raise ValueError("Invalid API response format")

            return [
                {
                    "value": (model.get("name", "") or "").removeprefix("models/"),
                    "label": model.get("displayName", (model.get("name", "") or "").removeprefix("models/")),
                }
                for model in data["models"]
                if "generateContent" in (model.get("supportedGenerationMethods") or [])
            ]
    except Exception as e:
        slogger.error(f"Error fetching Gemini models: {e}")
        raise ValueError(f"Failed to fetch models from Gemini API: {e}") from e


async def get_openrouter_models() -> list[dict]:
    """OpenRouterのモデルリストをAPIから取得"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://openrouter.ai/api/v1/models")

            if response.status_code != 200:
                slogger.error(f"OpenRouter API error: {response.status_code}")
                raise ValueError("Failed to fetch models from OpenRouter API")

            data = response.json()

            if not data or not isinstance(data.get("data"), list):
                slogger.error("Invalid response format from OpenRouter API")
                raise ValueError("Invalid API response format")

            return [
                {
                    "value": model.get("id", ""),
                    # /models に provider は無く、name が「提供元: モデル名」の形で提供元を含む
                    "label": model.get("name") or model.get("id", ""),
                }
                for model in data["data"]
            ]
    except Exception as e:
        slogger.error(f"Error fetching OpenRouter models: {e}")
        raise ValueError(f"Failed to fetch models from OpenRouter API: {e}") from e


async def get_local_llm_models(address: str | None = None) -> list[dict]:
    """LocalLLMのモデルリストをOpenAI互換APIから取得"""
    if not address:
        address = "localhost:11434"  # Ollamaのデフォルトポート

    # パイプライン (analysis_core) と同じ規則で接続先を決め、同じ認証情報を送る
    from analysis_core.services.llm import resolve_local_llm_base_url

    base_url = resolve_local_llm_base_url(address)

    try:
        client = OpenAI(
            base_url=base_url,
            api_key=os.environ.get("LOCAL_LLM_API_KEY", "not-needed"),  # OllamaとLM Studioは認証不要
        )

        import asyncio

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, client.models.list)

        return [{"value": model.id, "label": model.id} for model in response.data]
    except Exception as e:
        slogger.error(f"Error fetching LocalLLM models: {e}")
        raise ValueError(f"Failed to fetch models from LocalLLM API: {e}") from e


async def _discover_models_by_provider(provider: str, address: str | None = None) -> list[dict]:
    """プロバイダーに応じたモデルリストを取得"""
    if provider == "openai":
        return await get_openai_models()
    elif provider == "azure":
        return await get_azure_models()
    elif provider == "openrouter":
        return await get_openrouter_models()
    elif provider == "gemini":
        return await get_gemini_models()
    elif provider == "local":
        return await get_local_llm_models(address)
    else:
        raise ValueError(f"Unknown provider: {provider}")


async def get_models_by_provider(provider: str, address: str | None = None) -> list[dict]:
    try:
        discovered = await _discover_models_by_provider(provider, address)
    except ValueError:
        if provider not in ("gemini", "openrouter"):
            raise
        # The same server catalog provides an explicit fallback, never a second
        # frontend copy. Keep the failure visible to callers.
        models = models_for_provider(provider)
        for model in models:
            model["discovery_warning"] = "最新のモデル一覧を取得できませんでした。登録済みの一覧を表示しています。"
        return models
    return enrich_models(provider, discovered)
