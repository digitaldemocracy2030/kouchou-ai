"""取り込み・クリア・作成が既存レポートの入力 CSV / レポートを上書き・削除しないことのテスト"""

import json
import os
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import polars as pl
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.routers import admin_report, plugins, spreadsheet
from src.services import report_duplicate, report_launcher, report_status, spreadsheet_service

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
        patch.object(report_launcher, "settings", fake_settings),
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


# ---- 判定と保存・削除の間にレポート作成が割り込む競合 ----

RACE_SLUG = "race-id"
# 割り込ませる作成（別スレッド）がロック待ちで止まっていると見なすまでの待ち時間
CREATE_WAIT_SECONDS = 0.5


def _create_body(input_slug: str) -> dict:
    body = TestCreateReportGuard._body(input_slug)
    body["comments"] = [{"id": "1", "comment": "created report data"}]
    return body


def _create_report(client) -> None:
    """レポートを作成する（analysis-core の起動だけ止め、status 登録と入力 CSV の保存は実際に行う）"""
    response = client.post("/admin/reports", json=_create_body(RACE_SLUG))
    assert response.status_code == 200, response.text


def _create_report_in_thread(client) -> threading.Thread:
    """別スレッドでレポート作成を始め、ロック待ちで止まらなければ完了まで待つ"""
    thread = threading.Thread(target=_create_report, args=(client,))
    thread.start()
    thread.join(timeout=CREATE_WAIT_SECONDS)
    return thread


def _assert_created_input_intact(env) -> None:
    assert report_status.slug_exists(RACE_SLUG)
    input_path = env.input_dir / f"{RACE_SLUG}.csv"
    assert input_path.exists(), "作成したレポートの入力 CSV が削除された"
    assert "created report data" in input_path.read_text(encoding="utf-8"), "作成したレポートの入力 CSV が上書きされた"


@pytest.fixture
def no_launch():
    with patch.object(report_launcher, "_launch_analysis_process"):
        yield


class TestCreateRacingWithImportAndClear:
    def test_spreadsheet_import_rechecks_after_fetch(self, client, env, no_launch):
        """取り込みの外部取得中に作成されたレポートの入力 CSV を、取得後の保存で上書きしない"""
        df = pl.DataFrame({"comment-id": ["1"], "comment": ["other data"]})

        def fetch_while_creating(*_args, **_kwargs):
            _create_report(client)
            return df

        with (
            patch.object(spreadsheet_service, "parse_spreadsheet_url", return_value=("sheet", None)),
            patch.object(spreadsheet_service, "fetch_public_spreadsheet", side_effect=fetch_while_creating),
        ):
            response = client.post(
                "/admin/spreadsheet/import",
                json={"url": "https://docs.google.com/spreadsheets/d/x/edit", "file_name": RACE_SLUG},
            )

        assert response.status_code == 409
        _assert_created_input_intact(env)

    def test_spreadsheet_import_holds_lock_while_saving(self, client, env, no_launch):
        """取り込みの判定から保存までの間に始まった作成は、保存が終わるまで待ち、自分の入力 CSV を書く"""
        real_save = spreadsheet_service.save_as_csv
        threads = []

        def save_while_creating(df, file_name):
            threads.append(_create_report_in_thread(client))
            return real_save(df, file_name)

        p1, p2 = _fake_sheet()
        with p1, p2, patch.object(spreadsheet_service, "save_as_csv", side_effect=save_while_creating):
            response = client.post(
                "/admin/spreadsheet/import",
                json={"url": "https://docs.google.com/spreadsheets/d/x/edit", "file_name": RACE_SLUG},
            )
            threads[0].join()

        assert response.status_code == 200
        _assert_created_input_intact(env)

    def test_plugin_import_rechecks_after_fetch(self, client, env, no_launch):
        """プラグインの外部取得中に作成されたレポートの入力 CSV を、取得後の保存で上書きしない"""
        fake_plugin = MagicMock()

        def fetch_while_creating(*_args, **_kwargs):
            _create_report(client)
            return pl.DataFrame({"comment-id": ["1"], "comment": ["other data"]})

        fake_plugin.fetch_data.side_effect = fetch_while_creating
        with patch.object(plugins.PluginRegistry, "get_plugin", return_value=fake_plugin):
            response = client.post(
                "/admin/plugins/youtube/import",
                json={"source": "https://example.com/v", "fileName": RACE_SLUG},
            )

        assert response.json()["success"] is False
        fake_plugin.save_to_csv.assert_not_called()
        _assert_created_input_intact(env)

    def test_delete_holds_lock_while_removing(self, client, env, no_launch):
        """クリアの判定から削除までの間に始まった作成は、削除が終わるまで待ち、その入力 CSV は消されない"""
        (env.input_dir / f"{RACE_SLUG}.csv").write_text(ORIGINAL_CSV, encoding="utf-8")
        real_remove = os.remove
        threads = []

        def remove_while_creating(path):
            threads.append(_create_report_in_thread(client))
            real_remove(path)

        with patch.object(spreadsheet_service.os, "remove", side_effect=remove_while_creating):
            response = client.delete(f"/admin/inputs/{RACE_SLUG}")
            threads[0].join()

        assert response.status_code == 200
        _assert_created_input_intact(env)
