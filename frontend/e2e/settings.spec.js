// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

const hasSupabaseUrl = Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL);

test.describe('Settings', () => {
    test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
    test('settings page loads with form elements', async ({ page }) => {
        await page.goto('/settings');
        await expect(page.locator('body')).toBeVisible();

        const heading = page.getByRole('heading', { name: /Settings/i });
        await expect(heading).toBeVisible();

        const saveButton = page.getByRole('button', { name: /Save Settings/i });
        await expect(saveButton).toBeVisible();
    });

    test('settings page has General and Billing tabs', async ({ page }) => {
        await page.goto('/settings');

        const generalTab = page.getByRole('tab', { name: /General/i });
        await expect(generalTab).toBeVisible();

        const billingTab = page.getByRole('tab', { name: /Billing/i });
        await expect(billingTab).toBeVisible();
    });
});
