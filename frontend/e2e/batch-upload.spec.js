// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const hasSupabaseUrl = Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL);

test.describe('Batch Upload', () => {
    test.describe('Upload Flow', () => {
        test('shows batch upload page with file input and template selector', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/batch-upload');
            await expect(page.locator('body')).toBeVisible({ timeout: 15000 });

            const heading = page.getByRole('heading', { name: /Batch Upload/i });
            await expect(heading).toBeVisible();

            const templateSelect = page.locator('select').first();
            await expect(templateSelect).toBeVisible();

            const dropZone = page.getByRole('button', { name: /Upload multiple files/i });
            await expect(dropZone).toBeVisible();
        });

        test('displays uploaded files in the file list', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/batch-upload');

            const sampleFilePath = path.join(__dirname, 'test-files', 'sample.docx');
            const fileInput = page.locator('input[type="file"]');
            await expect(fileInput).toBeAttached({ timeout: 15000 });

            await fileInput.setInputFiles([sampleFilePath, sampleFilePath]);
            const fileEntries = page.locator('text=/sample.docx/i');
            await expect(fileEntries.first()).toBeVisible();
            const fileCount = await fileEntries.count();
            expect(fileCount).toBeGreaterThanOrEqual(1);
        });

        test('shows process all button with file count', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/batch-upload');

            const sampleFilePath = path.join(__dirname, 'test-files', 'sample.docx');
            const fileInput = page.locator('input[type="file"]');
            await expect(fileInput).toBeAttached({ timeout: 15000 });
            await fileInput.setInputFiles([sampleFilePath]);

            const processBtn = page.getByRole('button', { name: /Process All/i });
            await expect(processBtn).toBeVisible();
        });
    });

    test.describe('Validation', () => {
        test('shows upgrade modal for non-pro users', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/batch-upload');
            await expect(page.locator('body')).toBeVisible({ timeout: 15000 });

            const upgradeTitle = page.getByText(/Upgrade to Pro/i);
            const upgradeFeature = page.getByText(/Batch Upload is a Pro Feature/i);
            const upgradeVisible = (await upgradeTitle.count() > 0) || (await upgradeFeature.count() > 0);
            expect(upgradeVisible).toBeTruthy();
        });

        test('accept attribute restricts to manuscript file types', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/batch-upload');

            const fileInput = page.locator('input[type="file"]');
            const acceptAttr = await fileInput.getAttribute('accept');
            expect(acceptAttr).toBeTruthy();
            if (acceptAttr) {
                expect(acceptAttr.toLowerCase()).toContain('.docx');
                expect(acceptAttr.toLowerCase()).toContain('.pdf');
            }
        });
    });
});
