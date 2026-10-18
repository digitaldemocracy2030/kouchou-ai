import asyncio
from unittest.mock import MagicMock, patch

import polars as pl
import pytest
import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.routers.spreadsheet import router, verify_admin_api_key
from src.services import spreadsheet_service


def _csv_response(text: str) -> MagicMock:
    response = MagicMock()
    response.text = text
    response.raise_for_status.return_value = None
    return response


class TestFetchPublicSpreadsheet:
    def test_requests_get_has_timeout(self):
        """timeout 未指定だと応答しないサーバーに無期限ブロックされるため、必ず timeout を渡す"""
        with patch.object(
            spreadsheet_service.requests, "get", return_value=_csv_response("comment\nhello\n")
        ) as mock_get:
            df = spreadsheet_service.fetch_public_spreadsheet("sheet-id")

        assert df["comment"].to_list() == ["hello"]
        timeout = mock_get.call_args.kwargs.get("timeout")
        assert timeout is not None
        assert timeout == spreadsheet_service.SPREADSHEET_FETCH_TIMEOUT_SECONDS

    def test_timeout_is_reported_as_value_error(self):
        with patch.object(spreadsheet_service.requests, "get", side_effect=requests.exceptions.Timeout("slow")):
            with pytest.raises(ValueError, match="スプレッドシートの取得に失敗しました"):
                spreadsheet_service.fetch_public_spreadsheet("sheet-id")


class TestImportSpreadsheetEndpoint:
    @pytest.fixture
    def client(self):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[verify_admin_api_key] = lambda: "test-api-key"
        return TestClient(app)

    def test_import_runs_off_event_loop(self, client, tmp_path):
        """外部 HTTP 取得を含む同期処理がイベントループ上で直接実行されないこと"""
        seen = {}

        def fake_process(url, file_name):
            try:
                asyncio.get_running_loop()
                seen["on_loop"] = True
            except RuntimeError:
                seen["on_loop"] = False
            return tmp_path / f"{file_name}.csv"

        with patch("src.routers.spreadsheet.process_spreadsheet_url", side_effect=fake_process):
            response = client.post(
                "/admin/spreadsheet/import",
                json={"url": "https://docs.google.com/spreadsheets/d/abc/edit", "file_name": "sample"},
            )

        assert response.status_code == 200
        assert seen == {"on_loop": False}


def test_fetch_public_spreadsheet_reads_all_columns_as_strings():
    """数値に見える comment-id や属性値も文字列として読み、先頭の 0 を保持する"""
    with patch.object(
        spreadsheet_service.requests,
        "get",
        return_value=_csv_response("comment-id,comment,zip\n1,hello,01234\n2,world,00999\n"),
    ):
        df = spreadsheet_service.fetch_public_spreadsheet("sheet-id")

    assert df.schema["comment-id"] == pl.Utf8
    assert df["comment-id"].to_list() == ["1", "2"]
    assert df["zip"].to_list() == ["01234", "00999"]
