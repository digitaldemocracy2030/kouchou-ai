import { Page, Locator } from '@playwright/test';

/**
 * レポート作成ページのPage Object
 * data-testid属性を使用した信頼性の高いセレクタを使用
 */
export class CreateReportPage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly titleField: Locator;
  readonly introField: Locator;
  readonly idField: Locator;
  readonly csvTab: Locator;
  readonly csvFileUpload: Locator;
  readonly submitButton: Locator;

  constructor(page: Page) {
    this.page = page;
    
    this.pageTitle = page.getByTestId('create-report-title');
    this.titleField = page.getByTestId('title-field');
    this.introField = page.getByTestId('intro-field');
    this.idField = page.getByTestId('id-field');
    this.csvTab = page.getByTestId('csv-tab');
    this.csvFileUpload = page.getByTestId('file-upload');
    this.submitButton = page.getByTestId('submit-button');
  }

  async goto() {
    await this.page.goto('/create');
    await this.page.waitForLoadState('domcontentloaded');
  }

  async fillTitleField(text: string) {
    await this.titleField.fill(text);
  }

  async fillIntroField(text: string) {
    await this.introField.fill(text);
  }

  async fillIdField(text: string) {
    await this.idField.fill(text);
  }

  async uploadCsvFile(filePath: string) {
    await this.csvTab.click();
    const fileInput = this.page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);
  }

  async submitForm() {
    await this.submitButton.click();
  }
}
