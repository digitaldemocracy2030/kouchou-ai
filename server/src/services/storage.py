import os
from abc import ABC, abstractmethod
from pathlib import Path

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from src.config import settings
from src.utils.logger import setup_logger

logger = setup_logger()


class StorageService(ABC):
    """ストレージサービスの抽象基底クラス

    ファイルやディレクトリのアップロード・ダウンロード機能を提供する抽象基底クラス。
    異なるストレージバックエンド（ローカルストレージ、Azure Blob Storageなど）に対して共通のインターフェースを定義。
    """

    @abstractmethod
    def upload_file(self, local_file_path: str, remote_blob_path: str):
        """ローカルファイルをストレージにアップロードする

        Args:
            local_file_path: アップロードするローカルファイルのパス
            remote_blob_path: ストレージ上の保存先パス
        """
        pass

    @abstractmethod
    def download_file(self, remote_blob_path: str, local_file_path: str):
        """ストレージからファイルをダウンロードする

        Args:
            remote_blob_path: ダウンロードするストレージ上のファイルパス
            local_file_path: ローカルの保存先パス
        """
        pass

    @abstractmethod
    def download_directory(self, remote_dir_prefix: str, local_dir_path: str, target_suffixes: tuple[str, ...] = ()):
        """ストレージから指定プレフィックスに一致するファイル群をディレクトリとしてダウンロードする

        Args:
            remote_dir_prefix: ダウンロードするストレージ上のディレクトリプレフィックス
            local_dir_path: ローカルの保存先ディレクトリパス
        """
        pass

    @abstractmethod
    def upload_directory(self, local_dir_path: str, remote_dir_prefix: str, target_suffixes: tuple[str, ...] = ()):
        """ローカルディレクトリをストレージにアップロードする

        Args:
            local_dir_path: アップロードするローカルディレクトリのパス
            remote_dir_prefix: ストレージ上の保存先プレフィックス
            target_suffixes: アップロード対象とするファイルの拡張子リスト（省略可能）
        """
        pass


class LocalStorageService(StorageService):
    """ローカルストレージサービス

    ローカルストレージを使用する場合のサービス。
    ストレージタイプがlocalの場合にインターフェースを揃えるためのもので、実際には処理を行わない。
    """

    def upload_file(self, local_path: str | Path, remote_path: str) -> None:
        """ローカルストレージの場合はアップロード操作は不要

        Args:
            local_path: アップロード元のローカルファイルパス（文字列またはPathオブジェクト）
            remote_path: アップロード先のパス（文字列）
        """
        logger.debug(f"LocalStorageService: upload_file は何もしません - {local_path} -> {remote_path}")

    def download_file(self, remote_path: str, local_path: str | Path) -> None:
        """ローカルストレージの場合はダウンロード操作は不要

        Args:
            remote_path: ダウンロード元のパス（文字列）
            local_path: ダウンロード先のローカルファイルパス（文字列またはPathオブジェクト）
        """
        logger.debug(f"LocalStorageService: download_file は何もしません - {remote_path} -> {local_path}")

    def download_directory(
        self, remote_dir_prefix: str, local_dir_path: str, target_suffixes: tuple[str, ...] = ()
    ) -> None:
        """ローカルストレージの場合はファイル一覧取得は不要

        Args:
            remote_dir_prefix: ダウンロード対象のディレクトリプレフィックス
            local_dir_path: ダウンロード先のローカルディレクトリパス
            target_suffixes: ダウンロード対象とするファイルの拡張子リスト（省略可能）
        """
        logger.debug(
            f"LocalStorageService: download_directory は何もしません - {remote_dir_prefix} -> {local_dir_path}"
        )

    def upload_directory(
        self,
        local_dir_path: str,
        remote_dir_prefix: str,
        target_suffixes: tuple[str, ...] = (),  # noqa: B006
    ) -> None:
        """ディレクトリをストレージにアップロードする

        ローカルストレージの場合、ディレクトリのアップロード操作は実質的に不要なため何も行いません。

        Args:
            local_dir_path: アップロード元のローカルディレクトリパス（文字列）
            remote_dir_prefix: アップロード先のディレクトリプレフィックス（文字列）
            target_suffixes: アップロード対象とするファイルの拡張子リスト（省略可能）
        """
        logger.debug(f"LocalStorageService: upload_directory は何もしません - {local_dir_path} -> {remote_dir_prefix}")


