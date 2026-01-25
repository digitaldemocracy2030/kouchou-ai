# Azure Blob Storage 移行ガイド

このガイドでは、広聴AIアプリケーションでAzure Blob Storageを使用してレポートデータを永続化する方法について説明します。

## 目次

1. [概要](#概要)
2. [環境設定](#環境設定)
3. [既存レポートの永続化](#既存レポートの永続化)
4. [トラブルシューティング](#トラブルシューティング)
5. [運用コマンド](#運用コマンド)

## 概要
2025-04-08以前に作成されたAzure Container Apps環境では、コンテナが再起動されるとコンテナ内のファイルが失われます。Azure Blob Storageを使用することで、レポートデータを永続的に保存し、コンテナが再起動されても利用可能な状態を維持できます。

## 環境設定

### 0. 既存レポートのバックアップ

```bash
python scripts/fetch_reports.py --api-url https://your-api-url
```

このスクリプトは全てのレポートをローカル環境にダウンロードします。

注: 完了した分析の最終結果データのみを保存します。

### 1. 環境変数の設定

`.env`ファイルに以下の設定を追加します：

```
# Storage settings
# ローカル環境では"local"、Azure環境では"azure_blob"を設定
STORAGE_TYPE=azure_blob
# Azure Blob Storageのアカウント名
AZURE_BLOB_STORAGE_ACCOUNT_NAME=your_storage_account_name
# Azure Blob Storageのコンテナ名
AZURE_BLOB_STORAGE_CONTAINER_NAME=your_container_name
```

**注意事項：**
- ストレージアカウント名は3〜24文字の小文字英数字で、全体で一意である必要があります
- コンテナ名は3〜63文字の小文字英数字とハイフンで構成する必要があります

### 2. Azure Blob Storageの作成

既存のAzure環境がある場合は、以下のコマンドでストレージを作成します：

```bash
make azure-create-storage
```

### 3. ストレージへのアクセス権限の設定

ストレージへのアクセス権限を設定するには、以下のスクリプトを実行します：

```bash
./scripts/assign_storage_role.sh
```

このスクリプトは、現在ログインしているユーザーに「Storage Blob Data Contributor」ロールを付与します。

## 既存レポートの永続化

### 1. レポートのアップロード

既存のレポートをAzure Blob Storageにアップロードするには、以下のスクリプトを使用します：

```bash
python scripts/upload_reports_to_azure.py
```

### 2. APIコンテナの再起動

レポートをアップロードした後、変更を反映させるにはAPIコンテナの再起動が必要です：

```bash
make azure-restart-api
```

再起動後、ブラウザをリロードすると、アップロードしたレポートが表示されます。

## トラブルシューティング

### 権限エラー（AuthorizationPermissionMismatch）

アップロード時に以下のようなエラーが表示される場合：

```
ErrorCode:AuthorizationPermissionMismatch
```

これは、ストレージアカウントへのアクセス権限が不足していることを示しています。以下の手順で解決できます：

1. Azure CLIでログインしていることを確認：
   ```bash
   az login
   ```

2. ストレージへのアクセス権限を付与：
   ```bash
   ./scripts/assign_storage_role.sh
   ```

### コンテナ再起動後もレポートが表示されない

1. ログを確認して問題を特定：
   ```bash
   make azure-logs-api
   ```

2. 環境変数が正しく設定されているか確認：
   ```bash
   make azure-config-update
   ```

3. APIコンテナを再起動：
   ```bash
   make azure-restart-api
   ```

## 運用コマンド

### ステータス確認

```bash
make azure-status
```

### ログの確認

```bash
# APIログ
make azure-logs-api
```

### コンテナの停止/起動

```bash
# コンテナをスケールダウン
make azure-stop

# 再度使う時に起動
make azure-start
```
