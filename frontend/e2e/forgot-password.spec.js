// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

test.describe('Forgot Password', () => {
    test('forgot password page has email input and submit button', async ({ page }) => {
        await page.goto('/forgot-password');
        await expect(page).toHaveTitle(/Forgot Password/i);

        await expect(page.locator('input[type="email"]')).toBeVisible();
        await expect(page.getByRole('button', { name: /Send OTP/i })).toBeVisible();
    });

    test('forgot password page has back to sign in link', async ({ page }) => {
        await page.goto('/forgot-password');

        const backLink = page.getByRole('link', { name: /Back to Sign in/i });
        await expect(backLink).toBeVisible();
    });
});
