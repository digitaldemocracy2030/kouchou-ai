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
