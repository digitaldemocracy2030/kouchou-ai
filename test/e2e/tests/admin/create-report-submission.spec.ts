import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";

test("スプレッドシートで選んだ列と変更したAI設定が作成APIに届く", async ({ page, request }) => {
  const id = `e2e-create-${randomUUID()}`;
  const spreadsheetUrl = "https://docs.google.com/spreadsheets/d/e2e-test-sheet/edit";
  const spreadsheetRows = [
    {
      id: "1",
      comment: "元のコメント1",
      attribute_opinion: "公園を増やしてほしい",
      attribute_area: "北",
      attribute_zip: "01234",
    },
    {
      id: "2",
      comment: "元のコメント2",
      attribute_opinion: "バスを増便してほしい",
      attribute_area: "南",
      attribute_zip: "00999",
    },
    {
      id: "3",
      comment: "元のコメント3",
      attribute_opinion: "駅に屋根がほしい",
      attribute_area: "北",
      attribute_zip: "00001",
    },
  ];
  const importPath = "/admin/spreadsheet/import";
  const dataPath = `/admin/spreadsheet/data/${id}`;
  // Googleにはアクセスせず、ブラウザから呼ぶインポートAPIの応答を置き換える。
  await page.route(`**${importPath}`, (route) =>
    route.fulfill({
      json: {
        status: "success",
        message: "スプレッドシートのインポートが完了しました",
        file_path: `inputs/${id}.csv`,
        file_name: id,
      },
      headers: { "Access-Control-Allow-Origin": "*" },
    }),
  );
  await page.route(`**${dataPath}`, (route) =>
    route.fulfill({
      json: { status: "success", file_name: id, comments: spreadsheetRows, total: spreadsheetRows.length },
      headers: { "Access-Control-Allow-Origin": "*" },
    }),
  );

  await page.goto("/create");
  await page.waitForLoadState("networkidle");
  await page.getByRole("textbox", { name: "ID", exact: true }).fill(id);
  await page.getByRole("tab", { name: "Googleスプレッドシート" }).click();
  const sheetPanel = page.getByRole("tabpanel", { name: "Googleスプレッドシート" });
  const importButton = sheetPanel.getByRole("button", { name: "データを取得" });
  await expect(importButton).toBeDisabled();
  await sheetPanel.getByRole("textbox", { name: "スプレッドシートURL" }).fill(spreadsheetUrl);
  const [importRequest, dataRequest] = await Promise.all([
    page.waitForRequest((request) => new URL(request.url()).pathname === importPath && request.method() === "POST"),
    page.waitForRequest((request) => new URL(request.url()).pathname === dataPath && request.method() === "GET"),
    importButton.click(),
  ]);
  expect(importRequest.postDataJSON()).toEqual({ url: spreadsheetUrl, file_name: id });
  await expect(sheetPanel.getByText("スプレッドシートのデータ 3 件を取得しました")).toBeVisible();

  const commentColumn = sheetPanel.getByRole("combobox", { name: "コメントカラム選択" });
  await expect(commentColumn).toHaveValue("comment");
  await commentColumn.selectOption("attribute_opinion");
  await sheetPanel.getByRole("checkbox", { name: "attribute_area" }).check();
  await sheetPanel.getByRole("checkbox", { name: "attribute_zip" }).check();

  const model = "gpt-4o";
  const workers = 7;
  const prompt = {
    extraction: "要望を抽出してください。",
    initialLabelling: "要望に短いラベルを付けてください。",
    mergeLabelling: "関連するラベルをまとめてください。",
    overview: "ラベルから全体像を要約してください。",
  };
  await page.getByRole("button", { name: "レポート生成設定" }).click();
  await page.getByRole("combobox", { name: "AIモデル", exact: true }).selectOption(model);
  await page.getByRole("spinbutton", { name: "並列実行数" }).fill(String(workers));
  const pubcom = page.getByRole("checkbox", { name: "csv出力モード" });
  await expect(pubcom).toBeChecked();
  await pubcom.press("Space");
  await expect(pubcom).not.toBeChecked();
  await page.getByRole("textbox", { name: "抽出プロンプト" }).fill(prompt.extraction);
  await page.getByRole("textbox", { name: "初期ラベリングプロンプト" }).fill(prompt.initialLabelling);
  await page.getByRole("textbox", { name: "統合ラベリングプロンプト" }).fill(prompt.mergeLabelling);
  await page.getByRole("textbox", { name: "要約プロンプト" }).fill(prompt.overview);

  await page.getByRole("button", { name: "作成前の確認へ" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("コメント列：attribute_opinion")).toBeVisible();
  await expect(dialog.getByText("コメント件数：3件（非空：3件）")).toBeVisible();
  await expect(dialog.getByText("属性列：attribute_area、attribute_zip")).toBeVisible();
  await expect(dialog.getByText("AI：openai / gpt-4o")).toBeVisible();
  await expect(dialog.getByText("並列数：7")).toBeVisible();
  await dialog.getByRole("button", { name: "未確認のまま作成を開始" }).click();
  await expect(page).toHaveURL("/");

  // 作成は Server Action 経由なので、ダミーAPIが受け取ったHTTPリクエストを検証する。
  const captureUrl = new URL("/admin/reports", dataRequest.url());
  captureUrl.searchParams.set("e2eSubmittedId", id);
  const submitted = await request.get(captureUrl.toString(), { headers: { "x-api-key": "public" } });
  await expect(submitted).toBeOK();
  const { comments, ...settings } = await submitted.json();
  expect(settings).toMatchObject({
    input: id,
    inputType: "spreadsheet",
    provider: "openai",
    model,
    workers,
    is_pubcom: false,
    prompt,
  });
  expect(comments).toEqual([
    { id: "1", comment: "公園を増やしてほしい", source: null, url: null, attribute_area: "北", attribute_zip: "01234" },
    { id: "2", comment: "バスを増便してほしい", source: null, url: null, attribute_area: "南", attribute_zip: "00999" },
    { id: "3", comment: "駅に屋根がほしい", source: null, url: null, attribute_area: "北", attribute_zip: "00001" },
  ]);
});
