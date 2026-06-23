// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

test.describe('Landing Page', () => {
    test('landing page loads with hero section', async ({ page }) => {
        await page.goto('/');
        await expect(page).toHaveTitle(/Automated Academic Manuscript Formatter/i);

        const heading = page.locator('h1').first();
        await expect(heading).toBeVisible();

        const subtitle = page.getByText(/Format|Academic|Manuscript/i).first();
        await expect(subtitle).toBeVisible();
    });

    test('landing page has hero CTA links to formatter and generator', async ({ page }) => {
        await page.goto('/');

        const formatterCta = page.getByRole('link', { name: /Upload Manuscript/i }).first();
        await expect(formatterCta).toBeVisible();

        const generatorCta = page.getByRole('link', { name: /Create Draft/i }).first();
        await expect(generatorCta).toBeVisible();
    });

    test('hero CTA links navigate to correct pages', async ({ page }) => {
        await page.goto('/');

        const formatterCta = page.getByRole('link', { name: /Upload Manuscript/i }).first();
        const href = await formatterCta.getAttribute('href');
        expect(href).toBeTruthy();
        expect(href).toContain('upload');
    });

    test('landing page has navigation bar', async ({ page }) => {
        await page.goto('/');

        const nav = page.locator('nav, header');
        await expect(nav).toBeVisible();

        const navLinks = nav.locator('a');
        const linkCount = await navLinks.count();
        expect(linkCount).toBeGreaterThanOrEqual(1);
    });
});
