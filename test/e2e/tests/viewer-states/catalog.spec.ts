import { writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { expect, test } from "@playwright/test";
import fixture from "../../../../apps/public-viewer/components/dev/viewer-fixture.json";

test.beforeEach(async ({ page }) => {
  await page.route("https://fonts.**/*", (route) => route.abort());
  await page.goto("/dev/viewer-states/");
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("heading", { name: "Viewer状態カタログ（開発専用）" })).toBeVisible();
});

test("空一覧・接続エラー・属性なしを実コンポーネントで確認できる", async ({ page }) => {
  const state = page.getByRole("combobox", { name: "状態", exact: true });
  await state.selectOption("レポート0件");
  await expect(page.getByText("レポートが0件です")).toBeVisible();
  await state.selectOption("接続エラー");
  await expect(page.getByRole("heading", { name: "API接続エラー" })).toBeVisible();
  for (const name of ["メタデータなし", "属性なし", "空の意見", "通常"]) {
    await state.selectOption(name);
    await expect(page.getByRole("button", { name: "全画面表示" })).toBeVisible();
  }
});

test("全画面ツールバーは描画領域の外にある", async ({ page }) => {
  await page.getByRole("button", { name: "全画面表示" }).click();
  const exit = page.getByRole("button", { name: "全画面終了" });
  await expect(exit).toBeVisible();
  const plot = page.getByRole("dialog").locator(".js-plotly-plot");
  await expect(plot).toBeVisible();
  await expect
    .poll(() =>
      page.getByRole("dialog").evaluate((dialog) => {
        const toolbar = dialog.querySelector("#fullScreenButtons")?.getBoundingClientRect();
        const chart = dialog.querySelector(".js-plotly-plot")?.getBoundingClientRect();
        return chart && toolbar ? chart.top - toolbar.bottom : Number.NEGATIVE_INFINITY;
      }),
    )
    .toBeGreaterThanOrEqual(-0.1);
  await exit.click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
});

test("スマホは一覧を初期表示し明示設定を尊重する", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await page.waitForLoadState("networkidle");
  await expect(page.locator(".js-plotly-plot")).toHaveCount(0);
  await page.screenshot({ path: "test-results/viewer-mobile.png", fullPage: true });
  await page.getByRole("combobox", { name: "状態", exact: true }).selectOption("明示的な散布図");
  await expect(page.locator(".js-plotly-plot")).toBeVisible();
});

test("描画更新後もクラウド送信を表示せず階層クリックと説明が同期する", async ({ page }) => {
  await page.getByRole("combobox", { name: "状態", exact: true }).selectOption("明示的な散布図");
  const plot = page.locator(".js-plotly-plot");
  await expect(plot).toBeVisible();
  await plot.hover();
  await expect(plot.locator(".modebar-btn").first()).toBeVisible();
  await expect(plot.locator('[data-title="Share chart..."]')).toHaveCount(0);

  await page.getByText("階層", { exact: true }).click();
  const cluster = fixture.clusters.filter((item) => item.parent === "0").sort((a, b) => b.value - a.value)[0];
  const label = plot
    .locator(".treemap .slice > .slicetext")
    .filter({ hasText: cluster.label.slice(0, 10) })
    .first();
  await expect(label).toBeVisible();
  await label.locator("..").locator(":scope > .surface").click();
  await expect(page.getByRole("heading", { name: `表示中: ${cluster.label}`, exact: true })).toBeVisible();
  await page.getByRole("button", { name: "一つ上に戻る" }).click();
  const root = fixture.clusters.find((item) => item.id === "0");
  await expect(page.getByRole("heading", { name: `表示中: ${root?.label}`, exact: true })).toBeVisible();
});

test("fileで直接開くとNextの起動なしで案内を表示する", async ({ page, request }, testInfo) => {
  const response = await request.get("/dev/viewer-states/");
  const localPath = testInfo.outputPath("local-report.html");
  await writeFile(localPath, await response.text());
  await page.goto(pathToFileURL(localPath).href);
  await expect(page.locator("#local-file-notice")).toBeVisible();
  await expect(page.locator("#report-app")).toBeHidden();
  await expect(page.getByText("python -m http.server", { exact: false })).toBeVisible();
});
