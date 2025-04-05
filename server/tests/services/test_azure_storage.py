import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from azure.core.exceptions import ResourceNotFoundError

from src.config import settings
from src.services.storage import AzureBlobStorageService


class TestAzureBlobStorageService:
    """Azure Blob Storageサービスのテスト"""

    @pytest.fixture
    def mock_blob_service_client(self):
        """BlobServiceClientのモック"""
        with patch("src.services.storage.BlobServiceClient") as mock:
            # コンテナクライアントのモック
            container_client_mock = MagicMock()

            # BlobServiceClientのモック
            client_mock = MagicMock()
            client_mock.get_container_client.return_value = container_client_mock

            # コンストラクタのモック
            mock.return_value = client_mock

            yield client_mock, container_client_mock

    @pytest.fixture
    def azure_storage(self, mock_blob_service_client):
        """Azure Blob Storageサービスのインスタンス"""
        client_mock, container_client_mock = mock_blob_service_client
        with patch("src.services.storage.DefaultAzureCredential"):
            with patch.object(settings, "AZURE_BLOB_STORAGE_ACCOUNT_NAME", "testaccount"):
                with patch.object(settings, "AZURE_BLOB_STORAGE_CONTAINER_NAME", "testcontainer"):
                    # AzureBlobStorageServiceのインスタンスを作成
                    storage = AzureBlobStorageService()
                    # 作成したモックを直接設定
                    storage.blob_service_client = client_mock
                    storage.container_client = container_client_mock
                    yield storage

    @pytest.fixture
    def mock_blob_client(self, mock_blob_service_client):
        """Blobクライアントのモック"""
        _, container_client_mock = mock_blob_service_client
        blob_client_mock = MagicMock()
        container_client_mock.get_blob_client.return_value = blob_client_mock
        return blob_client_mock

    @pytest.fixture
    def temp_file_factory(self):
        """一時ファイルを作成するファクトリ関数を返す"""
        created_files = []

        def _create_file(content=b"test content"):
            with tempfile.NamedTemporaryFile(delete=False) as temp:
                temp.write(content)
                temp_path = temp.name
                created_files.append(temp_path)
            return temp_path

        yield _create_file

        # クリーンアップ
        for file_path in created_files:
            if os.path.exists(file_path):
                os.unlink(file_path)

    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリを作成して削除する"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_has_target_suffix(self, azure_storage: AzureBlobStorageService):
        # 空のsuffixesの場合
        assert azure_storage._has_target_suffix("test.txt", ()) is True
        assert azure_storage._has_target_suffix("test.jpg", ()) is True
        # suffixesに一致する場合
        assert azure_storage._has_target_suffix("test.txt", (".txt", ".json")) is True
        assert azure_storage._has_target_suffix("test.json", (".txt", ".json")) is True
        # suffixesに一致しない場合
        assert azure_storage._has_target_suffix("test.jpg", (".txt", ".json")) is False
        assert azure_storage._has_target_suffix("test", (".txt", ".json")) is False

    def test_upload_file_success(
        self, azure_storage: AzureBlobStorageService, mock_blob_client: MagicMock, temp_file_factory
    ):
        """upload_file: 成功時はTrueを返す"""
        mock_blob_client.exists.return_value = False
        file_path = temp_file_factory(b"test content")
        result = azure_storage.upload_file(file_path, "test/file.txt")

        assert result is True
        mock_blob_client.upload_blob.assert_called_once()

    def test_upload_file_skip_if_same(
        self, azure_storage: AzureBlobStorageService, mock_blob_client: MagicMock, temp_file_factory
    ):
        """upload_file: 同一ファイルが存在する場合はスキップする"""
        mock_blob_client.exists.return_value = True
        file_path = temp_file_factory(b"test content")
        # ファイルサイズが同じ場合はスキップ
        blob_properties = MagicMock()
        blob_properties.size = 12  # "test content"と同じサイズのファイルがストレージに存在すると仮定
        mock_blob_client.get_blob_properties.return_value = blob_properties

        result = azure_storage.upload_file(file_path, "test/file.txt", skip_if_same=True)
        assert result is True
        mock_blob_client.upload_blob.assert_not_called()

        # ファイルサイズが異なる場合はアップロード
        blob_properties.size = 13  # "test content"と異なるサイズのファイルがストレージに存在すると仮定
        mock_blob_client.get_blob_properties.return_value = blob_properties
        result = azure_storage.upload_file(file_path, "test/file.txt", skip_if_same=True)
        assert result is True
        mock_blob_client.upload_blob.assert_called_once()

    def test_upload_file_exception(
        self, azure_storage: AzureBlobStorageService, mock_blob_client: MagicMock, temp_file_factory
    ):
        """upload_file: 例外が発生した場合はFalseを返す"""
        # モックの設定
        mock_blob_client.upload_blob.side_effect = Exception("Upload failed")
        file_path = temp_file_factory(b"test content")
        # アップロード
        result = azure_storage.upload_file(file_path, "test/file.txt")

        # 検証
        assert result is False
        mock_blob_client.upload_blob.assert_called_once()

    def test_download_file_success(
        self, azure_storage: AzureBlobStorageService, mock_blob_client: MagicMock, temp_dir: str
    ):
        """download_file: 成功時はTrueを返す"""
        # モックの設定
        downloader_mock = MagicMock()
        downloader_mock.readall.return_value = b"test content"
        mock_blob_client.download_blob.return_value = downloader_mock

        # ダウンロード先のパス
        temp_path = os.path.join(temp_dir, "downloaded_file.txt")

        # ダウンロード
        result = azure_storage.download_file("test/file.txt", temp_path)

        # 検証
        assert result is True
        mock_blob_client.download_blob.assert_called_once()

        # ファイルが作成されたことを確認
        assert os.path.exists(temp_path)
        with open(temp_path, "rb") as f:
            assert f.read() == b"test content"

    def test_download_file_not_found(
        self, azure_storage: AzureBlobStorageService, mock_blob_client: MagicMock, temp_dir: str
    ):
        """download_file: ファイルが存在しない場合はFalseを返す"""
        # モックの設定
        mock_blob_client.download_blob.side_effect = ResourceNotFoundError("Blob not found")

        # ダウンロード先のパス
        temp_path = os.path.join(temp_dir, "downloaded_file.txt")

        # ダウンロード
        result = azure_storage.download_file("test/file.txt", temp_path)

        # 検証
        assert result is False
        mock_blob_client.download_blob.assert_called_once()

        # ファイルが作成されていないことを確認
        assert not os.path.exists(temp_path)

    def test_download_file_exception(
        self, azure_storage: AzureBlobStorageService, mock_blob_client: MagicMock, temp_dir: str
    ):
        """download_file: 例外が発生した場合はFalseを返す"""
        # モックの設定
        mock_blob_client.download_blob.side_effect = Exception("Download failed")

        # ダウンロード先のパス
        temp_path = os.path.join(temp_dir, "downloaded_file.txt")

        # ダウンロード
        result = azure_storage.download_file("test/file.txt", temp_path)

        # 検証
        assert result is False
        mock_blob_client.download_blob.assert_called_once()

        # ファイルが作成されていないことを確認
        assert not os.path.exists(temp_path)

    @pytest.fixture
    def test_dir_with_files(self, temp_dir: str):
        """テスト用のディレクトリ構造を作成する"""
        # テストファイルを作成
        file1_path = os.path.join(temp_dir, "file1.txt")
        with open(file1_path, "w") as f:
            f.write("test content 1")

        file2_path = os.path.join(temp_dir, "file2.json")
        with open(file2_path, "w") as f:
            f.write("test content 2")

        # サブディレクトリを作成
        subdir = os.path.join(temp_dir, "subdir")
        os.makedirs(subdir)

        file3_path = os.path.join(subdir, "file3.txt")
        with open(file3_path, "w") as f:
            f.write("test content 3")

        return {"dir": temp_dir, "files": {"file1": file1_path, "file2": file2_path, "file3": file3_path}}

    def test_upload_directory_success(self, azure_storage: AzureBlobStorageService, test_dir_with_files: dict):
        """upload_directory: 成功時はTrueを返す"""
        # upload_fileをモック化
        with patch.object(azure_storage, "upload_file", return_value=True) as mock_upload_file:
            # ディレクトリをアップロード
            result = azure_storage.upload_directory(test_dir_with_files["dir"], "test/dir")

            # 検証
            assert result is True
            assert mock_upload_file.call_count == 3

            # 呼び出し引数を検証
            calls = mock_upload_file.call_args_list
            paths = sorted([call[0][0] for call in calls])
            remote_paths = sorted([call[0][1] for call in calls])

            assert test_dir_with_files["files"]["file1"] in paths
            assert test_dir_with_files["files"]["file2"] in paths
            assert test_dir_with_files["files"]["file3"] in paths

            assert "test/dir/file1.txt" in remote_paths
            assert "test/dir/file2.json" in remote_paths
            assert "test/dir/subdir/file3.txt" in remote_paths

    def test_upload_directory_no_files(self, azure_storage: AzureBlobStorageService):
        """upload_directory: ファイルが見つからない場合はFalseを返す"""
        # 一時ディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            # upload_fileをモック化
            with patch.object(azure_storage, "upload_file", return_value=True) as mock_upload_file:
                # ディレクトリをアップロード
                result = azure_storage.upload_directory(temp_dir, "test/dir")

                # 検証
                assert result is False
                assert mock_upload_file.call_count == 0

    def test_upload_directory_failure(self, azure_storage: AzureBlobStorageService, test_dir_with_files: dict):
        """upload_directory: 1件でもアップロードに失敗した場合はFalseを返す"""

        # upload_fileをモック化（2回目の呼び出しで失敗）
        upload_results = [True, False, True]

        def side_effect(*args, **kwargs):
            return upload_results.pop(0)

        with patch.object(azure_storage, "upload_file", side_effect=side_effect) as mock_upload_file:
            # ディレクトリをアップロード
            result = azure_storage.upload_directory(test_dir_with_files["dir"], "test/dir")

            # 検証
            assert result is False
            assert mock_upload_file.call_count == 3

    def test_download_directory_with_suffixes(
        self, azure_storage: AzureBlobStorageService, mock_blob_service_client: tuple[MagicMock, MagicMock]
    ):
        """download_directory: suffixesを指定した場合、一致するファイルのみダウンロードする"""
        # モックの設定
        _, container_client_mock = mock_blob_service_client

        # list_blobsの戻り値を設定
        blob1 = MagicMock()
        blob1.name = "test/dir/file1.txt"
        blob2 = MagicMock()
        blob2.name = "test/dir/file2.json"
        blob3 = MagicMock()
        blob3.name = "test/dir/subdir/file3.txt"
        container_client_mock.list_blobs.return_value = [blob1, blob2, blob3]

        # 一時ディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            # download_fileをモック化
            with patch.object(azure_storage, "download_file", return_value=True) as mock_download_file:
                # ディレクトリをダウンロード（.txtファイルのみ）
                result = azure_storage.download_directory("test/dir", temp_dir, target_suffixes=(".txt",))

                # 検証
                assert result is True
                assert mock_download_file.call_count == 2

                # 呼び出し引数を検証
                calls = mock_download_file.call_args_list
                remote_paths = sorted([call[0][0] for call in calls])

                assert "test/dir/file1.txt" in remote_paths
                assert "test/dir/subdir/file3.txt" in remote_paths
                # jsonは指定したsuffixに一致しないためダウンロードされない
                assert "test/dir/file2.json" not in remote_paths
