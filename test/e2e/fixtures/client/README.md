# Public Viewer Test Fixtures

このディレクトリには、Public viewer（レポート表示画面）のE2Eテスト用のフィクスチャ（テストデータ）が含まれています。

## ファイル一覧

### `metadata.json`

Meta情報（レポート作成者情報）のモックデータです。

- **使用API**: `/meta/metadata.json`
- **用途**: レポート作成者名、メッセージ、ブランドカラーなどを表示

### `reports.json`

レポート一覧のモックデータです。

- **使用API**: `/reports`
- **用途**: トップページのレポート一覧表示
- **含まれるデータ**: 2件のテストレポート

### `report-test-report-1.json`

個別レポート詳細のモックデータです（test-report-1用）。

- **使用API**: `/reports/test-report-1`
- **用途**: レポート詳細ページの表示
- **含まれるデータ**:
  - 3件の意見（arguments）
  - 2つのクラスタ（公園/遊び場、道路/インフラ）
  - 3件のコメント

## 使用方法

Playwrightのテストで `page.route()` を使用してAPIレスポンスをモックします。

### 基本的な使い方

```typescript
import { test, expect } from "@playwright/test";
import metadata from "../fixtures/client/metadata.json";
import reports from "../fixtures/client/reports.json";

test("レポート一覧表示", async ({ page }) => {
  // Meta情報のモック
  await page.route("**/meta/metadata.json", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(metadata),
    });
  });

  // レポート一覧のモック
  await page.route("**/reports", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(reports),
    });
  });

  await page.goto("http://localhost:3000");
  await page.waitForLoadState("networkidle");

  await expect(page.getByText("テストレポート1")).toBeVisible();
});
```

### レポート詳細ページのモック

```typescript
import reportDetail from "../fixtures/client/report-test-report-1.json";

test("レポート詳細表示", async ({ page }) => {
  await page.route("**/meta/metadata.json", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(metadata),
    });
  });

  await page.route("**/reports/test-report-1", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(reportDetail),
    });
  });

  await page.goto("http://localhost:3000/test-report-1");
  await page.waitForLoadState("networkidle");

  await expect(page.getByText("まちづくりについてのご意見をお聞かせください")).toBeVisible();
});
```

## データのカスタマイズ

テストシナリオに応じてフィクスチャデータをカスタマイズできます：

### 空のレポート一覧

```typescript
await page.route("**/reports", async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify([]), // 空配列
  });
});
```

### エラーレスポンス

```typescript
await page.route("**/reports", async (route) => {
  await route.fulfill({
    status: 500,
    contentType: "application/json",
    body: JSON.stringify({ error: "Internal Server Error" }),
  });
});
```

## 注意事項

- フィクスチャデータは最小限の構造になっています（実際のレポートはもっと複雑）
- テストに必要な項目のみを含めています
- 新しいテストケースが必要な場合は、適宜データを追加してください
- JSONファイルの構造は `/apps/public-viewer/type.ts` の型定義に準拠しています

## 参考資料

- [E2Eテストガイド](../../README.md)
- [Public Viewer Type Definitions](../../../../apps/public-viewer/type.ts)
- [Playwright Route Mocking](https://playwright.dev/docs/mock)