# NOTE: 現在は外部ストレージ連携がAzure Blob Storageのみのため、一つのファイルに全てのクラスを記載している
# 外部ストレージ連携が増えた場合は、それぞれのストレージに応じたクラスを作成することを検討する
class AzureBlobStorageService(StorageService):
    """Azure Blob Storageを使用するストレージサービス

    Azure Blob Storageを使用するストレージサービスの実装です。
    ファイルやディレクトリのアップロード・ダウンロードをAzure Blob Storageとの間で行います。
    """

    def __init__(self):
        """AzureBlobStorageServiceのコンストラクタ

        設定からAzure Blob Storageの接続情報を取得し、クライアントを初期化します。
        """
        self.blob_service_client = BlobServiceClient(
            account_url=settings.azure_blob_storage_account_url,
            credential=DefaultAzureCredential(),
        )
        self.container_client = self.blob_service_client.get_container_client(
            settings.AZURE_BLOB_STORAGE_CONTAINER_NAME
        )

    def _has_target_suffix(self, blob_path: str, target_suffixes: tuple[str, ...] = ()) -> bool:
        """指定されたsuffixで終わるファイルを判定する

        Args:
            blob_path: 判定対象のBlobパス（文字列）
            target_suffixes: 対象とする拡張子のリスト（空の場合は全てのファイルが対象）

        Returns:
            bool: 指定された拡張子で終わる場合はTrue、それ以外はFalse
        """
        if len(target_suffixes) == 0:
            return True
        return any(blob_path.endswith(suffix) for suffix in target_suffixes)

    def upload_file(self, local_file_path: str, remote_blob_path: str, skip_if_same: bool = True) -> bool:
        """ファイルをストレージにアップロードする

        ローカルファイルをAzure Blob Storageにアップロードします。
        skip_if_sameがTrueの場合、同一ファイルが既に存在する場合はアップロードをスキップします。

        Args:
            local_file_path: アップロードするローカルファイルのパス（文字列）
            remote_blob_path: Azure Blob Storage上の保存先パス（文字列）
                パスが「/」で終わる場合、元のファイル名が自動的に追加されます
                パスが空または「.」の場合、元のファイル名のみが使用されます
            skip_if_same: 同一ファイルが存在する場合にスキップするかどうか（デフォルト: True）
        """
        try:
            if remote_blob_path.endswith("/"):
                remote_blob_path = remote_blob_path + os.path.basename(local_file_path)
            elif remote_blob_path == "" or remote_blob_path == ".":
                remote_blob_path = os.path.basename(local_file_path)

            blob_client = self.container_client.get_blob_client(remote_blob_path)

            # 同一ファイルチェック
            if skip_if_same and blob_client.exists():
                # ローカルファイルのサイズを取得
                local_file_size = os.path.getsize(local_file_path)

                # リモートBlobのプロパティを取得
                blob_properties = blob_client.get_blob_properties()
                remote_file_size = blob_properties.size

                # サイズが同じ場合はスキップ
                if local_file_size == remote_file_size:
                    logger.info(
                        f"同一ファイルが存在します。アップロードをスキップします。パス: '{local_file_path}' パス: '{remote_blob_path}'"
                    )
                    return True

            # ファイルをアップロード
            with open(local_file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            logger.info(f"ファイルをアップロードしました。パス: '{local_file_path}' パス: '{remote_blob_path}'")
            return True
        except Exception as e:
            logger.error(
                f"ファイルのアップロードに失敗しました。パス: '{local_file_path}' パス: '{remote_blob_path}' エラー: {str(e)}"
            )
            return False

    def upload_directory(
        self,
        local_dir_path: str,
        remote_dir_prefix: str,
        target_suffixes: tuple[str, ...] = (),
        skip_if_same: bool = True,
    ) -> bool:
        """ディレクトリをストレージにアップロードする

        ローカルディレクトリ内のファイルをAzure Blob Storageにアップロードします。

        Args:
            local_dir_path: アップロードするローカルディレクトリのパス（文字列）
            remote_dir_prefix: Azure Blob Storage上の保存先プレフィックス（文字列）
            target_suffixes: アップロード対象とするファイルの拡張子リスト（省略可能）
                指定された場合、リストに含まれる拡張子を持つファイルのみがアップロードされます
            skip_if_same: 同一ファイルが存在する場合にスキップするかどうか（デフォルト: True）
        """
        try:
            prefix = remote_dir_prefix
            if prefix and not prefix.endswith("/"):
                prefix += "/"

            files_processed = 0

            upload_results = []
            for root, _, files in os.walk(local_dir_path):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(file_path, local_dir_path)
                    remote_blob_path = (
                        prefix + relative_path.replace(os.sep, "/") if prefix else relative_path.replace(os.sep, "/")
                    )
                    if not self._has_target_suffix(remote_blob_path, target_suffixes):
                        continue

                    files_processed += 1
                    success = self.upload_file(file_path, remote_blob_path, skip_if_same=skip_if_same)
                    upload_results.append(success)

            if files_processed == 0:
                logger.warning(f"アップロード対象のファイルが見つかりませんでした。パス: '{local_dir_path}'")
                return False

            # 1件でもアップロードに失敗したらFalseを返す
            if not all(upload_results):
                logger.error(
                    f"ディレクトリのアップロードに失敗しました。パス: '{local_dir_path}' プレフィックス: '{remote_dir_prefix}'"
                )
                return False

            return True

        except Exception as e:
            logger.error(
                f"ディレクトリのアップロードに失敗しました。パス: '{local_dir_path}' プレフィックス: '{remote_dir_prefix}' エラー: {str(e)}"
            )
            return False

    def download_file(self, remote_blob_path: str, local_file_path: str) -> bool:
        """ファイルをダウンロードする

        Azure Blob Storageからファイルをローカルにダウンロードします。

        Args:
            remote_blob_path: ダウンロードするAzure Blob Storage上のファイルパス（文字列）
            local_file_path: ローカルの保存先パス（文字列）
                必要に応じて親ディレクトリが自動的に作成されます

        Raises:
            FileNotFoundError: 指定されたBlobが存在しない場合
        """
        try:
            blob_client = self.container_client.get_blob_client(remote_blob_path)
            try:
                downloader = blob_client.download_blob()
            except ResourceNotFoundError:
                logger.error(
                    f"ファイルが見つかりませんでした。パス: '{remote_blob_path}' コンテナ: '{self.container_client.container_name}'."
                )
                return False

            os.makedirs(os.path.dirname(local_file_path), exist_ok=True) if os.path.dirname(local_file_path) else None
            with open(local_file_path, "wb") as file:
                file.write(downloader.readall())
            logger.info(f"ファイルをダウンロードしました。パス: '{remote_blob_path}' ローカルパス: '{local_file_path}'")
            return True
        except Exception as e:
            if not isinstance(e, FileNotFoundError):
                logger.error(
                    f"ファイルのダウンロードに失敗しました。パス: '{remote_blob_path}' ローカルパス: '{local_file_path}' エラー: {str(e)}"
                )
            return False

    def download_directory(
        self, remote_dir_prefix: str, local_dir_path: str, target_suffixes: tuple[str, ...] = ()
    ) -> bool:
        """ディレクトリをダウンロードする

        指定されたプレフィックスに一致するAzure Blob Storage上のファイル群をローカルディレクトリにダウンロードします。

        Args:
            remote_dir_prefix: ダウンロードするAzure Blob Storage上のディレクトリプレフィックス（文字列）
            local_dir_path: ローカルの保存先ディレクトリパス（文字列）
            target_suffixes: ダウンロード対象とするファイルの拡張子リスト（省略可能）
                指定された場合、リストに含まれる拡張子を持つファイルのみがダウンロードされます

        Raises:
            FileNotFoundError: 一致するファイルが見つからない場合
        """
        try:
            prefix = remote_dir_prefix
            if prefix and not prefix.endswith("/"):
                prefix += "/"

            blobs_list = self.container_client.list_blobs(name_starts_with=prefix)
            found = False

            for blob in blobs_list:
                blob_name = blob.name
                # target_suffixが指定されていて、blob名がそのsuffixで終わらなければスキップ
                if not self._has_target_suffix(blob_name, target_suffixes):
                    continue

                found = True
                # プレフィックス部分を除いた相対パスを計算し、ローカルのパスと結合
                relative_path = blob_name[len(prefix) :] if prefix else blob_name
                local_path = os.path.join(local_dir_path, relative_path)

                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                # blob をローカルファイルにダウンロード
                self.download_file(blob_name, local_path)

            if not found:
                error_msg = f"プレフィックス: '{remote_dir_prefix}' サフィックス: '{target_suffixes}' のファイルが見つかりませんでした。コンテナ: '{self.container_client.container_name}'."
                logger.error(error_msg)
                return False

            return True

        except Exception as e:
            if not isinstance(e, FileNotFoundError):
                logger.error(
                    f"ディレクトリのダウンロードに失敗しました。プレフィックス: '{remote_dir_prefix}' ローカルパス: '{local_dir_path}' エラー: {str(e)}"
                )
            return False


def get_storage_service() -> StorageService:
    """設定に基づいて適切なストレージサービスを返す

    設定ファイルのSTORAGE_TYPE設定に基づいて、適切なストレージサービスのインスタンスを返します。

    Returns:
        StorageService: 設定に基づいたストレージサービスのインスタンス
            - "local": LocalStorageService
            - "azure_blob": AzureBlobStorageService
            - その他: LocalStorageService（デフォルト）
    """
    if settings.STORAGE_TYPE in ["local", ""] or settings.STORAGE_TYPE is None:
        logger.info("Using LocalStorageService")
        return LocalStorageService()

    elif settings.STORAGE_TYPE == "azure_blob":
        if not settings.AZURE_BLOB_STORAGE_ACCOUNT_NAME or not settings.AZURE_BLOB_STORAGE_CONTAINER_NAME:
            error_msg = "Azure Blob Storageの設定が不足しています。AZURE_BLOB_STORAGE_ACCOUNT_NAME と AZURE_BLOB_STORAGE_CONTAINER_NAME を設定してください。"
            logger.error(error_msg)
            raise ValueError(error_msg)
        logger.info(
            f"AzureBlobStorageServiceを使用します。アカウント: {settings.AZURE_BLOB_STORAGE_ACCOUNT_NAME} コンテナ: {settings.AZURE_BLOB_STORAGE_CONTAINER_NAME}"
        )
        return AzureBlobStorageService()

    logger.warning(f"STORAGE_TYPEが不明: {settings.STORAGE_TYPE}, ローカルストレージにフォールバックします")
    return LocalStorageService()
