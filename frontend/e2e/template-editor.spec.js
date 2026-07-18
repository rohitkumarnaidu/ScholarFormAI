// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

const hasSupabaseUrl = Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL);

test.describe('Template Editor', () => {
    test.describe('Template Editing', () => {
        test('template editor page loads with heading and settings', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/template-editor');
            await expect(page.locator('body')).toBeVisible({ timeout: 15000 });

            const heading = page.getByRole('heading', { name: /Template Editor/i });
            await expect(heading).toBeVisible();

            const formattingHeading = page.getByText(/Formatting Settings/i);
            await expect(formattingHeading).toBeVisible();
        });

        test('template editor has font family and size inputs', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/template-editor');

            const fontFamilySelect = page.locator('select').first();
            await expect(fontFamilySelect).toBeVisible();

            const fontSizeInput = page.locator('input[type="number"]').first();
            await expect(fontSizeInput).toBeVisible();
        });

        test('save button is present on template editor', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/template-editor');

            const saveButton = page.getByRole('button', { name: /Save Custom Template/i });
            await expect(saveButton).toBeVisible();

            const savedTemplatesSection = page.getByText(/Saved Templates/i);
            await expect(savedTemplatesSection).toBeVisible();
        });
    });
});
