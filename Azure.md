# Azure 環境へのセットアップ方法
このドキュメントでは、広聴AIアプリケーションをAzure Container Appsにデプロイする方法について説明します。

## 免責事項
* 本ドキュメントは情報提供のみを目的としており、特定の環境でのデプロイを保証するものではありません。
* 本ガイドに従って実施されたデプロイや設定によって生じた問題、損害、セキュリティインシデントについて、本プロジェクトのコントリビューターは一切の責任を負いません。
* 記載されている構成はあくまでインフラ構築の一例です。実運用にあたっては、各組織のセキュリティポリシーやコンプライアンス要件に従って適切に評価・カスタマイズしてください。

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

次に、以下の手順で `.env.azure` を作成し、Azure環境で用いる環境変数を設定してください。

```bash
cp .env.azure.example .env.azure
```

`.env.azure`ファイルでは以下のパラメータをカスタマイズできます：

```
# Azure環境特有の設定
AZURE_RESOURCE_GROUP=your-resource-group
AZURE_LOCATION=japaneast
AZURE_ACR_NAME=yourregistry
AZURE_ACR_SKU=Basic
AZURE_CONTAINER_ENV=your-container-env
AZURE_WORKSPACE_NAME=your-logs
AZURE_BLOB_STORAGE_CONTAINER_NAME=your_container_name
AZURE_BLOB_STORAGE_ACCOUNT_NAME=your_account_name
```

2025年4月時点での各項目の説明を以下に記載します。
詳細はAzureの公式ドキュメントをご確認ください。

#### AZURE_RESOURCE_GROUP
- **説明**: Azureリソースグループの名前を指定します。リソースグループは、Azureリソースを論理的にグループ化するためのコンテナです。
- **設定時の注意事項**:
  - 名前は1〜90文字で、英数字、ハイフン、アンダースコア、ピリオドのみ使用可能です
  - 名前の末尾にピリオドを含めることはできません
- **設定例**
  - kouchou-ai-rg

#### AZURE_LOCATION
- **説明**: Azureリソースをデプロイするリージョン（地理的な場所）を指定します。
- **設定時の注意事項**:
  - 「japaneast」等のAzureがサービスを提供しているリージョンが指定できます
  - 日本国内のユーザーを想定して広聴AIをホスティングする場合、基本的にはjapaneastを指定することをおすすめします
    - 国内からアクセスした際のレイテンシーが低く、また提供されているサービスの種類も国内の他のリージョンと比べて多いため
- **設定例**
  - japaneast

#### AZURE_ACR_NAME
- **説明**: Azure Container Registry（ACR）の名前を指定します。ACRはDockerコンテナイメージを保存するためのプライベートレジストリです。
- **設定時の注意事項**:
  - 名前は5〜50文字の英数字のみで構成する必要があります
  - 大文字は使用できません（小文字のみ）
  - **Azureの全アカウントにおいて一意である必要があります**
- **設定例**
  - kouchou-ai-acr

#### AZURE_ACR_SKU
- **説明**: Azure Container Registryのサービスティア（SKU）を指定します。
- **設定時の注意事項**:
  - Basic、Standard、Premiumの3種類があり、いずれかを指定してください。それぞれの詳細は公式ドキュメントをご確認ください
- **設定例**
  - Basic

#### AZURE_CONTAINER_ENV
- **説明**: Azure Container Appsの環境名を指定します。Container Appsは、コンテナ化されたアプリケーションを実行するためのフルマネージドサービスです。
- **設定時の注意事項**:
  - 名前は1〜63文字で、英数字、ハイフンのみ使用可能です
  - 名前の先頭と末尾はアルファベットまたは数字である必要があります
- **設定例**
  - kouchou-ai-env

#### AZURE_WORKSPACE_NAME
- **説明**: Azure Log Analyticsワークスペースの名前を指定します。ログ分析とモニタリングに使用されます。
- **設定時の注意事項**:
  - 名前は4〜63文字で、英数字、ハイフンのみ使用可能です
  - 名前の先頭と末尾はアルファベットまたは数字である必要があります
- **設定例**
  - kouchou-ai-logs

#### AZURE_BLOB_STORAGE_ACCOUNT_NAME
- **説明**: Azure Blob Storageアカウントの名前を指定します。Blobストレージはオブジェクトストレージソリューションで、テキストなどの非構造化データを保存するために使用されます。
- **設定時の注意事項**:
  - 名前は3〜24文字の英数字のみで構成する必要があります
  - 大文字は使用できません（小文字のみ）
  - **Azureの全アカウントにおいて一意である必要があります**
- **設定例**
  - kouchouaistorage

#### AZURE_BLOB_STORAGE_CONTAINER_NAME
- **説明**: Azure Blob Storageコンテナの名前を指定します。コンテナはBlobを整理するためのディレクトリのような概念です。
- **設定時の注意事項**:
  - 名前は3〜63文字で、小文字、数字、ハイフンのみ使用可能です
  - 名前の先頭はアルファベットまたは数字である必要があります
  - 連続したハイフンは使用できません
- **設定例**
  - kouchou-ai-storage-container

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

表示された admin の URL にアクセスし、BASIC_AUTH_USERNAME, BASIC_AUTH_PASSWORD で設定した認証情報を入力することで、レポート生成ができます。

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
make azure-fix-admin

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
make azure-logs-public-viewer

# APIログ
make azure-logs-api

# 管理画面ログ
make azure-logs-admin

# クライアントビルドログ
make azure-logs-static-site-builder
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
make azure-fix-admin
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
make azure-logs-public-viewer
make azure-logs-admin
```

### 5. デプロイ時のヘルスチェック設定問題

ヘルスチェック設定やポリシーの適用に問題がある場合：

```bash
make azure-apply-policies
