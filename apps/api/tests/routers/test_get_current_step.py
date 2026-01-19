import json
from unittest.mock import mock_open, patch

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from src.routers.admin_report import router, verify_admin_api_key


@pytest.fixture
def test_slug():
    """テスト用のスラグを提供するフィクスチャ"""
    return "test-slug"


@pytest.fixture
async def app():
    """テスト用のFastAPIアプリケーションを作成するフィクスチャ"""
    app = FastAPI()
    app.include_router(router)

    # 認証をバイパスするためのオーバーライド
    async def override_verify_admin_api_key():
        return "test-api-key"

    app.dependency_overrides[verify_admin_api_key] = override_verify_admin_api_key
    return app


@pytest.fixture
async def async_client(app):
    """非同期テスト用のクライアントを作成するフィクスチャ"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_get_current_step_with_token_usage(async_client, test_slug):
    """get_current_stepエンドポイントがトークン使用量情報を返すことをテスト"""
    status_data = {
        "status": "in_progress",
        "current_job": "extraction",
        "total_token_usage": 1500,
        "token_usage_input": 1000,
        "token_usage_output": 500,
    }

    with patch("builtins.open", mock_open(read_data=json.dumps(status_data))):
        with patch("os.path.exists", return_value=True):
            response = await async_client.get(f"/admin/reports/{test_slug}/status/step-json")
            assert response.status_code == 200
            data = response.json()
            assert data["current_step"] == "extraction"
            assert data["token_usage"] == 1500
            assert data["token_usage_input"] == 1000
            assert data["token_usage_output"] == 500


@pytest.mark.asyncio
async def test_get_current_step_with_no_token_usage(async_client, test_slug):
    """get_current_stepエンドポイントがトークン使用量情報がない場合でも適切に動作することをテスト"""
    status_data = {"status": "in_progress", "current_job": "extraction"}

    with patch("builtins.open", mock_open(read_data=json.dumps(status_data))):
        with patch("os.path.exists", return_value=True):
            response = await async_client.get(f"/admin/reports/{test_slug}/status/step-json")
            assert response.status_code == 200
            data = response.json()
            assert data["current_step"] == "extraction"
            assert data["token_usage"] == 0
            assert data["token_usage_input"] == 0
            assert data["token_usage_output"] == 0


@pytest.mark.asyncio
async def test_get_current_step_with_error(async_client, test_slug):
    """get_current_stepエンドポイントがエラー時に適切なレスポンスを返すことをテスト"""
    status_data = {
        "status": "error",
        "error": "Test error",
        "total_token_usage": 100,
        "token_usage_input": 70,
        "token_usage_output": 30,
    }

    with patch("builtins.open", mock_open(read_data=json.dumps(status_data))):
        with patch("os.path.exists", return_value=True):
            response = await async_client.get(f"/admin/reports/{test_slug}/status/step-json")
            assert response.status_code == 200
            data = response.json()
            assert data["current_step"] == "error"
            assert data["token_usage"] == 100
            assert data["token_usage_input"] == 70
            assert data["token_usage_output"] == 30


@pytest.mark.asyncio
async def test_get_current_step_file_not_found(async_client, test_slug):
    """get_current_stepエンドポイントがファイルが存在しない場合に適切なレスポンスを返すことをテスト"""
    with patch("os.path.exists", return_value=False):
        response = await async_client.get(f"/admin/reports/{test_slug}/status/step-json")
        assert response.status_code == 200
        data = response.json()
        assert data["current_step"] == "error"
        assert data["token_usage"] == 0
        assert data["token_usage_input"] == 0
        assert data["token_usage_output"] == 0


@pytest.mark.asyncio
async def test_get_current_step_exception(async_client, test_slug):
    """get_current_stepエンドポイントが例外発生時に適切なレスポンスを返すことをテスト"""
    with patch("os.path.exists", side_effect=Exception("Test exception")):
        response = await async_client.get(f"/admin/reports/{test_slug}/status/step-json")
        assert response.status_code == 200
        data = response.json()
        assert data["current_step"] == "error"
        assert data["token_usage"] == 0
        assert data["token_usage_input"] == 0
        assert data["token_usage_output"] == 0
