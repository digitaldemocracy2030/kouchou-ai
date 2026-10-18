from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.routers import spreadsheet
from src.routers.spreadsheet import router, verify_admin_api_key


@pytest.fixture
def client(tmp_path):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[verify_admin_api_key] = lambda: "test"
    with patch.object(spreadsheet.settings, "INPUT_DIR", tmp_path):
        yield TestClient(app), tmp_path


def test_get_spreadsheet_data_keeps_numeric_ids_and_leading_zeros_as_strings(client):
    """数値に見える comment-id や属性値も文字列のまま返す（id は str、先頭の 0 を保持）"""
    test_client, input_dir = client
    (input_dir / "sheet.csv").write_text("comment-id,comment,zip\n1,hello,01234\n2,world,00999\n", encoding="utf-8")

    response = test_client.get("/admin/spreadsheet/data/sheet")

    assert response.status_code == 200
    comments = response.json()["comments"]
    assert [c["id"] for c in comments] == ["1", "2"]
    assert [c["attribute_zip"] for c in comments] == ["01234", "00999"]
