import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from src.schemas.report import Report, ReportStatus, ReportVisibility
from src.services import report_status
from src.services.report_status import add_analysis_data, convert_old_format_status


# FIXME: report_status.jsonのフォーマット変更に対応するための関数のテストコード。広聴AIをver3.0にした段階で削除する。
# https://github.com/digitaldemocracy2030/kouchou-ai/issues/507
class TestReportStatus:
    """レポートステータス関連のテスト"""

    @pytest.fixture
    def old_format_public_data(self):
        """is_public: trueを持つ旧形式のデータ"""
        return {
            "test-slug": {
                "slug": "test-slug",
                "status": "ready",
                "title": "テストタイトル",
                "description": "テスト説明",
                "is_pubcom": True,
                "created_at": "2025-05-13T07:56:58.405239+00:00",
                "is_public": True,
            }
        }

    @pytest.fixture
    def old_format_private_data(self):
        """is_public: falseを持つ旧形式のデータ"""
        return {
            "test-slug": {
                "slug": "test-slug",
                "status": "ready",
                "title": "テストタイトル",
                "description": "テスト説明",
                "is_pubcom": True,
                "created_at": "2025-05-13T07:56:58.405239+00:00",
                "is_public": False,
            }
        }

    @pytest.fixture
    def new_format_data(self):
        """visibilityを持つ新形式のデータ"""
        return {
            "test-slug": {
                "slug": "test-slug",
                "status": "ready",
                "title": "テストタイトル",
                "description": "テスト説明",
                "is_pubcom": True,
                "visibility": "unlisted",
                "created_at": "2025-05-13T07:56:58.405239+00:00",
            }
        }

    @pytest.fixture
    def mixed_format_data(self):
        """旧形式と新形式が混在したデータ"""
        return {
            "old-slug": {
                "slug": "old-slug",
                "status": "ready",
                "title": "旧形式タイトル",
                "description": "旧形式説明",
                "is_pubcom": True,
                "created_at": "2025-05-13T07:56:58.405239+00:00",
                "is_public": True,
            },
            "new-slug": {
                "slug": "new-slug",
                "status": "ready",
                "title": "新形式タイトル",
                "description": "新形式説明",
                "is_pubcom": True,
                "visibility": "unlisted",
                "created_at": "2025-05-13T07:56:58.405239+00:00",
            },
        }

    def test_convert_is_public_true_to_visibility_public(self, old_format_public_data):
        """is_public: trueをvisibility: publicに変換するテスト"""
        # 入力データのコピーを作成して元のデータが変更されないようにする
        input_data = deepcopy(old_format_public_data)

        # 関数を実行
        result = convert_old_format_status(input_data)

        # 結果を検証
        assert "test-slug" in result
        assert "visibility" in result["test-slug"]
        assert result["test-slug"]["visibility"] == ReportVisibility.PUBLIC.value
        assert "is_public" not in result["test-slug"]

    def test_convert_is_public_false_to_visibility_private(self, old_format_private_data):
        """is_public: falseをvisibility: privateに変換するテスト"""
        # 入力データのコピーを作成して元のデータが変更されないようにする
        input_data = deepcopy(old_format_private_data)

        # 関数を実行
        result = convert_old_format_status(input_data)

        # 結果を検証
        assert "test-slug" in result
        assert "visibility" in result["test-slug"]
        assert result["test-slug"]["visibility"] == ReportVisibility.PRIVATE.value
        assert "is_public" not in result["test-slug"]

    def test_new_format_data_unchanged(self, new_format_data):
        """既に新形式になっているデータは変更されないことを確認するテスト"""
        # 入力データのコピーを作成して元のデータが変更されないようにする
        input_data = deepcopy(new_format_data)
        original_visibility = input_data["test-slug"]["visibility"]

        # 関数を実行
        result = convert_old_format_status(input_data)

        # 結果を検証
        assert "test-slug" in result
        assert "visibility" in result["test-slug"]
        assert result["test-slug"]["visibility"] == original_visibility
        assert "is_public" not in result["test-slug"]

    def test_empty_dict(self):
        """空の辞書を渡した場合のテスト"""
        # 空の辞書を渡す
        input_data = {}

        # 関数を実行
        result = convert_old_format_status(input_data)

        # 結果を検証
        assert result == {}

    def test_fill_missing_slug_from_status_key(self):
        """slug フィールドが欠落している場合、status key から補完する"""
        input_data = {
            "missing-slug": {
                "status": "ready",
                "title": "テストタイトル",
                "description": "テスト説明",
                "is_pubcom": True,
                "visibility": "public",
                "created_at": "2025-05-13T07:56:58.405239+00:00",
            }
        }

        result = convert_old_format_status(deepcopy(input_data))

        assert result["missing-slug"]["slug"] == "missing-slug"

    def test_mixed_format_data(self, mixed_format_data):
        """旧形式と新形式が混在したデータのテスト"""
        # 入力データのコピーを作成して元のデータが変更されないようにする
        input_data = deepcopy(mixed_format_data)
        original_new_visibility = input_data["new-slug"]["visibility"]

        # 関数を実行
        result = convert_old_format_status(input_data)

        # 結果を検証
        # 旧形式のデータが変換されていることを確認
        assert "old-slug" in result
        assert "visibility" in result["old-slug"]
        assert result["old-slug"]["visibility"] == ReportVisibility.PUBLIC.value
        assert "is_public" not in result["old-slug"]

        # 新形式のデータが変更されていないことを確認
        assert "new-slug" in result
        assert "visibility" in result["new-slug"]
        assert result["new-slug"]["visibility"] == original_new_visibility
        assert "is_public" not in result["new-slug"]

    @patch("src.services.report_status.STATE_FILE", Path("/fake/report_status.json"))
    def test_load_status_as_reports_fills_missing_slug(self):
        """一覧読み出し時にも key 由来の slug 補完で ValidationError を避ける"""
        status_data = {
            "legacy-report": {
                "status": "ready",
                "title": "Legacy Report",
                "description": "Legacy Description",
                "is_pubcom": False,
                "visibility": "public",
                "created_at": "2025-05-13T07:56:58.405239+00:00",
            }
        }

        report_status._report_status.clear()

        with patch("builtins.open", mock_open(read_data=json.dumps(status_data))):
            reports = report_status.load_status_as_reports()

        assert len(reports) == 1
        assert reports[0].slug == "legacy-report"
        assert reports[0].status == ReportStatus.READY


