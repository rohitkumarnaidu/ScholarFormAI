// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

const hasSupabaseUrl = Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL);

test.describe('Provider Management', () => {
    test.describe('Provider List', () => {
        test('providers page loads with heading', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/providers');
            await expect(page.locator('body')).toBeVisible({ timeout: 15000 });

            const heading = page.getByRole('heading', { name: /Providers/i });
            await expect(heading).toBeVisible();
        });

        test('providers page has search input and custom provider button', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/providers');

            const searchInput = page.locator('input[placeholder*="Search providers"]');
            await expect(searchInput).toBeVisible();

            const addCustomBtn = page.getByRole('button', { name: /Custom Provider/i });
            await expect(addCustomBtn).toBeVisible();
        });
    });

    test.describe('Custom Provider', () => {
        test('custom provider form opens on button click', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/providers');

            const addCustomBtn = page.getByRole('button', { name: /Custom Provider/i });
            await expect(addCustomBtn).toBeVisible({ timeout: 15000 });
            await addCustomBtn.click();

            const formHeading = page.getByText(/Add Custom Provider/i);
            await expect(formHeading).toBeVisible();

            const nameInput = page.locator('input[placeholder*="My Local LLM"]');
            await expect(nameInput).toBeVisible();

            const urlInput = page.locator('input[placeholder*="http://localhost"]');
            await expect(urlInput).toBeVisible();
        });

        test('api key field is masked on custom provider form', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/providers');

            const addCustomBtn = page.getByRole('button', { name: /Custom Provider/i });
            await expect(addCustomBtn).toBeVisible({ timeout: 15000 });
            await addCustomBtn.click();

            const apiKeyInput = page.locator('input[type="password"]').first();
            await expect(apiKeyInput).toBeVisible();

            const inputType = await apiKeyInput.getAttribute('type');
            expect(inputType).toBe('password');
        });

        test('custom provider form has add provider submit button', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/providers');

            const addCustomBtn = page.getByRole('button', { name: /Custom Provider/i });
            await expect(addCustomBtn).toBeVisible({ timeout: 15000 });
            await addCustomBtn.click();

            const submitBtn = page.getByRole('button', { name: /Add Provider|Update Provider/i });
            await expect(submitBtn).toBeVisible();

            const cancelBtn = page.getByRole('button', { name: /Cancel/i });
            await expect(cancelBtn).toBeVisible();
        });
    });
});
