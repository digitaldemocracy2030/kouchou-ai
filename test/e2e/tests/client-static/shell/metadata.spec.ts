import { expect, test } from "@playwright/test";
import cases from "../../../fixtures/client/shell-metadata-cases.json";

const [publicCase, unlistedCase] = cases;
const titleFor = (question: string) => `${question} - テスト太郎`;

test.describe("配布HTMLのメタデータ（JavaScriptなし）", () => {
  test.use({ javaScriptEnabled: false });

  for (const item of cases) {
    test(`${item.visibility}のタイトルとrobotsが最初から含まれる`, async ({ page }) => {
      await page.goto(`/${item.slug}/`);
      await page.waitForLoadState("networkidle");
      await expect(page).toHaveTitle(titleFor(item.question));
      await expect(page.locator("head title")).toHaveCount(1);
      await expect(page.locator('head meta[name="robots"]')).toHaveCount(1);
      await expect(page.locator('head meta[name="robots"]')).toHaveAttribute(
        "content",
        item.visibility === "unlisted" ? "noindex, nofollow" : "index, follow",
      );
      await expect(page.locator("head script:not([src])")).toHaveCount(0);
    });
  }
});

test("直接表示と一覧からの遷移でタイトルが整合し、noindexが残らない", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(`/${unlistedCase.slug}/`);
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("heading", { name: unlistedCase.question })).toBeVisible();
  await expect(page).toHaveTitle(titleFor(unlistedCase.question));
  await expect(page.locator('head meta[name="robots"]')).toHaveAttribute("content", "noindex, nofollow");

  await page.getByRole("link", { name: "一覧へ戻る" }).click();
  await page.waitForLoadState("networkidle");
  await expect(page).toHaveTitle("広聴AI");
  await expect(page.getByText(unlistedCase.title, { exact: true })).toHaveCount(0);
  await expect(page.locator('head meta[name="robots"]')).toHaveAttribute("content", "index, follow");
  await page
    .getByRole("link")
    .filter({ has: page.getByText(publicCase.title, { exact: true }) })
    .click();
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("heading", { name: publicCase.question, exact: true })).toBeVisible();
  await expect(page).toHaveTitle(titleFor(publicCase.question));
  await expect(page.locator("head title")).toHaveCount(1);
  await expect(page.locator('head meta[name="robots"]')).toHaveAttribute("content", "index, follow");
  expect(await page.evaluate(() => "__shellInjected" in window)).toBe(false);
  expect(errors).toEqual([]);

  await page.reload();
  await page.waitForLoadState("networkidle");
  await expect(page).toHaveTitle(titleFor(publicCase.question));
  await expect(page.locator("head title")).toHaveCount(1);
  expect(errors).toEqual([]);
});
