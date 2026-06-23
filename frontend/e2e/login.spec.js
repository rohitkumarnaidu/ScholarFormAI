// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

test.describe('Login', () => {
    test('login page displays sign-in form', async ({ page }) => {
        await page.goto('/login');
        await expect(page).toHaveTitle(/Sign In/i);

        const heading = page.getByRole('heading', { name: /Welcome back/i });
        await expect(heading).toBeVisible();

        const form = page.locator('form').first();
        await expect(form).toBeVisible();
    });

    test('login page has email and password inputs', async ({ page }) => {
        await page.goto('/login');

        await expect(page.locator('input[type="email"]')).toBeVisible();
        await expect(page.locator('input[type="password"]')).toBeVisible();
        await expect(page.getByRole('button', { name: /Sign in|Login/i })).toBeVisible();
    });

    test('login page has forgot password link', async ({ page }) => {
        await page.goto('/login');

        const forgotLink = page.getByRole('link', { name: /Forgot Password/i });
        await expect(forgotLink).toBeVisible();

        const href = await forgotLink.getAttribute('href');
        expect(href).toContain('forgot');
    });

    test('login page has sign up link', async ({ page }) => {
        await page.goto('/login');

        const signupLink = page.getByRole('link', { name: /Sign up|Create account/i });
        await expect(signupLink).toBeVisible();
    });
});
