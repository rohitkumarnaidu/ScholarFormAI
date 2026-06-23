// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

test.describe('Protected Routes Redirect', () => {
    test('redirects unauthenticated user from /dashboard to /login', async ({ page }) => {
        await page.goto('/dashboard');
        await expect(page).toHaveURL(/.*\/login/, { timeout: 10000 });
        const heading = page.getByRole('heading', { name: /Welcome back/i });
        await expect(heading).toBeVisible();
    });

    test('redirects unauthenticated user from /settings to /login', async ({ page }) => {
        await page.goto('/settings');
        await expect(page).toHaveURL(/.*\/login/, { timeout: 10000 });
    });

    test('redirects unauthenticated user from /profile to /login', async ({ page }) => {
        await page.goto('/profile');
        await expect(page).toHaveURL(/.*\/login/, { timeout: 10000 });
    });

    test('redirects unauthenticated user from /admin-dashboard to /login', async ({ page }) => {
        await page.goto('/admin-dashboard');
        await expect(page).toHaveURL(/.*\/login/, { timeout: 10000 });
    });
});
