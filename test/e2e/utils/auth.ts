import { Page } from '@playwright/test';
import * as dotenv from 'dotenv';
import * as path from 'path';
import * as fs from 'fs';

const envPath = path.resolve(__dirname, '../.env');

if (fs.existsSync(envPath)) {
  dotenv.config({ path: envPath });
  console.log('.env file loaded from:', envPath);
} else {
  console.log('.env file not found at:', envPath);
}

/**
 * Basic認証のヘッダーを設定する
 */
export async function setupBasicAuth(page: Page): Promise<void> {
  const username = process.env.BASIC_AUTH_USERNAME || 'test_user';
  const password = process.env.BASIC_AUTH_PASSWORD || 'test_password';
  
  console.log(`Setting up Basic Auth with username: ${username}`);
  
  await page.setExtraHTTPHeaders({
    'Authorization': `Basic ${Buffer.from(`${username}:${password}`).toString('base64')}`,
  });
}
