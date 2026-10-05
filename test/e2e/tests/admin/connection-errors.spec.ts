import path from "node:path";
import { expect, test } from "@playwright/test";

const scenarios = [
  ["e2e-authentication-error", "認証エラー：APIキーの設定・有効期限を確認してください。"],
  ["e2e-insufficient-quota", "残高不足 / quota不足：プロバイダーの課金設定・利用上限を確認してください。"],
  ["e2e-rate-limit", "rate limit：時間をおいて再度お試しください。"],
  ["e2e-server-error", "不明なエラー：接続先やAPI設定を確認してください。"],
  ["e2e-connection-error", "不明なエラー：接続先やAPI設定を確認してください。"],
];

for (const [key, message] of scenarios) {
  test(`${key}: エラー後に設定へ戻り、修正して再確認できる`, async ({ page }) => {
    await page.goto("/create");
    await page.waitForLoadState("networkidle");
    await page.getByLabel("タイトル（省略可）", { exact: true }).fill("エラーからの復帰");
    await page.locator('input[type="file"]').setInputFiles(path.resolve(__dirname, "../../fixtures/sample.csv"));
    await expect(page.getByRole("combobox", { name: "コメントカラム選択" })).toHaveValue("comment");
    await page.getByRole("button", { name: "レポート生成設定" }).click();
    const apiKey = page.getByPlaceholder("独自のAPIキーを入力（空欄の場合はサーバー設定を使用）");
    await apiKey.fill(key);
    await page.getByRole("button", { name: "作成前の確認へ" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText("未確認", { exact: true })).toBeVisible();
    await dialog.getByRole("button", { name: "API接続を確認する" }).click();
    await expect(dialog.getByText(message, { exact: true })).toBeVisible();
    await expect(dialog.getByRole("button", { name: "エラーを確認して作成を開始" })).toBeVisible();
    await expect(dialog.getByText("OK（表示中の設定でチャット接続確認済み）")).toHaveCount(0);

    await dialog.getByRole("button", { name: "設定に戻る" }).click();
    await expect(dialog).not.toBeVisible();
    await expect(page.getByLabel("タイトル（省略可）", { exact: true })).toHaveValue("エラーからの復帰");
    await expect(page.getByRole("combobox", { name: "コメントカラム選択" })).toHaveValue("comment");
    await expect(apiKey).toHaveValue(key);
    await apiKey.fill("e2e-success");
    await page.getByRole("button", { name: "作成前の確認へ" }).click();
    await expect(dialog.getByText("未確認", { exact: true })).toBeVisible();
    await expect(dialog.getByText("コメント件数：3件（非空：3件）")).toBeVisible();
    await dialog.getByRole("button", { name: "API接続を確認する" }).click();
    await expect(dialog.getByText("OK（表示中の設定でチャット接続確認済み）")).toBeVisible();
    await expect(dialog.getByRole("button", { name: "この内容で作成を開始" })).toBeEnabled();
    await expect(dialog.getByText(message, { exact: true })).toHaveCount(0);
  });
}
