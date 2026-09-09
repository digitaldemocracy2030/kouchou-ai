import json
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.routers import admin_report, report
from src.schemas.report import ReportStatus, ReportVisibility


@pytest.fixture
def density_api(tmp_path):
    app = FastAPI()
    app.include_router(admin_report.router)
    app.include_router(report.router)
    app.dependency_overrides[admin_report.verify_admin_api_key] = lambda: "test"
    app.dependency_overrides[report.verify_public_api_key] = lambda: "test"
    folder = tmp_path / "density-test"
    folder.mkdir()
    (folder / "hierarchical_result.json").write_text(
        json.dumps({"config": {"question": "テスト"}, "overview": "", "clusters": [], "arguments": []})
    )
    public = type(
        "Report", (), {"slug": "density-test", "status": ReportStatus.READY, "visibility": ReportVisibility.PUBLIC}
    )()
    with (
        patch.object(admin_report.settings, "REPORT_DIR", tmp_path),
        patch.object(report.settings, "REPORT_DIR", tmp_path),
        patch.object(report, "load_status_as_reports", return_value=[public]),
    ):
        yield TestClient(app)


def test_save_reload_and_public_read_preserve_density_and_other_settings(density_api):
    config = {
        "version": "1",
        "enabledCharts": ["scatterDensity", "treemap"],
        "defaultChart": "scatterDensity",
        "chartOrder": ["treemap", "scatterDensity"],
        "params": {"showClusterLabels": False, "scatterDensity": {"maxDensity": 0.35, "minValue": 7}},
    }
    url = "/admin/reports/density-test/visualization-config"
    assert density_api.patch(url, json=config).status_code == 200
    for endpoint in [url, "/reports/density-test"]:
        response = density_api.get(endpoint)
        assert response.status_code == 200
        saved = response.json()["visualizationConfig"]
        for key, value in config.items():
            assert saved[key] == value


@pytest.mark.parametrize("density,minimum", [(-0.1, 5), (1.1, 5), (0.2, -1), (0.2, 1.5), (0.2, True)])
def test_invalid_threshold_does_not_overwrite_saved_config(density_api, density, minimum):
    url = "/admin/reports/density-test/visualization-config"
    valid = {"params": {"scatterDensity": {"maxDensity": 0.2, "minValue": 5}}}
    assert density_api.patch(url, json=valid).status_code == 200
    bad = {"params": {"scatterDensity": {"maxDensity": density, "minValue": minimum}}}
    assert density_api.patch(url, json=bad).status_code == 422
    assert (
        density_api.get(url).json()["visualizationConfig"]["params"]["scatterDensity"]
        == valid["params"]["scatterDensity"]
    )
