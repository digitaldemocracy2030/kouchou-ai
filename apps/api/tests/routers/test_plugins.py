"""/admin/plugins の応答に、manifest.to_dict() の項目が欠けずに載ることの回帰テスト"""

import polars as pl
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.plugins.base import InputPlugin, PluginManifest
from src.plugins.registry import PluginRegistry
from src.routers import plugins
from src.routers.admin_report import verify_admin_api_key

PLACEHOLDER = "https://example.com/watch?v=..."


class _PlaceholderPlugin(InputPlugin):
    manifest = PluginManifest(
        id="placeholder-test",
        name="Placeholder Test",
        description="placeholder を持つテスト用プラグイン",
        placeholder=PLACEHOLDER,
    )

    def fetch_data(self, source, **options):
        return pl.DataFrame()


@pytest.fixture
def registered_plugin():
    # 他のテスト（レジストリのテスト）が clear() するので、登録状態を退避して戻す
    saved_plugins = dict(PluginRegistry._plugins)
    saved_instances = dict(PluginRegistry._instances)
    PluginRegistry.register(_PlaceholderPlugin)
    try:
        yield _PlaceholderPlugin.manifest
    finally:
        PluginRegistry._plugins.clear()
        PluginRegistry._plugins.update(saved_plugins)
        PluginRegistry._instances.clear()
        PluginRegistry._instances.update(saved_instances)


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(plugins.router)

    async def override_verify_admin_api_key():
        return "test-api-key"

    app.dependency_overrides[verify_admin_api_key] = override_verify_admin_api_key
    return TestClient(app)


def _find(plugins_json: list[dict], plugin_id: str) -> dict:
    return next(p for p in plugins_json if p["id"] == plugin_id)


def test_list_plugins_includes_placeholder_and_is_enabled(client, registered_plugin):
    response = client.get("/admin/plugins")

    assert response.status_code == 200
    plugin = _find(response.json()["plugins"], registered_plugin.id)
    assert plugin["placeholder"] == PLACEHOLDER
    assert plugin["isEnabled"] is registered_plugin.is_enabled()


def test_get_plugin_includes_placeholder_and_is_enabled(client, registered_plugin):
    response = client.get(f"/admin/plugins/{registered_plugin.id}")

    assert response.status_code == 200
    plugin = response.json()
    assert plugin["placeholder"] == PLACEHOLDER
    assert plugin["isEnabled"] is registered_plugin.is_enabled()


def test_response_keys_match_manifest_to_dict(client, registered_plugin):
    """to_dict に項目を足したとき、応答モデルの更新漏れで黙って捨てられないようにする"""
    expected_keys = set(registered_plugin.to_dict().keys())

    listed = _find(client.get("/admin/plugins").json()["plugins"], registered_plugin.id)
    single = client.get(f"/admin/plugins/{registered_plugin.id}").json()

    assert set(listed.keys()) == expected_keys
    assert set(single.keys()) == expected_keys
