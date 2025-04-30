import { test, expect } from '@playwright/test';
import { CreateReportPage } from '../../pages/admin/create-report';
import { setupBasicAuth } from '../../utils/auth';
import { mockReportCreation } from '../../utils/mock-api';

test.describe('レポート作成ページ', () => {
  test('CSVファイルをアップロードしてレポートを作成する', async ({ page }) => {
    test.setTimeout(60000); // タイムアウトを延長
    
    await setupBasicAuth(page);
    
    await mockReportCreation(page);
    
    console.log('Starting test: CSVファイルをアップロードしてレポートを作成する');
    
    const createReportPage = new CreateReportPage(page);
    
    console.log('Navigating to create report page');
    await createReportPage.goto();
    
    console.log('Waiting for page to load');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForLoadState('networkidle');
    
    console.log('Checking for page title');
    try {
      const h1Exists = await page.locator('h1').count() > 0;
      console.log(`H1 elements found: ${h1Exists}`);
      
      if (h1Exists) {
        const h1Text = await page.locator('h1').first().textContent();
        console.log(`H1 text: ${h1Text}`);
      }
      
      await Promise.race([
        expect(createReportPage.pageTitle).toBeVisible({ timeout: 15000 }),
        expect(page.locator('h1')).toBeVisible({ timeout: 15000 }),
        expect(page.locator('form')).toBeVisible({ timeout: 15000 })
      ]);
      
      console.log('Page title or form is visible');
    } catch (error) {
      console.log('Error while checking page title:');
      console.log(error);
      console.log('Current URL:', page.url());
      console.log('Page HTML:', await page.content());
      throw error;
    }
    
    console.log('Filling basic info');
    const reportId = `test-report-${Date.now()}`;
    const question = 'これはテスト質問です';
    const intro = 'これはテスト説明です';
    await createReportPage.fillBasicInfo(reportId, question, intro);
    
    console.log('Uploading CSV file');
    await createReportPage.uploadCsvFile('../../fixtures/sample.csv');
    
    console.log('Submitting form');
    await createReportPage.submitForm();
    
    console.log('Waiting for redirect');
    await page.waitForURL('**/');
    
    console.log('Test completed successfully');
  });
});
