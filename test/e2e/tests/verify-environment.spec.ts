import { test, expect } from "@playwright/test";

/**
 * 環境確認テスト
 *
 * E2Eテストを実行する前に、必要なサーバーが正しく起動していることを確認します。
 */

test.describe("環境確認", () => {
  test("ダミーサーバー (port 8002) が起動している", async ({ request }) => {
    const response = await request.get("http://localhost:8002/meta/metadata.json").catch(() => null);
    expect(response, "ダミーサーバーが起動していません。起動コマンド: cd utils/dummy-server && PUBLIC_API_KEY=public E2E_TEST=true npx next dev -p 8002").not.toBeNull();
    expect(response?.ok()).toBeTruthy();
  });

  test("public-viewerサーバー (port 3000) が起動している", async ({ request }) => {
    const response = await request.get("http://localhost:3000/").catch(() => null);
    expect(response, "public-viewerサーバーが起動していません。起動コマンド: cd apps/public-viewer && NEXT_PUBLIC_API_BASEPATH=http://localhost:8002 API_BASEPATH=http://localhost:8002 NEXT_PUBLIC_PUBLIC_API_KEY=public pnpm dev").not.toBeNull();
    expect(response?.ok()).toBeTruthy();
  });

  test("public-viewerサーバーがダミーサーバーを参照している", async ({ page }) => {
    // トップページにアクセス
    await page.goto("http://localhost:3000/");
    await page.waitForLoadState("networkidle");

    // テストデータ（テスト太郎）が表示されることを確認
    const hasTestData = await page.getByText("テスト太郎").isVisible().catch(() => false);
    expect(hasTestData, "public-viewerサーバーがダミーサーバーを参照していません。環境変数を確認してください: NEXT_PUBLIC_API_BASEPATH=http://localhost:8002 API_BASEPATH=http://localhost:8002 NEXT_PUBLIC_PUBLIC_API_KEY=public").toBeTruthy();
  });
});
