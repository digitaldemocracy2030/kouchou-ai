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
    
    if (!process.env.USE_TEST_IDS) {
      this.pageTitle = page.locator('h2:has-text("新しいレポートを作成する"), .chakra-heading:has-text("新しいレポートを作成する")');
      
      this.titleField = page.locator('label:has-text("タイトル") + div input, .chakra-field label:has-text("タイトル") ~ input');
      this.introField = page.locator('label:has-text("調査概要") + div input, .chakra-field label:has-text("調査概要") ~ input');
      this.idField = page.locator('label:has-text("ID") + div input, .chakra-field label:has-text("ID") ~ input');
      
      this.csvTab = page.locator('button:has-text("CSVファイル"), [role="tab"]:has-text("CSVファイル")');
      this.csvFileUpload = page.locator('input[type="file"]');
      
      this.submitButton = page.locator('button:has-text("レポート作成を開始")');
    }
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
    await this.csvFileUpload.setInputFiles(filePath);
  }

  async submitForm() {
    await this.submitButton.click();
  }
}
