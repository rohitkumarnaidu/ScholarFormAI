// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { defineConfig, devices } from '@playwright/test';

/**
 * See https://playwright.dev/docs/test-configuration.
 */
const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3005';
const useWebServer = !process.env.PLAYWRIGHT_BASE_URL;

export default defineConfig({
  testDir: './e2e',
  /* Placeholder specs are fine in parallel, but full browser fan-out overwhelms local dev machines. */
  fullyParallel: false,
  /* Global Timeout */
  timeout: process.env.CI ? 60 * 1000 : 120 * 1000,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI and locally */
  retries: process.env.CI ? 2 : 1,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : 4,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL,

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
    extraHTTPHeaders: {
      'x-playwright-test': 'true'
    }
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Run your local dev server before starting the tests */
  webServer: useWebServer
    ? {
        command: 'npm run start -- -p 3005',
        url: 'http://localhost:3005',
        reuseExistingServer: !process.env.CI,
        timeout: 120 * 1000,
      }
    : undefined,
});
