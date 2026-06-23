// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

test.describe('Auth Flow', () => {
    test('login page displays sign-in form', async ({ page }) => {
        await page.goto('/login');
        await expect(page).toHaveTitle(/Sign In/i);

        const heading = page.getByRole('heading', { name: /Welcome back/i });
        await expect(heading).toBeVisible();

        const form = page.locator('form').first();
        await expect(form).toBeVisible();
    });
});
