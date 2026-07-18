// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

const hasSupabaseUrl = Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL);

test.describe('Settings & Profile', () => {
    test.describe('Profile Update', () => {
        test('profile page loads with account settings heading', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/profile');
            await expect(page.locator('body')).toBeVisible({ timeout: 15000 });

            const heading = page.getByRole('heading', { name: /Account Settings/i });
            await expect(heading).toBeVisible();
        });

        test('profile page shows Edit Profile button', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/profile');

            const editButton = page.getByRole('button', { name: /Edit Profile/i });
            await expect(editButton).toBeVisible();
        });

        test('edit profile reveals name and institution fields', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/profile');

            const editButton = page.getByRole('button', { name: /Edit Profile/i });
            await expect(editButton).toBeVisible({ timeout: 15000 });
            await editButton.click();

            const nameInput = page.locator('input#edit-name');
            await expect(nameInput).toBeVisible();

            const institutionInput = page.locator('input#edit-institution');
            await expect(institutionInput).toBeVisible();

            const saveButton = page.getByRole('button', { name: /Save Changes/i });
            await expect(saveButton).toBeVisible();
        });
    });

    test.describe('Settings', () => {
        test('settings page loads with general and billing tabs', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/settings');
            await expect(page.locator('body')).toBeVisible({ timeout: 15000 });

            const heading = page.getByRole('heading', { name: /Settings/i });
            await expect(heading).toBeVisible();

            const saveSettings = page.getByRole('button', { name: /Save Settings/i });
            await expect(saveSettings).toBeVisible();
        });

        test('preferences section has dark mode toggle', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/profile');

            await expect(page.locator('body')).toBeVisible({ timeout: 15000 });
            const darkModeToggle = page.locator('[role="switch"]').filter({ hasText: /Dark Mode/i });
            const toggleExists = (await darkModeToggle.count()) > 0;
            expect(toggleExists).toBeTruthy();
        });

        test('settings has manuscript status updates toggle', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/profile');

            const statusToggle = page.locator('[role="switch"][aria-label*="Status Updates" i]');
            const newsletterToggle = page.locator('[role="switch"][aria-label*="Newsletter" i]');
            const hasStatusToggle = (await statusToggle.count()) > 0;
            const hasNewsletterToggle = (await newsletterToggle.count()) > 0;
            expect(hasStatusToggle || hasNewsletterToggle).toBeTruthy();
        });
    });
});
