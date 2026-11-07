"""Test cases for public report endpoints."""

import json
import os
from pathlib import Path
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

    def test_get_report_without_config_returns_500(self, client: TestClient, temp_report_dir, test_settings):
        """異常系：viewer 契約を満たさない report は 500 を返す"""
        slug = "test-invalid-report"

        report_dir = temp_report_dir / slug
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / "hierarchical_result.json"
        report_data = {"overview": "テスト概要", "clusters": [], "arguments": []}
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

        assert response.status_code == 500
        assert response.json()["detail"] == "Invalid report data"


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


class TestReportsListEndpoint:
    """Test cases for public /reports endpoint."""

    def test_reports_does_not_expose_source_slug_or_internal_fields(self, client: TestClient, test_settings):
        """公開一覧は複製元の slug（限定公開レポートの推測不能な slug を含みうる）や内部情報を返さない"""
        from src.schemas.report import AnalysisData, Report

        reports = [
            Report(
                slug="public-copy",
                source_slug="unlisted-secret-uuid",
                title="複製",
                description="説明",
                status=ReportStatus.READY,
                visibility=ReportVisibility.PUBLIC,
                created_at="2025-05-13T07:56:58.405239+00:00",
                token_usage=100,
                token_usage_input=60,
                token_usage_output=40,
                estimated_cost=0.12,
                provider="openai",
                model="gpt-4o-mini",
                analysis=AnalysisData(comment_num=10, arguments_num=20, cluster_num=3),
                # 管理画面向けの警告コード（#1120）も公開一覧には出さない
                warnings=["source_input_reconstructed"],
            ),
            Report(
                slug="unlisted-secret-uuid",
                title="元",
                description="説明",
                status=ReportStatus.READY,
                visibility=ReportVisibility.UNLISTED,
            ),
        ]
        with patch("src.routers.report.load_status_as_reports", return_value=reports):
            response = client.get("/reports", headers={"x-api-key": test_settings.PUBLIC_API_KEY})

        assert response.status_code == 200
        body = response.json()
        assert [r["slug"] for r in body] == ["public-copy"]
        assert "unlisted-secret-uuid" not in response.text
        assert "source_input_reconstructed" not in response.text
        for key in (
            "sourceSlug",
            "tokenUsage",
            "tokenUsageInput",
            "tokenUsageOutput",
            "estimatedCost",
            "provider",
            "model",
            "analysis",
            "warnings",
        ):
            assert key not in body[0]
        # 返す項目は public-viewer の Report 型（apps/public-viewer/type.ts）と同じものだけ
        assert set(body[0]) == {"slug", "title", "description", "status", "visibility", "isPubcom", "createdAt"}
        # public-viewer が使う項目は残す
        assert body[0]["title"] == "複製"
        assert body[0]["description"] == "説明"
        assert body[0]["visibility"] == "public"
        assert body[0]["status"] == "ready"
        assert body[0]["isPubcom"] is False
        assert body[0]["createdAt"] == "2025-05-13T07:56:58.405239+00:00"


