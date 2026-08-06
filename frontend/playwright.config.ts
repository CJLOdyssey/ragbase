import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 180000,
  expect: { timeout: 8000 },
  retries: 0,
  maxFailures: 1,
  // 两个 spec 共享同一后端 DB，串行避免数据互相踩踏
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:5174',
    actionTimeout: 10000,
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
    headless: true,
    launchOptions: {
      args: ['--no-sandbox'],
    },
  },
  projects: [
    {
      name: 'setup',
      testMatch: /auth\.setup\.ts/,
    },
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: '.auth/user.json',
      },
      dependencies: ['setup'],
    },
  ],
});
