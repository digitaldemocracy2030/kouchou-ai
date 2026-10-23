"""公開 API（GET /reports・GET /reports/{slug}）の公開範囲と公開 API キーの検証。

公開一覧に出してよいのは「処理が完了（READY）し、公開（PUBLIC）」のレポートだけで、
限定公開・非公開・処理中・エラー・削除済みのレポートの slug や題名は一覧に出してはいけない。
"""

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# (slug, status, visibility)
STATUS_VISIBILITY_CASES = [
    ("ready-public", "ready", "public"),
    ("ready-unlisted", "ready", "unlisted"),
    ("ready-private", "ready", "private"),
    ("processing-public", "processing", "public"),
    ("error-public", "error", "public"),
    ("deleted-public", "deleted", "public"),
]


@pytest.fixture
def report_state(tmp_path):
    """status × visibility の組合せのレポートを、一時ディレクトリの状態ファイルと成果物で用意する。"""
    state_file = tmp_path / "report_status.json"
    report_dir = tmp_path / "reports"
    state = {}
    for slug, status, visibility in STATUS_VISIBILITY_CASES:
        state[slug] = {
            "slug": slug,
            "title": f"{slug} のタイトル",
            "description": "説明",
            "status": status,
            "visibility": visibility,
        }
        # 成果物は全レポートに置き、404 が「ファイルが無いから」ではなく公開範囲の判定で決まることを確かめる
        (report_dir / slug).mkdir(parents=True)
        (report_dir / slug / "hierarchical_result.json").write_text(
            json.dumps({"config": {"question": "質問"}, "overview": "概要", "clusters": [], "arguments": []}),
            encoding="utf-8",
        )
    state_file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    with (
        patch("src.services.report_status.STATE_FILE", state_file),
        patch("src.routers.report.settings.REPORT_DIR", report_dir),
    ):
        yield


@pytest.fixture
def client_with_key_check():
    """公開 API キーの検証を差し替えていないクライアント。"""
    from src.main import app
    from src.routers.report import verify_public_api_key

    saved = app.dependency_overrides.pop(verify_public_api_key, None)
    try:
        yield TestClient(app)
    finally:
        if saved is not None:
            app.dependency_overrides[verify_public_api_key] = saved


class TestPublicReportList:
    def test_lists_only_ready_and_public_reports(self, client: TestClient, report_state, test_settings):
        response = client.get("/reports", headers={"x-api-key": test_settings.PUBLIC_API_KEY})

        assert response.status_code == 200
        assert [report["slug"] for report in response.json()] == ["ready-public"]


class TestPublicReportDetailStatus:
    def test_ready_public_report_is_returned(self, client: TestClient, report_state, test_settings):
        response = client.get("/reports/ready-public", headers={"x-api-key": test_settings.PUBLIC_API_KEY})

        assert response.status_code == 200
        assert response.json()["visibility"] == "public"

    @pytest.mark.parametrize("slug", ["processing-public", "error-public", "deleted-public"])
    def test_not_ready_report_returns_404(self, client: TestClient, report_state, test_settings, slug):
        response = client.get(f"/reports/{slug}", headers={"x-api-key": test_settings.PUBLIC_API_KEY})

        assert response.status_code == 404


class TestPublicApiKey:
    @pytest.mark.parametrize("path", ["/reports", "/reports/ready-public"])
    def test_missing_key_returns_401(self, client_with_key_check: TestClient, report_state, path):
        response = client_with_key_check.get(path)

        assert response.status_code == 401

    @pytest.mark.parametrize("path", ["/reports", "/reports/ready-public"])
    def test_wrong_key_returns_401(self, client_with_key_check: TestClient, report_state, path):
        response = client_with_key_check.get(path, headers={"x-api-key": "wrong-key"})

        assert response.status_code == 401

    @pytest.mark.parametrize("path", ["/reports", "/reports/ready-public"])
    def test_correct_key_is_accepted(self, client_with_key_check: TestClient, report_state, test_settings, path):
        response = client_with_key_check.get(path, headers={"x-api-key": test_settings.PUBLIC_API_KEY})

        assert response.status_code == 200
