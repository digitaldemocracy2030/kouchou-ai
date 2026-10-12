"""Shared model metadata. Discovery does not imply application verification."""

import json
import math
import os
from copy import deepcopy
from datetime import date
from pathlib import Path

CATALOG = json.loads(Path(__file__).with_name("model_catalog.json").read_text(encoding="utf-8"))

# チャットモデルと埋め込みモデルを同じカタログで扱う。`kind` 未指定の行は従来どおり
# チャットモデルとみなす (後方互換)。
CHAT_KIND = "chat"
EMBEDDING_KIND = "embedding"


def model_kind(row: dict) -> str:
    return row.get("kind") or CHAT_KIND


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
        "kind": CHAT_KIND,
        "verified": False,
        "available": True,
        "deprecated": False,
        "price": azure_price(),
        "selection_mode": "server",
    }


def azure_embedding_model() -> dict:
    # 埋め込みも AZURE_EMBEDDING_DEPLOYMENT_NAME のサーバー設定を使う。UI からは変更しない。
    return {
        "provider": "azure",
        "value": "azure-embedding-server",
        "label": "サーバー設定を使用",
        "description": "Azure OpenAIでは、サーバーに設定された埋め込みモデルを使用します。この画面では変更できません。",
        "actual_model": os.getenv("AZURE_EMBEDDING_DEPLOYMENT_NAME") or None,
        "kind": EMBEDDING_KIND,
        "verified": False,
        "available": True,
        "deprecated": False,
        "price": None,
        "selection_mode": "server",
    }


def models_for_provider(provider: str, kind: str | None = None) -> list[dict]:
    """プロバイダーのモデル一覧を返す。

    `kind` を省略すると chat / embedding を両方含む全モデルを返す。各行には必ず
    `kind` が入る (未指定のカタログ行は chat 扱い)。`kind` を指定するとその種別だけに絞る。
    """
    if provider == "azure":
        rows = [azure_model(), azure_embedding_model()]
    else:
        rows = deepcopy([row for row in CATALOG if row["provider"] == provider])
        for row in rows:
            row["kind"] = model_kind(row)
            row["price"] = price_for_model(provider, row["value"])
    if kind is not None:
        rows = [row for row in rows if model_kind(row) == kind]
    return rows


def enrich_models(provider: str, discovered: list[dict], kind: str = CHAT_KIND) -> list[dict]:
    """Preserve catalog lifecycle/verification, append discovered unverified models.

    `discovered` はライブ探索で得たチャットモデル一覧を想定し、カタログに無いものは
    `kind` 種別 (既定 chat) の未検証モデルとして追加する。カタログ側の embedding 行は
    そのまま温存されるので、呼び出し側 (フロント) が種別で振り分けられる。
    """
    models = {row["value"]: row for row in models_for_provider(provider)}
    for item in discovered:
        value = normalize_model(provider, item.get("value") or "")
        if value and value not in models:
            models[value] = {
                "provider": provider,
                "value": value,
                "label": item.get("label") or value,
                "description": "",
                "kind": kind,
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
