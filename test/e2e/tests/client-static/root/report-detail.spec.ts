import { test, expect } from "@playwright/test";

/**
 * Client Static - レポート詳細テスト（静的ビルド版）
 *
 * 静的ビルド（client/out）をホスティングした環境での個別レポート詳細ページをテストします。
 * http://localhost:3001 で http-server により静的ファイルが提供されます。
 *
 * 注意:
 * - 静的ビルドは事前に生成されている必要があります（cd client && npm run build:static）
 * - 静的HTMLなので、APIサーバーへのリクエストは発生しません
 * - ビルド時に埋め込まれたデータが表示されます
 */

test.describe("Client Static - レポート詳細", () => {
  test("正常系 - レポート詳細が表示される", async ({ page }) => {
    await page.goto("/test-report-1");
    await page.waitForLoadState("networkidle");

    // レポートタイトル（config.question）が表示される
    await expect(page.getByText("AIと著作権について、どのような意見が寄せられているのか？")).toBeVisible();

    // Overview（overview）が表示される
    await expect(page.getByText(/生成AI技術の進化に伴う著作権侵害/)).toBeVisible();

    // レポート作成者名が表示される
    await expect(page.getByText("テスト太郎")).toBeVisible();
  });

  test("クラスタ情報が表示される", async ({ page }) => {
    await page.goto("/test-report-1");
    await page.waitForLoadState("networkidle");

    // クラスタのラベルが表示される
    await expect(page.getByText(/生成AIと著作権に関する法的/).first()).toBeVisible();
  });

  test("戻るボタンが表示される", async ({ page }) => {
    await page.goto("/test-report-1");
    await page.waitForLoadState("networkidle");

    // 戻るボタンが表示されることを確認
    const backButton = page.locator("a[href='/']").or(page.getByRole("link", { name: /戻る|一覧/ }));
    await expect(backButton.first()).toBeVisible();
  });

  test("戻るボタンをクリックするとトップページに戻る", async ({ page }) => {
    await page.goto("/test-report-1");
    await page.waitForLoadState("networkidle");

    // 戻るボタンをクリック
    const backButton = page.locator("a[href='/']").first();
    await backButton.click();

    // トップページに戻ることを確認
    await page.waitForURL("**/");
    expect(page.url()).toMatch(/\/$/);
  });

  test("異常系 - 存在しないレポートで404エラーが表示される", async ({ page }) => {
    await page.goto("/non-existent-report");
    await page.waitForLoadState("networkidle");

    // 404ページまたはNot Foundメッセージが表示される
    await expect(page.getByText(/404|Not Found|見つかりません/)).toBeVisible();
  });

  test("コメント数が表示される", async ({ page }) => {
    await page.goto("/test-report-1");
    await page.waitForLoadState("networkidle");

    // コメント数（100件）が表示される
    await expect(page.getByText(/100.*コメント|コメント.*100/i)).toBeVisible();
  });
});

test.describe("Client Static - レポート詳細のレスポンシブデザイン", () => {
  const viewports = [
    { name: "デスクトップ", width: 1920, height: 1080 },
    { name: "タブレット", width: 768, height: 1024 },
    { name: "モバイル", width: 375, height: 667 },
  ];

  for (const viewport of viewports) {
    test(`${viewport.name}サイズでレポート詳細が表示される`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });

      await page.goto("/test-report-1");
      await page.waitForLoadState("networkidle");

      // レポートタイトルが表示される
      await expect(page.getByText("AIと著作権について、どのような意見が寄せられているのか？")).toBeVisible();

      // クラスタ情報が表示される
      await expect(page.getByText(/生成AIと著作権に関する法的/).first()).toBeVisible();
    });
  }
});

test.describe("Client Static - パフォーマンス", () => {
  test("レポート詳細の初期読み込み時間", async ({ page }) => {
    const startTime = Date.now();
    await page.goto("/test-report-1");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("AIと著作権について、どのような意見が寄せられているのか？")).toBeVisible();
    const loadTime = Date.now() - startTime;

    // 静的HTMLは高速に読み込まれるはず（5秒以内）
    expect(loadTime).toBeLessThan(5000);
  });
});

/**
 * 注意事項:
 * - このテストは静的ビルド（client/out）を http-server でホスティングした環境をテストします
 * - 静的ビルドは事前に生成されている必要があります: cd client && npm run build:static
 * - ビルド時にダミーAPIサーバー（port 8002）からデータを取得してHTMLに埋め込みます
 * - 環境変数: NEXT_PUBLIC_API_BASEPATH=http://localhost:8002 で静的ビルドを生成
 */
