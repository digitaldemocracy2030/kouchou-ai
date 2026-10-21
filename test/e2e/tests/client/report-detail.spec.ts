import { test, expect } from "@playwright/test";

/**
 * Client - レポート詳細テスト
 *
 * 個別レポート詳細ページ（http://localhost:3000/[slug]）の機能をテストします。
 * ダミーAPIサーバー（port 8002）がテストフィクスチャを返します。
 */

test.describe("Client - レポート詳細", () => {
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
    // (BackButtonコンポーネントによって表示される)
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
    // trailingSlash: true なので詳細ページの URL も "/" で終わる。末尾ではなくパス全体で判定する
    await page.waitForURL((url) => url.pathname === "/");
    expect(new URL(page.url()).pathname).toBe("/");
  });

  test("異常系 - 存在しないレポートで404エラーが表示される", async ({ page }) => {
    await page.goto("/non-existent-report");
    await page.waitForLoadState("networkidle");

    // 404ページまたはNot Foundメッセージが表示される
    // Next.jsのnot-found.tsxが表示される
    await expect(page.getByText(/404|Not Found|見つかりません/)).toBeVisible();
  });

  test("コメント数が表示される", async ({ page }) => {
    await page.goto("/test-report-1");
    await page.waitForLoadState("networkidle");

    // コメント数（100件）が表示される
    await expect(page.getByText(/100.*コメント|コメント.*100/i)).toBeVisible();
  });
});

test.describe("Client - レポート詳細のレスポンシブデザイン", () => {
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

test.describe("Client - パフォーマンス", () => {
  test("レポート詳細の初期読み込み時間", async ({ page }) => {
    const startTime = Date.now();
    await page.goto("/test-report-1");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("AIと著作権について、どのような意見が寄せられているのか？")).toBeVisible();
    const loadTime = Date.now() - startTime;

    // 10秒以内に読み込まれることを確認
    expect(loadTime).toBeLessThan(10000);
  });
});

/**
 * 注意事項:
 * - このテストはダミーAPIサーバー（port 8002）を使用します
 * - テストフィクスチャは test/e2e/fixtures/client/ に配置
 * - ダミーAPIサーバーは playwright.config.ts の webServer で自動起動されます
 * - Next.jsのハイドレーション完了を待つため waitForLoadState("networkidle") が必須
 */
