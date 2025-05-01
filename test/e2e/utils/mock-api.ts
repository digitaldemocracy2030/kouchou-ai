import { Page } from '@playwright/test';

/**
 * APIエンドポイントをモックする
 */
export async function mockApiEndpoint(page: Page, url: string, response: any, status = 200) {
  await page.route(url, async (route) => {
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(response),
    });
  });
}

/**
 * レポート作成APIをモックする
 */
export async function mockReportCreation(page: Page) {
  await mockApiEndpoint(
    page,
    '**/admin/reports',
    { success: true, slug: 'test-report' }
  );
}
