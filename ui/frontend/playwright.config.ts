import { defineConfig } from '@playwright/test';
import path from 'path';

const isCI = !!process.env['CI'];

// Project root is two levels above this config file (ui/frontend → ui → project root)
const PROJECT_ROOT = path.resolve(__dirname, '../..');

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
    video: 'on',
    viewport: { width: 1440, height: 900 },
  },

  // Start backend + frontend before tests run.
  // reuseExistingServer: true → if already listening, the command is skipped.
  // This makes the demo test fully self-sufficient — no manual `npm run dev` required.
  webServer: [
    {
      command: 'python -m uvicorn ui.backend.main:app --host 127.0.0.1 --port 8001',
      url: 'http://127.0.0.1:8001/api/health',
      timeout: 90_000,
      reuseExistingServer: true,
      cwd: PROJECT_ROOT,
    },
    {
      command: 'npm start --prefix ui/frontend',
      url: 'http://localhost:4200',
      timeout: 120_000,
      reuseExistingServer: true,
      cwd: PROJECT_ROOT,
    },
  ],

  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
      // Exclude the long-running demo recording — run it manually with --project=demo
      testIgnore: ['**/demo-showcase.spec.ts'],
    },
    {
      name: 'demo',
      retries: 0,
      timeout: 7_200_000,
      use: {
        browserName: 'chromium',
        viewport: { width: 1920, height: 1080 },
        deviceScaleFactor: 2,
        video: {
          mode: 'on',
          size: { width: 1920, height: 1080 },
        },
        launchOptions: { slowMo: 400 },
      },
    },
  ],
});
