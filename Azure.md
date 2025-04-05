# Azure 環境へのセットアップ方法
このドキュメントでは、広聴AIアプリケーションをAzure Container Appsにデプロイする方法について説明します。

## 免責事項
* 本ドキュメントは情報提供のみを目的としており、特定の環境でのデプロイを保証するものではありません。
* 本ガイドに従って実施されたデプロイや設定によって生じた問題、損害、セキュリティインシデントについて、本プロジェクトのコントリビューターは一切の責任を負いません。
* 記載されている構成はあくまでインフラ構築の一例です。実運用にあたっては、各組織のセキュリティポリシーやコンプライアンス要件に従って適切に評価・カスタマイズしてください。

## 注意事項
* 現在のサンプル構成では、Azure Container Appsのコンテナを停止すると、出力済みのレポートが消失します
  * コンテナ環境でのレポートデータ保存機能は現在開発中です
  * この現象は、永続化ボリュームを持たない実行環境に特有のものです。永続化ボリュームを備えた仮想マシンなどにAPIサーバーをデプロイした場合は、データがボリューム上に保存されるため、明示的にファイル削除等を行わない限りレポートが削除されることはありません

## 目次
1. 前提条件
2. 初期セットアップ
3. デプロイプロセス
4. 環境変数の設定
5. 運用コマンド
6. トラブルシューティング

## 前提条件

- Azureアカウント
- Dockerがインストールされた環境
- OpenAI APIキー

## 初期セットアップ

### 1. 環境変数の設定

`.env.example`をコピーして`.env`ファイルを作成し、必要な環境変数を設定します。

```bash
cp .env.example .env
```

特に以下の環境変数は重要です：

```
# API認証用キー
PUBLIC_API_KEY=your_public_key
ADMIN_API_KEY=your_admin_key

# BASIC認証用（管理画面）
BASIC_AUTH_USERNAME=your_username
BASIC_AUTH_PASSWORD=your_password

# OpenAI API設定
OPENAI_API_KEY=your_openai_key
```

また、Azure環境設定をカスタマイズする必要がある場合は、オプションで`.env.azure`ファイルを作成することができます。このファイルは必須ではなく、作成しなくても自動的にデフォルト値が使用されます。

```bash
cp .env.azure.example .env.azure
```

`.env.azure`ファイルでは以下のパラメータをカスタマイズできます：

```
# Azure環境特有の設定（すべてオプション）
AZURE_RESOURCE_GROUP=your-resource-group
AZURE_LOCATION=japaneast
AZURE_ACR_NAME=yourregistry
AZURE_ACR_SKU=Basic
AZURE_CONTAINER_ENV=your-container-env
AZURE_WORKSPACE_NAME=your-logs
AZURE_BLOB_STORAGE_CONTAINER_NAME=your_container_name
AZURE_BLOB_STORAGE_ACCOUNT_NAME=your_account_name
```

これらの設定は任意で、未設定の場合はシステムが自動的に以下のデフォルト値を使用します：

### 2. Azureにログイン

```bash
make azure-login
```

表示されるURLにアクセスしてログインします。

## デプロイプロセス

### 一括デプロイ（推奨）

すべてのセットアップを一度に行うには：

```bash
make azure-setup-all
```

これにより、以下の手順が自動的に実行されます：

1. リソースグループとACRのセットアップ
2. ACRへのログイン
3. ストレージの作成
4. コンテナイメージのビルド
5. イメージのプッシュ
6. Container Appsへのデプロイ
7. マネージドIDのContainer Appへの割り当て
8. Container AppのマネージドIDへのストレージアクセス権の割り当て
9. ポリシーとヘルスチェックの適用
10. 環境変数の設定
11. 管理画面の環境変数を修正してビルド
12. 環境の検証
13. サービスURLの確認

全体のプロセスは初回実行時に約20分程度かかることがあります。

表示された client-admin の URL にアクセスし、BASIC_AUTH_USERNAME, BASIC_AUTH_PASSWORD で設定した認証情報を入力することで、レポート生成ができます。

## 参考情報
### 手動ステップバイステップのデプロイ

個別のコマンドを実行することもできます：

```bash
# 1. リソースグループとACRのセットアップ
make azure-setup

# 2. ACRへのログイン
make azure-acr-login-auto

# 3. ストレージの作成
make azure-create-storage

# 4. コンテナイメージのビルド
make azure-build

# 5. イメージをプッシュ
make azure-push

# 6. Container Appsへのデプロイ
make azure-deploy

# 待機（20秒）

# 7. マネージドIDのContainer Appへの割り当て
make azure-assign-managed-identity

# 8. Container AppのマネージドIDへのストレージアクセス権の割り当て
make azure-assign-storage-access

# 9. ポリシーとヘルスチェックの適用
make azure-apply-policies

# 10. 環境変数の設定
make azure-config-update

# 待機（30秒）

# 11. 管理画面の環境変数を修正してビルド
make azure-fix-client-admin

# 12. 環境の検証
make azure-verify

# 13. サービスURLの確認
make azure-info
```

## 運用コマンド

### サービスURLの表示

```bash
make azure-info
```

### ステータス確認

```bash
make azure-status
```

### ログの確認

```bash
# クライアントログ
make azure-logs-client

# APIログ
make azure-logs-api

# 管理画面ログ
make azure-logs-admin
```

### コスト最適化

使用していない時間帯にコンテナをスケールダウンすることでコストを抑制できます：

```bash
# コンテナをスケールダウン
make azure-stop

# 再度使う時に起動
make azure-start
```

### リソースの完全削除

以下のコマンドで、作成したすべてのAzureリソースを削除できます：

```bash
make azure-cleanup
```

**注意**: このコマンドは取り消せません。すべてのリソースが完全に削除されます。

## トラブルシューティング

### 1. 環境変数の問題

環境変数が正しく設定されていない場合は：

```bash
make azure-fix-client-admin
```

### 2. デプロイ失敗時の検証

デプロイ状態を確認します：

```bash
make azure-verify
```

### 3. コンテナの再起動

問題が発生した場合、コンテナを再起動することで解決することがあります：

```bash
make azure-stop
sleep 10
make azure-start
```

### 4. ログの確認

エラーの詳細を確認するにはログを調査します：

```bash
make azure-logs-api
make azure-logs-client
make azure-logs-admin
```

### 5. デプロイ時のヘルスチェック設定問題

ヘルスチェック設定やポリシーの適用に問題がある場合：

```bash
make azure-apply-policies
