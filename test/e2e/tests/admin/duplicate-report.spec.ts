import { test, expect } from "@playwright/test";

test.describe("管理画面 - レポート複製", () => {
  test("要約プロンプトの複製ができ、再実行ステップが表示される", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    await page.getByTestId("report-actions-test-report").click();
    await page.getByText("複製").click();
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("再実行されるステップ")).toBeVisible();
    await expect(page.getByText("overview")).toBeVisible();

    await page.getByPlaceholder("未入力の場合は元のプロンプトを再利用します").fill("new overview prompt");

    await page.getByRole("button", { name: "複製を開始" }).click();
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("複製を開始しました")).toBeVisible();
  });
});
