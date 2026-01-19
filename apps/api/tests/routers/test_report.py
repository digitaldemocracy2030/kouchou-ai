"""Test cases for public report endpoints."""

import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.schemas.report import ReportStatus, ReportVisibility


class TestReportEndpoint:
    """Test cases for /reports/{slug} endpoint."""

    def test_get_report_with_visibility_public(self, client: TestClient, temp_report_dir, test_settings):
        """正常系：publicなレポートの取得とvisibilityフィールドの確認"""
        slug = "test-public-report"

        # テスト用のレポートファイルを作成
        report_dir = temp_report_dir / slug
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / "hierarchical_result.json"
        report_data = {"config": {"question": "テスト質問"}, "overview": "テスト概要", "clusters": [], "arguments": []}
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f)

        # モックレポートステータスを設定
        mock_reports = [
            type("Report", (), {"slug": slug, "status": ReportStatus.READY, "visibility": ReportVisibility.PUBLIC})()
        ]

        # settings.REPORT_DIRをパッチして、report routerがテスト用ディレクトリを使用するようにする
        with (
            patch("src.routers.report.settings.REPORT_DIR", temp_report_dir),
            patch("src.routers.report.load_status_as_reports", return_value=mock_reports),
        ):
            # test_settingsからAPIキーを取得
            response = client.get(f"/reports/{slug}", headers={"x-api-key": test_settings.PUBLIC_API_KEY})

        assert response.status_code == 200
        response_data = response.json()

        # visibilityフィールドが正しく含まれていることを確認
        assert response_data["visibility"] == "public"
        assert response_data["config"]["question"] == "テスト質問"
        assert response_data["overview"] == "テスト概要"

    def test_get_report_with_visibility_unlisted(self, client: TestClient, temp_report_dir, test_settings):
        """正常系：限定公開のレポートの取得とvisibilityフィールドの確認"""
        slug = "test-unlisted-report"

        # テスト用のレポートファイルを作成
        report_dir = temp_report_dir / slug
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / "hierarchical_result.json"
        report_data = {
            "config": {"question": "限定公開レポートの質問"},
            "overview": "限定公開レポートの概要",
            "clusters": [],
            "arguments": [],
        }
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f)

        # モックレポートステータスを設定
        mock_reports = [
            type("Report", (), {"slug": slug, "status": ReportStatus.READY, "visibility": ReportVisibility.UNLISTED})()
        ]

        # settings.REPORT_DIRをパッチして、report routerがテスト用ディレクトリを使用するようにする
        with (
            patch("src.routers.report.settings.REPORT_DIR", temp_report_dir),
            patch("src.routers.report.load_status_as_reports", return_value=mock_reports),
        ):
            # test_settingsからAPIキーを取得
            response = client.get(f"/reports/{slug}", headers={"x-api-key": test_settings.PUBLIC_API_KEY})

        assert response.status_code == 200
        response_data = response.json()

        # visibilityフィールドが正しく含まれていることを確認
        assert response_data["visibility"] == "unlisted"

    def test_get_private_report_returns_404(self, client: TestClient, temp_report_dir, test_settings):
        """異常系：非公開のレポートは404を返す"""
        slug = "test-private-report"

        # テスト用のレポートファイルを作成
        report_dir = temp_report_dir / slug
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / "hierarchical_result.json"
        report_data = {"config": {"question": "非公開のレポートの質問"}}
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f)

        # モックレポートステータスを設定
        mock_reports = [
            type("Report", (), {"slug": slug, "status": ReportStatus.READY, "visibility": ReportVisibility.PRIVATE})()
        ]

        # settings.REPORT_DIRをパッチして、report routerがテスト用ディレクトリを使用するようにする
        with (
            patch("src.routers.report.settings.REPORT_DIR", temp_report_dir),
            patch("src.routers.report.load_status_as_reports", return_value=mock_reports),
        ):
            # test_settingsからAPIキーを取得
            response = client.get(f"/reports/{slug}", headers={"x-api-key": test_settings.PUBLIC_API_KEY})

        assert response.status_code == 404
        assert "Report is private" in response.json()["detail"]

    def test_get_nonexistent_report_returns_404(self, client: TestClient, temp_report_dir, test_settings):
        """異常系：存在しないレポートは404を返す"""
        # settings.REPORT_DIRをパッチして、report routerがテスト用ディレクトリを使用するようにする
        with (
            patch("src.routers.report.settings.REPORT_DIR", temp_report_dir),
            patch("src.routers.report.load_status_as_reports", return_value=[]),
        ):
            # test_settingsからAPIキーを取得
            response = client.get("/reports/nonexistent-slug", headers={"x-api-key": test_settings.PUBLIC_API_KEY})

        assert response.status_code == 404
        assert "Report not found" in response.json()["detail"]


