import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.routers.admin_report import router, verify_admin_api_key


@pytest.fixture
def test_slug():
    """テスト用のスラグを提供するフィクスチャ"""
    return "test-slug"


@pytest_asyncio.fixture
async def app():
    """テスト用のFastAPIアプリケーションを作成するフィクスチャ"""
    app = FastAPI()
    app.include_router(router)

    # 認証をバイパスするためのオーバーライド
    async def override_verify_admin_api_key():
        return "test-api-key"

    app.dependency_overrides[verify_admin_api_key] = override_verify_admin_api_key
    return app


@pytest_asyncio.fixture
async def async_client(app):
    """非同期テスト用のクライアントを作成するフィクスチャ"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def create_mock_path(exists: bool, read_data: str | None = None):
    """モックPathオブジェクトを作成するヘルパー"""
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = exists
    if read_data is not None:
        mock_path.__truediv__ = lambda self, other: mock_path
        mock_open = MagicMock()
        mock_open.__enter__ = MagicMock(return_value=MagicMock(read=lambda: read_data))
        mock_open.__exit__ = MagicMock(return_value=False)
    return mock_path


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

    # Mock the Path operations
    mock_status_file = MagicMock(spec=Path)
    mock_status_file.exists.return_value = True

    with patch("src.routers.admin_report.settings") as mock_settings:
        mock_settings.REPORT_DIR.__truediv__ = MagicMock(return_value=MagicMock())
        mock_settings.REPORT_DIR.__truediv__.return_value.__truediv__ = MagicMock(return_value=mock_status_file)
        with patch("builtins.open", return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=lambda: json.dumps(status_data))), __exit__=MagicMock(return_value=False))):
            with patch("json.load", return_value=status_data):
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

    mock_status_file = MagicMock(spec=Path)
    mock_status_file.exists.return_value = True

    with patch("src.routers.admin_report.settings") as mock_settings:
        mock_settings.REPORT_DIR.__truediv__ = MagicMock(return_value=MagicMock())
        mock_settings.REPORT_DIR.__truediv__.return_value.__truediv__ = MagicMock(return_value=mock_status_file)
        with patch("builtins.open", return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=lambda: json.dumps(status_data))), __exit__=MagicMock(return_value=False))):
            with patch("json.load", return_value=status_data):
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
        "current_job": "error",
        "total_token_usage": 100,
        "token_usage_input": 70,
        "token_usage_output": 30,
    }

    mock_status_file = MagicMock(spec=Path)
    mock_status_file.exists.return_value = True

    with patch("src.routers.admin_report.settings") as mock_settings:
        mock_settings.REPORT_DIR.__truediv__ = MagicMock(return_value=MagicMock())
        mock_settings.REPORT_DIR.__truediv__.return_value.__truediv__ = MagicMock(return_value=mock_status_file)
        with patch("builtins.open", return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=lambda: json.dumps(status_data))), __exit__=MagicMock(return_value=False))):
            with patch("json.load", return_value=status_data):
                response = await async_client.get(f"/admin/reports/{test_slug}/status/step-json")
                assert response.status_code == 200
                data = response.json()
                # status が error の場合、current_job も error なので "error" が返る
                assert data["current_step"] == "error"
                assert data["token_usage"] == 100
                assert data["token_usage_input"] == 70
                assert data["token_usage_output"] == 30


@pytest.mark.asyncio
async def test_get_current_step_file_not_found(async_client, test_slug):
    """get_current_stepエンドポイントがファイルが存在しない場合に適切なレスポンスを返すことをテスト"""
    mock_status_file = MagicMock(spec=Path)
    mock_status_file.exists.return_value = False

    with patch("src.routers.admin_report.settings") as mock_settings:
        mock_settings.REPORT_DIR.__truediv__ = MagicMock(return_value=MagicMock())
        mock_settings.REPORT_DIR.__truediv__.return_value.__truediv__ = MagicMock(return_value=mock_status_file)
        response = await async_client.get(f"/admin/reports/{test_slug}/status/step-json")
        assert response.status_code == 200
        data = response.json()
        # ファイルが存在しない場合は "loading" を返す
        assert data["current_step"] == "loading"


@pytest.mark.asyncio
async def test_get_current_step_exception(async_client, test_slug):
    """get_current_stepエンドポイントが例外発生時に適切なレスポンスを返すことをテスト"""
    mock_status_file = MagicMock(spec=Path)
    mock_status_file.exists.side_effect = Exception("Test exception")

    with patch("src.routers.admin_report.settings") as mock_settings:
        mock_settings.REPORT_DIR.__truediv__ = MagicMock(return_value=MagicMock())
        mock_settings.REPORT_DIR.__truediv__.return_value.__truediv__ = MagicMock(return_value=mock_status_file)
        response = await async_client.get(f"/admin/reports/{test_slug}/status/step-json")
        assert response.status_code == 200
        data = response.json()
        assert data["current_step"] == "error"
        assert data["token_usage"] == 0
        assert data["token_usage_input"] == 0
        assert data["token_usage_output"] == 0