class TestAddAnalysisData:
    @pytest.fixture
    def ready_report(self):
        return Report(
            slug="test-report",
            status=ReportStatus.READY,
            title="Test Report",
            description="Description",
            visibility=ReportVisibility.PUBLIC,
        )

    @pytest.fixture
    def mock_hierarchical_result(self):
        return {
            "comment_num": 150,
            "arguments": [{"id": 1}, {"id": 2}, {"id": 3}],
            "clusters": [
                {"id": 1, "level": 1},
                {"id": 2, "level": 2},
                {"id": 3, "level": 2},
            ],
        }

    @patch("src.services.report_status.settings")
    def test_add_analysis_data_success(self, mock_settings, ready_report, mock_hierarchical_result):
        mock_settings.REPORT_DIR = Path("/fake/path")
        json_data = json.dumps(mock_hierarchical_result)

        with patch("builtins.open", mock_open(read_data=json_data)):
            updated = add_analysis_data(ready_report)

        assert updated.analysis is not None
        assert updated.analysis.comment_num == 150
        assert updated.analysis.arguments_num == 3
        assert updated.analysis.cluster_num == 1  # level 1 のみ

    @patch("src.services.report_status.settings")
    def test_add_analysis_data_file_not_found(self, mock_settings, ready_report):
        mock_settings.REPORT_DIR = Path("/fake/path")

        with patch("builtins.open", side_effect=FileNotFoundError):
            updated = add_analysis_data(ready_report)

        assert updated.analysis is None

    @patch("src.services.report_status.settings")
    def test_add_analysis_data_json_decode_error(self, mock_settings, ready_report):
        mock_settings.REPORT_DIR = Path("/fake/path")

        with patch("builtins.open", mock_open(read_data="invalid json")):
            updated = add_analysis_data(ready_report)

        assert updated.analysis is None

    def test_add_analysis_data_non_ready_status(self):
        processing_report = Report(
            slug="slug",
            status=ReportStatus.PROCESSING,
            title="title",
            description="desc",
            visibility=ReportVisibility.PRIVATE,
        )

        updated = add_analysis_data(processing_report)
        assert updated == processing_report
        assert updated.analysis is None


