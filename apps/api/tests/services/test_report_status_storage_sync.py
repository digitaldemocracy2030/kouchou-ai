"""公開範囲・削除・可視化設定の変更がストレージ(Azure Blob 等)へ同期されることのテスト

ローカルが一時的なファイルシステムの運用では、起動時に initialize_from_storage が
ストレージ上の report_status.json / outputs/<slug>/*.json を正として復元する。
変更をストレージへ上げないと、再起動で非公開化や削除が元に戻ってしまう。
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.routers import admin_report
from src.routers.admin_report import router, verify_admin_api_key
from src.schemas.report import ReportVisibility
from src.services import report_status
from src.services.report_sync import ReportSyncService


@pytest.fixture
def status_env(tmp_path):
    status_file = tmp_path / "report_status.json"
    data = {
        "test-slug": {
            "slug": "test-slug",
            "status": "ready",
            "title": "t",
            "description": "d",
            "is_pubcom": False,
            "visibility": ReportVisibility.PUBLIC.value,
            "created_at": "2025-05-13T07:56:58.405239+00:00",
        }
    }
    status_file.write_text(json.dumps(data), encoding="utf-8")
    storage = MagicMock()
    storage.upload_file.return_value = True
    with (
        patch.object(report_status, "STATE_FILE", status_file),
        patch.object(ReportSyncService, "LOCAL_STATUS_FILE_PATH", status_file),
        patch("src.services.report_sync.get_storage_service", return_value=storage),
        patch("src.services.report_status.invalidate_report_cache"),
    ):
        report_status.load_status()
        yield status_file, storage
    report_status.load_status()


def _uploaded_status(storage: MagicMock, status_file) -> list[dict]:
    """status/report_status.json へのアップロード呼び出しを返す"""
    return [c for c in storage.upload_file.call_args_list if c.args[1] == "status/report_status.json"]


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[verify_admin_api_key] = lambda: "test-api-key"
    return TestClient(app)


class TestStatusSyncedToStorage:
    def test_visibility_change_uploads_status(self, status_env):
        status_file, storage = status_env
        report_status.update_report_visibility_state("test-slug", ReportVisibility.PRIVATE)
        calls = _uploaded_status(storage, status_file)
        assert len(calls) == 1
        assert calls[0].args[0] == str(status_file)
        assert json.loads(status_file.read_text())["test-slug"]["visibility"] == "private"

    def test_visibility_change_raises_when_upload_fails(self, status_env):
        _, storage = status_env
        storage.upload_file.return_value = False
        with pytest.raises(report_status.StatusStorageSyncError):
            report_status.update_report_visibility_state("test-slug", ReportVisibility.PRIVATE)
        # ローカルの変更自体は有効なまま（このプロセスでは非公開として扱う）
        assert report_status._report_status["test-slug"]["visibility"] == "private"

    def test_visibility_endpoint_returns_500_when_upload_fails(self, status_env, client):
        _, storage = status_env
        storage.upload_file.return_value = False
        response = client.patch("/admin/reports/test-slug/visibility", json={"visibility": "private"})
        assert response.status_code == 500

    def test_delete_endpoint_uploads_status(self, status_env, client):
        status_file, storage = status_env
        response = client.delete("/admin/reports/test-slug")
        assert response.status_code == 200
        assert len(_uploaded_status(storage, status_file)) == 1
        assert json.loads(status_file.read_text())["test-slug"]["status"] == "deleted"

    def test_delete_endpoint_returns_500_when_upload_fails(self, status_env, client):
        _, storage = status_env
        storage.upload_file.return_value = False
        response = client.delete("/admin/reports/test-slug")
        assert response.status_code == 500

    def test_update_report_config_uploads_status(self, status_env):
        status_file, storage = status_env
        from src.schemas.report_config import ReportConfigUpdate

        report_status.update_report_config("test-slug", ReportConfigUpdate(question="新タイトル"))
        assert len(_uploaded_status(storage, status_file)) == 1


class TestVisualizationConfigSyncedToStorage:
    def test_update_visualization_config_uploads_file(self, tmp_path, client):
        report_dir = tmp_path / "reports"
        (report_dir / "test-slug").mkdir(parents=True)
        storage = MagicMock()
        storage.upload_file.return_value = True
        with (
            patch.object(admin_report.settings, "REPORT_DIR", report_dir),
            patch("src.services.report_sync.get_storage_service", return_value=storage),
            patch("src.routers.admin_report.invalidate_report_cache"),
        ):
            response = client.patch("/admin/reports/test-slug/visualization-config", json={})
        assert response.status_code == 200
        storage.upload_file.assert_called_once_with(
            str(report_dir / "test-slug" / "visualization_config.json"),
            "outputs/test-slug/visualization_config.json",
        )

    def test_update_visualization_config_returns_500_when_upload_fails(self, tmp_path, client):
        report_dir = tmp_path / "reports"
        (report_dir / "test-slug").mkdir(parents=True)
        storage = MagicMock()
        storage.upload_file.return_value = False
        with (
            patch.object(admin_report.settings, "REPORT_DIR", report_dir),
            patch("src.services.report_sync.get_storage_service", return_value=storage),
            patch("src.routers.admin_report.invalidate_report_cache"),
        ):
            response = client.patch("/admin/reports/test-slug/visualization-config", json={})
        assert response.status_code == 500
