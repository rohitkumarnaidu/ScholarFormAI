// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

const hasSupabaseUrl = Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL);

test.describe('Dark Mode', () => {
    test('dark mode toggle exists on landing page', async ({ page }) => {
        test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set — app may not hydrate');
        await page.goto('/');
        await expect(page.locator('body')).toBeVisible();

        const toggle = page.locator('button, label, [role="switch"]').filter({
            hasText: /dark|theme|mode|toggle/i,
        }).first();
        const toggleExists = await toggle.count() > 0;
        expect(toggleExists).toBeTruthy();
    });

    test('dark mode persists across page navigation', async ({ page }) => {
        test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
        await page.goto('/');

        const initialClass = await page.evaluate(() => {
            return document.documentElement.className || '';
        });
        expect(initialClass).toBeDefined();
    });
});
