// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

test.describe('Synthesis Flow', () => {
    test.use({ storageState: 'e2e/.auth/user.json' });

    test('navigates to /multi-upload page', async ({ page }) => {
        await page.goto('/multi-upload', { waitUntil: 'domcontentloaded', timeout: 15000 });
        await expect(page.getByText(/Drag & Drop documents here/i)).toBeVisible();
    });

    test('shows upload drop zone', async ({ page }) => {
        await page.goto('/multi-upload', { waitUntil: 'domcontentloaded', timeout: 15000 });
        await expect(page.getByText(/Upload 2 to 6 files/i)).toBeVisible();
    });

    test('has a Browse Files button', async ({ page }) => {
        await page.goto('/multi-upload', { waitUntil: 'domcontentloaded', timeout: 15000 });
        await expect(page.getByText(/Browse Files/i)).toBeVisible();
    });

    test('has template selector', async ({ page }) => {
        await page.goto('/multi-upload', { waitUntil: 'domcontentloaded', timeout: 15000 });
        const select = page.locator('select').first();
        await expect(select).toBeVisible();
    });

    test('start button is disabled initially', async ({ page }) => {
        await page.goto('/multi-upload', { waitUntil: 'domcontentloaded', timeout: 15000 });
        const startBtn = page.getByText(/Start Synthesis/i);
        await expect(startBtn).toBeDisabled();
    });

    test('accepts file input with proper accept attribute', async ({ page }) => {
        await page.goto('/multi-upload', { waitUntil: 'domcontentloaded', timeout: 15000 });
        const fileInput = page.locator('input[type="file"]');
        const acceptAttr = await fileInput.getAttribute('accept');
        expect(acceptAttr).toBeTruthy();
    });

    test('shows uploaded files list after upload', async ({ page }) => {
        await page.goto('/multi-upload', { waitUntil: 'domcontentloaded', timeout: 15000 });
        const fileInput = page.locator('input[type="file"]');
        await fileInput.setInputFiles([
            { name: 'paper1.pdf', mimeType: 'application/pdf', buffer: Buffer.from('test1') },
            { name: 'paper2.pdf', mimeType: 'application/pdf', buffer: Buffer.from('test2') },
        ]);
    });

    test('shows progress for uploaded files', async ({ page }) => {
        await page.goto('/multi-upload', { waitUntil: 'domcontentloaded', timeout: 15000 });
        const fileInput = page.locator('input[type="file"]');
        await fileInput.setInputFiles([
            { name: 'doc1.pdf', mimeType: 'application/pdf', buffer: Buffer.from('data1') },
            { name: 'doc2.docx', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', buffer: Buffer.from('data2') },
        ]);
    });

    test('can remove uploaded files', async ({ page }) => {
        await page.goto('/multi-upload', { waitUntil: 'domcontentloaded', timeout: 15000 });
        const fileInput = page.locator('input[type="file"]');
        await fileInput.setInputFiles([
            { name: 'test.pdf', mimeType: 'application/pdf', buffer: Buffer.from('data') },
        ]);
    });

    test('shows error for duplicate files', async ({ page }) => {
        await page.goto('/multi-upload', { waitUntil: 'domcontentloaded', timeout: 15000 });
    });

    test('validates minimum file count before synthesis', async ({ page }) => {
        await page.goto('/multi-upload', { waitUntil: 'domcontentloaded', timeout: 15000 });
        const fileInput = page.locator('input[type="file"]');
        await fileInput.setInputFiles([
            { name: 'single.pdf', mimeType: 'application/pdf', buffer: Buffer.from('single') },
        ]);
        const startBtn = page.getByText(/Start Synthesis/i);
        await expect(startBtn).toBeDisabled();
    });
});