class TestSaveStatusAtomicity:
    """save_status() の atomic 書き込み・round-trip のテスト"""

    @pytest.fixture(autouse=True)
    def _reset_global(self):
        """各テストの前後でモジュールグローバルを掃除する"""
        original = deepcopy(report_status._report_status)
        report_status._report_status.clear()
        yield
        report_status._report_status.clear()
        report_status._report_status.update(original)

    def test_save_status_keeps_original_on_write_failure(self, tmp_path):
        """書き込みが途中で失敗しても、既存の STATE_FILE が破損しないこと。

        旧実装は open(STATE_FILE, "w") で先に truncate するため、json.dump が
        失敗すると既存ファイルが空になり、同時に走る GET /admin/reports が
        空の一覧を読んでしまう。atomic な書き込み(temp + os.replace)なら、
        書き込み失敗時も元ファイルが丸ごと残る。
        """
        state_file = tmp_path / "report_status.json"
        original_content = {
            "existing-slug": {
                "slug": "existing-slug",
                "status": "ready",
                "title": "既存レポート",
                "description": "既存説明",
                "is_pubcom": False,
                "visibility": "public",
                "created_at": "2025-05-13T07:56:58.405239+00:00",
            }
        }
        state_file.write_text(
            json.dumps(original_content, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )

        report_status._report_status.clear()
        report_status._report_status.update({"new-slug": {"slug": "new-slug", "status": "processing"}})

        with patch("src.services.report_status.STATE_FILE", state_file):
            # 書き込みを途中で失敗させる
            with patch("src.services.report_status.json.dump", side_effect=RuntimeError("boom")):
                with pytest.raises(RuntimeError):
                    report_status.save_status()

        # 失敗後も元ファイルの内容がそのまま残っていること
        raw = state_file.read_text(encoding="utf-8")
        assert raw != "", "既存ファイルが truncate されて空になった (非 atomic な書き込み)"
        assert json.loads(raw) == original_content
        # temp ファイルが残っていないこと
        leftovers = [p.name for p in tmp_path.iterdir() if p.name != "report_status.json"]
        assert leftovers == [], f"temp ファイルが掃除されていない: {leftovers}"

    def test_save_status_then_load_status_round_trip(self, tmp_path):
        """save_status() した内容を load_status() で読み戻せること"""
        state_file = tmp_path / "report_status.json"
        data = {
            "round-trip-slug": {
                "slug": "round-trip-slug",
                "status": "ready",
                "title": "ラウンドトリップ",
                "description": "説明",
                "is_pubcom": False,
                "visibility": "public",
                "created_at": "2025-05-13T07:56:58.405239+00:00",
            }
        }

        with patch("src.services.report_status.STATE_FILE", state_file):
            report_status._report_status.clear()
            report_status._report_status.update(deepcopy(data))
            report_status.save_status()

            # ディスクに書けていること
            assert state_file.exists()

            # グローバルをクリアしてからディスクから読み戻す
            report_status._report_status.clear()
            report_status.load_status()

        assert report_status._report_status == data

    def test_load_status_acquires_lock(self, tmp_path):
        """load_status() が _lock を取得してから読み込むこと"""
        state_file = tmp_path / "report_status.json"
        state_file.write_text("{}", encoding="utf-8")

        real_lock = report_status._lock
        entered = {"value": False}

        class _TrackingLock:
            def __enter__(self):
                entered["value"] = True
                return real_lock.__enter__()

            def __exit__(self, *args):
                return real_lock.__exit__(*args)

        with patch("src.services.report_status.STATE_FILE", state_file):
            with patch("src.services.report_status._lock", _TrackingLock()):
                report_status.load_status()

        assert entered["value"] is True


class TestLegacyStatusEntries:
    """古いバージョンで作られた report_status.json のエントリを読めること

    v1.0.x の add_new_report_to_status は slug・status・title・description の 4 キーしか書かず、
    v2.0.x も公開設定を切り替えない限り is_public をファイルに書かなかった。
    このようなエントリが 1 件でもあると、一覧の読み込み全体が ValidationError で失敗していた。
    """

    # v1.0.0 の add_new_report_to_status が書く形（visibility も is_public も無い）
    V1_ENTRY = {"slug": "v100a", "status": "ready", "title": "Q v100a", "description": "intro"}
    # v2.0.0 で公開設定を切り替えたエントリ（is_public だけを持つ）
    V2_ENTRY = {
        "slug": "v200b",
        "status": "ready",
        "title": "Q v200b",
        "description": "intro",
        "is_pubcom": True,
        "is_public": True,
        "created_at": "2026-10-23T12:19:04.341019+00:00",
    }
    CURRENT_ENTRY = {
        "slug": "v410a",
        "status": "ready",
        "title": "Q v410a",
        "description": "intro",
        "is_pubcom": True,
        "visibility": "public",
        "created_at": "2026-10-23T12:30:00+00:00",
    }

    @pytest.fixture(autouse=True)
    def _reset_global(self):
        original = deepcopy(report_status._report_status)
        report_status._report_status.clear()
        yield
        report_status._report_status.clear()
        report_status._report_status.update(original)

    @pytest.fixture
    def state_file(self, tmp_path, monkeypatch):
        path = tmp_path / "report_status.json"
        path.write_text(
            json.dumps({"v100a": self.V1_ENTRY, "v200b": self.V2_ENTRY, "v410a": self.CURRENT_ENTRY}),
            encoding="utf-8",
        )
        monkeypatch.setattr(report_status, "STATE_FILE", path)
        return path

    def test_convert_entry_without_visibility_and_is_public_to_private(self):
        """visibility も is_public も無いエントリは非公開として扱う"""
        result = convert_old_format_status({"v100a": deepcopy(self.V1_ENTRY)})

        assert result["v100a"]["visibility"] == ReportVisibility.PRIVATE.value

    def test_load_status_as_reports_reads_v1_entry(self, state_file):
        reports = {r.slug: r for r in report_status.load_status_as_reports()}

        assert set(reports) == {"v100a", "v200b", "v410a"}
        assert reports["v100a"].visibility == ReportVisibility.PRIVATE
        assert reports["v200b"].visibility == ReportVisibility.PUBLIC
        assert reports["v410a"].visibility == ReportVisibility.PUBLIC

    def test_load_status_as_reports_skips_invalid_entry(self, tmp_path, monkeypatch):
        """検証に通らないエントリが 1 件あっても、他のレポートは読める"""
        path = tmp_path / "report_status.json"
        broken = {
            "slug": "broken",
            "status": "unknown-status",
            "title": "t",
            "description": "d",
            "visibility": "public",
        }
        path.write_text(json.dumps({"broken": broken, "v410a": self.CURRENT_ENTRY}), encoding="utf-8")
        monkeypatch.setattr(report_status, "STATE_FILE", path)

        warnings: list[str] = []
        monkeypatch.setattr(report_status.logger, "warning", lambda msg, *a, **k: warnings.append(msg))

        reports = report_status.load_status_as_reports(include_deleted=True)

        assert [r.slug for r in reports] == ["v410a"]
        assert any("broken" in w for w in warnings)
        # 飛ばしたエントリは保存時に消えないよう、メモリ上の生データには残す
        assert report_status._report_status["broken"]["status"] == "unknown-status"

    def test_public_and_admin_endpoints_with_v1_entry(self, state_file, client, test_settings):
        """v1 のエントリがあっても一覧・公開ページが 500 にならない"""
        public_headers = {"x-api-key": test_settings.PUBLIC_API_KEY}
        admin_headers = {"x-api-key": test_settings.ADMIN_API_KEY}

        public_list = client.get("/reports", headers=public_headers)
        assert public_list.status_code == 200
        # 非公開扱いなので、公開一覧には出ない
        assert [r["slug"] for r in public_list.json()] == ["v200b", "v410a"]

        admin_list = client.get("/admin/reports", headers=admin_headers)
        assert admin_list.status_code == 200
        assert {r["slug"]: r["visibility"] for r in admin_list.json()}["v100a"] == "private"

        # 他のレポートの公開ページは、成果物が無いので 404（500 ではない）
        assert client.get("/reports/v410a", headers=public_headers).status_code == 404
        # v1 のレポートは非公開扱いなので 404
        response = client.get("/reports/v100a", headers=public_headers)
        assert response.status_code == 404
        assert response.json()["detail"] == "Report is private"

    def test_recover_interrupted_reports_with_v1_entry(self, tmp_path, monkeypatch):
        """v1 のエントリがあっても、起動時の復旧処理が processing のレポートを確定する"""
        from src.services import report_launcher

        report_dir = tmp_path / "reports"
        report_dir.mkdir()
        path = tmp_path / "report_status.json"
        processing = {**self.CURRENT_ENTRY, "slug": "running", "status": "processing"}
        path.write_text(json.dumps({"v100a": self.V1_ENTRY, "running": processing}), encoding="utf-8")
        monkeypatch.setattr(report_status, "STATE_FILE", path)
        monkeypatch.setattr(report_launcher.settings, "REPORT_DIR", report_dir)

        class DummyReportSyncService:
            def sync_status_file_to_storage(self):
                return True

        monkeypatch.setattr(report_launcher, "ReportSyncService", DummyReportSyncService)

        report_launcher.recover_interrupted_reports()

        saved = json.loads(path.read_text(encoding="utf-8"))
        assert saved["running"]["status"] == "error"
        assert saved["v100a"]["status"] == "ready"
