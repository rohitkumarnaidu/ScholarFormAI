// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Upload -> Processing -> Download Journey', () => {
    test('allows guest to upload, process, and see results', async ({ page }) => {
        const jobId = 'upload-journey-e2e';

        await page.route('**/api/v1/documents/upload', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    data: {
                        job_id: jobId,
                        status: 'PROCESSING',
                        message: 'Processing started',
                    },
                    error: null,
                }),
            });
        });

        await page.route('**/api/v1/documents/*/status*', async (route) => {
            const requestUrl = new URL(route.request().url());
            const pathParts = requestUrl.pathname.split('/');
            const requestedJobId = decodeURIComponent(pathParts[pathParts.length - 2] || jobId);

            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    data: {
                        job_id: requestedJobId,
                        status: 'COMPLETED',
                        phase: 'PERSISTENCE',
                        message: 'Formatting complete',
                        progress_percentage: 100,
                        output_path: `uploads/${requestedJobId}.docx`,
                    },
                    error: null,
                }),
            });
        });

        await page.route('**/api/v1/documents/*/summary*', async (route) => {
            const requestUrl = new URL(route.request().url());
            const pathParts = requestUrl.pathname.split('/');
            const requestedJobId = decodeURIComponent(pathParts[pathParts.length - 2] || jobId);

            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    data: {
                        id: requestedJobId,
                        filename: 'sample.docx',
                        template: 'none',
                        status: 'COMPLETED',
                        created_at: '2026-03-26T00:00:00Z',
                        output_path: `uploads/${requestedJobId}.docx`,
                    },
                    error: null,
                }),
            });
        });

        await page.addInitScript(({ id }) => {
            window.sessionStorage.setItem('scholarform_currentJob', JSON.stringify({
                id,
                timestamp: '2026-03-26T00:00:00Z',
                status: 'COMPLETED',
                phase: 'PERSISTENCE',
                originalFileName: 'sample.docx',
                template: 'none',
                flags: {
                    add_page_numbers: true,
                    add_cover_page: true,
                },
                progress: 100,
                output_path: `uploads/${id}.docx`,
            }));
        }, { id: jobId });

        await page.goto('/upload');

        await expect(page).toHaveURL(/.*\/upload/);

        const sampleFilePath = path.join(__dirname, 'test-files', 'sample.docx');
        const fileInput = page.locator('input[type="file"]').first();
        await expect(fileInput).toBeAttached();
        await fileInput.setInputFiles(sampleFilePath);

        await page.getByRole('button', { name: /process document|format document/i }).click();

        await expect(page.getByText(/initiating upload|processing manuscript|upload complete/i).first()).toBeVisible({ timeout: 15000 });

        await page.goto('/download');
        await expect(page).toHaveURL(/.*\/download/);
        await expect(page.getByRole('heading', { name: /Formatting Complete/i })).toBeVisible();

        await page.getByRole('button', { name: /Choose Export Format/i }).click();

        const exportDialog = page.getByTestId('export-dialog');
        await expect(exportDialog).toBeVisible();

        await expect(page.getByText(/Select a format and download your manuscript/i)).toBeVisible();
    });
});
