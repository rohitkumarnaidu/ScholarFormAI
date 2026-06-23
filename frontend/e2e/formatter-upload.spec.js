// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

test.describe('Formatter Upload', () => {
    test('upload page loads with manuscript upload heading', async ({ page }) => {
        await page.goto('/upload', { waitUntil: 'domcontentloaded', timeout: 15000 });

        const heading = page.getByRole('heading', { name: /Upload Manuscript/i });
        await expect(heading).toBeVisible();

        const fileInput = page.locator('input[type="file"]');
        await expect(fileInput).toBeAttached();

        const browseButton = page.getByRole('button', { name: /Browse Files/i });
        await expect(browseButton).toBeVisible();
    });

    test('upload page has template selector', async ({ page }) => {
        await page.goto('/upload', { waitUntil: 'domcontentloaded', timeout: 15000 });

        const templateSelect = page.locator('select, [role="combobox"]').first();
        await expect(templateSelect).toBeVisible();
    });

    test('upload page shows format options', async ({ page }) => {
        await page.goto('/upload', { waitUntil: 'domcontentloaded', timeout: 15000 });

        const pageNumbersCheckbox = page.getByText(/page numbers/i);
        await expect(pageNumbersCheckbox).toBeVisible();

        const tocCheckbox = page.getByText(/table of contents|generate toc/i);
        await expect(tocCheckbox).toBeVisible();
    });

    test('upload page has accept attribute restricting to docx', async ({ page }) => {
        await page.goto('/upload', { waitUntil: 'domcontentloaded', timeout: 15000 });

        const fileInput = page.locator('input[type="file"]');
        const acceptAttr = await fileInput.getAttribute('accept');
        expect(acceptAttr).toBeTruthy();
        if (acceptAttr) {
            expect(acceptAttr.toLowerCase()).toContain('.docx');
        }
    });
});
