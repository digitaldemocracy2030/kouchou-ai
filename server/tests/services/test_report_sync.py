import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import settings
from src.services.report_sync import ReportSyncService


class TestReportSyncService:
    """ReportSyncServiceのテスト"""

    @pytest.fixture
    def mock_storage_service(self):
        """ストレージサービスのモック"""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def report_sync_service(self, mock_storage_service: MagicMock):
        """ReportSyncServiceのインスタンス"""
        with patch("src.services.report_sync.get_storage_service", return_value=mock_storage_service):
            service = ReportSyncService()
            yield service

    @pytest.fixture
    def mock_status_file_empty(self, tmp_path: Path):
        """空のステータスファイルのモック"""
        # 一時ディレクトリに空のステータスファイルを作成
        status_file = tmp_path / "report_status_empty.json"
        status_file.write_text("")

        # テスト用のパスに置き換え
        with patch.object(ReportSyncService, "LOCAL_STATUS_FILE_PATH", status_file):
            yield status_file

    @pytest.fixture
    def mock_status_file_with_data(self, tmp_path: Path):
        """データが入ったステータスファイルのモック"""
        # 一時ディレクトリにデータが入ったステータスファイルを作成
        status_file = tmp_path / "report_status_with_data.json"
        status_file.write_text('{"test": "data"}')

        # テスト用のパスに置き換え
        with patch.object(ReportSyncService, "LOCAL_STATUS_FILE_PATH", status_file):
            yield status_file

    @pytest.fixture
    def mock_report_dir(self, tmp_path: Path):
        """レポートディレクトリのモック"""
        # 一時ディレクトリにレポートディレクトリを作成
        report_dir = tmp_path / "reports"
        report_dir.mkdir()

        # テスト用のスラグディレクトリを作成
        slug_dir = report_dir / "test-slug"
        slug_dir.mkdir()

        # テストファイルを作成
        test_file = slug_dir / "test.json"
        test_file.write_text('{"data": "test"}')

        # テスト用のパスに置き換え
        with patch.object(settings, "REPORT_DIR", report_dir):
            yield report_dir

    def test_init(self, report_sync_service: ReportSyncService, mock_storage_service: MagicMock):
        """初期化時にストレージサービスが取得されることを確認"""
        assert report_sync_service.storage_service == mock_storage_service

    def test_sync_status_file_to_storage_success(
        self, report_sync_service: ReportSyncService, mock_storage_service: MagicMock, mock_status_file_with_data: Path
    ):
        """ステータスファイルのアップロードが成功することを確認"""
        # モックの設定
        mock_storage_service.upload_file.return_value = True

        # 実行
        report_sync_service.sync_status_file_to_storage()

        # 検証
        mock_storage_service.upload_file.assert_called_once_with(
            str(mock_status_file_with_data),
            f"{report_sync_service.REMOTE_STATUS_FILE_PREFIX}/report_status.json",
        )

    def test_sync_status_file_to_storage_file_not_exists(
        self, report_sync_service: ReportSyncService, mock_storage_service: MagicMock
    ):
        """ステータスファイルが存在しない場合、アップロードがスキップされることを確認"""
        # 存在しないファイルパスを設定
        with patch.object(ReportSyncService, "LOCAL_STATUS_FILE_PATH", Path("/non/existent/path.json")):
            # 実行
            report_sync_service.sync_status_file_to_storage()

            # 検証
            mock_storage_service.upload_file.assert_not_called()

    def test_sync_report_files_to_storage_success(
        self, report_sync_service: ReportSyncService, mock_storage_service: MagicMock, mock_report_dir: Path
    ):
        """レポートファイルのアップロードが成功することを確認"""
        # モックの設定
        mock_storage_service.upload_directory.return_value = True

        # 実行
        report_sync_service.sync_report_files_to_storage("test-slug")

        # 検証
        mock_storage_service.upload_directory.assert_called_once_with(
            str(mock_report_dir / "test-slug"),
            f"{report_sync_service.REMOTE_REPORT_DIR_PREFIX}/test-slug",
        )

    def test_download_status_file_from_storage_success(
        self, report_sync_service: ReportSyncService, mock_storage_service: MagicMock, mock_status_file_empty: Path
    ):
        """ステータスファイルのダウンロードが成功することを確認"""
        # モックの設定
        mock_storage_service.download_file.return_value = True

        # 実行
        result = report_sync_service.download_status_file_from_storage()

        # 検証
        assert result is True
        mock_storage_service.download_file.assert_called_once_with(
            f"{report_sync_service.REMOTE_STATUS_FILE_PREFIX}/report_status.json",
            str(mock_status_file_empty),
        )

    def test_download_status_file_from_storage_file_not_found(
        self, report_sync_service: ReportSyncService, mock_storage_service: MagicMock, mock_status_file_empty: Path
    ):
        """ステータスファイルが見つからない場合、Falseが返されることを確認"""
        # モックの設定
        mock_storage_service.download_file.side_effect = FileNotFoundError("File not found")

        # 実行
        result = report_sync_service.download_status_file_from_storage()

        # 検証
        assert result is False
        mock_storage_service.download_file.assert_called_once()

    def test_download_status_file_from_storage_exception(
        self, report_sync_service: ReportSyncService, mock_storage_service: MagicMock, mock_status_file_empty: Path
    ):
        """ダウンロード中に例外が発生した場合、Falseが返されることを確認"""
        # モックの設定
        mock_storage_service.download_file.side_effect = Exception("Download failed")

        # 実行
        result = report_sync_service.download_status_file_from_storage()

        # 検証
        assert result is False
        mock_storage_service.download_file.assert_called_once()

    def test_download_all_report_results_from_storage_success(
        self, report_sync_service: ReportSyncService, mock_storage_service: MagicMock
    ):
        """レポート結果ファイルのダウンロードが成功することを確認"""
        # モックの設定
        mock_storage_service.download_directory.return_value = True

        # 実行
        result = report_sync_service.download_all_report_results_from_storage()

        # 検証
        assert result is True
        mock_storage_service.download_directory.assert_called_once_with(
            str(report_sync_service.REMOTE_REPORT_DIR_PREFIX),
            str(settings.REPORT_DIR),
            target_suffixes=("json",),
        )

    def test_download_all_report_results_from_storage_file_not_found(
        self, report_sync_service: ReportSyncService, mock_storage_service: MagicMock
    ):
        """レポート結果ファイルが見つからない場合、Falseが返されることを確認"""
        # モックの設定
        mock_storage_service.download_directory.side_effect = FileNotFoundError("Files not found")

        # 実行
        result = report_sync_service.download_all_report_results_from_storage()

        # 検証
        assert result is False
        mock_storage_service.download_directory.assert_called_once()

    def test_download_all_report_results_from_storage_exception(
        self, report_sync_service: ReportSyncService, mock_storage_service: MagicMock
    ):
        """ダウンロード中に例外が発生した場合、Falseが返されることを確認"""
        # モックの設定
        mock_storage_service.download_directory.side_effect = Exception("Download failed")

        # 実行
        result = report_sync_service.download_all_report_results_from_storage()

        # 検証
        assert result is False
        mock_storage_service.download_directory.assert_called_once()

    @pytest.fixture
    def mock_report_dir_with_mixed_files(self, tmp_path: Path):
        """JSONファイルと非JSONファイルが混在するレポートの出力ディレクトリのモック"""
        # 一時ディレクトリにレポートディレクトリを作成
        report_dir = tmp_path / "reports_mixed"
        report_dir.mkdir()

        # テスト用のスラグディレクトリを作成
        slug_dir = report_dir / "test-slug"
        slug_dir.mkdir()

        # JSONファイルを作成
        json_file = slug_dir / "test.json"
        json_file.write_text('{"data": "test"}')

        # 非JSONファイルを作成
        non_json_file = slug_dir / "test.txt"
        non_json_file.write_text("This is a test file")

        return report_dir

    @pytest.fixture
    def mock_input_file(self, tmp_path: Path):
        """入力ファイルのモック"""
        # 一時ディレクトリに入力ファイルを作成
        input_file = tmp_path / "test-slug.csv"
        input_file.write_text("id,comment\n1,test comment")

        return input_file

    def test_cleanup_report_files_success(
        self, report_sync_service: ReportSyncService, mock_report_dir_with_mixed_files: Path
    ):
        """レポートディレクトリからJSONファイル以外を削除することを確認"""
        # テスト用のディレクトリパス
        slug_dir = mock_report_dir_with_mixed_files / "test-slug"

        # 実行前の状態を確認
        assert (slug_dir / "test.json").exists()
        assert (slug_dir / "test.txt").exists()

        # 実行
        result = report_sync_service._cleanup_report_files(slug_dir)

        # 検証
        assert result is True
        assert (slug_dir / "test.json").exists()  # JSONファイルは残っている
        assert not (slug_dir / "test.txt").exists()  # 非JSONファイルは削除されている

    def test_cleanup_report_files_exception(self, report_sync_service: ReportSyncService, monkeypatch):
        """存在しないディレクトリを指定した場合、Falseが返されることを確認"""
        # 存在しないディレクトリパス
        non_existent_dir = Path("/non/existent/path")

        # os.walkが例外を発生させるようにモックする
        def mock_os_walk(*args, **kwargs):
            raise FileNotFoundError("Directory not found")

        monkeypatch.setattr(os, "walk", mock_os_walk)

        # 実行
        result = report_sync_service._cleanup_report_files(non_existent_dir)

        # 検証
        assert result is False

    def test_cleanup_file_success(self, report_sync_service: ReportSyncService, mock_input_file: Path):
        """入力ファイルを削除することを確認"""
        # 実行前の状態を確認
        assert mock_input_file.exists()

        # 実行
        result = report_sync_service._cleanup_file(mock_input_file)

        # 検証
        assert result is True
        assert not mock_input_file.exists()  # ファイルが削除されている