class TestPublicResultArtifact:
    """/reports/{slug} は公開用レポート結果（public_result.json の契約）だけを返す。"""

    SLUG = "public-result-report"

    @staticmethod
    def _full_result(overview: str = "結果の概要") -> dict:
        return {
            "arguments": [
                {
                    "arg_id": "A1_0",
                    "argument": "意見",
                    "comment_id": "c1",
                    "x": 0.1,
                    "y": 0.2,
                    "p": 0,
                    "cluster_ids": ["0", "1_0"],
                    "attributes": {"age": "20代"},
                    "internal_note": "x",
                }
            ],
            "clusters": [
                {
                    "level": 1,
                    "id": "1_0",
                    "label": "ラベル",
                    "takeaway": "要約",
                    "value": 1,
                    "parent": "0",
                    "density_rank_percentile": 0.5,
                }
            ],
            "comments": {},
            "propertyMap": {"age": {"A1_0": "20代"}, "source": {"A1_0": "internal"}},
            "overview": overview,
            "comment_num": 1,
            "config": {
                "name": "internal-name",
                "input": "internal-input",
                "question": "テスト質問",
                "intro": "イントロ",
                "model": "gpt-4o-mini",
                "user_api_key": "sk-should-not-leak",
                "_input_base_dir": "/srv/internal/path",
                "status": "completed",
                "hierarchical_aggregation": {"hidden_properties": {"source": ["internal"]}, "source_code": "agg"},
                "extraction": {"prompt": "抽出プロンプト", "model": "gpt-4o-mini", "source_code": "ext"},
            },
        }

    def _get(self, client, temp_report_dir, test_settings):
        mock_reports = [
            type(
                "Report", (), {"slug": self.SLUG, "status": ReportStatus.READY, "visibility": ReportVisibility.PUBLIC}
            )()
        ]
        with (
            patch("src.routers.report.settings.REPORT_DIR", temp_report_dir),
            patch("src.routers.report.load_status_as_reports", return_value=mock_reports),
        ):
            return client.get(f"/reports/{self.SLUG}", headers={"x-api-key": test_settings.PUBLIC_API_KEY})

    def _write(self, temp_report_dir, name: str, data) -> Path:
        report_dir = temp_report_dir / self.SLUG
        report_dir.mkdir(parents=True, exist_ok=True)
        path = report_dir / name
        path.write_text(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def test_old_report_without_public_result_is_converted(self, client, temp_report_dir, test_settings):
        """public_result.json の無い古いレポートは、結果からその場で公開用の形に変換して返す"""
        self._write(temp_report_dir, "hierarchical_result.json", self._full_result())

        response = self._get(client, temp_report_dir, test_settings)

        assert response.status_code == 200
        body = response.json()
        assert body["schema_version"] == 1
        assert body["visibility"] == "public"
        assert body["config"]["question"] == "テスト質問"
        assert body["config"]["extraction"]["prompt"] == "抽出プロンプト"
        for key in ("name", "input", "user_api_key", "_input_base_dir", "status"):
            assert key not in body["config"]
        assert body["config"]["hierarchical_aggregation"] == {"source_code": "agg"}
        assert "internal_note" not in body["arguments"][0]
        assert "source" not in body["propertyMap"]
        text = response.text
        assert "sk-should-not-leak" not in text
        assert "/srv/internal/path" not in text
        assert "internal" not in json.dumps(body["propertyMap"])

    def test_stale_public_result_newer_mtime_does_not_leak(self, client, temp_report_dir, test_settings):
        """結果ファイルがあれば、更新日時が新しくても古い写しの public_result.json は使わない

        例：hidden_properties を足す前の写しだけがファイル単位で復元された。写しには隠すと指定した列が
        残っているが、正本から作り直すので返らない。
        """
        from analysis_core.public_result import build_public_result

        stale_source = self._full_result("古い写しの概要")
        stale_source["config"]["hierarchical_aggregation"] = {"source_code": "agg"}
        result_path = self._write(temp_report_dir, "hierarchical_result.json", self._full_result("正本の概要"))
        public_path = self._write(temp_report_dir, "public_result.json", build_public_result(stale_source))
        os.utime(result_path, (1_000_000, 1_000_000))
        os.utime(public_path, (1_000_001, 1_000_001))

        response = self._get(client, temp_report_dir, test_settings)

        assert response.status_code == 200
        body = response.json()
        assert body["overview"] == "正本の概要"
        assert "source" not in body["propertyMap"]

    def test_invalid_public_result_is_ignored_when_result_exists(self, client, temp_report_dir, test_settings):
        """公開用ファイルが壊れていても、契約を満たさなくても、結果ファイルがあればそこから作る"""
        self._write(temp_report_dir, "hierarchical_result.json", self._full_result("結果の概要"))
        for broken in ("{ broken", json.dumps({"overview": "config が無い"})):
            self._write(temp_report_dir, "public_result.json", broken)

            response = self._get(client, temp_report_dir, test_settings)

            assert response.status_code == 200
            assert response.json()["overview"] == "結果の概要"

    def test_public_result_alone_is_not_served(self, client, temp_report_dir, test_settings):
        """正本が無く写し（public_result.json）だけがある場合は返さない

        写しが正本と食い違っていないか（古い写しで隠すべき列が残っていないか）を確かめる手段が無いので、
        従来どおり「レポートが無い」として扱う。
        """
        from analysis_core.public_result import build_public_result

        self._write(temp_report_dir, "public_result.json", build_public_result(self._full_result("写しだけ")))

        response = self._get(client, temp_report_dir, test_settings)

        assert response.status_code == 404
        assert "写しだけ" not in response.text

    def test_non_object_result_returns_500(self, client, temp_report_dir, test_settings):
        """結果ファイルがオブジェクトでなければ 500"""
        self._write(temp_report_dir, "hierarchical_result.json", "[]")

        response = self._get(client, temp_report_dir, test_settings)

        assert response.status_code == 500
        assert response.json()["detail"] == "Invalid report data"
