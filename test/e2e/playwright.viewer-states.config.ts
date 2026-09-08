import { defineConfig, devices } from "@playwright/test";
// APIを使わない状態カタログだけの検査。通常E2EのダミーAPI起動は不要。
export default defineConfig({
  testDir: "./tests/viewer-states",
  timeout: 60000,
  workers: 1,
  use: { ...devices["Desktop Chrome"], baseURL: "http://localhost:4001", screenshot: "only-on-failure" },
  webServer: {
    command: "cd ../../apps/public-viewer && pnpm exec next dev --webpack -p 4001",
    url: "http://localhost:4001/dev/viewer-states/",
    timeout: 180000,
    reuseExistingServer: !process.env.CI,
  },
});
