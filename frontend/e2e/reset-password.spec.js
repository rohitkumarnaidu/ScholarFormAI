// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

test.describe('Reset Password', () => {
    test('reset password redirects to forgot-password when no token provided', async ({ page }) => {
        await page.goto('/reset-password');

        await expect(page).toHaveURL(/.*\/forgot-password/, { timeout: 10000 });
    });

    test('reset password page shows password fields when email and otp are provided', async ({ page }) => {
        await page.goto('/reset-password?email=test@example.com&otp=123456');

        await expect(page.locator('input[type="password"]')).toHaveCount(2);
        await expect(page.getByRole('button', { name: /Reset Password/i })).toBeVisible();
    });
});
