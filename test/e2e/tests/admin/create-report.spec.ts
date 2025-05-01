import { test, expect } from '@playwright/test';
import { CreateReportPage } from '../../pages/admin/create-report';
import { setupBasicAuth } from '../../utils/auth';
import { mockReportCreation } from '../../utils/mock-api';
import * as path from 'path';

test.describe('レポート作成ページ', () => {
  test('CSVファイルをアップロードしてレポートを作成する', async ({ page }) => {
    await setupBasicAuth(page);
    
    await mockReportCreation(page);
    
    const createReportPage = new CreateReportPage(page);
    
    console.log('Navigating to create page...');
    await createReportPage.goto();
    
    console.log('Waiting for page to load...');
    await page.waitForLoadState('networkidle');
    
    const html = await page.content();
    console.log('Page HTML contains create-report-title:', html.includes('data-testid="create-report-title"'));
    
    console.log('Checking if page title is visible...');
    await expect(page.locator('h2')).toBeVisible({ timeout: 10000 });
    await expect(createReportPage.pageTitle).toBeVisible({ timeout: 10000 });
    
    const reportId = `test-report-${Date.now()}`;
    const question = 'これはテスト質問です';
    const intro = 'これはテスト説明です';
    
    console.log('Filling form fields...');
    await createReportPage.fillTitleField(question);
    await createReportPage.fillIntroField(intro);
    await createReportPage.fillIdField(reportId);
    
    console.log('Uploading CSV file...');
    const csvPath = path.resolve(__dirname, '../../fixtures/sample.csv');
    await createReportPage.uploadCsvFile(csvPath);
    
    console.log('Submitting form...');
    await createReportPage.submitForm();
    
    console.log('Waiting for redirect...');
    await page.waitForURL('**/');
  });
});
