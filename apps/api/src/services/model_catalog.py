"""Shared model metadata. Discovery does not imply application verification."""

import json
import math
import os
from copy import deepcopy
from datetime import date
from pathlib import Path

CATALOG = json.loads(Path(__file__).with_name("model_catalog.json").read_text(encoding="utf-8"))


def normalize_model(provider: str, model: str) -> str:
    model = model.strip()
    if provider == "gemini" and "models/" in model:
        model = model.rsplit("models/", 1)[-1]
    return model


def azure_price() -> dict | None:
    if not os.getenv("AZURE_CHATCOMPLETION_MODEL_NAME"):
        return None
    try:
        prices = {key: float(os.environ[f"AZURE_CHATCOMPLETION_{key.upper()}_PRICE"]) for key in ("input", "output")}
    except (ValueError, KeyError):
        return None
    if not all(math.isfinite(value) and value >= 0 for value in prices.values()):
        return None
    return {
        **prices,
        "source": "server configuration",
        "checked_at": None,
        "conditions": "サーバー管理者が設定したAzureのテキスト単価。",
    }


def azure_model() -> dict:
    # The request still uses AZURE_CHATCOMPLETION_DEPLOYMENT_NAME. Metadata is
    # explicit and never inferred from the old, ignored UI model selection.
    return {
        "provider": "azure",
        "value": "azure-server",
        "label": "サーバー設定を使用",
        "description": "Azure OpenAIでは、サーバーに設定されたモデルを使用します。この画面では変更できません。",
        "actual_model": os.getenv("AZURE_CHATCOMPLETION_MODEL_NAME") or None,
        "verified": False,
        "available": True,
        "deprecated": False,
        "price": azure_price(),
        "selection_mode": "server",
    }


def models_for_provider(provider: str) -> list[dict]:
    if provider == "azure":
        return [azure_model()]
    rows = deepcopy([row for row in CATALOG if row["provider"] == provider])
    for row in rows:
        row["price"] = price_for_model(provider, row["value"])
    return rows


def enrich_models(provider: str, discovered: list[dict]) -> list[dict]:
    """Preserve catalog lifecycle/verification, append discovered unverified models."""
    models = {row["value"]: row for row in models_for_provider(provider)}
    for item in discovered:
        value = normalize_model(provider, item.get("value") or "")
        if value and value not in models:
            models[value] = {
                "provider": provider,
                "value": value,
                "label": item.get("label") or value,
                "description": "",
                "verified": False,
                "available": True,
                "deprecated": False,
                "price": None,
            }
    return list(models.values())


def price_for_model(provider: str, model: str) -> dict | None:
    # Azure rates depend on the deployment contract/region, not OpenAI rates.
    if provider == "azure":
        return azure_price()
    row = next(
        (r for r in CATALOG if r["provider"] == provider and r["value"] == normalize_model(provider, model)), None
    )
    price = row.get("price") if row else None
    if price and price.get("valid_until") and date.today().isoformat() > price["valid_until"]:
        return None
    return price


def pricing_table() -> dict:
    result = {provider: {} for provider in ("openai", "azure", "gemini", "openrouter", "local")}
    result["azure"]["azure-server"] = azure_price()
    for row in CATALOG:
        result[row["provider"]][row["value"]] = price_for_model(row["provider"], row["value"])
    return result
