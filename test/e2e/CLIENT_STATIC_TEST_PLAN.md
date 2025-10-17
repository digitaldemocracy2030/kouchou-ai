# Client 静的ビルドテスト計画

## 概要

このドキュメントは広聴AI Client の静的ビルド版（GitHub Pages等の静的ホスティング）のE2Eテスト計画を定義します。

**対象URL**: http://localhost:3001
**テストフレームワーク**: Playwright
**テストファイルの場所**: `/test/e2e/tests/client-static/`
**ホスティング方法**: http-server で `client/out` をホスティング

## 静的ビルドの特徴

### 1. ビルド時データ埋め込み

静的ビルドは**ビルド時**にAPIサーバーからデータを取得してHTMLに埋め込みます：

```
ビルド時（npm run build:static）:
  Next.js
    ↓ HTTPリクエスト
  APIサーバー（http://localhost:8002）
    ↓ JSONレスポンス
  client/out/*.html（静的HTML生成）

テスト実行時:
  http-server（port 3001）
    ↓ 静的HTMLを配信
  ブラウザ（APIリクエストなし）
```

### 2. basePath（subdirectory）ホスティング

環境変数 `NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH` でサブディレクトリホスティングを設定可能：

- **Root hosting**: `NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH=""` → `https://example.com/`
- **Subdirectory hosting**: `NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH="/kouchou-ai"` → `https://example.com/kouchou-ai/`

この設定により、Next.jsの `basePath` と `assetPrefix` が自動的に設定されます（`client/next.config.ts`）。

## テスト対象

### 1. Root ホスティング（basePath なし）

**環境変数**: `NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH=""`
**アクセスURL**: `http://localhost:3001/`
**用途**: 独自ドメインでのホスティング

### 2. Subdirectory ホスティング（basePath あり）

**環境変数**: `NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH="/kouchou-ai"`
**アクセスURL**: `http://localhost:3001/kouchou-ai/`
**用途**: GitHub Pages（例: `https://username.github.io/kouchou-ai/`）

## テストシナリオ

### 1. Root ホスティング - レポート一覧

#### 1.1 正常系 - レポート一覧の表示

**前提条件:**
- 静的ビルドが `NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH=""` で生成されている

**テスト手順:**
1. http://localhost:3001/ にアクセス
2. `waitForLoadState("networkidle")` で読み込み完了を待つ

**期待結果:**
- ページタイトルに「レポート一覧」が表示される
- レポート作成者名「テスト太郎」が表示される
- 各レポートがカード形式で表示される
- レポートタイトル「テストレポート1」「テストレポート2」が表示される

#### 1.2 正常系 - 静的リソースの読み込み

**テスト手順:**
1. http://localhost:3001/ にアクセス
2. ネットワークリクエストを監視

**期待結果:**
- CSS/JS ファイルが正しく読み込まれる（`/_next/static/...`）
- 画像ファイルが正しく読み込まれる（`/images/...`）
- すべてのリソースが 200 OK で返る
- APIリクエストが発生しない

### 2. Root ホスティング - レポート詳細

#### 2.1 正常系 - レポート詳細の表示

**前提条件:**
- 静的ビルドが生成されている

**テスト手順:**
1. http://localhost:3001/test-report-1 にアクセス
2. `waitForLoadState("networkidle")` で読み込み完了を待つ

**期待結果:**
- レポートタイトルが表示される
- Overview（概要）が表示される
- クラスタ情報が表示される
- 戻るボタンが表示される

#### 2.2 正常系 - 戻るボタン

**テスト手順:**
1. レポート詳細ページから戻るボタンをクリック
2. トップページに戻ることを確認

**期待結果:**
- URL が `/` に変わる
- レポート一覧が表示される

### 3. Subdirectory ホスティング - レポート一覧

#### 3.1 正常系 - basePath付きでレポート一覧の表示

**前提条件:**
- 静的ビルドが `NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH="/kouchou-ai"` で生成されている
- http-server が `--proxy http://localhost:3001?` で起動している（404をindex.htmlにリダイレクト）

**テスト手順:**
1. http://localhost:3001/kouchou-ai/ にアクセス
2. `waitForLoadState("networkidle")` で読み込み完了を待つ

**期待結果:**
- ページタイトルに「レポート一覧」が表示される
- レポート作成者名「テスト太郎」が表示される
- 各レポートがカード形式で表示される

#### 3.2 正常系 - basePath付きで静的リソースの読み込み

**テスト手順:**
1. http://localhost:3001/kouchou-ai/ にアクセス
2. ネットワークリクエストを監視

**期待結果:**
- CSS/JS ファイルが正しいパスで読み込まれる（`/kouchou-ai/_next/static/...`）
- 画像ファイルが正しいパスで読み込まれる（`/kouchou-ai/images/...`）
- すべてのリソースが 200 OK で返る

#### 3.3 正常系 - basePath付きでレポート詳細へのナビゲーション

**テスト手順:**
1. http://localhost:3001/kouchou-ai/ にアクセス
2. 最初のレポートカードをクリック

**期待結果:**
- URL が `/kouchou-ai/test-report-1` に変わる
- レポート詳細が表示される

### 4. Subdirectory ホスティング - レポート詳細

#### 4.1 正常系 - basePath付きでレポート詳細の表示

