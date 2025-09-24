import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.routers.admin_report import router, verify_admin_api_key
from src.schemas.report import ReportVisibility


@pytest.fixture
def temp_status_file():
    """テスト用の一時的なステータスファイルを作成するフィクスチャ"""
    # 一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        # テスト用のステータスファイルパスを設定
        temp_status_file = Path(temp_dir) / "test_report_status.json"

        # テスト用のデータを作成
        test_data = {
            "test-slug": {
                "slug": "test-slug",
                "status": "ready",
                "title": "テストタイトル",
                "description": "テスト説明",
                "is_pubcom": True,
                "visibility": ReportVisibility.UNLISTED.value,
                "created_at": "2025-05-13T07:56:58.405239+00:00",
            }
        }

        # テスト用のデータをファイルに書き込む
        with open(temp_status_file, "w") as f:
            json.dump(test_data, f)

        # テスト用のパッチを適用
        with patch("src.services.report_status.STATE_FILE", temp_status_file):
            yield temp_status_file

            # テスト後にファイルを削除（tempfileが自動的に行うが念のため）
            if temp_status_file.exists():
                os.unlink(temp_status_file)


@pytest.fixture
def app():
    """テスト用のFastAPIアプリケーションを作成するフィクスチャ"""
    app = FastAPI()
    app.include_router(router)

    # 認証をバイパスするためのオーバーライド
    async def override_verify_admin_api_key():
        return "test-api-key"

    app.dependency_overrides[verify_admin_api_key] = override_verify_admin_api_key
    return app


@pytest.fixture
def client(app):
    """テスト用のクライアントを作成するフィクスチャ"""
    return TestClient(app)


@pytest.fixture
def app():
    """テスト用のFastAPIアプリケーションを作成するフィクスチャ"""
    app = FastAPI()
    app.include_router(router)

    # 認証をバイパスするためのオーバーライド
    async def override_verify_admin_api_key():
        return "test-api-key"

    app.dependency_overrides[verify_admin_api_key] = override_verify_admin_api_key
    return app

class TestUpdateReportVisibility:
    """update_report_visibilityエンドポイントのテスト"""

    def test_update_report_visibility_success(self, client):
        """正常系：有効なスラッグと可視性で更新が成功するケース"""
        # update_report_visibility_stateをモック化
        with patch("src.routers.admin_report.update_report_visibility_state") as mock_toggle:
            # モック関数の戻り値を設定
            mock_toggle.return_value = ReportVisibility.PUBLIC.value

            # エンドポイントにリクエストを送信
            response = client.patch(
                "/admin/reports/test-slug/visibility",
                json={"visibility": ReportVisibility.PUBLIC.value},
                headers={"x-api-key": "test-api-key"},
            )

            # レスポンスを検証
            assert response.status_code == 200
            assert response.json() == {"success": True, "visibility": ReportVisibility.PUBLIC.value}

            # モック関数が正しく呼び出されたことを確認
            mock_toggle.assert_called_once_with("test-slug", ReportVisibility.PUBLIC)

    def test_update_report_visibility_not_found(self, client):
        """異常系：存在しないスラッグで404エラーが発生するケース"""
        # update_report_visibility_stateをモック化してValueErrorを発生させる
        with patch("src.routers.admin_report.update_report_visibility_state") as mock_toggle:
            mock_toggle.side_effect = ValueError("slug non-existent-slug not found in report status")
            # 存在しないスラッグでリクエストを送信
            response = client.patch(
                "/admin/reports/non-existent-slug/visibility",
                json={"visibility": ReportVisibility.PUBLIC.value},
                headers={"x-api-key": "test-api-key"},
            )

            # レスポンスを検証
            assert response.status_code == 404
            assert "not found in report status" in response.json()["detail"]

    def test_update_report_visibility_unauthorized(self, client, app):
        """認証エラー：無効なAPIキーで401エラーが発生するケース"""
        # 依存関係のオーバーライドを元に戻す
        app.dependency_overrides = {}

        # 無効なAPIキーでリクエストを送信
        response = client.patch(
            "/admin/reports/test-slug/visibility",
            json={"visibility": ReportVisibility.PUBLIC.value},
            headers={"x-api-key": "invalid-api-key"},
        )

        # レスポンスを検証
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"

class TestVerifyApiKey:
    def test_verify_api_key_openai(self, client):
        with patch("broadlistening.pipeline.services.llm.request_to_chat_ai") as mock_request:
            mock_request.return_value = ("ok", 0, 0, 0)

            response = client.get("/admin/environment/verify?provider=openai", headers={"x-api-key": "test-api-key"})
            assert response.status_code == 200
            assert response.json()["success"] is True

            mock_request.assert_called_once()
            _, kwargs = mock_request.call_args
            assert kwargs["provider"] == "openai"
            assert kwargs["model"] == "gpt-4o-mini"

    def test_verify_api_key_gemini(self, client):
        with patch("broadlistening.pipeline.services.llm.request_to_chat_ai") as mock_request:
            mock_request.return_value = ("ok", 0, 0, 0)

            response = client.get("/admin/environment/verify?provider=gemini", headers={"x-api-key": "test-api-key"})
            assert response.status_code == 200
            assert response.json()["success"] is True

            mock_request.assert_called_once()
            _, kwargs = mock_request.call_args
            assert kwargs["provider"] == "gemini"
            assert kwargs["model"] == "gemini-2.5-flash"
