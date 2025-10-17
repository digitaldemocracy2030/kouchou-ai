# Kouchou AI E2Eテスト

このディレクトリにはPlaywrightを使用したKouchou AIアプリケーションのエンドツーエンドテストが含まれています。

## セットアップ

1. 依存関係のインストール:
   ```
   npm install
   ```

2. Playwrightブラウザのインストール:
   ```
   npx playwright install
   ```

3. 環境変数の設定:
   ```
   cp .env.example .env
   ```
   その後、`.env`ファイルを編集してテスト用の認証情報を追加します。

## テストの実行

### 自動サーバー起動（推奨）

Playwrightの`webServer`機能により、テスト実行時に必要なサーバーが**自動的に起動**されます。

- **Admin tests**: client-admin（port 4000）が自動起動
- **Client tests**: dummy-server（port 8002）とclient（port 3000）が自動起動

**手動でサーバーを起動する必要はありません。**

### テスト実行コマンド

すべてのテストを実行:
```bash
npm test
```

管理画面のテストのみ実行:
```bash
npx playwright test --project=admin
```

Clientのテストのみ実行:
```bash
npx playwright test --project=client
```

Client静的ビルドのテストのみ実行:
```bash
# Root ホスティング用（basePath なし）
npx playwright test --project=client-static-root

# Subdirectory ホスティング用（basePath="/kouchou-ai"）
npx playwright test --project=client-static-subdir

# 両方実行
npx playwright test --project=client-static-root --project=client-static-subdir
```

UIモードでテストを実行:
```bash
npm run test:ui
```

デバッグモードでテストを実行:
```bash
npm run test:debug
```

テストレポートを表示:
```bash
npm run report
```

## ディレクトリ構造とテストファイル

```
test/e2e/
├── tests/
│   ├── admin/
│   │   └── create-report.spec.ts  # 管理画面のレポート作成テスト
│   ├── client/
│   │   ├── reports.spec.ts        # Client レポート一覧テスト（開発サーバー版）
│   │   └── report-detail.spec.ts  # Client レポート詳細テスト（開発サーバー版）
│   ├── client-static/
│   │   ├── root/
│   │   │   ├── reports.spec.ts    # Client レポート一覧テスト（静的ビルド・Root）
│   │   │   └── report-detail.spec.ts  # Client レポート詳細テスト（静的ビルド・Root）
│   │   └── subdir/
│   │       ├── reports.spec.ts    # Client レポート一覧テスト（静的ビルド・Subdir）
│   │       └── report-detail.spec.ts  # Client レポート詳細テスト（静的ビルド・Subdir）
│   ├── seed.spec.ts               # 管理画面の基本的な環境確認テスト
│   ├── verify-dummy-server.spec.ts # ダミーサーバー検証テスト
│   ├── verify-environment.spec.ts  # 環境設定検証テスト
│   ├── simple.spec.ts             # シンプルな接続確認テスト（デバッグ用）
│   └── debug.spec.ts              # 要素確認テスト（デバッグ用）
├── scripts/
│   ├── build-static.sh            # 静的ビルド生成スクリプト
│   └── global-setup.ts            # テスト前のグローバルセットアップ
├── fixtures/
│   ├── admin/                     # 管理画面用フィクスチャ
│   └── client/                    # Client用フィクスチャ（APIモック）
│       ├── metadata.json          # Meta情報
│       ├── reports.json           # レポート一覧
│       └── report-test-report-1.json  # レポート詳細
├── pages/                         # ページオブジェクトモデル（将来的に使用）
├── playwright.config.ts           # Playwright設定
├── TEST_PLAN.md                   # 管理画面テスト計画書
└── CLIENT_TEST_PLAN.md            # Clientテスト計画書
```

### テストファイルの説明

**本番テスト:**
- `tests/admin/create-report.spec.ts` - 管理画面（port 4000）の主要な機能テスト
- `tests/client/reports.spec.ts` - Client（port 3000）のレポート一覧テスト
- `tests/client/report-detail.spec.ts` - Client（port 3000）のレポート詳細テスト
- `tests/seed.spec.ts` - 管理画面の基本的な環境確認テスト

