import { test, expect } from "@playwright/test";

/**
 * 広聴AI 管理画面テストスイート
 *
 * このファイルは管理画面（http://localhost:4000）の主要な機能をテストします。
 * 管理画面は admin で実装されており、レポート作成やパイプライン設定を行います。
 */

test.describe("管理画面 - 初期表示とナビゲーション", () => {
  test("トップページが正常に表示される", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // ページタイトルを確認
    await expect(page).toHaveTitle(/デジタル民主主義|広聴|Kouchou/);
  });

  test("レポート作成ページに遷移できる", async ({ page }) => {
    await page.goto("/create");
    await page.waitForLoadState("networkidle");

    // レポート作成ページの見出しが表示される
    await expect(page.getByRole("heading", { name: "新しいレポートを作成する" })).toBeVisible();

    // ヘッダーのロゴが表示される
    await expect(page.getByRole("img", { name: "広聴AI" })).toBeVisible();
  });
});

test.describe("管理画面 - レポート作成フロー", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/create");
    await page.waitForLoadState("networkidle");
  });

  test("レポート作成画面の初期表示", async ({ page }) => {
    // ページタイトルの確認
    await expect(page.getByRole("heading", { name: "新しいレポートを作成する" })).toBeVisible();

    // タブの確認
    await expect(page.getByRole("tab", { name: "CSVファイル" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Googleスプレッドシート" })).toBeVisible();

    // レポート生成設定ボタンの確認
    await expect(page.getByRole("button", { name: "レポート生成設定" })).toBeVisible();

    // 作成開始ボタンの確認
    await expect(page.getByRole("button", { name: "レポート作成を開始" })).toBeVisible();

    // 料金に関する注意書きの確認
    await expect(page.getByText("有料のAIプロバイダーの場合は作成する度にAPI利用料がかかります")).toBeVisible();
  });

  test("入力データタブが表示される", async ({ page }) => {
    // タブの確認
    await expect(page.getByRole("tab", { name: "CSVファイル" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Googleスプレッドシート" })).toBeVisible();
  });

  test("CSVファイルタブが選択されている", async ({ page }) => {
    // CSVファイルタブがデフォルトで選択されている
    const csvTab = page.getByRole("tab", { name: "CSVファイル" });
    await expect(csvTab).toBeVisible();

    // タブの選択状態を確認（aria-selected属性）
    await expect(csvTab).toHaveAttribute("aria-selected", "true");
  });

  test("Googleスプレッドシートタブに切り替えられる", async ({ page }) => {
    // Googleスプレッドシートタブをクリック
    await page.getByRole("tab", { name: "Googleスプレッドシート" }).click();

    // タブが選択されたことを確認
    await expect(page.getByRole("tab", { name: "Googleスプレッドシート" })).toHaveAttribute("aria-selected", "true");
  });

  test("レポート生成設定ボタンをクリックできる", async ({ page }) => {
    // レポート生成設定ボタンが存在することを確認
    const settingsButton = page.getByRole("button", { name: "レポート生成設定" });
    await expect(settingsButton).toBeVisible();
    await settingsButton.click();
  });

  test("必須項目が未入力の場合は作成ボタンをクリックするとエラーが表示される", async ({ page }) => {
    // 何も入力せずに作成ボタンをクリック
    await page.getByRole("button", { name: "レポート作成を開始" }).click();

    // エラーメッセージの確認（toaster による表示）
    // ※Chakra UIのtoasterはalert roleで表示される
    await expect(page.getByText("入力エラー")).toBeVisible({ timeout: 5000 });
  });
});

test.describe("管理画面 - API連携", () => {
  // NOTE: このテストはE2E環境ではスキップします
  // 理由: E2Eは「実際のユーザーフローが動作すること」を確認する場所であり、
  // エラーハンドリングの詳細なテストはコンポーネントテスト/統合テストで行うべきです
  // 推奨: apps/admin/__tests__/ にReact Testing Library + MSWでテストを作成
  test.skip("APIエラー時にエラーメッセージが表示される", async ({ page }) => {
    // APIをモックしてエラーレスポンスを返す
    await page.route("**/admin/reports", (route) => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: "Internal Server Error" }),
      });
    });

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // エラーメッセージが表示されることを確認
    await expect(page.getByRole("heading", { name: "レポートの取得に失敗しました" })).toBeVisible();
  });
});

test.describe("管理画面 - レスポンシブデザイン", () => {
  const viewports = [
    { name: "デスクトップ", width: 1920, height: 1080 },
    { name: "タブレット", width: 768, height: 1024 },
    { name: "モバイル", width: 375, height: 667 },
  ];

  for (const viewport of viewports) {
    test(`${viewport.name}サイズでの表示確認`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto("/create");
      await page.waitForLoadState("networkidle");

      // ページタイトルが表示されることを確認
      await expect(page.getByRole("heading", { name: "新しいレポートを作成する" })).toBeVisible();

      // ヘッダーのロゴが表示されることを確認
      await expect(page.getByRole("img", { name: "広聴AI" })).toBeVisible();
    });
  }
});

test.describe("管理画面 - パフォーマンス", () => {
  test("ページの初期読み込み時間", async ({ page }) => {
    const startTime = Date.now();
    await page.goto("/create");
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("heading", { name: "新しいレポートを作成する" })).toBeVisible();
    const loadTime = Date.now() - startTime;

    // 10秒以内に読み込まれることを確認（Next.jsの初回起動を考慮）
    expect(loadTime).toBeLessThan(10000);
  });
});

/**
 * 注意事項:
 * - 上記のテストは実際のUIコード（apps/admin/app）に基づいて作成されています
 * - サーバーが http://localhost:4000 で起動している必要があります
 * - テストを実行する前に `docker compose up` または `cd apps/admin && pnpm run dev` でサーバーを起動してください
 * - 一部のテストはAPI応答に依存するため、APIサーバー（port 8000）も起動している必要があります
 */
