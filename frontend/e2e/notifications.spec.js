// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

const hasSupabaseUrl = Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL);

test.describe('Notifications', () => {
    test.describe('Notification Center', () => {
        test('notifications page loads with heading', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/notifications');
            await expect(page.locator('body')).toBeVisible({ timeout: 15000 });

            const heading = page.getByRole('heading', { name: /Notifications/i });
            await expect(heading).toBeVisible();
        });

        test('shows empty state when no notifications exist', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/notifications');

            const emptyMessage = page.getByText(/No notifications yet/i);
            await expect(emptyMessage).toBeVisible({ timeout: 15000 });
        });

        test('renders notification preferences section with toggles', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/notifications');

            await expect(page.locator('body')).toBeVisible({ timeout: 15000 });
            const prefsHeading = page.getByText(/Notification Preferences/i);
            await expect(prefsHeading).toBeVisible();

            const switches = page.locator('[role="switch"]');
            const switchCount = await switches.count();
            expect(switchCount).toBeGreaterThanOrEqual(5);
        });

        test('displays notification list when notifications are stored', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
                window.localStorage.setItem('scholarform_notifications', JSON.stringify([
                    { id: 'n1', type: 'success', message: 'Document formatted successfully', read: false, timestamp: Date.now() },
                    { id: 'n2', type: 'info', message: 'New template available: IEEE', read: true, timestamp: Date.now() - 3600000 },
                    { id: 'n3', type: 'warning', message: 'Processing delayed', read: false, timestamp: Date.now() - 7200000 },
                ]));
            });
            await page.goto('/notifications');

            await expect(page.getByText(/Document formatted successfully/i)).toBeVisible({ timeout: 15000 });
            await expect(page.getByText(/New template available/i)).toBeVisible();
            await expect(page.getByText(/Processing delayed/i)).toBeVisible();

            const markAllBtn = page.getByRole('button', { name: /Mark all read/i });
            await expect(markAllBtn).toBeVisible();

            const clearAllBtn = page.getByRole('button', { name: /Clear all/i });
            await expect(clearAllBtn).toBeVisible();

            const unreadBadge = page.locator('text=/3/i');
            await expect(unreadBadge).toBeVisible();
        });
    });
});
