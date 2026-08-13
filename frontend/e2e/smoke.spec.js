// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

test.describe('ScholarForm AI - Core Routes Smoke Tests', () => {

    test.beforeEach(async ({ page }) => {
        page.on('console', msg => console.log(`BROWSER: ${msg.type()}: ${msg.text()}`));
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
        
        await page.context().addCookies([{
            name: 'playwright-bypass-auth',
            value: 'true',
            url: 'http://localhost:3005',
        }]);
    });

    test('Formatter - Edit Page (/edit) should load correctly', async ({ page }) => {
        await page.goto('/edit?jobId=test-123');
        await expect(page).toHaveTitle(/AMF/i);
        await page.waitForLoadState('domcontentloaded');

        const editor = page.locator('.ProseMirror, .tiptap, [contenteditable="true"]').first();
        await expect(editor).toBeVisible({ timeout: 15000 });

        const liveReport = page.getByText(/Live Report/i);
        await expect(liveReport).toBeVisible();
    });

    test('Formatter - Results Page (/results) should load correctly', async ({ page }) => {
        await page.goto('/results?jobId=test-123');
        await expect(page).toHaveTitle(/AMF/i);
        await page.waitForLoadState('domcontentloaded');

        const bodyContent = await page.textContent('body');
        expect(bodyContent).toBeTruthy();

        const downloadButton = page.getByRole('button', { name: /Verify & Download/i });
        try {
            await expect(downloadButton).toBeVisible({ timeout: 5000 });
        } catch (e) {
            console.error('DOM state on failure (Results):', await page.innerHTML('body'));
            throw e;
        }
    });

    test('Formatter - Live Preview Page (/live) should load correctly', async ({ page }) => {
        await page.goto('/live?jobId=test-123');
        await expect(page).toHaveTitle(/AMF/i);
        await page.waitForLoadState('domcontentloaded');

        const bodyContent = await page.textContent('body');
        expect(bodyContent).toBeTruthy();

        const editorArea = page.locator('.ProseMirror, .tiptap, [contenteditable="true"], textarea').first();
        await expect(editorArea).toBeVisible({ timeout: 10000 });
    });

    test('Generator - AI Agent Page (/agent) should load correctly', async ({ page }) => {
        await page.goto('/agent?jobId=test-123');
        await expect(page).toHaveTitle(/AMF/i);
        await page.waitForLoadState('domcontentloaded');

        const bodyContent = await page.textContent('body');
        expect(bodyContent).toBeTruthy();

        const chatInput = page.getByPlaceholder(/Type your prompt here/i);
        try {
            await expect(chatInput).toBeVisible({ timeout: 5000 });
        } catch (e) {
            console.error('DOM state on failure (Agent):', await page.innerHTML('body'));
            throw e;
        }
    });
});
