import json
import os
from pathlib import Path

from src.config import settings
from src.services.storage import get_storage_service
from src.utils.logger import setup_logger

logger = setup_logger()


class ReportSyncService:
    REMOTE_INPUT_DIR_PREFIX = "inputs"
    REMOTE_REPORT_DIR_PREFIX = "outputs"
    REMOTE_STATUS_FILE_PREFIX = "status"
    REMOTE_CONFIG_DIR_PREFIX = "configs"
    LOCAL_STATUS_FILE_PATH = settings.DATA_DIR / "report_status.json"
    PRESERVED_REPORT_FILES = (
        ".json",
        "final_result_with_comments.csv",
        "hierarchical_merge_labels.csv",
        "hierarchical_result.json",
        "args.csv",
        "hierarchical_clusters.csv",
        "relations.csv",
        "hierarchical_overview.txt",
    )

    def __init__(self):
        self.storage_service = get_storage_service()

    def sync_status_file_to_storage(self) -> None:
        """ステータスファイルをストレージにアップロードする"""
        if not self.LOCAL_STATUS_FILE_PATH.exists():
            logger.warning(f"Status file does not exist: {self.LOCAL_STATUS_FILE_PATH}")
            return

        remote_status_file_path = f"{self.REMOTE_STATUS_FILE_PREFIX}/report_status.json"
        self.storage_service.upload_file(str(self.LOCAL_STATUS_FILE_PATH), remote_status_file_path)

    def _cleanup_report_files(self, report_dir: Path) -> bool:
        """レポートディレクトリから保持すべきファイル以外を削除する

        Args:
            report_dir: 削除対象のレポートディレクトリパス

        Returns:
            bool: 削除に成功した場合はTrue、失敗した場合はFalse
        """
        try:
            for root, _, files in os.walk(report_dir):
                for file in files:
                    # 保持すべきファイルは残し、それ以外は削除
                    if not file.endswith(self.PRESERVED_REPORT_FILES):
                        file_path = os.path.join(root, file)
                        os.remove(file_path)
                        logger.info(f"ファイルを削除しました: {file_path}")

            logger.info(f"レポートディレクトリから保持すべきファイル以外を削除しました: {report_dir}")
            return True
        except Exception as e:
            logger.error(f"レポートディレクトリのクリーンアップに失敗しました: {report_dir} エラー: {str(e)}")
            return False

    def _cleanup_file(self, file_path: Path) -> bool:
        """ファイルを削除する

        Args:
            file_path: 削除対象のファイルパス

        Returns:
            bool: 削除に成功した場合はTrue、失敗した場合はFalse
        """
        try:
            file_path.unlink()
            logger.info(f"ローカルファイルを削除しました: {file_path}")
            return True
        except Exception as e:
            logger.error(f"ローカルファイルの削除に失敗しました: {file_path} エラー: {str(e)}")
            return False

    def sync_report_files_to_storage(self, slug: str) -> None:
        """レポートの中間ファイルと結果ファイルをストレージにアップロードし、保持すべきファイル以外を削除する"""

        report_dir = settings.REPORT_DIR / slug
        if not report_dir.exists():
            logger.warning(f"レポートディレクトリが存在しません: {report_dir}")
            return

        local_dir = settings.REPORT_DIR / slug
        remote_dir_prefix = f"{self.REMOTE_REPORT_DIR_PREFIX}/{slug}"

        # ファイルをストレージにアップロード
        upload_success = self.storage_service.upload_directory(str(local_dir), remote_dir_prefix)

        # アップロードが成功した場合、保持すべきファイル以外を削除
        if upload_success:
            self._cleanup_report_files(local_dir)

    def sync_input_file_to_storage(self, slug: str) -> None:
        """入力ファイルをストレージにアップロードし、アップロード後にローカルファイルを削除する"""
        input_file_path = settings.INPUT_DIR / f"{slug}.csv"
        if not input_file_path.exists():
            logger.warning(f"入力ファイルが存在しません: {input_file_path}")
            return

        remote_input_file_path = f"{self.REMOTE_INPUT_DIR_PREFIX}/{slug}.csv"

        # ファイルをストレージにアップロード
        self.storage_service.upload_file(str(input_file_path), remote_input_file_path)

    def sync_config_file_to_storage(self, slug: str) -> None:
        """設定ファイルをストレージにアップロードする"""
        config_file_path = settings.CONFIG_DIR / f"{slug}.json"
        if not config_file_path.exists():
            logger.warning(f"設定ファイルが存在しません: {config_file_path}")
            return

        remote_config_file_path = f"{self.REMOTE_CONFIG_DIR_PREFIX}/{slug}.json"
        self.storage_service.upload_file(str(config_file_path), remote_config_file_path)

    def download_status_file_from_storage(self) -> bool:
        """ステータスファイルをストレージからダウンロードする

        Returns:
            bool: ダウンロードに成功した場合はTrue、失敗した場合はFalse
        """
        # 予期せぬ上書きを避けるため、statusファイルが存在し中身が空でない場合はダウンロードをスキップする
        if self.LOCAL_STATUS_FILE_PATH.exists() and self.LOCAL_STATUS_FILE_PATH.stat().st_size > 0:
            with open(self.LOCAL_STATUS_FILE_PATH) as f:
                report_status = json.load(f)
            if report_status:  # データが存在する場合はスキップ
                logger.info(
                    "ステータスファイルが存在していますが、中身が空ではありません。ダウンロードをスキップします"
                )
                return True

        try:
            remote_status_file_path = f"{self.REMOTE_STATUS_FILE_PREFIX}/report_status.json"
            self.storage_service.download_file(remote_status_file_path, str(self.LOCAL_STATUS_FILE_PATH))
            return True
        except FileNotFoundError:
            logger.warning(f"ストレージにステータスファイルが存在しません: {remote_status_file_path}")
            return False
        except Exception as e:
            logger.error(f"ステータスファイルのダウンロードに失敗しました: {e}")
            return False

    def _download_directory_from_storage(
        self, remote_dir_prefix: str, local_dir: Path, target_suffixes: tuple[str, ...], file_type_name: str
    ) -> bool:
        """ストレージからディレクトリをダウンロードする汎用関数

        Args:
            remote_dir_prefix: リモートディレクトリのプレフィックス
            local_dir: ローカルディレクトリのパス
            target_suffixes: ダウンロード対象のファイル拡張子のタプル
            file_type_name: ログメッセージで使用するファイルタイプ名

        Returns:
            bool: ダウンロードに成功した場合はTrue、失敗した場合はFalse
        """
        try:
            self.storage_service.download_directory(
                remote_dir_prefix,
                str(local_dir),
                target_suffixes=target_suffixes,
            )
            return True
        except FileNotFoundError:
            logger.warning(f"ストレージに{file_type_name}が存在しません: {remote_dir_prefix}")
            return False
        except Exception as e:
            logger.error(f"{file_type_name}のダウンロードに失敗しました: {e}")
            return False

    def download_all_report_results_from_storage(self) -> bool:
        """レポート結果ファイル（hierarchical_result.json）のみをストレージからダウンロードする

        Returns:
            bool: ダウンロードに成功した場合はTrue、失敗した場合はFalse
        """
        return self._download_directory_from_storage(
            self.REMOTE_REPORT_DIR_PREFIX, settings.REPORT_DIR, self.PRESERVED_REPORT_FILES, "レポートファイル"
        )

    def download_all_config_files_from_storage(self) -> bool:
        """設定ファイルをストレージからダウンロードする

        Returns:
            bool: ダウンロードに成功した場合はTrue、失敗した場合はFalse
        """
        return self._download_directory_from_storage(
            self.REMOTE_CONFIG_DIR_PREFIX, settings.CONFIG_DIR, (".json",), "設定ファイル"
        )

    def download_all_input_files_from_storage(self) -> bool:
        """入力ファイルをストレージからダウンロードする

        Returns:
            bool: ダウンロードに成功した場合はTrue、失敗した場合はFalse
        """
        return self._download_directory_from_storage(
            self.REMOTE_INPUT_DIR_PREFIX, settings.INPUT_DIR, (".csv",), "入力ファイル"
        )


def initialize_from_storage() -> bool:
    """サーバー起動時にストレージからファイルを初期化する

    Returns:
        bool: 初期化に成功した場合はTrue、失敗した場合はFalse
    """
    report_sync_service = ReportSyncService()
    try:
        status_success = report_sync_service.download_status_file_from_storage()
    except Exception as e:
        logger.error(f"ステータスファイルのダウンロードに失敗しました: {e}")
        return False
    try:
        reports_success = report_sync_service.download_all_report_results_from_storage()
    except Exception as e:
        logger.error(f"レポートファイルのダウンロードに失敗しました: {e}")
        return False

    try:
        config_success = report_sync_service.download_all_config_files_from_storage()
    except Exception as e:
        logger.error(f"設定ファイルのダウンロードに失敗しました: {e}")
        return False
    try:
        input_success = report_sync_service.download_all_input_files_from_storage()
    except Exception as e:
        logger.error(f"入力ファイルのダウンロードに失敗しました: {e}")
        return False

    return status_success and reports_success and config_success and input_success