**検証テスト（Clientテスト実行前に推奨）:**
- `tests/verify-dummy-server.spec.ts` - ダミーサーバーが期待通りにテストフィクスチャを返すことを確認
- `tests/verify-environment.spec.ts` - 必要なサーバーが正しい環境変数で起動していることを確認

**デバッグ用テスト:**
- `tests/simple.spec.ts` - ページが正常にロードされるかをチェック（ステータスコード確認）
- `tests/debug.spec.ts` - ページ内の要素（見出し、ボタン、画像など）を表示して確認

## 新しいテストの追加

1. `tests/` または `tests/admin/` にテストファイルを追加
2. テスト内で **必ず `await page.waitForLoadState("networkidle")` を使用**
3. 複雑な操作には `pages/` にページオブジェクトを作成することを検討

## CI連携

テストは以下のタイミングで自動的に実行されます:
- 毎日0時(UTC)
- `e2e-test-required`ラベルが付いたPR

テスト結果はGitHub Actionsのアーティファクトとして利用できます。

## 重要な注意事項

### Next.jsのレンダリング待機

**必須:** すべてのテストで `await page.waitForLoadState("networkidle")` を使用してください。

```typescript
test("例", async ({ page }) => {
  await page.goto("http://localhost:4000/create");
  await page.waitForLoadState("networkidle");  // ← 必須！

  // この後に要素の検証
  await expect(page.getByRole("heading", { name: "..." })).toBeVisible();
});
```

**理由:** Next.jsはクライアントサイドでReactをハイドレーションするため、`goto`だけでは要素が表示される前にテストが実行されてタイムアウトします。

### プロジェクトの分離

`playwright.config.ts` では3つのプロジェクトが定義されています：

- **verify**: 検証テスト（ダミーサーバーと環境設定の確認）
- **admin**: 管理画面テスト（port 4000）
- **client**: Clientテスト（port 3000）- 開発サーバー版
- **client-static-root**: Client静的ビルドテスト（port 3001）- Root ホスティング用
- **client-static-subdir**: Client静的ビルドテスト（port 3002）- Subdirectory ホスティング用（GitHub Pages等）

各プロジェクトは独立して実行でき、それぞれ異なるbaseURLを使用します。

### 検証テストの重要性

Clientテストを実行する前に、検証テストを実行することを強く推奨します：

```bash
# ダミーサーバーの動作確認
npx playwright test tests/verify-dummy-server.spec.ts --project=verify

# 環境変数と設定の確認
npx playwright test tests/verify-environment.spec.ts --project=verify
```

**なぜ検証テストが重要か:**
1. **ダミーサーバーの検証** (`verify-dummy-server.spec.ts`)
   - ダミーサーバーが期待通りにテストフィクスチャを返しているか確認
   - `/meta/metadata.json`, `/reports`, `/reports/[slug]` のエンドポイントを個別にテスト
   - フィクスチャのデータ構造が正しいか検証

2. **環境設定の検証** (`verify-environment.spec.ts`)
   - clientサーバーがダミーサーバーを正しく参照しているか確認
   - 環境変数が正しく設定されているか確認
   - テストに必要なサーバーが起動しているか確認

これらの検証テストが失敗する場合、Clientテストも失敗するため、先に問題を特定できます。

## テストのデバッグ

テストが失敗する場合は、以下の順序でデバッグを行ってください：

### 0. 検証テスト（最優先）

```bash
# まず検証テストで基本的な環境を確認
npx playwright test tests/verify-dummy-server.spec.ts --project=verify
npx playwright test tests/verify-environment.spec.ts --project=verify
```

これらが失敗する場合、サーバーの起動状態や環境変数の設定を確認してください。

### 1. 接続確認

```bash
npx playwright test tests/simple.spec.ts
```

- ページが200 OKで返ってくるか確認
- ページのHTMLサイズを表示

### 2. 要素確認

```bash
npx playwright test tests/debug.spec.ts
```

- ページ内の全ての見出し、ボタン、画像を表示
- 要素が見つからない場合のデバッグに使用

### 3. ブラウザで確認

```bash
npx playwright test --headed --debug
```

- ブラウザを表示してステップ実行
- Playwrightインスペクターを使用

