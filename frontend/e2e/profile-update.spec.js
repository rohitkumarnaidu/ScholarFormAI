// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

const hasSupabaseUrl = Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL);

test.describe('Profile Update', () => {
    test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
    test('profile page loads with editable fields', async ({ page }) => {
        await page.goto('/profile');
        await expect(page.locator('body')).toBeVisible();

        const heading = page.getByRole('heading', { name: /Account Settings/i });
        await expect(heading).toBeVisible();

        const editButton = page.getByRole('button', { name: /Edit Profile/i });
        await expect(editButton).toBeVisible();
    });
});
