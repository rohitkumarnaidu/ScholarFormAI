// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

test.describe('ScholarForm AI - Core Routes Smoke Tests', () => {

    test.beforeEach(async ({ page }) => {
        await page.addInitScript(() => {
            sessionStorage.setItem('scholarform_currentJob', JSON.stringify({
                id: 'test-123',
                status: 'completed',
                originalFileName: 'test.docx',
                processedText: 'This is a test document.',
                result: {
                    structured_data: {
                        sections: { BODY: 'This is a test document.' }
                    },
                    metrics: { overall_score: 95 },
                    errors: [],
                    warnings: []
                }
            }));
        });
    });

    test('Formatter - Edit Page (/edit) should load correctly', async ({ page }) => {
        await page.goto('/edit?jobId=test-123');
        await expect(page).toHaveTitle(/ScholarForm/i);
        await page.waitForLoadState('domcontentloaded');

        const editor = page.locator('.ProseMirror, .tiptap, [contenteditable="true"]').first();
        await expect(editor).toBeVisible({ timeout: 15000 });

        const qualityScore = page.getByText(/quality|score|95/i);
        await expect(qualityScore).toBeVisible();
    });

    test('Formatter - Results Page (/results) should load correctly', async ({ page }) => {
        await page.goto('/results?jobId=test-123');
        await expect(page).toHaveTitle(/ScholarForm/i);
        await page.waitForLoadState('domcontentloaded');

        const bodyContent = await page.textContent('body');
        expect(bodyContent).toBeTruthy();

        const downloadButton = page.getByRole('button', { name: /download|export/i });
        await expect(downloadButton).toBeVisible();
    });

    test('Formatter - Live Preview Page (/live) should load correctly', async ({ page }) => {
        await page.goto('/live?jobId=test-123');
        await expect(page).toHaveTitle(/ScholarForm/i);
        await page.waitForLoadState('domcontentloaded');

        const bodyContent = await page.textContent('body');
        expect(bodyContent).toBeTruthy();

        const editorArea = page.locator('.ProseMirror, .tiptap, [contenteditable="true"], textarea').first();
        await expect(editorArea).toBeVisible({ timeout: 10000 });
    });

    test('Generator - AI Agent Page (/agent) should load correctly', async ({ page }) => {
        await page.goto('/agent?jobId=test-123');
        await expect(page).toHaveTitle(/ScholarForm/i);
        await page.waitForLoadState('domcontentloaded');

        const bodyContent = await page.textContent('body');
        expect(bodyContent).toBeTruthy();

        const chatInput = page.locator('textarea, input[type="text"], [contenteditable="true"]').first();
        await expect(chatInput).toBeVisible({ timeout: 10000 });
    });
});
