import json
from copy import deepcopy
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.routers import admin_report, report
from src.schemas.report import ReportStatus, ReportVisibility
from src.schemas.visualization_config import ReportDisplayConfig, parse_saved_visualization_config


@pytest.fixture
def density_api(tmp_path):
    """同じ一時保存先を使う管理用・公開用APIを提供する。"""
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
    """保存した密度と他の表示設定を両方のAPIから取得できる。"""
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
    """新しい不正な値の保存を拒否し、既存ファイルを保持する。"""
    url = "/admin/reports/density-test/visualization-config"
    valid = {"params": {"scatterDensity": {"maxDensity": 0.2, "minValue": 5}}}
    assert density_api.patch(url, json=valid).status_code == 200
    bad = {"params": {"scatterDensity": {"maxDensity": density, "minValue": minimum}}}
    assert density_api.patch(url, json=bad).status_code == 422
    assert (
        density_api.get(url).json()["visualizationConfig"]["params"]["scatterDensity"]
        == valid["params"]["scatterDensity"]
    )


@pytest.mark.parametrize("camel_case", [False, True])
@pytest.mark.parametrize(
    "field,value,expected",
    [
        ("max_density", 1.1, 0.2),
        ("max_density", -0.1, 0.2),
        ("max_density", float("nan"), 0.2),
        ("max_density", float("inf"), 0.2),
        ("min_value", -1, 5),
        ("min_value", 1.5, 5),
        ("min_value", True, 5),
    ],
)
def test_legacy_density_recovers_only_invalid_field(density_api, tmp_path, camel_case, field, value, expected):
    """旧設定の無効な閾値だけを補い、他の表示設定と保存ファイルを変更しない。"""
    config = ReportDisplayConfig.model_validate(
        {
            "enabledCharts": ["treemap", "scatterDensity"],
            "defaultChart": "treemap",
            "chartOrder": ["treemap", "scatterDensity"],
            "params": {"showClusterLabels": False, "scatterDensity": {"maxDensity": 0.35, "minValue": 7}},
        }
    ).model_dump(by_alias=camel_case)
    density_key = "scatterDensity" if camel_case else "scatter_density"
    field_key = {"max_density": "maxDensity", "min_value": "minValue"}[field] if camel_case else field
    config["params"][density_key][field_key] = value
    config_path = tmp_path / "density-test" / "visualization_config.json"
    original = json.dumps(config)
    config_path.write_text(original)

    expected_density = {"maxDensity": 0.35, "minValue": 7}
    expected_density[{"max_density": "maxDensity", "min_value": "minValue"}[field]] = expected
    for endpoint in ["/admin/reports/density-test/visualization-config", "/reports/density-test"]:
        response = density_api.get(endpoint)
        assert response.status_code == 200
        saved = response.json()["visualizationConfig"]
        assert saved["enabledCharts"] == ["treemap", "scatterDensity"]
        assert saved["defaultChart"] == "treemap"
        assert saved["chartOrder"] == ["treemap", "scatterDensity"]
        assert saved["params"]["showClusterLabels"] is False
        assert saved["params"]["scatterDensity"] == expected_density
        assert config_path.read_text() == original


def test_saved_config_recovery_does_not_mutate_input_or_hide_other_errors():
    """密度の補正は入力を変更せず、密度以外の不正な設定は引き続き拒否する。"""
    raw_config = {"params": {"scatterDensity": {"maxDensity": 1.1, "minValue": -1}}}
    original = deepcopy(raw_config)
    saved = parse_saved_visualization_config(raw_config).model_dump(by_alias=True)
    assert saved["params"]["scatterDensity"] == {"maxDensity": 0.2, "minValue": 5}
    assert raw_config == original

    for config in [None, [], {"enabledCharts": 5}, {**raw_config, "enabledCharts": 5}]:
        with pytest.raises(ValidationError):
            parse_saved_visualization_config(config)
