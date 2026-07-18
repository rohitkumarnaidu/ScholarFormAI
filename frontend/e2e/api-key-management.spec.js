// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

const hasSupabaseUrl = Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL);

test.describe('API Key Management', () => {
    test.describe('API Keys', () => {
        test('api keys page loads with heading', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/api-keys');
            await expect(page.locator('body')).toBeVisible({ timeout: 15000 });

            const heading = page.getByRole('heading', { name: /API Keys/i });
            await expect(heading).toBeVisible();
        });

        test('add key button opens form with provider select and masked key input', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/api-keys');

            const addKeyBtn = page.getByRole('button', { name: /Add Key/i });
            await expect(addKeyBtn).toBeVisible({ timeout: 15000 });
            await addKeyBtn.click();

            const formHeading = page.getByText(/Add New API Key/i);
            await expect(formHeading).toBeVisible();

            const providerSelect = page.locator('select').first();
            await expect(providerSelect).toBeVisible();

            const apiKeyInput = page.locator('input[type="password"]').first();
            await expect(apiKeyInput).toBeVisible();

            const inputType = await apiKeyInput.getAttribute('type');
            expect(inputType).toBe('password');
        });

        test('api keys page has save and test connection buttons', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/api-keys');

            const addKeyBtn = page.getByRole('button', { name: /Add Key/i });
            await expect(addKeyBtn).toBeVisible({ timeout: 15000 });
            await addKeyBtn.click();

            const saveBtn = page.getByRole('button', { name: /Save Key/i });
            await expect(saveBtn).toBeVisible();

            const testBtn = page.getByRole('button', { name: /Test Connection/i });
            await expect(testBtn).toBeVisible();
        });
    });
});
