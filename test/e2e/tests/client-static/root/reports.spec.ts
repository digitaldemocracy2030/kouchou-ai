import { test, expect } from "@playwright/test";

/**
 * Client Static - レポート一覧テスト（静的ビルド版）
 *
 * 静的ビルド（client/out）をホスティングした環境でのレポート一覧機能をテストします。
 * http://localhost:3001 で http-server により静的ファイルが提供されます。
 *
 * 注意:
 * - 静的ビルドは事前に生成されている必要があります（cd client && npm run build:static）
 * - 静的HTMLなので、APIサーバーへのリクエストは発生しません
 * - ビルド時に埋め込まれたデータが表示されます
 */

test.describe("Client Static - レポート一覧", () => {
  test("正常系 - レポート一覧が表示される", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // レポート作成者名が表示される
    await expect(page.getByText("テスト太郎")).toBeVisible();

    // 「レポート一覧」の見出しが表示される
    await expect(page.getByRole("heading", { name: "レポート一覧" })).toBeVisible();

    // 各レポートが表示される
    await expect(page.getByText("テストレポート1")).toBeVisible();
    await expect(page.getByText("テストレポート2：市民の声を集めよう")).toBeVisible();

    // レポートの説明文が表示される
    await expect(page.getByText(/1つ目のE2Eテスト用レポート/)).toBeVisible();
  });

  test("レポートの作成日時が表示される", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 作成日時が表示される
    // 複数のレポートカードがあるため .first() を使用
    await expect(page.getByText(/作成日時:/).first()).toBeVisible();
  });
});

test.describe("Client Static - レスポンシブデザイン", () => {
  const viewports = [
    { name: "デスクトップ", width: 1920, height: 1080 },
    { name: "タブレット", width: 768, height: 1024 },
    { name: "モバイル", width: 375, height: 667 },
  ];

  for (const viewport of viewports) {
    test(`${viewport.name}サイズでレポート一覧が表示される`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });

      await page.goto("/");
      await page.waitForLoadState("networkidle");

      // レポート一覧が表示される
      await expect(page.getByRole("heading", { name: "レポート一覧" })).toBeVisible();
      await expect(page.getByText("テストレポート1")).toBeVisible();
    });
  }
});

/**
 * 注意事項:
 * - このテストは静的ビルド（client/out）を http-server でホスティングした環境をテストします
 * - 静的ビルドは事前に生成されている必要があります: cd client && npm run build:static
 * - ビルド時にダミーAPIサーバー（port 8002）からデータを取得してHTMLに埋め込みます
 * - 環境変数: NEXT_PUBLIC_API_BASEPATH=http://localhost:8002 で静的ビルドを生成
 */
