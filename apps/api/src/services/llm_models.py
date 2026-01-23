"""
LLMモデルリスト取得サービス
"""

import os

import httpx
from openai import OpenAI

from src.utils.logger import setup_logger

slogger = setup_logger()


class ModelOption:
    """モデルオプション"""

    def __init__(self, value: str, label: str):
        self.value = value
        self.label = label

    def to_dict(self) -> dict[str, str]:
        return {"value": self.value, "label": self.label}


OPENAI_MODELS = [
    ModelOption("gpt-4o-mini", "GPT-4o mini"),
    ModelOption("gpt-4o", "GPT-4o"),
    ModelOption("o3-mini", "o3-mini"),
]


GEMINI_MODELS = [
    ModelOption("gemini-2.5-flash", "Gemini 2.5 Flash"),
    ModelOption("gemini-1.5-flash", "Gemini 1.5 Flash"),
    ModelOption("gemini-1.5-pro", "Gemini 1.5 Pro"),
]


async def get_openai_models() -> list[dict[str, str]]:
    """OpenAIのモデルリストを取得"""
    return [model.to_dict() for model in OPENAI_MODELS]


async def get_azure_models() -> list[dict[str, str]]:
    """Azureのモデルリストを取得（OpenAIと同じ）"""
    return [model.to_dict() for model in OPENAI_MODELS]


async def get_gemini_models() -> list[dict[str, str]]:
    """Google Geminiのモデルリストを取得"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return [model.to_dict() for model in GEMINI_MODELS]

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


async def get_openrouter_models() -> list[dict[str, str]]:
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
                    "label": f"{model.get('provider', 'unknown')} - {model.get('name', model.get('id', 'unknown'))}",
                }
                for model in data["data"]
            ]
    except Exception as e:
        slogger.error(f"Error fetching OpenRouter models: {e}")
        raise ValueError(f"Failed to fetch models from OpenRouter API: {e}") from e


async def get_local_llm_models(address: str | None = None) -> list[dict[str, str]]:
    """LocalLLMのモデルリストをOpenAI互換APIから取得"""
    if not address:
        address = "localhost:11434"  # Ollamaのデフォルトポート

    if ":" in address:
        host, port = address.split(":")
        base_url = f"http://{host}:{port}/v1"
    else:
        base_url = f"http://{address}/v1"

    try:
        client = OpenAI(
            base_url=base_url,
            api_key="not-needed",  # OllamaとLM Studioは認証不要
        )

        import asyncio

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, client.models.list)

        return [{"value": model.id, "label": model.id} for model in response.data]
    except Exception as e:
        slogger.error(f"Error fetching LocalLLM models: {e}")
        raise ValueError(f"Failed to fetch models from LocalLLM API: {e}") from e


async def get_models_by_provider(provider: str, address: str | None = None) -> list[dict[str, str]]:
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
