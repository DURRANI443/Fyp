import { defineConfig } from '@playwright/test';
import { existsSync } from 'node:fs';
import { join } from 'node:path';

const cachedChromium = process.env.LOCALAPPDATA ? join(process.env.LOCALAPPDATA, 'ms-playwright', 'chromium_headless_shell-1234', 'chrome-headless-shell-win64', 'chrome-headless-shell.exe') : '';
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  expect: { timeout: 12000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:8001',
    browserName: 'chromium',
    headless: true,
    viewport: { width: 1440, height: 1000 },
    launchOptions: { ...(existsSync(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ?? cachedChromium) ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ?? cachedChromium } : {}) },
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: process.platform === 'win32' ? '..\\.venv\\Scripts\\python.exe e2e/serve.py' : '../.venv/bin/python e2e/serve.py',
    url: 'http://127.0.0.1:8001/api/health',
    timeout: 120000,
    reuseExistingServer: false,
  },
});
