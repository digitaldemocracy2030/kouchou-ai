import { test, expect } from "@playwright/test";

/**
 * Client Static (Subdirectory) - レポート詳細テスト（静的ビルド版）
 *
 * Subdirectory ホスティング（例: GitHub Pages）での静的ビルドをテストします。
 * basePath="/kouchou-ai" でビルドされた静的ファイルをテストします。
 *
 * http://localhost:3002/kouchou-ai/ で http-server により静的ファイルが提供されます。
 *
 * 注意:
 * - 静的ビルドは事前に NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH="/kouchou-ai" で生成されている必要があります
 * - すべてのパスは /kouchou-ai プレフィックス付きになります
 */

test.describe("Client Static (Subdirectory) - レポート詳細", () => {
  test("正常系 - basePath付きでレポート詳細が表示される", async ({ page }) => {
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
    const backButton = page.locator("a[href='/kouchou-ai/']").or(page.getByRole("link", { name: /戻る|一覧/ }));
    await expect(backButton.first()).toBeVisible();
  });

  test("戻るボタンをクリックするとトップページに戻る（basePath付き）", async ({ page }) => {
    await page.goto("/test-report-1");
    await page.waitForLoadState("networkidle");

    // 戻るボタンをクリック
    const backButton = page.locator("a[href='/kouchou-ai/']").first();
    await backButton.click();

    // トップページに戻ることを確認
    await page.waitForURL("**/kouchou-ai/");
    expect(page.url()).toMatch(/\/kouchou-ai\/$/);
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

test.describe("Client Static (Subdirectory) - レポート詳細のレスポンシブデザイン", () => {
  const viewports = [
    { name: "デスクトップ", width: 1920, height: 1080 },
    { name: "タブレット", width: 768, height: 1024 },
    { name: "モバイル", width: 375, height: 667 },
  ];

  for (const viewport of viewports) {
    test(`${viewport.name}サイズでレポート詳細が表示される（basePath付き）`, async ({ page }) => {
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

test.describe("Client Static (Subdirectory) - パフォーマンス", () => {
  test("レポート詳細の初期読み込み時間（basePath付き）", async ({ page }) => {
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
 * - このテストはsubdirectory ホスティング（basePath="/kouchou-ai"）用の静的ビルドをテストします
 * - 静的ビルドは事前に生成されている必要があります
 * - baseURL が http://localhost:3002/kouchou-ai に設定されているため、goto("/test-report-1") は /kouchou-ai/test-report-1 にアクセスします
 * - 環境変数: NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH="/kouchou-ai" で静的ビルドを生成
 */
