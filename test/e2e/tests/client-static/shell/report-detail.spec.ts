import { expect, test } from "@playwright/test";

/**
 * Client Static (shell) - データ非依存な静的出力のテスト
 *
 * shell ビルドはレポートに依存しない HTML を 1 枚だけ出力し、配布時に
 * その 1 枚を各レポートの slug へコピーする。レポートの中身は data/*.json として
 * 並べ、ページは実行時に URL から slug を求めて読む。
 *
 * ここで確かめるのは「コピーした HTML が実ブラウザで hydrate し、
 * URL に応じて別のレポートを描画すること」＝ ビルドし直さずにレポートを
 * 増減できること。http://localhost:3003 で out-shell を配信する。
 */

test.describe("Client Static (shell) - レポート詳細", () => {
  test("コピーした shell HTML が URL の slug のレポートを描画する", async ({ page }) => {
    await page.goto("/test-report-1/");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("AIと著作権について、どのような意見が寄せられているのか？")).toBeVisible();
    await expect(page.getByText(/生成AI技術の進化に伴う著作権侵害/)).toBeVisible();
    await expect(page.getByText("テスト太郎")).toBeVisible();
  });

  test("ビルド時のデータが HTML に焼き込まれていない", async ({ page }) => {
    // JavaScript を切ると何も描画できない＝データはビルド成果物に含まれていない
    const response = await page.request.get("/test-report-1/");
    const html = await response.text();

    expect(response.status()).toBe(200);
    expect(html).not.toContain("AIと著作権について、どのような意見が寄せられているのか？");
  });

  test("同梱データの無い slug は見つかりません表示になる", async ({ page }) => {
    await page.goto("/test-report-2/");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("ページが見つかりませんでした")).toBeVisible();
  });

  test("トップページが同梱データからレポート一覧を描画する", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: "レポート一覧" })).toBeVisible();
    await expect(page.getByText("テストレポート1")).toBeVisible();
    await expect(page.getByText("テストレポート2：市民の声を集めよう")).toBeVisible();
  });
});
