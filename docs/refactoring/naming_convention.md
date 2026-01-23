# ディレクトリ命名規約

このドキュメントは、リファクタリングによるディレクトリ構成変更の対応表と命名規約を定義します。

## ディレクトリ対応表

### アプリケーション (apps/)

| 旧名 | 新名 | Docker サービス名 | 説明 |
|-----|-----|------------------|------|
| `server/` | `apps/api/` | `api` | FastAPI バックエンドAPI |
| `client/` | `apps/public-viewer/` | `public-viewer` | 一般公開用レポート閲覧画面 (Next.js) |
| `client-admin/` | `apps/admin/` | `admin` | 管理画面 (Next.js) |
| `client-static-build/` | `apps/static-site-builder/` | `static-site-builder` | 静的サイトビルドサービス |

### ツール・スクリプト (tools/)

| 旧名 | 新名 | 説明 |
|-----|-----|------|
| `scripts/` | `tools/scripts/` | ユーティリティスクリプト |

### 実験的コード (experiments/)

| 旧名 | 新名 | 説明 |
|-----|-----|------|
| `experimental/` | `experiments/` | 実験的・調査目的のコード |

## 命名規約

### アプリケーションディレクトリ (apps/)

1. **役割が明確な名前**を使用する
   - `api` - バックエンドAPI
   - `public-viewer` - 公開閲覧用フロントエンド
   - `admin` - 管理者用フロントエンド
   - `static-site-builder` - 静的サイト生成

2. **ケバブケース（kebab-case）**を使用する
   - 例: `public-viewer`, `static-site-builder`

3. **抽象的すぎる名前を避ける**
   - 避けるべき: `client`, `server`, `frontend`, `backend`
   - 推奨: `public-viewer`, `admin`, `api`

### パッケージディレクトリ (packages/)

1. **機能または関心領域を表す名前**を使用する
   - `analysis-core` - 分析パイプライン基盤
   - `report-schema` - レポートスキーマ定義
   - `ui-shared` - 共通UIコンポーネント

2. **ケバブケース（kebab-case）**を使用する

### プラグインディレクトリ (plugins/)

1. **カテゴリ別にサブディレクトリ**を構成する
   - `plugins/analysis/` - 分析プラグイン
   - `plugins/visualization/` - 可視化プラグイン

2. **プラグイン個別ディレクトリはケバブケース**
   - 例: `plugins/analysis/hierarchical-clustering/`

## Docker サービス名との対応

Docker Compose のサービス名とディレクトリ名は統一されています:

| apps/ ディレクトリ | Docker サービス名 |
|-------------------|------------------|
| `apps/api/` | `api` |
| `apps/public-viewer/` | `public-viewer` |
| `apps/admin/` | `admin` |
| `apps/static-site-builder/` | `static-site-builder` |

## Azure Container Apps 名との対応

Azure Container Apps でのコンテナ名もディレクトリ名と統一されています:

| apps/ ディレクトリ | Azure Container App 名 |
|-------------------|------------------------|
| `apps/api/` | `api` |
| `apps/public-viewer/` | `public-viewer` |
| `apps/admin/` | `admin` |
| `apps/static-site-builder/` | `static-site-builder` |

## 既存環境からの移行ガイド

### ⚠️ 互換性に関する重要な注意

このリファクタリングでは、Docker サービス名と Azure Container Apps 名が変更されました。**既にデプロイ済みの環境がある場合**は、以下の対応が必要です。

### サービス名の変更

| 旧サービス名 | 新サービス名 |
|-------------|-------------|
| `client` | `public-viewer` |
| `client-admin` | `admin` |
| `client-static-build` | `static-site-builder` |

※ `api` は変更なし

### Azure Container Apps 移行手順

既存の Azure Container Apps 環境を移行する場合、以下のいずれかの方法を選択してください:

#### 方法 A: 新規環境を構築（推奨）

最も確実な方法です。既存のデータをバックアップし、新規環境を構築します。

```bash
# 1. 既存環境からレポートデータをバックアップ
make azure-check-revalidate-secret  # REVALIDATE_SECRETの確認
python tools/scripts/fetch_reports.py --api-url https://<YOUR_API_DOMAIN>

# 2. 既存リソースグループを削除（注意: 全データが削除されます）
make azure-cleanup

# 3. 新規環境をセットアップ
make azure-setup-all
```

#### 方法 B: 既存環境を更新（高度）

Azure CLI を使用して既存のコンテナアプリ名を変更することはできません。そのため、以下の手順が必要です:

1. **既存コンテナを削除**
   ```bash
   az containerapp delete --name client --resource-group <YOUR_RG> --yes
   az containerapp delete --name client-admin --resource-group <YOUR_RG> --yes
   az containerapp delete --name client-static-build --resource-group <YOUR_RG> --yes
   ```

2. **新しい名前でコンテナを作成**
   ```bash
   make azure-deploy
   ```

3. **環境変数とシークレットを再設定**
   ```bash
   make azure-config-update
   ```

### ローカル Docker Compose 環境

ローカル環境では、`docker compose down` を実行してから `docker compose up --build` を実行するだけで新しいサービス名が適用されます。

```bash
docker compose down
docker compose up --build
```

### Makefile ターゲット名の変更

以下の Make ターゲット名が変更されました。スクリプトやCI/CDで使用している場合は更新が必要です:

| 旧ターゲット名 | 新ターゲット名 |
|---------------|---------------|
| `azure-logs-client` | `azure-logs-public-viewer` |
| `azure-logs-client-static-build` | `azure-logs-static-site-builder` |
| `azure-restart-client` | `azure-restart-public-viewer` |
| `azure-restart-client-static-build` | `azure-restart-static-site-builder` |
| `azure-fix-client-admin` | `azure-fix-admin` |

### GitHub Actions 環境変数

GitHub Actions で Azure デプロイを使用している場合、リポジトリ変数（Variables）やシークレット（Secrets）の変更は不要です。ワークフローファイル自体が更新されているため、自動的に新しいサービス名が使用されます。

### 確認事項

移行後、以下を確認してください:

1. **ヘルスチェック**: 全サービスが正常に起動していること
   ```bash
   make azure-verify
   ```

2. **サービスURL**: 新しいサービスURLにアクセスできること
   ```bash
   make azure-info
   ```

3. **レポート表示**: 既存のレポートが正常に表示されること

## 更新履歴

- 2026-01-19: Docker/Azureサービス名をディレクトリ名に統一、移行ガイドを追加
- 2026-01-19: 初版作成
