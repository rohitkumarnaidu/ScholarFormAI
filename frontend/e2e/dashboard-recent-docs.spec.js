// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

const hasSupabaseUrl = Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL);

test.describe('Dashboard Recent Docs', () => {
    test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
    test('dashboard page loads with heading', async ({ page }) => {
        await page.goto('/dashboard');
        await expect(page.locator('body')).toBeVisible();

        const heading = page.getByRole('heading', { name: /dashboard/i });
        await expect(heading).toBeVisible();
    });
});