class TestVisualizationConfigMerge:
    """Test cases for visualization config merge in /reports/{slug} endpoint."""

    def test_visualization_config_snake_case_converted_to_camel_case(
        self, client: TestClient, temp_report_dir, test_settings
    ):
        """snake_caseで保存されたvisualization_config.jsonがcamelCaseで返される"""
        slug = "test-viz-config"

        # レポートディレクトリとファイルを作成
        report_dir = temp_report_dir / slug
        report_dir.mkdir(parents=True, exist_ok=True)

        report_file = report_dir / "hierarchical_result.json"
        report_data = {"config": {"question": "テスト"}, "overview": "", "clusters": [], "arguments": []}
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f)

        # snake_caseでvisualization_config.jsonを作成
        viz_config_file = report_dir / "visualization_config.json"
        viz_config_data = {
            "version": "1",
            "enabled_charts": ["scatterAll", "treemap"],
            "default_chart": "treemap",
            "params": {"show_cluster_labels": False, "scatter_density": {"max_density": 0.5, "min_value": 10}},
        }
        with open(viz_config_file, "w", encoding="utf-8") as f:
            json.dump(viz_config_data, f)

        mock_reports = [
            type("Report", (), {"slug": slug, "status": ReportStatus.READY, "visibility": ReportVisibility.PUBLIC})()
        ]

        with (
            patch("src.routers.report.settings.REPORT_DIR", temp_report_dir),
            patch("src.routers.report.load_status_as_reports", return_value=mock_reports),
        ):
            response = client.get(f"/reports/{slug}", headers={"x-api-key": test_settings.PUBLIC_API_KEY})

        assert response.status_code == 200
        data = response.json()

        # visualizationConfigがcamelCaseで返されることを確認
        assert "visualizationConfig" in data
        viz_config = data["visualizationConfig"]
        assert viz_config["version"] == "1"
        assert viz_config["enabledCharts"] == ["scatterAll", "treemap"]
        assert viz_config["defaultChart"] == "treemap"
        assert viz_config["params"]["showClusterLabels"] is False
        assert viz_config["params"]["scatterDensity"]["maxDensity"] == 0.5
        assert viz_config["params"]["scatterDensity"]["minValue"] == 10

    def test_visualization_config_not_present_when_file_missing(
        self, client: TestClient, temp_report_dir, test_settings
    ):
        """visualization_config.jsonが存在しない場合はvisializationConfigフィールドが含まれない"""
        slug = "test-no-viz-config"

        report_dir = temp_report_dir / slug
        report_dir.mkdir(parents=True, exist_ok=True)

        report_file = report_dir / "hierarchical_result.json"
        report_data = {"config": {"question": "テスト"}, "overview": "", "clusters": [], "arguments": []}
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f)

        mock_reports = [
            type("Report", (), {"slug": slug, "status": ReportStatus.READY, "visibility": ReportVisibility.PUBLIC})()
        ]

        with (
            patch("src.routers.report.settings.REPORT_DIR", temp_report_dir),
            patch("src.routers.report.load_status_as_reports", return_value=mock_reports),
        ):
            response = client.get(f"/reports/{slug}", headers={"x-api-key": test_settings.PUBLIC_API_KEY})

        assert response.status_code == 200
        data = response.json()
        assert "visualizationConfig" not in data

    def test_visualization_config_invalid_returns_default(self, client: TestClient, temp_report_dir, test_settings):
        """不正なvisualization_config.jsonの場合はデフォルト設定が返される"""
        slug = "test-invalid-viz-config"

        report_dir = temp_report_dir / slug
        report_dir.mkdir(parents=True, exist_ok=True)

        report_file = report_dir / "hierarchical_result.json"
        report_data = {"config": {"question": "テスト"}, "overview": "", "clusters": [], "arguments": []}
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f)

        # 不正な値を持つvisualization_config.jsonを作成
        viz_config_file = report_dir / "visualization_config.json"
        viz_config_data = {
            "version": "1",
            "enabled_charts": ["invalidChart"],  # 不正なチャートタイプ
        }
        with open(viz_config_file, "w", encoding="utf-8") as f:
            json.dump(viz_config_data, f)

        mock_reports = [
            type("Report", (), {"slug": slug, "status": ReportStatus.READY, "visibility": ReportVisibility.PUBLIC})()
        ]

        with (
            patch("src.routers.report.settings.REPORT_DIR", temp_report_dir),
            patch("src.routers.report.load_status_as_reports", return_value=mock_reports),
        ):
            response = client.get(f"/reports/{slug}", headers={"x-api-key": test_settings.PUBLIC_API_KEY})

        assert response.status_code == 200
        data = response.json()

        # デフォルト設定が返されることを確認
        assert "visualizationConfig" in data
        viz_config = data["visualizationConfig"]
        assert viz_config["enabledCharts"] == ["scatterAll", "scatterDensity", "treemap"]
        assert viz_config["defaultChart"] == "scatterAll"
