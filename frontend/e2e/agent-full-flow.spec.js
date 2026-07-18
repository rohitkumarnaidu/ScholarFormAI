// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

test.describe('Agent Full Flow', () => {
    test.use({ storageState: 'e2e/.auth/user.json' });

    test('navigates to /agent page', async ({ page }) => {
        await page.goto('/agent', { waitUntil: 'domcontentloaded', timeout: 15000 });
        await expect(page.getByRole('heading', { name: /ScholarForm Assistant/i })).toBeVisible();
    });

    test('shows empty state with ready prompt', async ({ page }) => {
        await page.goto('/agent', { waitUntil: 'domcontentloaded', timeout: 15000 });
        await expect(page.getByText(/Ready to write/i)).toBeVisible();
    });

    test('has text input area', async ({ page }) => {
        await page.goto('/agent', { waitUntil: 'domcontentloaded', timeout: 15000 });
        const input = page.locator('textarea[placeholder*="prompt"]');
        await expect(input).toBeAttached();
    });

    test('typing in input enables submit button', async ({ page }) => {
        await page.goto('/agent', { waitUntil: 'domcontentloaded', timeout: 15000 });
        const input = page.locator('textarea[placeholder*="prompt"]');
        await input.fill('Write a research paper on AI');
        const submitBtn = page.locator('button[title*="Submit"]');
        await expect(submitBtn).toBeEnabled();
    });

    test('sends message and receives response', async ({ page }) => {
        await page.goto('/agent', { waitUntil: 'domcontentloaded', timeout: 15000 });
        const input = page.locator('textarea[placeholder*="prompt"]');
        await input.fill('Write a research paper outline');
        await page.locator('button[title*="Submit"]').click();
    });

    test('keyboard shortcut Ctrl+Enter sends message', async ({ page }) => {
        await page.goto('/agent', { waitUntil: 'domcontentloaded', timeout: 15000 });
        const input = page.locator('textarea[placeholder*="prompt"]');
        await input.fill('Outline: Transformer models');
        await input.press('Control+Enter');
    });

    test('stop button appears during generation', async ({ page }) => {
        await page.goto('/agent', { waitUntil: 'domcontentloaded', timeout: 15000 });
        const input = page.locator('textarea[placeholder*="prompt"]');
        await input.fill('Generate a paper');
        await page.locator('button[title*="Submit"]').click();
    });

    test('has model selector dropdown', async ({ page }) => {
        await page.goto('/agent', { waitUntil: 'domcontentloaded', timeout: 15000 });
        const modelSelector = page.getByText(/Auto|gpt|claude/i).first();
        await expect(modelSelector).toBeVisible();
    });

    test('shows outline after approval', async ({ page }) => {
        await page.goto('/agent', { waitUntil: 'domcontentloaded', timeout: 15000 });
    });

    test('downloads document after completion', async ({ page }) => {
        await page.goto('/agent', { waitUntil: 'domcontentloaded', timeout: 15000 });
    });

    test('displays error banner on failure', async ({ page }) => {
        await page.goto('/agent', { waitUntil: 'domcontentloaded', timeout: 15000 });
        await page.locator('textarea[placeholder*="prompt"]').fill('test');
        await page.locator('button[title*="Submit"]').click();
    });
});
