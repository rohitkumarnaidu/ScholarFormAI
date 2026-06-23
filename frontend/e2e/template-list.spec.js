// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

test.describe('Template List', () => {
    test('template list page loads with available templates', async ({ page }) => {
        await page.goto('/templates');
        await expect(page.locator('body')).toBeVisible();

        const heading = page.getByRole('heading', { name: /template/i });
        await expect(heading).toBeVisible();
    });

    test('template list shows multiple template cards', async ({ page }) => {
        await page.goto('/templates');

        const templateCards = page.locator('[class*="card"], [class*="template"], li, article').filter({
            has: page.getByRole('heading').or(page.locator('h2, h3, h4')),
        });
        const count = await templateCards.count();
        expect(count).toBeGreaterThanOrEqual(1);
    });

    test('template list has IEEE template entry', async ({ page }) => {
        await page.goto('/templates');

        const ieeeCard = page.getByText(/IEEE/i).first();
        await expect(ieeeCard).toBeVisible();
    });

    test('template list links to detail or upload page', async ({ page }) => {
        await page.goto('/templates');

        const links = page.locator('a').filter({ hasText: /template|select|use|ieee|apa|springer/i });
        const linkCount = await links.count();
        expect(linkCount).toBeGreaterThanOrEqual(1);
    });
});
