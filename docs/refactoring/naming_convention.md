# ディレクトリ命名規約

このドキュメントは、リファクタリングによるディレクトリ構成変更の対応表と命名規約を定義します。

## ディレクトリ対応表

### アプリケーション (apps/)

| 旧名 | 新名 | Docker サービス名 | 説明 |
|-----|-----|------------------|------|
| `server/` | `apps/api/` | `api` | FastAPI バックエンドAPI |
| `client/` | `apps/public-viewer/` | `client` | 一般公開用レポート閲覧画面 (Next.js) |
| `client-admin/` | `apps/admin/` | `client-admin` | 管理画面 (Next.js) |
| `client-static-build/` | `apps/static-site-builder/` | `client-static-build` | 静的サイトビルドサービス |

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

Docker Compose でのサービス名は後方互換性のため変更しない:

| apps/ ディレクトリ | Docker サービス名 |
|-------------------|------------------|
| `apps/api/` | `api` |
| `apps/public-viewer/` | `client` |
| `apps/admin/` | `client-admin` |
| `apps/static-site-builder/` | `client-static-build` |

## Azure Container Apps 名との対応

Azure Container Apps でのコンテナ名も後方互換性のため変更しない:

| apps/ ディレクトリ | Azure Container App 名 |
|-------------------|------------------------|
| `apps/api/` | `api` |
| `apps/public-viewer/` | `client` |
| `apps/admin/` | `client-admin` |
| `apps/static-site-builder/` | `client-static-build` |

## 更新履歴

- 2026-01-19: 初版作成
