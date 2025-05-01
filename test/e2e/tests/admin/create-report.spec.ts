import { test, expect } from '@playwright/test';
import { CreateReportPage } from '../../pages/admin/create-report';
import { mockReportCreation } from '../../utils/mock-api';

test.describe('レポート作成ページ', () => {
  test('data-testid属性を使用したセレクタのテスト', async ({ page }) => {
    await page.setContent(`
      <html>
        <body>
          <h2 data-testid="create-report-title">新しいレポートを作成する</h2>
          <div>
            <input data-testid="title-field" type="text" />
            <input data-testid="intro-field" type="text" />
            <input data-testid="id-field" type="text" />
            <button data-testid="csv-tab">CSVファイル</button>
            <input data-testid="file-upload" type="file" />
            <button data-testid="submit-button">レポート作成を開始</button>
          </div>
        </body>
      </html>
    `);
    
    await mockReportCreation(page);
    
    const createReportPage = new CreateReportPage(page);
    
    await expect(createReportPage.pageTitle).toBeVisible();
    await expect(createReportPage.titleField).toBeVisible();
    await expect(createReportPage.introField).toBeVisible();
    await expect(createReportPage.idField).toBeVisible();
    await expect(createReportPage.csvTab).toBeVisible();
    await expect(createReportPage.csvFileUpload).toBeVisible();
    await expect(createReportPage.submitButton).toBeVisible();
    
    const reportId = `test-report-${Date.now()}`;
    const question = 'これはテスト質問です';
    const intro = 'これはテスト説明です';
    
    await createReportPage.fillTitleField(question);
    await createReportPage.fillIntroField(intro);
    await createReportPage.fillIdField(reportId);
    
    await expect(createReportPage.titleField).toHaveValue(question);
    await expect(createReportPage.introField).toHaveValue(intro);
    await expect(createReportPage.idField).toHaveValue(reportId);
    
    await createReportPage.csvTab.click();
    await createReportPage.submitButton.click();
  });
});
