import { defineConfig } from '@playwright/test';

const isCI = !!process.env['CI'];

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: isCI ? 2 : 1,
  reporter: [
    ['list'],
    ['html', { open: 'never' }],
    ...(isCI ? [['junit', { outputFile: 'test-results/e2e-junit.xml' }] as const] : []),
  ],
  use: {
    baseURL: 'http://localhost:4200',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
});
