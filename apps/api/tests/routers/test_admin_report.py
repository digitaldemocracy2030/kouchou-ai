import json
import os
import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.routers import admin_report
from src.routers.admin_report import router, verify_admin_api_key
from src.schemas.report import Report, ReportStatus, ReportVisibility
from src.services import report_duplicate, report_launcher, report_status, report_sync


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


class TestDownloadReportJson:
    def test_download_report_json_success(self, client, tmp_path):
        report_dir = tmp_path / "reports"
        slug_dir = report_dir / "test-slug"
        slug_dir.mkdir(parents=True)
        json_path = slug_dir / "hierarchical_result.json"
        json_path.write_text('{"foo":"bar"}', encoding="utf-8")

        with patch.object(admin_report.settings, "REPORT_DIR", report_dir):
            response = client.get("/admin/reports/test-slug/json", headers={"x-api-key": "test-api-key"})

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        assert "kouchou_test-slug.json" in response.headers["content-disposition"]
        assert response.content == b'{"foo":"bar"}'

    def test_download_report_json_missing(self, client, tmp_path):
        report_dir = tmp_path / "reports"
        report_dir.mkdir(parents=True)

        with patch.object(admin_report.settings, "REPORT_DIR", report_dir):
            response = client.get("/admin/reports/test-slug/json", headers={"x-api-key": "test-api-key"})

        assert response.status_code == 404
        assert response.json()["detail"] == "JSON file not found"


class TestDuplicateReport:
    def _setup_duplicate_env(self, tmp_path: Path, source_slug: str) -> dict:
        config_dir = tmp_path / "configs"
        input_dir = tmp_path / "inputs"
        report_dir = tmp_path / "outputs"
        data_dir = tmp_path / "data"
        config_dir.mkdir(parents=True)
        input_dir.mkdir(parents=True)
        report_dir.mkdir(parents=True)
        data_dir.mkdir(parents=True)

        status_file = data_dir / "report_status.json"
        status_file.write_text("{}", encoding="utf-8")

        source_config = {
            "name": source_slug,
            "input": source_slug,
            "question": "Q",
            "intro": "I",
            "model": "gpt-4o-mini",
            "provider": "openai",
            "is_pubcom": False,
            "extraction": {"prompt": "ex", "workers": 1, "limit": 1},
            "hierarchical_clustering": {"cluster_nums": [5]},
            "hierarchical_initial_labelling": {"prompt": "il", "sampling_num": 30, "workers": 1},
            "hierarchical_merge_labelling": {"prompt": "ml", "sampling_num": 30, "workers": 1},
            "hierarchical_overview": {"prompt": "ov"},
            "hierarchical_aggregation": {"sampling_num": 1},
        }

        (config_dir / f"{source_slug}.json").write_text(json.dumps(source_config), encoding="utf-8")
        (input_dir / f"{source_slug}.csv").write_text("comment-id,comment-body\n1,hello\n", encoding="utf-8")

        source_output = report_dir / source_slug
        source_output.mkdir(parents=True)
        for name in (
            "args.csv",
            "relations.csv",
            "embeddings.pkl",
            "hierarchical_clusters.csv",
            "hierarchical_initial_labels.csv",
            "hierarchical_merge_labels.csv",
            "hierarchical_status.json",
            "hierarchical_overview.txt",
            "hierarchical_result.json",
        ):
            (source_output / name).write_text("x", encoding="utf-8")

        return {
            "config_dir": config_dir,
            "input_dir": input_dir,
            "report_dir": report_dir,
            "data_dir": data_dir,
            "status_file": status_file,
        }

    def _patch_settings(self, env: dict):
        return (
            patch.object(admin_report.settings, "CONFIG_DIR", env["config_dir"]),
            patch.object(admin_report.settings, "INPUT_DIR", env["input_dir"]),
            patch.object(admin_report.settings, "REPORT_DIR", env["report_dir"]),
            patch.object(admin_report.settings, "DATA_DIR", env["data_dir"]),
            patch.object(report_duplicate.settings, "CONFIG_DIR", env["config_dir"]),
            patch.object(report_duplicate.settings, "INPUT_DIR", env["input_dir"]),
            patch.object(report_duplicate.settings, "REPORT_DIR", env["report_dir"]),
            patch.object(report_duplicate.settings, "DATA_DIR", env["data_dir"]),
            patch.object(report_launcher.settings, "CONFIG_DIR", env["config_dir"]),
            patch.object(report_launcher.settings, "INPUT_DIR", env["input_dir"]),
            patch.object(report_launcher.settings, "REPORT_DIR", env["report_dir"]),
            patch.object(report_sync.settings, "REPORT_DIR", env["report_dir"]),
            patch.object(report_sync.settings, "INPUT_DIR", env["input_dir"]),
            patch.object(report_sync.settings, "CONFIG_DIR", env["config_dir"]),
            patch.object(report_status.settings, "DATA_DIR", env["data_dir"]),
            patch.object(report_status, "STATE_FILE", env["status_file"]),
        )

    def test_duplicate_report_slug_conflict_returns_409(self, client, tmp_path):
        source_slug = "source-slug"
        env = self._setup_duplicate_env(tmp_path, source_slug)

        new_slug = "source-slug-copy"
        (env["config_dir"] / f"{new_slug}.json").write_text("{}", encoding="utf-8")

        source_report = Report(
            slug=source_slug,
            title="t",
            description="d",
            status=ReportStatus.READY,
            visibility=ReportVisibility.UNLISTED,
        )

        with ExitStack() as stack:
            for cm in self._patch_settings(env):
                stack.enter_context(cm)
            stack.enter_context(patch("src.routers.admin_report.load_status_as_reports", return_value=[source_report]))
            stack.enter_context(patch("src.services.report_duplicate.launch_report_generation_from_config"))
            response = client.post(
                f"/admin/reports/{source_slug}/duplicate",
                json={"newSlug": new_slug, "reuse": {"enabled": True}},
                headers={"x-api-key": "test-api-key"},
            )

        assert response.status_code == 409

    def test_duplicate_report_removes_overview_and_result(self, client, tmp_path):
        source_slug = "source-slug"
        env = self._setup_duplicate_env(tmp_path, source_slug)

        new_slug = "source-slug-copy"

        source_report = Report(
            slug=source_slug,
            title="t",
            description="d",
            status=ReportStatus.READY,
            visibility=ReportVisibility.UNLISTED,
        )

        with ExitStack() as stack:
            for cm in self._patch_settings(env):
                stack.enter_context(cm)
            stack.enter_context(patch("src.routers.admin_report.load_status_as_reports", return_value=[source_report]))
            stack.enter_context(patch("src.services.report_duplicate.launch_report_generation_from_config"))
            response = client.post(
                f"/admin/reports/{source_slug}/duplicate",
                json={"newSlug": new_slug, "reuse": {"enabled": True}},
                headers={"x-api-key": "test-api-key"},
            )

        assert response.status_code == 200
        new_output = env["report_dir"] / new_slug
        assert not (new_output / "hierarchical_overview.txt").exists()
        assert not (new_output / "hierarchical_result.json").exists()
        assert (new_output / "args.csv").exists()
