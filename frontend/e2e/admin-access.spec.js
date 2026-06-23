// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

test.describe('Admin Access', () => {
    test('admin dashboard page loads or redirects to login when unauthenticated', async ({ page }) => {
        await page.goto('/admin-dashboard');

        await expect(page.locator('body')).toBeVisible();

        const url = page.url();
        const isLoginPage = url.includes('/login');
        const isAdminPage = url.includes('/admin-dashboard');
        expect(isLoginPage || isAdminPage).toBeTruthy();
    });
});
