// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

test.describe('Signup', () => {
    test('signup page has form inputs', async ({ page }) => {
        await page.goto('/signup');
        await expect(page).toHaveTitle(/Create Account/i);

        await expect(page.locator('input[type="email"]')).toBeVisible();
        await expect(page.locator('input[type="password"]').first()).toBeVisible();
        await expect(page.getByRole('button', { name: /Create Account/i })).toBeVisible();
    });

    test('signup page has sign in link', async ({ page }) => {
        await page.goto('/signup');

        const signInLink = page.getByRole('link', { name: /Sign in/i });
        await expect(signInLink).toBeVisible();
    });
});
