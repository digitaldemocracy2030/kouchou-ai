import asyncio
import json
import os
import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from google.genai import errors as genai_errors

from src.routers import admin_report
from src.routers.admin_report import router, verify_admin_api_key
from src.schemas.report import Report, ReportStatus, ReportVisibility
from src.services import report_duplicate, report_launcher, report_status, report_sync


def _has_running_event_loop() -> bool:
    """呼び出し元スレッドでイベントループが動いているか（=async 関数から直接呼ばれたか）"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


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

    def test_update_report_visibility_runs_off_event_loop(self, client):
        """revalidate の同期 HTTP を含む処理がイベントループ上で直接実行されないこと"""
        seen = {}

        def fake_update(slug, visibility):
            seen["on_loop"] = _has_running_event_loop()
            return visibility.value

        with patch("src.routers.admin_report.update_report_visibility_state", side_effect=fake_update):
            response = client.patch(
                "/admin/reports/test-slug/visibility",
                json={"visibility": ReportVisibility.PUBLIC.value},
                headers={"x-api-key": "test-api-key"},
            )

        assert response.status_code == 200
        assert seen == {"on_loop": False}

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
        with patch("analysis_core.services.llm.request_to_chat_ai") as mock_request:
            mock_request.return_value = ("ok", 0, 0, 0)

            response = client.get("/admin/environment/verify?provider=openai", headers={"x-api-key": "test-api-key"})
            assert response.status_code == 200
            assert response.json()["success"] is True

            mock_request.assert_called_once()
            _, kwargs = mock_request.call_args
            assert kwargs["provider"] == "openai"
            assert kwargs["model"] == "gpt-4o-mini"

    @pytest.mark.parametrize("provider", ["azure", "openrouter", "local"])
    def test_verify_selected_provider_settings(self, client, provider):
        with patch("analysis_core.services.llm.request_to_chat_ai") as call:
            call.return_value = ("ok", 0, 0, 0)
            response = client.get(
                "/admin/environment/verify",
                params={"provider": provider, "model": "selected/model", "local_llm_address": "localhost:1234"},
                headers={"x-api-key": "test-api-key"},
            )
            assert response.status_code == 200
            assert response.json()["success"] is True
            assert call.call_args.kwargs["provider"] == provider
            assert call.call_args.kwargs["model"] == "selected/model"
            assert call.call_args.kwargs["local_llm_address"] == ("localhost:1234" if provider == "local" else None)
            assert call.call_args.kwargs["timeout_seconds"] == 30

    @pytest.mark.parametrize(
        "params",
        [
            {"provider": "unknown"},
            {"provider": "local"},
            {"provider": "local", "model": "model"},
            {"provider": "local", "model": " ", "local_llm_address": "localhost:1234"},
        ],
    )
    def test_verify_rejects_incomplete_target(self, client, params):
        with patch("analysis_core.services.llm.request_to_chat_ai") as call:
            response = client.get("/admin/environment/verify", params=params, headers={"x-api-key": "test-api-key"})
            assert response.status_code == 400
            call.assert_not_called()

    def test_verify_api_key_gemini(self, client):
        with patch("analysis_core.services.llm.request_to_chat_ai") as mock_request:
            mock_request.return_value = ("ok", 0, 0, 0)

            response = client.get("/admin/environment/verify?provider=gemini", headers={"x-api-key": "test-api-key"})
            assert response.status_code == 200
            assert response.json()["success"] is True

            mock_request.assert_called_once()
            _, kwargs = mock_request.call_args
            assert kwargs["provider"] == "gemini"
            assert kwargs["model"] == "gemini-2.5-flash"

    @pytest.mark.parametrize(
        ("error", "expected_type"),
        [
            (
                genai_errors.ClientError(
                    400,
                    {
                        "error": {
                            "code": 400,
                            "message": "API key not valid. Please pass a valid API key.",
                            "status": "INVALID_ARGUMENT",
                            "details": [{"reason": "API_KEY_INVALID"}],
                        }
                    },
                ),
                "authentication_error",
            ),
            (
                genai_errors.ClientError(401, {"error": {"code": 401, "status": "UNAUTHENTICATED"}}),
                "authentication_error",
            ),
            (
                genai_errors.ClientError(403, {"error": {"code": 403, "status": "PERMISSION_DENIED"}}),
                "authentication_error",
            ),
            (
                genai_errors.ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED"}}),
                "rate_limit_error",
            ),
            (RuntimeError("Gemini API rate limit exceeded after retries"), "rate_limit_error"),
            (genai_errors.ClientError(400, {"error": {"code": 400, "status": "INVALID_ARGUMENT"}}), "unknown_error"),
        ],
    )
    def test_verify_api_key_gemini_classifies_errors(self, client, error, expected_type):
        with patch("analysis_core.services.llm.request_to_chat_ai", side_effect=error):
            response = client.get("/admin/environment/verify?provider=gemini", headers={"x-api-key": "test-api-key"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == expected_type

    def test_verify_api_key_uses_user_provided_key_header(self, client):
        with patch("analysis_core.services.llm.request_to_chat_ai") as mock_request:
            mock_request.return_value = ("ok", 0, 0, 0)

            response = client.get(
                "/admin/environment/verify?provider=openai",
                headers={"x-api-key": "test-api-key", "x-user-api-key": "user-test-key"},
            )
            assert response.status_code == 200
            assert response.json()["success"] is True

            mock_request.assert_called_once()
            _, kwargs = mock_request.call_args
            assert kwargs["user_api_key"] == "user-test-key"

    def test_verify_empty_response_is_not_success(self, client):
        with patch("analysis_core.services.llm.request_to_chat_ai", return_value=("", 0, 0, 0)):
            response = client.get("/admin/environment/verify?provider=openai", headers={"x-api-key": "test-api-key"})
            assert response.json()["success"] is False
            assert response.json()["error_type"] == "unknown_error"

    def test_verify_api_key_runs_chat_request_off_event_loop(self, client):
        """同期の request_to_chat_ai（timeout + リトライ）がイベントループを塞がないこと"""
        seen = {}

        def fake_request(**kwargs):
            seen["on_loop"] = _has_running_event_loop()
            return ("ok", 0, 0, 0)

        with patch("analysis_core.services.llm.request_to_chat_ai", side_effect=fake_request):
            response = client.get("/admin/environment/verify?provider=openai", headers={"x-api-key": "test-api-key"})

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert seen == {"on_loop": False}

    def test_verify_api_key_does_not_expose_exception_detail(self, client):
        with patch("analysis_core.services.llm.request_to_chat_ai") as mock_request:
            mock_request.side_effect = RuntimeError("secret stack detail")

            response = client.get("/admin/environment/verify?provider=openai", headers={"x-api-key": "test-api-key"})

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert data["error_type"] == "unknown_error"
            assert "secret stack detail" not in data["message"]
            assert "secret stack detail" not in data["error_detail"]


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


class TestCreateReport:
    """create_report（POST /admin/reports）のテスト"""

    @staticmethod
    def _valid_body(input_slug: str) -> dict:
        return {
            "input": input_slug,
            "question": "テスト質問",
            "intro": "テスト概要",
            "cluster": [3, 5],
            "model": "gpt-4o-mini",
            "workers": 1,
            "prompt": {
                "extraction": "ex",
                "initial_labelling": "il",
                "merge_labelling": "ml",
                "overview": "ov",
            },
            "comments": [{"id": "1", "comment": "hello"}],
        }

    def test_create_report_rejects_path_traversal_input(self, client):
        """異常系：input がパストラバーサル文字列なら400を返し、launchを呼ばない"""
        with patch("src.routers.admin_report.launch_report_generation") as mock_launch:
            response = client.post(
                "/admin/reports",
                json=self._valid_body("../../etc/pwn"),
                headers={"x-api-key": "test-api-key"},
            )

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid slug format"
        mock_launch.assert_not_called()

    def test_create_report_valid_input_launches(self, client, tmp_path):
        """正常系：有効なinputならslug検証を通過しlaunch_report_generationに到達する"""
        with ExitStack() as stack:
            self._isolated_dirs(stack, tmp_path, {})
            mock_launch = stack.enter_context(patch("src.routers.admin_report.launch_report_generation"))
            response = client.post(
                "/admin/reports",
                json=self._valid_body("valid-slug"),
                headers={"x-api-key": "test-api-key"},
            )

        # 成功時はハンドラが自前の ORJSONResponse を返すため既定の 200
        # （ルートの status_code=202 は上書きされる）。slug検証で弾かれないことを確認する。
        assert response.status_code == 200
        mock_launch.assert_called_once()

    @staticmethod
    def _isolated_dirs(stack: ExitStack, tmp_path: Path, status: dict) -> dict:
        dirs = {name: tmp_path / name for name in ("configs", "inputs", "outputs", "data")}
        for d in dirs.values():
            d.mkdir(parents=True)
        status_file = dirs["data"] / "report_status.json"
        status_file.write_text(json.dumps(status), encoding="utf-8")
        stack.enter_context(patch.object(report_duplicate.settings, "CONFIG_DIR", dirs["configs"]))
        stack.enter_context(patch.object(report_duplicate.settings, "INPUT_DIR", dirs["inputs"]))
        stack.enter_context(patch.object(report_duplicate.settings, "REPORT_DIR", dirs["outputs"]))
        stack.enter_context(patch.object(report_status, "STATE_FILE", status_file))
        return dirs

    @pytest.mark.parametrize("status", ["ready", "deleted"])
    def test_create_report_rejects_existing_slug_in_status(self, client, tmp_path, status):
        """異常系：status に既存（削除済みを含む）の slug があれば 409 を返し、上書きしない"""
        existing = {
            "existing-slug": {
                "slug": "existing-slug",
                "status": status,
                "title": "old",
                "description": "old",
                "visibility": "public",
            }
        }
        with ExitStack() as stack:
            self._isolated_dirs(stack, tmp_path, existing)
            mock_launch = stack.enter_context(patch("src.routers.admin_report.launch_report_generation"))
            response = client.post(
                "/admin/reports",
                json=self._valid_body("existing-slug"),
                headers={"x-api-key": "test-api-key"},
            )

        assert response.status_code == 409
        mock_launch.assert_not_called()

    def test_create_report_rejects_slug_with_leftover_outputs(self, client, tmp_path):
        """異常系：status に無くても outputs/<slug> が残っていれば 409 を返す（旧成果物の再利用を防ぐ）"""
        with ExitStack() as stack:
            dirs = self._isolated_dirs(stack, tmp_path, {})
            (dirs["outputs"] / "leftover-slug").mkdir()
            mock_launch = stack.enter_context(patch("src.routers.admin_report.launch_report_generation"))
            response = client.post(
                "/admin/reports",
                json=self._valid_body("leftover-slug"),
                headers={"x-api-key": "test-api-key"},
            )

        assert response.status_code == 409
        mock_launch.assert_not_called()

    def test_create_report_allows_preimported_input_csv(self, client, tmp_path):
        """正常系：取り込み済みの inputs/<slug>.csv だけがある slug は 409 にしない
        （スプレッドシート・プラグイン取り込みは作成前に inputs/<slug>.csv を書き出す）"""
        with ExitStack() as stack:
            dirs = self._isolated_dirs(stack, tmp_path, {})
            (dirs["inputs"] / "imported-slug.csv").write_text("comment-id,comment-body\n1,a\n", encoding="utf-8")
            mock_launch = stack.enter_context(patch("src.routers.admin_report.launch_report_generation"))
            response = client.post(
                "/admin/reports",
                json=self._valid_body("imported-slug"),
                headers={"x-api-key": "test-api-key"},
            )

        assert response.status_code == 200
        mock_launch.assert_called_once()


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


@pytest.mark.parametrize("error_kind", ["bad_request", "not_found", "connection", "runtime"])
def test_azure_verification_guidance_without_exception_details(client, error_kind):
    """Azureの接続失敗では例外の詳細を返さず、設定項目の確認を案内する。"""
    import httpx
    import openai

    request = httpx.Request("POST", "https://example.invalid/private-endpoint")
    if error_kind == "bad_request":
        error = openai.BadRequestError("secret detail", response=httpx.Response(400, request=request), body=None)
    elif error_kind == "not_found":
        error = openai.NotFoundError("secret detail", response=httpx.Response(404, request=request), body=None)
    elif error_kind == "connection":
        error = openai.APIConnectionError(message="secret detail", request=request)
    else:
        error = RuntimeError("secret detail")
    with patch("analysis_core.services.llm.request_to_chat_ai", side_effect=error):
        response = client.get("/admin/environment/verify?provider=azure", headers={"x-api-key": "test-api-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["error_type"] == "unknown_error"
    assert "AZURE_CHATCOMPLETION_VERSION" in data["message"]
    assert "モデルのバージョンではなくAPIバージョン" in data["message"]
    assert "secret detail" not in response.text
    assert "private-endpoint" not in response.text


class TestEditRejectsDeletedOrProcessingReport:
    """削除済み・生成中のレポートへの編集（タイトル・説明、意見グループ名）を受け付けない

    削除済みのレポートを別タブなどから編集すると、再集計の完了時に status が ready に
    上書きされ、削除前の公開状態のまま復活していた。
    """

    @pytest.fixture
    def status_file(self, tmp_path):
        path = tmp_path / "report_status.json"
        with patch.object(report_status, "STATE_FILE", path):
            yield path

    def _write_status(self, path, status):
        path.write_text(
            json.dumps(
                {
                    "test-slug": {
                        "slug": "test-slug",
                        "status": status,
                        "title": "t",
                        "description": "d",
                        "visibility": ReportVisibility.PUBLIC.value,
                    }
                }
            ),
            encoding="utf-8",
        )

    @pytest.mark.parametrize(("status", "expected_code"), [("deleted", 404), ("processing", 409)])
    def test_update_config_rejects(self, client, status_file, status, expected_code):
        self._write_status(status_file, status)
        with (
            patch("src.routers.admin_report.ConfigRepository") as mock_repo,
            patch("src.routers.admin_report.execute_aggregation") as mock_execute,
            patch("src.routers.admin_report.update_report_config") as mock_update,
        ):
            response = client.patch(
                "/admin/reports/test-slug/config",
                json={"question": "new title"},
                headers={"x-api-key": "test-api-key"},
            )

        assert response.status_code == expected_code
        mock_repo.return_value.update_json.assert_not_called()
        mock_execute.assert_not_called()
        mock_update.assert_not_called()

    @pytest.mark.parametrize(("status", "expected_code"), [("deleted", 404), ("processing", 409)])
    def test_update_cluster_label_rejects(self, client, status_file, status, expected_code):
        self._write_status(status_file, status)
        with (
            patch("src.routers.admin_report.ClusterRepository") as mock_repo,
            patch("src.routers.admin_report.execute_aggregation") as mock_execute,
        ):
            response = client.patch(
                "/admin/reports/test-slug/cluster-label",
                json={"id": "1_1", "label": "l", "description": "d"},
                headers={"x-api-key": "test-api-key"},
            )

        assert response.status_code == expected_code
        mock_repo.return_value.update_csv.assert_not_called()
        mock_execute.assert_not_called()

    def test_delete_then_edit_does_not_launch_aggregation(self, client, status_file):
        """DELETE の後の PATCH config は 404 になり、再集計を起動しない"""
        self._write_status(status_file, "ready")
        report_status.load_status()
        with (
            patch("src.routers.admin_report.ConfigRepository") as mock_repo,
            patch("src.routers.admin_report.execute_aggregation") as mock_execute,
        ):
            assert client.delete("/admin/reports/test-slug", headers={"x-api-key": "test-api-key"}).status_code == 200
            response = client.patch(
                "/admin/reports/test-slug/config",
                json={"question": "new title"},
                headers={"x-api-key": "test-api-key"},
            )

        assert response.status_code == 404
        mock_repo.return_value.update_json.assert_not_called()
        mock_execute.assert_not_called()
        assert report_status.get_status("test-slug") == "deleted"

    def test_update_config_allows_ready_report(self, client, status_file):
        self._write_status(status_file, "ready")
        with (
            patch("src.routers.admin_report.ConfigRepository") as mock_repo,
            patch("src.routers.admin_report.execute_aggregation", return_value=True) as mock_execute,
            patch("src.routers.admin_report.update_report_config", return_value={"slug": "test-slug"}),
        ):
            mock_repo.return_value.update_json.return_value = True
            response = client.patch(
                "/admin/reports/test-slug/config",
                json={"question": "new title"},
                headers={"x-api-key": "test-api-key"},
            )

        assert response.status_code == 200
        mock_execute.assert_called_once_with("test-slug")
