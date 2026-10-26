"""取り込み・クリア・作成が既存レポートの入力 CSV / レポートを上書き・削除しないことのテスト"""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import polars as pl
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.routers import admin_report, plugins, spreadsheet
from src.services import report_duplicate, report_status, spreadsheet_service

EXISTING_SLUG = "city-survey"
ORIGINAL_CSV = "comment-id,comment\n1,original\n"


@pytest.fixture
def env(tmp_path: Path):
    dirs = SimpleNamespace(
        input_dir=tmp_path / "inputs",
        config_dir=tmp_path / "configs",
        report_dir=tmp_path / "outputs",
        state_file=tmp_path / "data" / "report_status.json",
    )
    for d in (dirs.input_dir, dirs.config_dir, dirs.report_dir, dirs.state_file.parent):
        d.mkdir(parents=True)
    dirs.state_file.write_text(
        json.dumps({EXISTING_SLUG: {"slug": EXISTING_SLUG, "status": "ready"}}),
        encoding="utf-8",
    )
    (dirs.input_dir / f"{EXISTING_SLUG}.csv").write_text(ORIGINAL_CSV, encoding="utf-8")

    fake_settings = SimpleNamespace(
        INPUT_DIR=dirs.input_dir,
        CONFIG_DIR=dirs.config_dir,
        REPORT_DIR=dirs.report_dir,
    )
    with (
        patch.object(report_status, "settings", fake_settings),
        patch.object(report_status, "STATE_FILE", dirs.state_file),
        patch.object(spreadsheet_service, "settings", fake_settings),
        patch.object(report_duplicate, "settings", fake_settings),
    ):
        yield dirs
    report_status.load_status()


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(spreadsheet.router)
    app.include_router(plugins.router)
    app.include_router(admin_report.router)
    app.dependency_overrides[spreadsheet.verify_admin_api_key] = lambda: "ok"
    app.dependency_overrides[admin_report.verify_admin_api_key] = lambda: "ok"
    return TestClient(app)


def _fake_sheet():
    df = pl.DataFrame({"comment-id": ["1"], "comment": ["other data"]})
    return (
        patch.object(spreadsheet_service, "parse_spreadsheet_url", return_value=("sheet", None)),
        patch.object(spreadsheet_service, "fetch_public_spreadsheet", return_value=df),
    )


def _import(client, file_name: str):
    p1, p2 = _fake_sheet()
    with p1, p2:
        return client.post(
            "/admin/spreadsheet/import",
            json={"url": "https://docs.google.com/spreadsheets/d/x/edit", "file_name": file_name},
        )


class TestSpreadsheetImportGuard:
    def test_import_rejects_existing_report_slug(self, client, env):
        response = _import(client, EXISTING_SLUG)

        assert response.status_code == 409
        assert (env.input_dir / f"{EXISTING_SLUG}.csv").read_text(encoding="utf-8") == ORIGINAL_CSV

    def test_import_rejects_slug_with_existing_outputs(self, client, env):
        (env.report_dir / "orphan-report").mkdir()

        response = _import(client, "orphan-report")

        assert response.status_code == 409
        assert not (env.input_dir / "orphan-report.csv").exists()

    def test_import_allows_new_id_even_if_previously_imported(self, client, env):
        assert _import(client, "new-id").status_code == 200
        # 同じ作成フローでの再取り込み（inputs/<id>.csv だけがある状態）は許可する
        response = _import(client, "new-id")

        assert response.status_code == 200
        assert "other data" in (env.input_dir / "new-id.csv").read_text(encoding="utf-8")


class TestDeleteInputGuard:
    def test_delete_rejects_existing_report_slug(self, client, env):
        response = client.delete(f"/admin/inputs/{EXISTING_SLUG}")

        assert response.status_code == 409
        assert (env.input_dir / f"{EXISTING_SLUG}.csv").read_text(encoding="utf-8") == ORIGINAL_CSV

    def test_delete_allows_imported_new_id(self, client, env):
        (env.input_dir / "new-id.csv").write_text(ORIGINAL_CSV, encoding="utf-8")

        response = client.delete("/admin/inputs/new-id")

        assert response.status_code == 200
        assert not (env.input_dir / "new-id.csv").exists()


class TestPluginImportGuard:
    def test_plugin_import_rejects_existing_report_slug(self, client, env):
        fake_plugin = MagicMock()
        with patch.object(plugins.PluginRegistry, "get_plugin", return_value=fake_plugin):
            response = client.post(
                "/admin/plugins/youtube/import",
                json={"source": "https://example.com/v", "fileName": EXISTING_SLUG},
            )

        assert response.status_code == 200
        assert response.json()["success"] is False
        fake_plugin.fetch_data.assert_not_called()
        fake_plugin.save_to_csv.assert_not_called()
        assert (env.input_dir / f"{EXISTING_SLUG}.csv").read_text(encoding="utf-8") == ORIGINAL_CSV


class TestCreateReportGuard:
    @staticmethod
    def _body(input_slug: str) -> dict:
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

    def test_create_rejects_existing_report_slug(self, client, env):
        with patch.object(admin_report, "launch_report_generation") as mock_launch:
            response = client.post("/admin/reports", json=self._body(EXISTING_SLUG))

        assert response.status_code == 409
        mock_launch.assert_not_called()

    def test_create_allows_new_id_with_imported_input(self, client, env):
        (env.input_dir / "new-id.csv").write_text(ORIGINAL_CSV, encoding="utf-8")
        with patch.object(admin_report, "launch_report_generation") as mock_launch:
            response = client.post("/admin/reports", json=self._body("new-id"))

        assert response.status_code == 200
        mock_launch.assert_called_once()
