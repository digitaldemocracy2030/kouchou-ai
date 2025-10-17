import { test, expect } from "@playwright/test";

/**
 * Client Static (Subdirectory) - レポート一覧テスト（静的ビルド版）
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

test.describe("Client Static (Subdirectory) - レポート一覧", () => {
  test("正常系 - basePath付きでレポート一覧が表示される", async ({ page }) => {
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

  test("正常系 - basePath付きで静的リソースが正しいパスで読み込まれる", async ({ page }) => {
    // ネットワークリクエストを監視
    const requests: string[] = [];
    page.on("request", (request) => {
      const url = request.url();
      if (url.includes("_next") || url.includes("images")) {
        requests.push(url);
      }
    });

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // すべての静的リソースが /kouchou-ai プレフィックス付きで読み込まれることを確認
    const hasCorrectBasePath = requests.every(
      (url) => url.includes("/kouchou-ai/_next") || url.includes("/kouchou-ai/images") || !url.includes("localhost"),
    );

    expect(hasCorrectBasePath).toBe(true);
  });

  test("レポートの作成日時が表示される", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 作成日時が表示される
    // 複数のレポートカードがあるため .first() を使用
    await expect(page.getByText(/作成日時:/).first()).toBeVisible();
  });
});

test.describe("Client Static (Subdirectory) - レスポンシブデザイン", () => {
  const viewports = [
    { name: "デスクトップ", width: 1920, height: 1080 },
    { name: "タブレット", width: 768, height: 1024 },
    { name: "モバイル", width: 375, height: 667 },
  ];

  for (const viewport of viewports) {
    test(`${viewport.name}サイズでレポート一覧が表示される（basePath付き）`, async ({ page }) => {
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
 * - このテストはsubdirectory ホスティング（basePath="/kouchou-ai"）用の静的ビルドをテストします
 * - 静的ビルドは事前に生成されている必要があります
 * - baseURL が http://localhost:3002/kouchou-ai に設定されているため、goto("/") は /kouchou-ai/ にアクセスします
 * - 環境変数: NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH="/kouchou-ai" で静的ビルドを生成
 */
