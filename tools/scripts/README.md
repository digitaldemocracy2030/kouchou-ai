# スクリプト集

このディレクトリには、kouchou-aiプロジェクトの運用と管理に役立つスクリプトが含まれています。

## スクリプト一覧

### download_reports_from_azure.py
Azure Blob Storage を canonical store として、status / reports / configs / inputs を
ローカルファイルシステムへ復元するスクリプト。
`--slug` を付けると特定レポートだけを落とせます。

### upload_reports_to_azure.py
ローカル環境の status / reports / configs / inputs をAzure Blob Storageにアップロードするスクリプト。
Azure環境への移行時に使用します。

### assign_storage_role.sh
Azure Blob Storageへのアクセス権限（Storage Blob Data Contributor）を
現在ログインしているユーザーに付与するスクリプト。

## 使用方法

各スクリプトの詳細な使用方法は、スクリプトファイル内のコメントを参照してください。
一般的な実行手順：

```bash
# Azure Blob Storage からローカルへ復元
python tools/scripts/download_reports_from_azure.py

# Azure Blob Storageへのアクセス権限付与
./tools/scripts/assign_storage_role.sh

# レポートデータのAzure Blob Storageへのアップロード
python tools/scripts/upload_reports_to_azure.py
```

## 環境変数

`download_reports_from_azure.py` は `apps/api/src/config.py` を読むため、`.env` または環境変数で `ADMIN_API_KEY`, `PUBLIC_API_KEY`, `OPENAI_API_KEY`, `STORAGE_TYPE`, `AZURE_BLOB_STORAGE_ACCOUNT_NAME`, `AZURE_BLOB_STORAGE_CONTAINER_NAME` を与えてください。

`upload_reports_to_azure.py` は少なくとも `STORAGE_TYPE`, `AZURE_BLOB_STORAGE_ACCOUNT_NAME`, `AZURE_BLOB_STORAGE_CONTAINER_NAME` が必要です。

## アップロード後のコンテナ再起動

レポートをアップロードした後、変更を反映させるにはAPIコンテナの再起動が必要です：

```bash
make azure-restart-api
```

再起動後、ブラウザをリロードすると、アップロードしたレポートが表示されます。
