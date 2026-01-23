#!/usr/bin/env python3
"""Azure Blob Storage接続テストと確認方法

このスクリプトはAzure Blob Storageへの接続をテストし、ファイルのアップロードが正常に動作するか確認します。

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

# serverフォルダから実行する場合のパス設定
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.services.storage import get_storage_service

print(f"STORAGE_TYPE: {settings.STORAGE_TYPE}")
print(f"AZURE_BLOB_STORAGE_ACCOUNT_NAME: {settings.AZURE_BLOB_STORAGE_ACCOUNT_NAME}")
print(f"AZURE_BLOB_STORAGE_CONTAINER_NAME: {settings.AZURE_BLOB_STORAGE_CONTAINER_NAME}")
print(f"Azure Blob Storage Account URL: {settings.azure_blob_storage_account_url}")

try:
    storage_service = get_storage_service()
    print(f"Storage service initialized: {storage_service.__class__.__name__}")

    # テストファイルを作成
    test_file_path = "test_upload.txt"
    with open(test_file_path, "w") as f:
        f.write("Test upload to Azure Blob Storage")

    # アップロードテスト
    remote_path = "test/test_upload.txt"
    result = storage_service.upload_file(test_file_path, remote_path)

    if hasattr(storage_service, "upload_file"):
        if result:
            print(f"✅ Upload successful to: {remote_path}")
        else:
            print("❌ Upload failed")

    # クリーンアップ
    os.remove(test_file_path)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
