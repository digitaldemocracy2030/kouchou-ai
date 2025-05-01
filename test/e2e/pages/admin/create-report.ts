import { Page, Locator } from '@playwright/test';

/**
 * レポート作成ページのPage Object
 * data-testidを使用したシンプルで信頼性の高いセレクタ
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
    
    this.pageTitle = page.getByTestId('create-report-title').or(page.locator('h2:has-text("新しいレポートを作成する")'));
    this.titleField = page.getByTestId('title-field').or(page.locator('label:has-text("タイトル") + div input'));
    this.introField = page.getByTestId('intro-field').or(page.locator('label:has-text("調査概要") + div input'));
    this.idField = page.getByTestId('id-field').or(page.locator('label:has-text("ID") + div input'));
    this.csvTab = page.getByTestId('csv-tab').or(page.locator('button:has-text("CSVファイル")'));
    this.csvFileUpload = page.locator('input[type="file"]');
    this.submitButton = page.getByTestId('submit-button').or(page.locator('button:has-text("レポート作成を開始")'));
  }

  async goto() {
    await this.page.goto('/create');
    await this.page.waitForLoadState('domcontentloaded');
    
    const html = await this.page.content();
    if (html.includes('デジタル民主主義2030プロジェクト') && !html.includes('新しいレポートを作成する')) {
      console.log('WARNING: Page appears to be showing login page or unauthorized content');
      return false;
    }
    
    return true;
  }

  async fillTitleField(text: string) {
    try {
      await this.titleField.fill(text);
      return true;
    } catch (e) {
      console.log(`Error filling title field: ${e.message}`);
      return false;
    }
  }

  async fillIntroField(text: string) {
    try {
      await this.introField.fill(text);
      return true;
    } catch (e) {
      console.log(`Error filling intro field: ${e.message}`);
      return false;
    }
  }

  async fillIdField(text: string) {
    try {
      await this.idField.fill(text);
      return true;
    } catch (e) {
      console.log(`Error filling ID field: ${e.message}`);
      return false;
    }
  }

  async uploadCsvFile(filePath: string) {
    try {
      await this.csvTab.click();
      const fileInput = this.page.locator('input[type="file"]');
      await fileInput.setInputFiles(filePath);
      return true;
    } catch (e) {
      console.log(`Error uploading CSV file: ${e.message}`);
      return false;
    }
  }

  async submitForm() {
    try {
      await this.submitButton.click();
      return true;
    } catch (e) {
      console.log(`Error submitting form: ${e.message}`);
      return false;
    }
  }
}
