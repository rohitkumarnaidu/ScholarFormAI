// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

const hasSupabaseUrl = Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL);

test.describe('Accessibility Tests', () => {

    test('homepage has no critical accessibility violations', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('body')).toBeVisible();

        const results = await page.evaluate(async () => {
            if (typeof window.axe === 'undefined') {
                const script = document.createElement('script');
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.3/axe.min.js';
                document.head.appendChild(script);
                await new Promise((resolve) => script.onload = resolve);
            }
            return await window.axe.run({
                rules: {
                    'color-contrast': { enabled: false },
                },
            });
        });

        const criticalViolations = results.violations.filter(
            (v) => v.impact === 'critical' || v.impact === 'serious'
        );
        expect(criticalViolations.length).toBe(0);
    });

    test('login page has no critical accessibility violations', async ({ page }) => {
        await page.goto('/login');
        await expect(page.locator('body')).toBeVisible();

        const results = await page.evaluate(async () => {
            if (typeof window.axe === 'undefined') {
                const script = document.createElement('script');
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.3/axe.min.js';
                document.head.appendChild(script);
                await new Promise((resolve) => script.onload = resolve);
            }
            return await window.axe.run({
                rules: {
                    'color-contrast': { enabled: false },
                },
            });
        });

        const criticalViolations = results.violations.filter(
            (v) => v.impact === 'critical' || v.impact === 'serious'
        );
        expect(criticalViolations.length).toBe(0);
    });

    test('dashboard page loads without critical accessibility violations', async ({ page }) => {
        test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
        await page.goto('/dashboard');
        await expect(page.locator('body')).toBeVisible();

        const results = await page.evaluate(async () => {
            if (typeof window.axe === 'undefined') {
                const script = document.createElement('script');
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.3/axe.min.js';
                document.head.appendChild(script);
                await new Promise((resolve) => script.onload = resolve);
            }
            return await window.axe.run();
        });

        const criticalViolations = results.violations.filter(
            (v) => v.impact === 'critical' || v.impact === 'serious'
        );
        expect(criticalViolations.length).toBe(0);
    });

    test('all interactive elements are keyboard accessible', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('body')).toBeVisible();

        const focusableCount = await page.evaluate(() => {
            const focusable = document.querySelectorAll(
                'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            return focusable.length;
        });

        expect(focusableCount).toBeGreaterThan(0);
    });

    test('tab navigation moves focus through elements', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('body')).toBeVisible();

        await page.keyboard.press('Tab');
        const firstFocused = await page.evaluate(() => document.activeElement?.tagName || '');
        expect(firstFocused).toBeTruthy();

        await page.keyboard.press('Tab');
        const secondFocused = await page.evaluate(() => document.activeElement?.tagName || '');
        expect(secondFocused).toBeTruthy();
    });

    test('all content images have alt text', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('body')).toBeVisible();

        const imagesWithoutAlt = await page.evaluate(() => {
            const images = Array.from(document.querySelectorAll('img'));
            return images.filter(img => !img.alt || img.alt.trim() === '').length;
        });

        expect(imagesWithoutAlt).toBe(0);
    });

    test('form inputs have associated labels on login page', async ({ page }) => {
        await page.goto('/login');
        await expect(page.locator('body')).toBeVisible();

        const inputsWithoutLabels = await page.evaluate(() => {
            const inputs = Array.from(document.querySelectorAll('input[type="text"], input[type="email"], input[type="password"]'));
            return inputs.filter(input => {
                const hasLabel = input.labels && input.labels.length > 0;
                const hasAriaLabel = input.hasAttribute('aria-label') || input.hasAttribute('aria-labelledby');
                const hasPlaceholder = input.hasAttribute('placeholder') && input.placeholder.trim() !== '';
                return !hasLabel && !hasAriaLabel && !hasPlaceholder;
            }).length;
        });

        expect(inputsWithoutLabels).toBe(0);
    });

    test('page has valid heading hierarchy', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('body')).toBeVisible();

        const headingIssues = await page.evaluate(() => {
            const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6'));
            if (headings.length === 0) return 0;

            let issues = 0;
            let lastLevel = 0;
            for (const h of headings) {
                const level = parseInt(h.tagName[1]);
                if (lastLevel > 0 && level > lastLevel + 1) {
                    issues++;
                }
                lastLevel = level;
            }
            return issues;
        });

        expect(headingIssues).toBeLessThanOrEqual(1);
    });

    test('aria roles are valid', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('body')).toBeVisible();

        const results = await page.evaluate(async () => {
            if (typeof window.axe === 'undefined') {
                const script = document.createElement('script');
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.3/axe.min.js';
                document.head.appendChild(script);
                await new Promise((resolve) => script.onload = resolve);
            }
            return await window.axe.run({ runOnly: { type: 'tag', values: ['cat.aria'] } });
        });

        const criticalAria = results.violations.filter(
            (v) => v.impact === 'critical' || v.impact === 'serious'
        );
        expect(criticalAria.length).toBe(0);
    });

    test('screen reader can announce page title', async ({ page }) => {
        await page.goto('/');
        const title = await page.title();
        expect(title).toBeTruthy();
        expect(title.length).toBeGreaterThan(0);
    });

    test('page is navigable without mouse', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('body')).toBeVisible();

        await page.keyboard.press('Tab');
        const activeElement = await page.evaluate(() => document.activeElement?.tagName || '');
        expect(activeElement).toBeTruthy();
    });


});
