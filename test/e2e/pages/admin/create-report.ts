import { Page, Locator } from '@playwright/test';

/**
 * レポート作成ページのPage Object
 * 複数のロケーター戦略を使用して、CI環境でも要素を確実に見つけられるようにする
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

  readonly inputFieldById: Locator;
  readonly questionFieldById: Locator;
  readonly introFieldById: Locator;
  readonly submitButtonByText: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('h1:has-text("新しいレポートを作成する"), h1:has-text("Create New Report")');
    
    this.inputField = page.getByLabel('レポートID');
    this.questionField = page.getByLabel('質問');
    this.introField = page.getByLabel('イントロダクション');
    
    this.inputFieldById = page.locator('#r0, input[id^="r"][id$="0"]');
    this.questionFieldById = page.locator('#r1, input[id^="r"][id$="1"]');
    this.introFieldById = page.locator('#r2, input[id^="r"][id$="2"]');
    
    this.csvTab = page.getByRole('tab', { name: 'CSVファイル' }).or(page.locator('button:has-text("CSVファイル")'));
    this.spreadsheetTab = page.getByRole('tab', { name: 'Googleスプレッドシート' }).or(page.locator('button:has-text("Googleスプレッドシート")'));
    this.csvFileUpload = page.locator('input[type="file"]');
    this.spreadsheetUrlInput = page.getByPlaceholder('https://docs.google.com/spreadsheets/d/xxxxxxxxxxxx/edit');
    
    this.submitButton = page.getByRole('button', { name: 'レポート作成を開始' });
    this.submitButtonByText = page.locator('button:has-text("レポート作成を開始")');
  }

  async goto() {
    await this.page.goto('/create');
  }

  /**
   * 基本情報を入力する
   * CI環境では複数のロケーター戦略を試みる
   */
  async fillBasicInfo(input: string, question: string, intro: string) {
    try {
      await this.inputField.fill(input);
    } catch (error) {
      console.log(`[TEST-DEBUG] 主要なレポートIDロケーターが失敗、バックアップを試行: ${error}`);
      await this.inputFieldById.fill(input);
    }
    
    try {
      await this.questionField.fill(question);
    } catch (error) {
      console.log(`[TEST-DEBUG] 主要な質問ロケーターが失敗、バックアップを試行: ${error}`);
      await this.questionFieldById.fill(question);
    }
    
    try {
      await this.introField.fill(intro);
    } catch (error) {
      console.log(`[TEST-DEBUG] 主要なイントロロケーターが失敗、バックアップを試行: ${error}`);
      await this.introFieldById.fill(intro);
    }
  }

  /**
   * CSVファイルをアップロードする
   */
  async uploadCsvFile(filePath: string) {
    try {
      await this.csvTab.click();
    } catch (error) {
      console.log(`[TEST-DEBUG] CSVタブクリックに失敗、代替方法を試行: ${error}`);
      await this.page.locator('button, [role="tab"]').filter({ hasText: 'CSV' }).click();
    }
    await this.csvFileUpload.setInputFiles(filePath);
  }

  async enterSpreadsheetUrl(url: string) {
    try {
      await this.spreadsheetTab.click();
    } catch (error) {
      console.log(`[TEST-DEBUG] スプレッドシートタブクリックに失敗、代替方法を試行: ${error}`);
      await this.page.locator('button, [role="tab"]').filter({ hasText: 'Google' }).click();
    }
    await this.spreadsheetUrlInput.fill(url);
  }

  /**
   * フォームを送信する
   */
  async submitForm() {
    try {
      await this.submitButton.click();
    } catch (error) {
      console.log(`[TEST-DEBUG] 主要な送信ボタンロケーターが失敗、バックアップを試行: ${error}`);
      await this.submitButtonByText.click();
    }
  }
}
