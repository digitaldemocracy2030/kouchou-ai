import { test, expect } from "@playwright/test";

test.describe("管理画面 - レポート複製", () => {
  test("要約プロンプトの複製ができ、再実行ステップが表示される", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    await page.getByTestId("report-actions-test-report").click();
    await page.getByRole("menuitem", { name: "複製" }).click();
    await expect(page.getByRole("heading", { name: "レポートを複製" })).toBeVisible();

    await expect(page.getByText("再実行されるステップ")).toBeVisible();
    await expect(page.getByText("overview", { exact: true })).toBeVisible();

    await page.getByLabel("要約プロンプト").fill("new overview prompt");

    await page.getByRole("button", { name: "複製を開始" }).click();
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("複製を開始しました")).toBeVisible();
  });
});
