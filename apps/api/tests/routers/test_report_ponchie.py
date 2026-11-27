import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import openai
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.routers import admin_report
from src.schemas.report import ReportStatus

PNG = b"\x89PNG\r\n\x1a\nexample"


@pytest.fixture
def ponchie(tmp_path, monkeypatch):
    settings = SimpleNamespace(
        REPORT_DIR=tmp_path,
        ADMIN_API_KEY="admin",
        OPENAI_API_KEY="fake-image-key",
        REPORT_IMAGE_MODEL="fake-image-model",
    )
    monkeypatch.setattr(admin_report, "settings", settings)
    monkeypatch.setattr(
        admin_report, "load_status_as_reports", lambda: [SimpleNamespace(slug="demo", status=ReportStatus.READY)]
    )
    generate = AsyncMock(return_value=PNG)
    monkeypatch.setattr(admin_report, "generate_ponchie_png", generate)
    path = tmp_path / "demo" / "hierarchical_result.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "config": {"name": "demo-input", "question": "街の交通", "user_api_key": "DO_NOT_SEND_KEY"},
                "overview": "交通と移動の検討",
                "clusters": [
                    {"level": 1, "label": "自転車", "value": 5},
                    {"level": 2, "label": "DO_NOT_SEND_SUBTOPIC", "value": 3},
                ],
                "comments": {"1": {"comment": "DO_NOT_SEND_ORIGINAL"}},
                "arguments": [{"argument": "DO_NOT_SEND_OPINION"}],
            }
        ),
        encoding="utf-8",
    )
    app = FastAPI()
    app.include_router(admin_report.router)
    return TestClient(app), settings, generate


def test_requires_admin_key_and_ready_report(ponchie):
    client, _, generate = ponchie
    assert client.post("/admin/reports/demo/ponchie").status_code == 401
    assert client.post("/admin/reports/absent/ponchie", headers={"x-api-key": "admin"}).status_code == 404
    generate.assert_not_awaited()


def test_uses_only_the_report_summary_and_top_level_topics(ponchie):
    client, _, generate = ponchie
    response = client.post("/admin/reports/demo/ponchie", headers={"x-api-key": "admin"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-type"] == "image/png"
    assert response.content == PNG
    prompt, key, model = generate.await_args.args
    assert "街の交通" in prompt and "自転車" in prompt and "交通と移動の検討" in prompt
    assert '"題名": "街の交通"' in prompt and "demo-input" not in prompt
    assert "DO_NOT_SEND" not in prompt
    assert (key, model) == ("fake-image-key", "fake-image-model")


def test_disabled_without_model_and_hides_provider_error_details(ponchie):
    client, settings, generate = ponchie
    settings.REPORT_IMAGE_MODEL = None
    assert client.post("/admin/reports/demo/ponchie", headers={"x-api-key": "admin"}).status_code == 503
    generate.assert_not_awaited()
    settings.REPORT_IMAGE_MODEL = "fake-image-model"
    generate.side_effect = openai.OpenAIError("private provider details")
    response = client.post("/admin/reports/demo/ponchie", headers={"x-api-key": "admin"})
    assert response.status_code == 502
    assert "private provider details" not in response.text
