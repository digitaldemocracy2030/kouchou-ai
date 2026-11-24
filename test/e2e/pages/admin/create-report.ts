import type { Locator, Page } from "@playwright/test";

/**
 * レポート作成ページのPage Object
 */
export class CreateReportPage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly inputField: Locator;
  readonly questionField: Locator;
  readonly introField: Locator;
  readonly csvTab: Locator;
  readonly spreadsheetTab: Locator;
  readonly csvFileUpload: Locator;
  readonly spreadsheetUrlInput: Locator;
  readonly submitButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('h1:has-text("新しいレポートを作成する")');
    this.inputField = page.getByLabel("レポートID");
    this.questionField = page.getByLabel("質問");
    this.introField = page.getByLabel("イントロダクション");
    this.csvTab = page.getByRole("tab", { name: "CSVファイル" });
    this.spreadsheetTab = page.getByRole("tab", {
      name: "Googleスプレッドシート",
    });
    this.csvFileUpload = page.getByRole("tabpanel", { name: "CSVファイル" }).locator('input[type="file"]');
    this.spreadsheetUrlInput = page.getByPlaceholder("https://docs.google.com/spreadsheets/d/xxxxxxxxxxxx/edit");
    this.submitButton = page.getByRole("button", {
      name: "レポート作成を開始",
    });
  }

  async goto() {
    await this.page.goto("/create");
  }

  async fillBasicInfo(input: string, question: string, intro: string) {
    await this.inputField.fill(input);
    await this.questionField.fill(question);
    await this.introField.fill(intro);
  }

  async uploadCsvFile(filePath: string) {
    await this.csvTab.click();
    await this.csvFileUpload.setInputFiles(filePath);
  }

  async enterSpreadsheetUrl(url: string) {
    await this.spreadsheetTab.click();
    await this.spreadsheetUrlInput.fill(url);
  }

  async submitForm() {
    await this.submitButton.click();
  }
}