**前提条件:**
- 静的ビルドが `NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH="/kouchou-ai"` で生成されている

**テスト手順:**
1. http://localhost:3001/kouchou-ai/test-report-1 にアクセス
2. `waitForLoadState("networkidle")` で読み込み完了を待つ

**期待結果:**
- レポートタイトルが表示される
- Overview（概要）が表示される
- クラスタ情報が表示される
- 戻るボタンが表示される

#### 4.2 正常系 - basePath付きで戻るボタン

**テスト手順:**
1. レポート詳細ページから戻るボタンをクリック
2. トップページに戻ることを確認

**期待結果:**
- URL が `/kouchou-ai/` に変わる
- レポート一覧が表示される

### 5. パフォーマンステスト

#### 5.1 静的HTMLの高速読み込み

**テスト対象:**
- Root ホスティング
- Subdirectory ホスティング

**期待結果:**
- レポート詳細ページが5秒以内に読み込まれる（開発サーバー版は10秒）
- 静的HTMLは動的レンダリングよりも高速

### 6. レスポンシブデザイン

#### 6.1 異なる画面サイズでの表示

**テスト対象:**
- デスクトップ（1920x1080）
- タブレット（768x1024）
- モバイル（375x667）

**期待結果:**
- 各画面サイズで適切にレイアウトが調整される
- すべてのコンテンツが表示される
- Root と Subdirectory の両方で正しく動作

## ビルドプロセス

### 1. Root ホスティング用ビルド

```bash
# ダミーAPIサーバーを起動
cd utils/dummy-server
PUBLIC_API_KEY=public E2E_TEST=true npx next dev -p 8002

# 別のターミナルで静的ビルド
cd client
NEXT_PUBLIC_API_BASEPATH=http://localhost:8002 \
API_BASEPATH=http://localhost:8002 \
NEXT_PUBLIC_PUBLIC_API_KEY=public \
NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH="" \
npm run build:static
```

### 2. Subdirectory ホスティング用ビルド

```bash
# ダミーAPIサーバーを起動
cd utils/dummy-server
PUBLIC_API_KEY=public E2E_TEST=true npx next dev -p 8002

# 別のターミナルで静的ビルド
cd client
NEXT_PUBLIC_API_BASEPATH=http://localhost:8002 \
API_BASEPATH=http://localhost:8002 \
NEXT_PUBLIC_PUBLIC_API_KEY=public \
NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH="/kouchou-ai" \
npm run build:static
```

## テスト実装のアプローチ

### Playwright プロジェクト構成

```typescript
// playwright.config.ts
projects: [
  {
    name: "client-static-root",
    testMatch: "**/client-static/root/**/*.spec.ts",
    use: {
      baseURL: "http://localhost:3001",
    },
  },
  {
    name: "client-static-subdir",
    testMatch: "**/client-static/subdir/**/*.spec.ts",
    use: {
      baseURL: "http://localhost:3001/kouchou-ai",
    },
  },
]
```

### ビルドスクリプトの自動化

テスト実行前に自動的に静的ビルドを生成：

```typescript
// playwright.config.ts
webServer: [
  // ダミーAPIサーバーを起動
  {
    command: "cd ../../utils/dummy-server && PUBLIC_API_KEY=public E2E_TEST=true npx next dev -p 8002",
    port: 8002,
  },
  // Root用の静的ビルドを生成
  {
    command: "cd ../../client && NEXT_PUBLIC_API_BASEPATH=http://localhost:8002 API_BASEPATH=http://localhost:8002 NEXT_PUBLIC_PUBLIC_API_KEY=public NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH=\"\" npm run build:static",
    // ビルド完了を待つ
  },
  // Root用のhttp-serverを起動
  {
    command: "cd ../../client && npx http-server out -p 3001 --cors --silent",
    port: 3001,
  },
]
```

## 実装の優先順位

1. **高** - Root ホスティング: レポート一覧表示
2. **高** - Root ホスティング: レポート詳細表示
3. **高** - Root ホスティング: 静的リソースの読み込み検証
4. **高** - Subdirectory ホスティング: レポート一覧表示
5. **高** - Subdirectory ホスティング: レポート詳細表示
6. **中** - Subdirectory ホスティング: 静的リソースのパス検証
7. **中** - パフォーマンステスト
8. **低** - レスポンシブデザインテスト

## 注意事項

1. **ビルド時データ**: 静的ビルドはビルド時にデータが埋め込まれるため、テストフィクスチャを変更した場合は再ビルドが必要
2. **APIリクエストなし**: テスト実行時にAPIリクエストは発生しないため、ネットワークモックは不要
3. **basePath の重要性**: GitHub Pages等では必ずsubdirectoryでホスティングされるため、basePathのテストは必須
4. **http-server の設定**: Subdirectory ホスティングでは `--proxy` オプションが必要（SPAルーティング対応）
5. **トレイリングスラッシュ**: Next.jsの `trailingSlash: true` により、すべてのURLは `/` で終わる

## 参考資料

- [Client型定義](/client/type.ts)
- [Next.js Static Exports](https://nextjs.org/docs/app/building-your-application/deploying/static-exports)
- [Next.js basePath設定](https://nextjs.org/docs/app/api-reference/next-config-js/basePath)
- [Client開発サーバー版テスト計画](/test/e2e/CLIENT_TEST_PLAN.md)
