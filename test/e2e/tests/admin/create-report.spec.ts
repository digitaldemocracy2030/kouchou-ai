import { test, expect } from '@playwright/test';
import { CreateReportPage } from '../../pages/admin/create-report';
import { setupBasicAuth } from '../../utils/auth';
import { mockReportCreation } from '../../utils/mock-api';

test.describe('レポート作成ページ', () => {
  test('CSVファイルをアップロードしてレポートを作成する', async ({ page }) => {
    await setupBasicAuth(page);
    
    await mockReportCreation(page);
    
    const createReportPage = new CreateReportPage(page);
    
    await createReportPage.goto();
    
    await expect(createReportPage.pageTitle).toBeVisible();
    
    const reportId = `test-report-${Date.now()}`;
    const question = 'これはテスト質問です';
    const intro = 'これはテスト説明です';
    await createReportPage.fillBasicInfo(reportId, question, intro);
    
    await createReportPage.uploadCsvFile('../../fixtures/sample.csv');
    
    await createReportPage.submitForm();
    
    await page.waitForURL('**/');
  });
});
