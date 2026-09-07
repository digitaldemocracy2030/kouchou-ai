from unittest.mock import AsyncMock, patch

import pytest

from src.services.llm_models import get_models_by_provider
from src.services.llm_pricing import LLMPricing
from src.services.model_catalog import CATALOG, enrich_models, models_for_provider, price_for_model


def test_requested_models_are_selectable_but_unverified():
    for provider, ids in (
        ("openai", ["gpt-5.6-terra", "gpt-5.6-luna"]),
        ("gemini", ["gemini-3.8-flash", "gemini-3.5-flash-lite"]),
    ):
        for model in ids:
            row = next(r for r in models_for_provider(provider) if r["value"] == model)
            assert row["available"] is True
            assert row["verified"] is False
            assert row["unverified_label"] == "動作未確認"
            assert row["verification_issue"]
            assert row["price"]["source"]


def test_discovery_preserves_lifecycle():
    rows = enrich_models(
        "gemini", [{"value": "models/gemini-1.5-pro", "label": "old"}, {"value": "models/new-model", "label": "New"}]
    )
    old = next(r for r in rows if r["value"] == "gemini-1.5-pro")
    new = next(r for r in rows if r["value"] == "new-model")
    assert old["available"] is False
    assert old["deprecated"] is True
    assert new["available"] is True
    assert new["verified"] is False
    assert new["price"] is None


@pytest.mark.asyncio
async def test_discovery_failure_returns_catalog_with_warning():
    with patch(
        "src.services.llm_models._discover_models_by_provider", new=AsyncMock(side_effect=ValueError("offline"))
    ):
        rows = await get_models_by_provider("gemini")
    assert any(r["value"] == "gemini-3.8-flash" for r in rows)
    assert all(r["discovery_warning"] for r in rows)


def test_normalized_price_and_unknown_are_distinct():
    assert LLMPricing.calculate_cost("gemini", "models/gemini-2.5-flash", 1000, 1000) == LLMPricing.calculate_cost(
        "gemini", "gemini-2.5-flash", 1000, 1000
    )
    assert LLMPricing.calculate_cost("openai", "unknown", 1000, 1000) is None
    assert LLMPricing.calculate_cost("openai", "gpt-4o", 0, 0) == 0
    assert LLMPricing.format_cost(None) == "料金不明"


def test_azure_ignores_ui_model_for_pricing(monkeypatch):
    monkeypatch.setenv("AZURE_CHATCOMPLETION_MODEL_NAME", "custom-model")
    row = models_for_provider("azure")[0]
    assert row["actual_model"] == "custom-model"
    assert row["selection_mode"] == "server"
    assert row["price"] is None
    assert LLMPricing.calculate_cost("azure", "gpt-4o", 1000, 1000) is None


def test_catalog_has_unique_ids_and_verification_evidence():
    assert len(CATALOG) == len({(r["provider"], r["value"]) for r in CATALOG})
    assert all(not r["verified"] or r.get("verification_source") for r in CATALOG)


def test_expired_price_is_unknown(monkeypatch):
    monkeypatch.setattr(
        "src.services.model_catalog.CATALOG",
        [{"provider": "test", "value": "old", "price": {"input": 1, "output": 2, "valid_until": "2000-01-01"}}],
    )
    assert price_for_model("test", "old") is None
    assert LLMPricing.calculate_cost("test", "old", 1000, 1000) is None


def test_api_delivers_verification_and_nullable_price(client):
    from src.routers.admin_report import verify_admin_api_key

    client.app.dependency_overrides[verify_admin_api_key] = lambda: "test"
    try:
        response = client.get("/admin/models?provider=openai")
        assert response.status_code == 200
        row = next(r for r in response.json() if r["value"] == "gpt-5.6-terra")
        assert row["verified"] is False
        assert row["available"] is True
        assert row["price"]["input"] == 2
        assert client.get("/admin/llm-pricing").json()["azure"]["azure-server"] is None
    finally:
        client.app.dependency_overrides.pop(verify_admin_api_key, None)


def test_azure_explicit_prices(monkeypatch):
    monkeypatch.setenv("AZURE_CHATCOMPLETION_MODEL_NAME", "custom-model")
    monkeypatch.setenv("AZURE_CHATCOMPLETION_INPUT_PRICE", "0.5")
    monkeypatch.setenv("AZURE_CHATCOMPLETION_OUTPUT_PRICE", "2")
    assert LLMPricing.calculate_cost("azure", "ignored-ui-model", 1000, 1000) == 0.0025
    monkeypatch.setenv("AZURE_CHATCOMPLETION_INPUT_PRICE", "NaN")
    assert LLMPricing.calculate_cost("azure", "ignored-ui-model", 1000, 1000) is None


def test_report_status_persists_unknown_cost(monkeypatch):
    from src.services import report_status

    state = {"test": {}}
    monkeypatch.setattr(report_status, "_report_status", state)
    monkeypatch.setattr(report_status, "save_status", lambda: None)
    report_status.update_token_usage("test", 20, 10, 10, "new-provider", "new-model")
    assert state["test"]["estimated_cost"] is None
