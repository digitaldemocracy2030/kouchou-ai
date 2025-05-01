import { Page, Locator } from '@playwright/test';

/**
 * レポート作成ページのPage Object
 * 複数のセレクタ戦略を使用して信頼性を高める
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
    
    this.pageTitle = page.locator('h2:has-text("新しいレポートを作成する"), [data-testid="create-report-title"]');
    this.titleField = page.locator('label:has-text("タイトル") + div input, [data-testid="title-field"]');
    this.introField = page.locator('label:has-text("調査概要") + div input, [data-testid="intro-field"]');
    this.idField = page.locator('label:has-text("ID") + div input, [data-testid="id-field"]');
    this.csvTab = page.locator('button:has-text("CSVファイル"), [data-testid="csv-tab"]');
    this.csvFileUpload = page.locator('input[type="file"]');
    this.submitButton = page.locator('button:has-text("レポート作成を開始"), [data-testid="submit-button"]');
  }

  async goto() {
    console.log('Navigating to /create page...');
    await this.page.goto('/create');
    
    console.log('Waiting for page to load (domcontentloaded)...');
    await this.page.waitForLoadState('domcontentloaded');
    
    // console.log('Waiting for page to load (networkidle)...');
    // await this.page.waitForLoadState('networkidle');
    
    console.log('Waiting for page title to be visible...');
    await this.page.waitForSelector('h2:has-text("新しいレポートを作成する")', { timeout: 10000 });
  }

  async fillTitleField(text: string) {
    console.log(`Filling title field with: ${text}`);
    await this.titleField.fill(text);
  }

  async fillIntroField(text: string) {
    console.log(`Filling intro field with: ${text}`);
    await this.introField.fill(text);
  }

  async fillIdField(text: string) {
    console.log(`Filling ID field with: ${text}`);
    await this.idField.fill(text);
  }

  async uploadCsvFile(filePath: string) {
    console.log(`Uploading CSV file: ${filePath}`);
    await this.csvTab.click();
    
    console.log('Waiting for file input to be visible...');
    const fileInput = this.page.locator('input[type="file"]');
    await fileInput.waitFor({ state: 'attached', timeout: 10000 });
    
    console.log('Setting input files...');
    await fileInput.setInputFiles(filePath);
  }

  async submitForm() {
    console.log('Clicking submit button...');
    await this.submitButton.click();
  }
}
