import { test, expect } from "@playwright/test";

test.describe("管理画面 - レポート再利用", () => {
  test("要約プロンプトの再利用ができる", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    await page.getByTestId("report-actions-test-report-1").click();
    await page.getByRole("menuitem", { name: "再利用" }).click();
    await expect(page.getByRole("heading", { name: "レポートを再利用" })).toBeVisible();
    await page.getByRole("button", { name: "レポート生成設定" }).click();
    await page.getByLabel("要約プロンプト").fill("new overview prompt");

    await expect(page.getByRole("button", { name: "再利用を開始" })).toBeEnabled();
    await page.getByRole("button", { name: "再利用を開始" }).click();
    await page.waitForURL(/\/$/);
    await expect(page.getByTestId("report-actions-test-report-1")).toBeVisible();
  });
});
