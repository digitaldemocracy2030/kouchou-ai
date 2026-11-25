import { expect, test } from "@playwright/test";
import fixture from "../../../../apps/public-viewer/components/dev/viewer-fixture.json";

const originalText = "確認用の共有元コメント本文です。";

test.beforeEach(async ({ page }) => {
  await page.route("https://fonts.**/*", (route) => route.abort());
  await page.goto("/dev/viewer-states/");
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("heading", { name: "Viewer状態カタログ（開発専用）" })).toBeVisible();
  await page.getByRole("combobox", { name: "状態", exact: true }).selectOption("元コメントあり");
});

test("階層リストで同じ原文を別の末端から開き直しても、本文は1件だけ表示する", async ({ page }) => {
  await page.getByText("リスト", { exact: true }).click();
  await page.getByRole("button", { name: "すべて開く" }).click();

  const disclosures = page.getByText("元コメント 1", { exact: true });
  const body = page.getByText(originalText, { exact: true });
  await expect(disclosures).toHaveCount(2);
  await expect(body).toHaveCount(0);
  await disclosures.nth(0).press("Enter");
  await expect(body).toHaveCount(1);
  await disclosures.nth(1).press("Enter");
  await expect(disclosures.nth(0).locator("..")).not.toHaveAttribute("open", "");
  await expect(disclosures.nth(1).locator("..")).toHaveAttribute("open", "");
  await expect(body).toHaveCount(1);
});

test("階層図の末端で、詳細欄から元コメントを読める", async ({ page }) => {
  await page.getByText("階層", { exact: true }).click();

  const details = page.getByRole("region", { name: "階層図の説明" });
  for (const id of fixture.arguments[0].cluster_ids.slice(1)) {
    const cluster = fixture.clusters.find((entry) => entry.id === id);
    if (!cluster) throw new Error(`Missing cluster ${id} in the viewer fixture`);
    await details.getByRole("button", { name: cluster.label, exact: true }).click();
  }
  await details.getByText("元コメント 1", { exact: true }).click();
  await expect(details.getByText(originalText, { exact: true })).toBeVisible();
});
