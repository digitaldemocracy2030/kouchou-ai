import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 30 * 1000,
  expect: {
    timeout: 5000,
  },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ["html", { outputFolder: "playwright-report" }],
    ["json", { outputFile: "playwright-report/results.json" }],
    ["list"],
  ],
  use: {
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "verify",
      testMatch: ["**/verify-*.spec.ts", "**/seed.spec.ts"],
      use: {
        ...devices["Desktop Chrome"],
        baseURL: "http://localhost:4000",
      },
    },
    {
      name: "admin",
      testMatch: "**/admin/**/*.spec.ts",
      use: {
        ...devices["Desktop Chrome"],
        baseURL: "http://localhost:4000",
      },
    },
    {
      name: "client",
      testMatch: "**/client/**/*.spec.ts",
      use: {
        ...devices["Desktop Chrome"],
        baseURL: "http://localhost:3000",
      },
    },
    {
      name: "client-static-root",
      testMatch: "**/client-static/root/**/*.spec.ts",
      use: {
        ...devices["Desktop Chrome"],
        baseURL: "http://localhost:3001",
      },
    },
    {
      name: "client-static-subdir",
      testMatch: "**/client-static/subdir/**/*.spec.ts",
      use: {
        ...devices["Desktop Chrome"],
        baseURL: "http://localhost:3002/kouchou-ai/",
      },
    },
    {
      name: "debug",
      testMatch: ["**/simple.spec.ts", "**/debug.spec.ts"],
      use: {
        ...devices["Desktop Chrome"],
      },
    },
  ],
  webServer: [
    // Dummy API server: admin/public tests depend on this
    {
      command: "cd ../../utils/dummy-server && pnpm exec next dev -p 8002",
      url: "http://localhost:8002/",
      timeout: 120 * 1000,
      reuseExistingServer: !process.env.CI,
      env: {
        PUBLIC_API_KEY: "public",
        ADMIN_API_KEY: "public",
        E2E_TEST: "true",
      },
    },
    // Admin tests: 管理画面サーバーを起動（ダミーAPIサーバーを参照）
    {
      command: "cd ../../apps/admin && pnpm run dev",
      url: "http://localhost:4000/",
      timeout: 180 * 1000,
      reuseExistingServer: !process.env.CI,
      env: {
        NEXT_PUBLIC_API_BASEPATH: "http://localhost:8002",
        NEXT_PUBLIC_ADMIN_API_KEY: "public",
        ADMIN_API_KEY: "public",
        API_BASEPATH: "http://localhost:8002",
      },
    },
    // Public viewer静的ビルドテスト用（Root）: 静的ファイルをホスティング（port 3001）
    {
      command:
        "./scripts/build-static.sh root && cd ../../apps/public-viewer && pnpm exec http-server out-root -p 3001 --cors --silent",
      url: "http://localhost:3001/",
      timeout: 120 * 1000,
      reuseExistingServer: !process.env.CI,
    },
    // Public viewer静的ビルドテスト用（Subdirectory）: 静的ファイルをホスティング（port 3002）
    {
      command:
        "./scripts/build-static.sh subdir && cd ../../apps/public-viewer && pnpm exec http-server out-subdir -p 3002 --cors --silent",
      url: "http://localhost:3002/kouchou-ai/",
      timeout: 120 * 1000,
      reuseExistingServer: !process.env.CI,
    },
    // Public viewer tests: フロントエンドサーバーを起動（ダミーAPIサーバーを参照）
    {
      command: "cd ../../apps/public-viewer && pnpm run dev",
      url: "http://localhost:3000/",
      timeout: 180 * 1000,
      reuseExistingServer: !process.env.CI,
      env: {
        NEXT_PUBLIC_API_BASEPATH: "http://localhost:8002",
        API_BASEPATH: "http://localhost:8002",
        NEXT_PUBLIC_PUBLIC_API_KEY: "public",
      },
    },
  ],
});
