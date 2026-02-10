# E2Eテスト開発ガイド

このファイルは、広聴AI（Kouchou-AI）のE2Eテスト開発における重要な知見と注意事項をまとめています。

## 目次
1. [Next.jsとPlaywrightの重要な注意事項](#nextjsとplaywrightの重要な注意事項)
2. [テスト実行の基本原則](#テスト実行の基本原則)
3. [ダミーサーバーの実装パターン](#ダミーサーバーの実装パターン)
4. [よくある問題と解決方法](#よくある問題と解決方法)
5. [テストデータの管理](#テストデータの管理)

---

## Next.jsとPlaywrightの重要な注意事項

### 1. ハイドレーション待機は必須

**必ず `await page.waitForLoadState("networkidle")` を使用すること**

```typescript
// ❌ 悪い例
test("例", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("タイトル")).toBeVisible(); // タイムアウトする
});

// ✅ 良い例
test("例", async ({ page }) => {
  await page.goto("/");
  await page.waitForLoadState("networkidle"); // 必須！
  await expect(page.getByText("タイトル")).toBeVisible();
});
```

**理由**: Next.jsはクライアントサイドでReactをハイドレーションするため、`goto`だけでは要素が表示される前にテストが実行されてタイムアウトします。

### 2. Strict Mode違反への対処

Playwrightはデフォルトで厳密モード（strict mode）が有効で、セレクタが複数の要素にマッチするとエラーになります。

```typescript
// ❌ エラー: strict mode violation: getByText() resolved to 2 elements
await expect(page.getByText(/生成AIと著作権/)).toBeVisible();

// ✅ 修正: .first() または .last() を使用
await expect(page.getByText(/生成AIと著作権/).first()).toBeVisible();

// ✅ 修正: より具体的なセレクタを使用
await expect(page.getByRole("heading").getByText(/生成AIと著作権/)).toBeVisible();
```

**よくあるケース**: SVGの`<tspan>`とHTMLの`<h2>`の両方に同じテキストが含まれている場合など。

### 3. Next.js 15の非同期params

Next.js 15では、動的ルートの`params`が非同期になっているため、必ず`await`が必要です。

```typescript
// ❌ Next.js 15ではエラー
export async function GET(request: Request, context: { params: { slug: string } }) {
  const { slug } = context.params;
}

// ✅ 正しい書き方
export async function GET(request: Request, context: { params: Promise<{ slug: string }> }) {
  const { slug } = await context.params;
}
```

---

## テスト実行の基本原則

### 1. 検証テストを最初に実行する

**重要**: テストが失敗した場合、まず検証テストを実行して環境を確認すること。

```bash
# 1. ダミーサーバーの動作確認
npx playwright test tests/verify-dummy-server.spec.ts --project=verify

# 2. 環境変数と設定の確認
npx playwright test tests/verify-environment.spec.ts --project=verify

# 3. 検証が成功したら本番テストを実行
npx playwright test --project=client
```

**理由**:
- ダミーサーバーが期待通りにフィクスチャを返していない場合、すべてのテストが失敗します
- 環境変数が正しく設定されていない場合、clientが間違ったサーバーを参照します
- 検証テストで問題を早期発見することで、デバッグ時間を大幅に短縮できます

### 2. サーバー起動の確認

テスト実行前に必要なサーバーがすべて起動していることを確認：

```bash
# ポート使用状況を確認
lsof -i :3000  # public-viewer
lsof -i :4000  # admin
lsof -i :8002  # dummy server

# プロセスを停止
kill -9 <PID>
```

### 3. 環境変数の確認

Clientテストでは、clientサーバーが正しい環境変数で起動している必要があります：

```bash
# clientサーバーの環境変数（必須）
NEXT_PUBLIC_API_BASEPATH=http://localhost:8002
API_BASEPATH=http://localhost:8002
NEXT_PUBLIC_PUBLIC_API_KEY=public

# ダミーサーバーの環境変数（必須）
PUBLIC_API_KEY=public
E2E_TEST=true
```

**確認方法**: `tests/verify-environment.spec.ts` を実行して、clientがダミーサーバーを参照しているか確認。

---

## ダミーサーバーの実装パターン

### 1. Server Componentsのテストには実際のHTTP APIが必要

Next.jsのServer Componentsは**サーバーサイドで実際にHTTPリクエストを行う**ため、クライアントサイドのモック（MSWなど）は使用できません。

```typescript
// ❌ Server Componentsではクライアントサイドモックは動作しない
// app/page.tsx (Server Component)
async function Page() {
  const res = await fetch("http://localhost:8001/api/reports"); // 実際のHTTPリクエスト
  // ...
}
```

**解決策**: `utils/dummy-server`（Next.js）を実際のHTTPサーバーとして起動し、テストフィクスチャを返す。

### 2. ダミーサーバーの起動方法

```bash
# ❌ 間違い: pnpmは --port オプションを正しく処理できない
PUBLIC_API_KEY=public E2E_TEST=true pnpm run dev -- --port 8002

# ✅ 正しい: npx next dev -p を使用
cd utils/dummy-server
PUBLIC_API_KEY=public E2E_TEST=true npx next dev -p 8002
```

### 3. middleware vs API route

**middleware.ts を使用すべきケース**:
- `/meta/metadata.json` のように、`public/`ディレクトリと同じパスのAPIを作成する場合
- API routeを作成すると「conflicting public file」エラーが発生する

```typescript
// utils/dummy-server/middleware.ts
export function middleware(request: NextRequest) {
  if (process.env.E2E_TEST === "true" && request.nextUrl.pathname === "/meta/metadata.json") {
    return NextResponse.json(testMetadata);
  }
  return NextResponse.next();
}
```

**API routeを使用すべきケース**:
- `/reports`, `/reports/[slug]` のように、publicディレクトリと競合しないパス
- 複雑なロジックが必要な場合

```typescript
// utils/dummy-server/app/reports/[slug]/route.ts
export async function GET(request: Request, context: { params: Promise<{ slug: string }> }) {
  const { slug } = await context.params;
  if (process.env.E2E_TEST === "true") {
    const fixturePath = path.join(process.cwd(), `../../test/e2e/fixtures/client/report-${slug}.json`);
    // ...
  }
}
```

### 4. 相対パスを使用する

ダミーサーバーからフィクスチャを読み込む際は、相対パスを使用：

```typescript
// ✅ 正しい: process.cwd()からの相対パス
const fixtureDir = path.join(process.cwd(), "../../test/e2e/fixtures/client");

// ❌ 間違い: 絶対パスは環境依存
const fixtureDir = "/Users/nishio/kouchou-ai/test/e2e/fixtures/client";
```

---

## よくある問題と解決方法

### 1. テストが404エラーで失敗する

**原因**:
- ダミーサーバーが起動していない
- clientが間違ったサーバー（本番APIサーバー port 8001など）を参照している
- 環境変数が設定されていない

**解決方法**:
1. 検証テストを実行: `npx playwright test tests/verify-dummy-server.spec.ts --project=verify`
2. ダミーサーバーのログを確認
3. clientサーバーを正しい環境変数で再起動

### 2. テストが500エラーで失敗する

**原因**: テストフィクスチャのデータ構造が間違っている

**解決方法**:
1. 実際の本番データ構造を確認: `utils/dummy-server/app/reports/example/hierarchical_result.json`
2. フィクスチャを本番データ構造に合わせる
3. **推奨**: 本番データをそのままコピーして使用する

```bash
# 本番データをフィクスチャとして使用
cp utils/dummy-server/app/reports/example/hierarchical_result.json \
   test/e2e/fixtures/client/report-test-report-1.json
```

### 3. テストが30000msのタイムアウトで失敗する

**原因**:
- サーバーが起動していない
- 環境変数が設定されていない
- `waitForLoadState("networkidle")` を忘れている
- ポート衝突で古いプロセスが動いている

**解決方法**:
1. 検証テストを実行
2. ポート使用状況を確認: `lsof -i :3000` `lsof -i :8002`
3. 古いプロセスを停止してサーバーを再起動
4. `waitForLoadState("networkidle")` を追加

### 4. キャッシュの問題

**問題**: middlewareやAPI routeの変更が反映されない

**解決方法**:
```bash
# .nextディレクトリを削除して再起動
cd utils/dummy-server
rm -rf .next
PUBLIC_API_KEY=public E2E_TEST=true npx next dev -p 8002
```

### 5. ポート衝突

**問題**: 「Port 3000 is already in use」エラー

**解決方法**:
```bash
# 使用中のプロセスを確認
lsof -i :3000

# プロセスを停止
kill -9 <PID>

# または、すべてのnodeプロセスを停止（注意）
pkill -9 node
```

---

## テストデータの管理

### 1. 本番データ構造を使用する

**重要**: テストフィクスチャは、可能な限り実際の本番データ構造を使用すること。

```bash
# ✅ 推奨: 本番データをコピー
cp utils/dummy-server/app/reports/example/hierarchical_result.json \
   test/e2e/fixtures/client/report-test-report-1.json

# ❌ 非推奨: 手動でダミーデータを作成
# → データ構造の不整合により500エラーが発生しやすい
```

**理由**:
- 本番データ構造は複雑で、手動で再現するのは困難
- データ構造の不整合により、テストが失敗したり500エラーが発生する
- 本番データを使用することで、テストが実際のアプリケーションの動作を正確に検証できる

### 2. フィクスチャのサイズ

`test/e2e/fixtures/client/report-test-report-1.json` は約4.5MBの大きなファイルです。これは**意図的**です。

**理由**:
- 実際の本番データには100件以上のクラスタと大量のコメントが含まれる
- パフォーマンステストで大きなデータを扱う必要がある
- 大きなファイルでも問題なく動作することを確認するため

### 3. フィクスチャの配置

```
test/e2e/fixtures/
├── admin/          # 管理画面用フィクスチャ（将来的に使用）
└── client/         # Client用フィクスチャ
    ├── metadata.json                   # Meta情報（軽量）
    ├── reports.json                    # レポート一覧（軽量）
    └── report-test-report-1.json       # レポート詳細（4.5MB、本番データ）
```

### 4. テストデータの更新

本番のデータ構造が変更された場合、フィクスチャも更新する必要があります：

1. 最新の本番データを確認: `utils/dummy-server/app/reports/example/hierarchical_result.json`
2. フィクスチャを更新
3. テストを実行して検証

---

## プロジェクト構成

### Playwright config

`playwright.config.ts` では3つのプロジェクトが定義されています：

```typescript
projects: [
  {
    name: "verify",           // 検証テスト（最初に実行）
    testMatch: "**/verify-*.spec.ts",
  },
  {
    name: "admin",            // 管理画面テスト
    use: { baseURL: "http://localhost:4000" },
    testMatch: "**/admin/*.spec.ts",
  },
  {
    name: "client",           // Clientテスト
    use: { baseURL: "http://localhost:3000" },
    testMatch: "**/client/*.spec.ts",
  },
],
```

### テスト実行の順序

```bash
# 1. 検証テスト（verify project）
npx playwright test --project=verify

# 2. 管理画面テスト（admin project）
npx playwright test --project=admin

# 3. Clientテスト（client project）
npx playwright test --project=client

# すべてのテストを実行
npx playwright test
```

---

## デバッグのベストプラクティス

### 1. 検証テストから始める

テストが失敗した場合、以下の順序でデバッグ：

```bash
# ステップ1: ダミーサーバーの検証
npx playwright test tests/verify-dummy-server.spec.ts --project=verify

# ステップ2: 環境設定の検証
npx playwright test tests/verify-environment.spec.ts --project=verify

# ステップ3: 接続確認（デバッグ用）
npx playwright test tests/simple.spec.ts

# ステップ4: 要素確認（デバッグ用）
npx playwright test tests/debug.spec.ts

# ステップ5: ブラウザで確認
npx playwright test --headed --debug
```

### 2. スクリーンショットを活用

テストが失敗した場合、自動的にスクリーンショットが保存されます：

```
test-results/
└── {test-name}/
    ├── test-failed-1.png      # 失敗時のスクリーンショット
    └── error-context.md       # エラーコンテキスト
```

### 3. トレースビューアを使用

```bash
# トレースを有効にして実行
npx playwright test --trace on

# トレースビューアを開く
npx playwright show-trace test-results/{test-name}/trace.zip
```

---

## まとめ

### 必ず守るべきルール

1. ✅ **すべてのテストで `waitForLoadState("networkidle")` を使用**
2. ✅ **テスト実行前に検証テストを実行**
3. ✅ **本番データ構造をフィクスチャに使用**
4. ✅ **ダミーサーバーは `npx next dev -p 8002` で起動**
5. ✅ **環境変数を正しく設定**

### よくある失敗パターン

1. ❌ `waitForLoadState("networkidle")` を忘れる → タイムアウト
2. ❌ 検証テストをスキップ → 環境設定ミスに気づかない
3. ❌ 手動でダミーデータを作成 → データ構造の不整合で500エラー
4. ❌ pnpmでポート指定 → ポートが正しく設定されない
5. ❌ 古いプロセスが残っている → ポート衝突やキャッシュ問題

### トラブルシューティングフロー

```
テスト失敗
  ↓
検証テストを実行
  ↓
├─ 失敗 → サーバー起動状態/環境変数を確認
│           ↓
│         サーバーを再起動
│
└─ 成功 → テストコードを確認
            ↓
          ├─ waitForLoadState あり？
          ├─ セレクタは正しい？
          ├─ strict mode違反？
          └─ スクリーンショット確認
```

---

## 参考資料

- [README.md](./README.md) - 詳細な実行手順
- [Playwright公式ドキュメント](https://playwright.dev/)
- [Next.js 15ドキュメント](https://nextjs.org/docs)
