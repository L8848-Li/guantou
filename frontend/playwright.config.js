import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  // The CI stack uses SQLite and audit middleware writes on every request.
  workers: process.env.CI ? 1 : undefined,
  // H5 运行时存在 toast/loading 遮罩等时序竞态，CI 上允许重试以隔离偶发干扰。
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:8181',
    viewport: { width: 390, height: 844 },
    launchOptions: process.env.PLAYWRIGHT_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH }
      : undefined,
    // 失败即保留 trace，保证 CI 偶发失败可取证。
    trace: 'retain-on-failure',
  },
});