## 管理画面テスト（Admin）

詳細なテスト計画は `TEST_PLAN.md` を参照してください。

### 対象

- **URL**: http://localhost:4000（client-admin）
- **機能**: レポート作成、パイプライン設定

### テスト実行

```bash
# サーバーは自動起動されるので、テストを直接実行できます
npx playwright test --project=admin
# または
npx playwright test tests/admin/
```

**注意**: `playwright.config.ts`の`webServer`設定により、client-adminサーバーは自動的に起動されます。手動起動は不要です。

## Clientテスト（レポート表示画面）

詳細なテスト計画は `CLIENT_TEST_PLAN.md` を参照してください。

### 対象

- **URL**: http://localhost:3000（client）
- **機能**: レポート一覧表示、レポート詳細表示

### テストの特徴

**ダミーAPIサーバーを使用:**
- `utils/dummy-server`（Next.js）がテストフィクスチャを返すAPIサーバーとして動作
- 実際のPython APIサーバー（port 8001）は不要
- テストデータは `fixtures/client/` に配置
- Next.js Server Componentsが実際にHTTPリクエストを行うため、真のE2Eテスト

### テスト実行

```bash
# サーバーは自動起動されるので、テストを直接実行できます
npx playwright test --project=client
# または個別のテストファイルを実行
npx playwright test tests/client/reports.spec.ts
npx playwright test tests/client/report-detail.spec.ts

# 推奨: まず検証テストを実行して環境を確認
npx playwright test tests/verify-dummy-server.spec.ts --project=verify
npx playwright test tests/verify-environment.spec.ts --project=verify
```

**注意**:
- `playwright.config.ts`の`webServer`設定により、dummy-server（port 8002）とclient（port 3000）は自動的に起動されます
- 手動起動は不要です
- テスト失敗時は、まず検証テストを実行してサーバーと環境変数が正しく設定されているか確認してください

### 手動でサーバーを起動する場合（デバッグ用）

通常は不要ですが、デバッグのためにサーバーを手動で起動したい場合：

```bash
# ターミナル1: ダミーAPIサーバーを起動（port 8002）
cd utils/dummy-server
PUBLIC_API_KEY=public E2E_TEST=true npx next dev -p 8002

# ターミナル2: Clientサーバーを起動（port 3000、ダミーAPIサーバーを参照）
cd client
NEXT_PUBLIC_API_BASEPATH=http://localhost:8002 \
API_BASEPATH=http://localhost:8002 \
NEXT_PUBLIC_PUBLIC_API_KEY=public \
npx next dev -p 3000
```

### テストデータ（フィクスチャ）

Clientテストでは以下のフィクスチャを使用：

- `fixtures/client/metadata.json` - Meta情報（レポート作成者情報）
- `fixtures/client/reports.json` - レポート一覧（2件のテストレポート）
- `fixtures/client/report-test-report-1.json` - レポート詳細（**実際の本番データ**: `utils/dummy-server/app/reports/example/hierarchical_result.json` から取得したAIと著作権に関する意見データ）

これらのフィクスチャは `utils/dummy-server` が読み込み、HTTP APIとして提供します。

**重要:** `report-test-report-1.json` は実際のパイプライン処理結果をコピーした本番データ構造を使用しているため、テストが実際のデータ構造を正確に検証できます。

### テストコード例

```typescript
test("レポート一覧表示", async ({ page }) => {
  // ダミーAPIサーバーが自動的にテストフィクスチャを返す
  await page.goto("/");
  await page.waitForLoadState("networkidle");

  // テストフィクスチャのデータを検証
  await expect(page.getByText("テスト太郎")).toBeVisible();
  await expect(page.getByText("テストレポート1")).toBeVisible();
});
```

### ダミーサーバーの実装

ダミーサーバー（`utils/dummy-server`）は以下の機能を提供：

1. **環境変数 `E2E_TEST=true`** の時、テストフィクスチャを読み込み
2. **`/meta/metadata.json`**: middleware.tsがテストフィクスチャを返す
3. **`/reports`**: `app/reports/route.ts`がテストフィクスチャを返す
4. **`/reports/[slug]`**: `app/reports/[slug]/route.ts`がテストフィクスチャを返す

