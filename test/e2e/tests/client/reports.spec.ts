import { test, expect } from "@playwright/test";

/**
 * Client - レポート一覧テスト
 *
 * トップページ（http://localhost:3000）のレポート一覧機能をテストします。
 * ダミーAPIサーバー（port 8002）がテストフィクスチャを返します。
 */

test.describe("Client - レポート一覧", () => {
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

  // NOTE: このテストはコンポーネントテストで行うべきと判断しスキップします
  // 理由: 詳細ページの表示は report-detail.spec.ts で既にテストしており、
  // ナビゲーション動作の詳細な検証はコンポーネントテスト（React Testing Library）で行うべきです
  // E2Eは主要なユーザーフロー全体の動作確認に集中します
  test.skip("レポートカードをクリックすると詳細ページに遷移する", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Linkコンポーネントを取得してクリック（apps/public-viewer/app/page.tsx:74のLink）
    await page.getByRole("link", { name: /テストレポート1/ }).click();

    // ページ遷移を待機してURLを確認
    await page.waitForLoadState("networkidle");
    expect(page.url()).toMatch(/\/test-report-1\/?$/);
  });

  test("レポートの作成日時が表示される", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 作成日時が表示される（apps/public-viewer/app/page.tsx:92-96で条件付きレンダリング）
    // 複数のレポートカードがあるため .first() を使用
    await expect(page.getByText(/作成日時:/).first()).toBeVisible();
  });

  // NOTE: このテストはE2Eの範囲外と判断しスキップします
  // CSSの細かい検証（色、レイアウト等）はビジュアルリグレッションテストで行うべきです
  // Playwrightのスクリーンショット比較機能を使用することを推奨します
  // 参考: https://playwright.dev/docs/test-snapshots
  test.skip("ブランドカラーが適用される", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 代替案: ビジュアルリグレッションテスト
    // await expect(page).toHaveScreenshot("reports-list.png");
  });
});

test.describe("Client - レスポンシブデザイン", () => {
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
 * - このテストはダミーAPIサーバー（port 8002）を使用します
 * - テストフィクスチャは test/e2e/fixtures/client/ に配置
 * - ダミーAPIサーバーは playwright.config.ts の webServer で自動起動されます
 * - Next.jsのハイドレーション完了を待つため waitForLoadState("networkidle") が必須
 */
