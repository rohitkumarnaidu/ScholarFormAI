// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

const hasSupabaseUrl = Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL);

test.describe('Account Deletion', () => {
    test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
    test('profile page loads with account action elements', async ({ page }) => {
        await page.goto('/profile');
        await expect(page.locator('body')).toBeVisible();

        const heading = page.getByRole('heading', { name: /Account Settings/i });
        await expect(heading).toBeVisible();

        const signOutButton = page.getByRole('button', { name: /Sign out/i });
        await expect(signOutButton).toBeVisible();
    });
});