E2E_TEST環境変数が設定されていない場合は、通常のダミーデータを返します。

## Client静的ビルドテスト（GitHub Pages等の静的ホスティング）

静的ビルドをホスティングした環境での動作をテストします。

### 対象

**2種類のホスティング環境をテスト:**

1. **Root ホスティング** (`client-static-root`)
   - **URL**: http://localhost:3001
   - **basePath**: なし
   - **用途**: 独自ドメインでのホスティング（例: `https://example.com/`）

2. **Subdirectory ホスティング** (`client-static-subdir`)
   - **URL**: http://localhost:3002/kouchou-ai
   - **basePath**: `/kouchou-ai`
   - **用途**: GitHub Pages等のサブディレクトリホスティング（例: `https://username.github.io/kouchou-ai/`）

### テストの特徴

**静的HTMLファイルをテスト:**
- 事前にビルドされた静的HTML を http-server でホスティング
- APIサーバーへのリクエストは発生しない（ビルド時にデータが埋め込まれている）
- 実際のホスティング環境に近い状態でテスト可能
- **basePath の違い**により、リソースのパスやリンクが異なることを検証

### 自動ビルド（推奨）

テスト実行時に **自動的に静的ビルドが生成されます**：

```bash
# Root と Subdirectory の両方のビルドが自動生成されます
npx playwright test --project=client-static-root
npx playwright test --project=client-static-subdir

# または両方同時に実行
npx playwright test --project=client-static-root --project=client-static-subdir
```

**自動ビルドの仕組み:**
- テスト実行前に `scripts/global-setup.ts` が実行されます
- ダミーAPIサーバー（port 8002）からデータを取得して2種類のビルドを生成
  1. Root用: `client/out` (basePath なし)
  2. Subdirectory用: `client/out-subdir` (basePath="/kouchou-ai")

### 手動ビルド（デバッグ用）

自動ビルドをスキップしたい場合：

```bash
# 1. 手動でビルドを生成
cd test/e2e
./scripts/build-static.sh root      # Root用
./scripts/build-static.sh subdir    # Subdirectory用

# 2. 自動ビルドをスキップしてテスト実行
SKIP_STATIC_BUILD=true npx playwright test --project=client-static-root
```

### テスト実行

```bash
# Root ホスティング用テスト
npx playwright test --project=client-static-root

# Subdirectory ホスティング用テスト
npx playwright test --project=client-static-subdir

# 両方実行
npx playwright test --project=client-static-root --project=client-static-subdir

# 個別のテストファイルを実行
npx playwright test tests/client-static/root/reports.spec.ts
npx playwright test tests/client-static/subdir/reports.spec.ts
```

**注意**:
- `playwright.config.ts`の`webServer`設定により、http-server が自動的に起動されます
  - Root用: port 3001
  - Subdirectory用: port 3002
- 初回実行時はビルドに数分かかります（2回目以降はキャッシュされます）

### 静的ビルドとダミーサーバーの関係

静的ビルドは**ビルド時**にダミーAPIサーバーからデータを取得してHTMLに埋め込みます：

```
ビルド時（グローバルセットアップ）:
  scripts/build-static.sh
    ↓ HTTPリクエスト
  dummy-server (port 8002)
    ↓ フィクスチャを返す
  client/out (Root用静的HTML)
  client/out-subdir (Subdirectory用静的HTML)

テスト実行時:
  http-server (port 3001 / 3002)
    ↓ 静的HTMLを配信
  ブラウザ（APIリクエストなし）
```

### basePath の検証

Subdirectory ホスティング用テストでは、以下を検証します：

1. **リソースパス**: CSS/JSファイルが `/kouchou-ai/_next/...` のパスで読み込まれる
2. **ナビゲーション**: リンクが `/kouchou-ai/test-report-1` などの正しいパスになる
3. **戻るボタン**: `/kouchou-ai/` に正しく戻る

### デバッグ用：手動でサーバーを起動する場合

通常は不要ですが、デバッグのために手動で静的ファイルをホスティングしたい場合：

```bash
# Root用
cd client
npx http-server out -p 3001

# Subdirectory用
cd client
npx http-server out-subdir -p 3002
```
