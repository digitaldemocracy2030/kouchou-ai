"""入力 CSV ファイル名を受け取るエンドポイントのパストラバーサル対策の回帰テスト"""

from unittest.mock import MagicMock, patch

import polars as pl
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.routers import plugins, spreadsheet
from src.routers.admin_report import verify_admin_api_key as admin_report_verify
from src.routers.spreadsheet import verify_admin_api_key as spreadsheet_verify
from src.utils.slug_utils import validate_slug

INVALID_FILE_NAMES = [
    "../outputs/test-slug/args",
    "../../tmp/pwn",
    "foo/bar",
    "..",
    "foo.bar",
    "valid-name\n",
    "",
]


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(plugins.router)
    app.include_router(spreadsheet.router)

    async def override_verify_admin_api_key():
        return "test-api-key"

    app.dependency_overrides[admin_report_verify] = override_verify_admin_api_key
    app.dependency_overrides[spreadsheet_verify] = override_verify_admin_api_key
    return TestClient(app)


@pytest.fixture
def mock_plugin():
    plugin = MagicMock()
    plugin.fetch_data.return_value = pl.DataFrame({"comment-id": ["1"], "comment": ["hello"]})
    plugin.save_to_csv.return_value = "/tmp/dummy.csv"
    with patch.object(plugins.PluginRegistry, "get_plugin", return_value=plugin):
        yield plugin


class TestValidateSlugTrailingNewline:
    def test_trailing_newline_is_rejected(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            validate_slug("valid-name\n")
        assert exc_info.value.status_code == 400

    def test_valid_slug_passes(self):
        validate_slug("Valid_name-123")


class TestPluginImportFileName:
    @pytest.mark.parametrize("file_name", INVALID_FILE_NAMES)
    def test_invalid_file_name_returns_400_without_writing(self, client, mock_plugin, file_name):
        response = client.post(
            "/admin/plugins/youtube/import",
            json={"source": "https://example.com/watch?v=x", "fileName": file_name},
        )

        assert response.status_code == 400
        mock_plugin.fetch_data.assert_not_called()
        mock_plugin.save_to_csv.assert_not_called()

    def test_valid_file_name_is_saved(self, client, mock_plugin):
        response = client.post(
            "/admin/plugins/youtube/import",
            json={"source": "https://example.com/watch?v=x", "fileName": "my-input_1"},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_plugin.save_to_csv.assert_called_once()
        assert mock_plugin.save_to_csv.call_args.args[1] == "my-input_1"


class TestGetSpreadsheetDataFileName:
    @pytest.mark.parametrize("file_name", ["foo.bar", "valid-name%0A", "%2E%2E", "..%5C..%5Cpwn"])
    def test_invalid_file_name_returns_400(self, client, file_name):
        with patch.object(spreadsheet.pl, "read_csv") as mock_read_csv:
            response = client.get(f"/admin/spreadsheet/data/{file_name}")

        assert response.status_code == 400
        mock_read_csv.assert_not_called()

    def test_valid_file_name_reads_csv(self, client, tmp_path):
        (tmp_path / "my-input.csv").write_text("comment-id,comment\n1,hello\n")
        with patch.object(spreadsheet.settings, "INPUT_DIR", tmp_path):
            response = client.get("/admin/spreadsheet/data/my-input")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["comments"][0]["comment"] == "hello"
