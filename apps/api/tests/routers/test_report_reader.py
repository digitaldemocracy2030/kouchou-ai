import json

import pytest
from pydantic import SecretStr

from src.routers import report_reader
from src.services import report_status
from src.services.report_launcher import UPLOAD_FAILED_ERROR

READER_KEY = "reader-test-key"
READER_HEADERS = {"x-api-key": READER_KEY}
REPORTS = "/admin/v1/reports"


@pytest.fixture
def report_files(monkeypatch, tmp_path):
    monkeypatch.setattr(report_reader.settings, "REPORT_READER_API_KEY", SecretStr(READER_KEY))
    monkeypatch.setattr(report_reader.settings, "ADMIN_API_KEY", "admin-test-key")
    monkeypatch.setattr(report_reader.settings, "PUBLIC_API_KEY", "public-test-key")
    monkeypatch.setattr(report_reader.settings, "REPORT_DIR", tmp_path / "outputs")
    state_file = tmp_path / "report_status.json"
    monkeypatch.setattr(report_status, "STATE_FILE", state_file)

    entry = {"title": "試験レポート", "description": "private description", "source_slug": "private source"}
    state = {
        "failed": {**entry, "status": "error", "visibility": "private", "created_at": "2026-11-24T01:00:00+00:00"},
        "running": {**entry, "status": "processing", "visibility": "unlisted"},
        "ready": {**entry, "status": "ready", "is_public": True, "estimated_cost": 0.12},
        "legacy": {**entry, "status": "ready"},
        "deleted": {**entry, "status": "deleted", "visibility": "private"},
    }
    state_file.write_text(json.dumps(state), encoding="utf-8")

    def write_step(slug, step):
        path = report_reader.settings.REPORT_DIR / slug / "hierarchical_status.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(step), encoding="utf-8")
        return path

    return write_step


@pytest.mark.parametrize("configured", [None, "", "admin-test-key", "public-test-key"])
def test_reader_api_stays_disabled_without_distinct_key(client, report_files, monkeypatch, configured):
    monkeypatch.setattr(report_reader.settings, "REPORT_READER_API_KEY", SecretStr(configured) if configured else None)
    assert client.get(REPORTS, headers=READER_HEADERS).status_code == 404


@pytest.mark.parametrize("key", [None, "admin-test-key", "public-test-key", "wrong-key"])
def test_both_endpoints_require_reader_key(client, report_files, key):
    headers = {"x-api-key": key} if key else {}
    assert client.get(REPORTS, headers=headers).status_code == 401
    assert client.get(f"{REPORTS}/failed/status", headers=headers).status_code == 401


def test_reader_key_cannot_use_admin_routes(client, report_files):
    assert client.get("/admin/reports", headers=READER_HEADERS).status_code == 401
    assert client.get("/admin/comments/failed/csv", headers=READER_HEADERS).status_code == 401
    assert client.delete("/admin/reports/failed", headers=READER_HEADERS).status_code == 401
    assert client.post(REPORTS, headers=READER_HEADERS, json={}).status_code == 405


def test_list_can_filter_and_only_returns_metadata(client, report_files):
    response = client.get(REPORTS, headers=READER_HEADERS)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    reports = {item["slug"]: item for item in response.json()["reports"]}
    assert set(reports) == {"failed", "running", "ready", "legacy"}
    assert reports["ready"]["visibility"] == "public"
    assert reports["legacy"]["visibility"] == "private"
    filtered = client.get(REPORTS, headers=READER_HEADERS, params={"status": "error"})
    assert filtered.json() == {
        "reports": [
            {
                "slug": "failed",
                "title": "試験レポート",
                "created_at": "2026-11-24T01:00:00+00:00",
                "status": "error",
                "visibility": "private",
            }
        ],
    }


def test_progress_shows_step_without_diagnostics_or_configs(client, report_files):
    report_files(
        "failed",
        {
            "status": "error",
            "current_job": "embedding",
            "error": "private error",
            "error_log_excerpt": "private excerpt",
            "error_log_path": "private path",
            "prompt": "private prompt",
        },
    )
    report_files("running", {"status": "running", "current_job": "llm_grouping"})

    response = client.get(f"{REPORTS}/failed/status", headers=READER_HEADERS)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "slug": "failed",
        "status": "error",
        "current_step": "embedding",
        "estimated_cost_usd": None,
    }
    assert client.get(f"{REPORTS}/running/status", headers=READER_HEADERS).json()["current_step"] == "llm_grouping"
    assert client.get(f"{REPORTS}/ready/status", headers=READER_HEADERS).json()["estimated_cost_usd"] == 0.12


@pytest.mark.parametrize(
    "step",
    [
        {"status": "completed", "current_job": "embedding"},
        {"status": "error", "current_job": "unrecognized-private-value"},
        {"status": "error", "current_job": "hierarchical_aggregation", "error": UPLOAD_FAILED_ERROR},
        [],
    ],
)
def test_progress_omits_stale_or_unsafe_step(client, report_files, step):
    report_files("failed", step)
    progress = client.get(f"{REPORTS}/failed/status", headers=READER_HEADERS).json()
    assert progress["status"] == "error"
    assert progress["current_step"] is None


def test_progress_handles_missing_corrupt_or_deleted_reports(client, report_files):
    assert client.get(f"{REPORTS}/running/status", headers=READER_HEADERS).json()["current_step"] is None
    path = report_files("running", {})
    path.write_text("{", encoding="utf-8")
    assert client.get(f"{REPORTS}/running/status", headers=READER_HEADERS).json()["current_step"] is None
    assert client.get(f"{REPORTS}/deleted/status", headers=READER_HEADERS).status_code == 404
    assert client.get(f"{REPORTS}/unknown/status", headers=READER_HEADERS).status_code == 404
    assert client.get(f"{REPORTS}/bad.slug/status", headers=READER_HEADERS).status_code == 400


def test_progress_does_not_follow_link_outside_report_dir(client, report_files, tmp_path):
    outside = tmp_path / "other.json"
    outside.write_text('{"status":"error","current_job":"embedding"}', encoding="utf-8")
    path = report_files("failed", {})
    path.unlink()
    path.symlink_to(outside)
    assert client.get(f"{REPORTS}/failed/status", headers=READER_HEADERS).json()["current_step"] is None
