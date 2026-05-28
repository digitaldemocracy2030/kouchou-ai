#!/usr/bin/env python3
"""Azure Blob Storage接続テストと確認方法

このスクリプトはAzure Blob Storageへの接続をテストし、ファイルのアップロードと
ダウンロードが正常に動作するか確認します。

実行方法:
    cd server && rye run python scripts/test_storage.py

出力例:
2025-09-25 12:31:44 [info     ] Logger setup complete          [app] json_logs=False log_file=stdout log_level=INFO
STORAGE_TYPE: azure_blob
AZURE_BLOB_STORAGE_ACCOUNT_NAME: <BLOB_STORAGE_NAME>
AZURE_BLOB_STORAGE_CONTAINER_NAME: kouchou-reports
Azure Blob Storage Account URL: https://<BLOB_STORAGE_NAME>.blob.core.windows.net
2025-09-25 12:31:44 [info     ] AzureBlobStorageServiceを使用します。アカウント: <BLOB_STORAGE_NAME> コンテナ: kouchou-reports [app]
Storage service initialized: AzureBlobStorageService
2025-09-25 12:31:46 [info     ] ファイルをアップロードしました。パス: 'test_upload.txt' パス: 'test/test_upload.txt' [app]
✅ Upload successful to: test/test_upload.txt
2025-09-25 12:31:47 [info     ] ファイルをダウンロードしました。パス: 'test/test_upload.txt' ローカルパス: 'test_download.txt' [app]
✅ Download and content verification successful: test/test_upload.txt

Azure Storage内のファイル確認方法:

1. Azure CLI を使用した確認:
   # 全ファイルのリスト表示
   az storage blob list --account-name <BLOB_STORAGE_NAME> --container-name kouchou-reports --output table

   # 特定レポートのファイル確認
   az storage blob list --account-name <BLOB_STORAGE_NAME> --container-name kouchou-reports \\
       --prefix "outputs/[REPORT-ID]" --output table

   # ファイルのダウンロード
   az storage blob download --account-name <BLOB_STORAGE_NAME> --container-name kouchou-reports \\
       --name "outputs/[REPORT-ID]/hierarchical_result.json" --file ./downloaded.json

2. Azure Storage Explorer での確認:
   - ストレージアカウント: <BLOB_STORAGE_NAME>
   - コンテナ: kouchou-reports
   - 表示設定: 「すべてのBlobと現在のバージョンがないBlob」を選択

   スクリーンショット: https://gyazo.com/81698c6fdf2532005c5b1cd5d9ac2298

   ファイル構造:
   kouchou-reports/
   ├── outputs/[REPORT-ID]/     # レポート出力ファイル
   │   ├── hierarchical_result.json
   │   ├── hierarchical_overview.txt
   │   └── その他の結果ファイル
   ├── configs/[REPORT-ID].json # パイプライン設定
   └── inputs/[REPORT-ID].csv   # 入力データ

3. Python での確認（このスクリプトの拡張例）:
   storage_service = get_storage_service()
   # AzureBlobStorageService の場合、container_client を使用してリスト取得可能

環境変数の確認:
   - STORAGE_TYPE=azure_blob
   - AZURE_BLOB_STORAGE_ACCOUNT_NAME=<BLOB_STORAGE_NAME>
   - AZURE_BLOB_STORAGE_CONTAINER_NAME=kouchou-reports

注意事項:
   - LocalStorageService（STORAGE_TYPE=local）では実際の外部ストレージ保存は行われません
   - Azure Container Apps上で実行された場合、ローカル環境にはファイルが存在しません
"""

import os
import sys
from pathlib import Path

# serverフォルダから実行する場合のパス設定
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.services.storage import AzureBlobStorageService, get_storage_service


def cleanup_local_files(*paths: str) -> None:
    """Remove temporary local files if they exist."""
    for path in paths:
        if os.path.exists(path):
            os.remove(path)


def cleanup_remote_file(storage_service, remote_path: str) -> None:
    """Remove the uploaded test blob when running against Azure Blob Storage."""
    if not isinstance(storage_service, AzureBlobStorageService):
        return
    try:
        storage_service.container_client.delete_blob(remote_path, delete_snapshots="include")
        print(f"🧹 Deleted remote test blob: {remote_path}")
    except Exception as e:
        print(f"⚠️ Failed to delete remote test blob: {remote_path} ({e})")

print(f"STORAGE_TYPE: {settings.STORAGE_TYPE}")
print(f"AZURE_BLOB_STORAGE_ACCOUNT_NAME: {settings.AZURE_BLOB_STORAGE_ACCOUNT_NAME}")
print(f"AZURE_BLOB_STORAGE_CONTAINER_NAME: {settings.AZURE_BLOB_STORAGE_CONTAINER_NAME}")
print(f"Azure Blob Storage Account URL: {settings.azure_blob_storage_account_url}")

try:
    storage_service = get_storage_service()
    print(f"Storage service initialized: {storage_service.__class__.__name__}")

    test_file_path = "test_upload.txt"
    downloaded_file_path = "test_download.txt"
    test_content = "Test upload to Azure Blob Storage"
    remote_path = "test/test_upload.txt"

    Path(test_file_path).write_text(test_content, encoding="utf-8")

    upload_success = storage_service.upload_file(test_file_path, remote_path)
    if not upload_success:
        print("❌ Upload failed")
        cleanup_local_files(test_file_path, downloaded_file_path)
        sys.exit(1)
    print(f"✅ Upload successful to: {remote_path}")

    download_success = storage_service.download_file(remote_path, downloaded_file_path)
    if not download_success:
        print(f"❌ Download failed: {remote_path}")
        cleanup_local_files(test_file_path, downloaded_file_path)
        cleanup_remote_file(storage_service, remote_path)
        sys.exit(1)

    downloaded_content = Path(downloaded_file_path).read_text(encoding="utf-8")
    if downloaded_content != test_content:
        print(f"❌ Downloaded content mismatch: {remote_path}")
        cleanup_local_files(test_file_path, downloaded_file_path)
        cleanup_remote_file(storage_service, remote_path)
        sys.exit(1)

    print(f"✅ Download and content verification successful: {remote_path}")

    cleanup_local_files(test_file_path, downloaded_file_path)
    cleanup_remote_file(storage_service, remote_path)

except Exception as e:
    print(f"❌ Error: {e}")
    cleanup_local_files("test_upload.txt", "test_download.txt")
    import traceback

    traceback.print_exc()
