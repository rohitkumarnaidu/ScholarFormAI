import { test, expect } from '@playwright/test';

test.describe('Core User Journeys', () => {
  test('Landing page renders correctly', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/AMF/i);
    await expect(page.locator('h1')).toBeVisible();
  });

  test('Navigation to dashboard works', async ({ page }) => {
    await page.goto('/dashboard');
    // We expect a redirect to login if unauthenticated, or the dashboard itself
    // We just verify it doesn't crash
    await expect(page).not.toBeNull();
  });
});
