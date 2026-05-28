# スクリプト集

このディレクトリには、kouchou-aiプロジェクトの運用と管理に役立つスクリプトが含まれています。

## スクリプト一覧

### upload_reports_to_azure.py
ローカル環境のレポートデータをAzure Blob Storageにアップロードするスクリプト。
Azure環境への移行時に使用します。

### assign_storage_role.sh
Azure Blob Storageへのアクセス権限（Storage Blob Data Contributor）を
現在ログインしているユーザーに付与するスクリプト。

## 使用方法

各スクリプトの詳細な使用方法は、スクリプトファイル内のコメントを参照してください。
一般的な実行手順：

```bash
# Azure Blob Storageへのアクセス権限付与
./tools/scripts/assign_storage_role.sh

# レポートデータのAzure Blob Storageへのアップロード
python tools/scripts/upload_reports_to_azure.py
```

## アップロード後のコンテナ再起動

レポートをアップロードした後、変更を反映させるにはAPIコンテナの再起動が必要です：

```bash
make azure-restart-api
```

再起動後、ブラウザをリロードすると、アップロードしたレポートが表示されます。
