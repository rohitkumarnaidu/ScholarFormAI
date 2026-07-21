// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

// @ts-check
const { test, expect } = require('@playwright/test');

const LCP_THRESHOLD_MS = 2500;
const LCP_UPLOAD_THRESHOLD_MS = 3000;
const CLS_THRESHOLD = 0.1;
const INP_THRESHOLD_MS = 200;
const FCP_THRESHOLD_MS = 1000;

/**
 * Collect performance metrics from the browser.
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<{lcp: number, cls: number, fcp: number, fid: number}>}
 */
async function collectWebVitals(page) {
    const metrics = await page.evaluate(() => {
        return new Promise((resolve) => {
            const results = { lcp: 0, cls: 0, fcp: 0, fid: 0 };

            // LCP observer
            const lcpObserver = new PerformanceObserver((list) => {
                const entries = list.getEntries();
                if (entries.length > 0) {
                    results.lcp = entries[entries.length - 1].startTime;
                }
            });
            lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true });

            // CLS observer
            let clsValue = 0;
            const clsObserver = new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    const shiftEntry = /** @type {any} */(entry);
                    if (!shiftEntry.hadRecentInput) {
                        clsValue += shiftEntry.value;
                    }
                }
                results.cls = clsValue;
            });
            clsObserver.observe({ type: 'layout-shift', buffered: true });

            // FCP observer
            const fcpObserver = new PerformanceObserver((list) => {
                const entries = list.getEntries();
                if (entries.length > 0) {
                    results.fcp = entries[0].startTime;
                }
            });
            fcpObserver.observe({ type: 'paint', buffered: true });

            // FID observer
            const fidObserver = new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    const fidEntry = /** @type {any} */(entry);
                    results.fid = fidEntry.processingStart - fidEntry.startTime;
                    break;
                }
            });
            fidObserver.observe({ type: 'first-input', buffered: true });

            // Wait and return results
            setTimeout(() => resolve(results), 3000);
        });
    });

    return metrics;
}

test.describe('Core Web Vitals', () => {

    test('LCP under 2.5s on landing page', async ({ page }) => {
        await page.goto('/', { waitUntil: 'domcontentloaded' });

        // Wait for the page to be fully interactive
        await page.waitForLoadState('networkidle');

        const vitals = await collectWebVitals(page);
        console.log(`[CWV] Landing LCP: ${vitals.lcp.toFixed(1)}ms`);

        expect(vitals.lcp).toBeLessThan(LCP_THRESHOLD_MS);
    });

    test('LCP under 3s on upload page', async ({ page }) => {
        await page.goto('/upload', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        const vitals = await collectWebVitals(page);
        console.log(`[CWV] Upload LCP: ${vitals.lcp.toFixed(1)}ms`);

        expect(vitals.lcp).toBeLessThan(LCP_UPLOAD_THRESHOLD_MS);
    });

    test('CLS under 0.1 on results page', async ({ page }) => {
        // Navigate to results page with a mock job
        await page.addInitScript(() => {
            sessionStorage.setItem('scholarform_currentJob', JSON.stringify({
                id: 'cwv-test-job',
                status: 'completed',
                originalFileName: 'paper.docx',
                processedText: 'Formatted manuscript content for CLS measurement.',
                result: {
                    structured_data: { sections: { BODY: 'Test content.' } },
                    metrics: { overall_score: 90 },
                    errors: [],
                    warnings: [],
                },
            }));
        });

        await page.goto('/results?jobId=cwv-test-job', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        const vitals = await collectWebVitals(page);
        console.log(`[CWV] Results CLS: ${vitals.cls.toFixed(4)}`);

        expect(vitals.cls).toBeLessThan(CLS_THRESHOLD);
    });

    test('INP under 200ms on agent workspace', async ({ page }) => {
        await page.addInitScript(() => {
            sessionStorage.setItem('scholarform_currentJob', JSON.stringify({
                id: 'cwv-agent-job',
                status: 'processing',
                originalFileName: 'draft.docx',
                processedText: '',
                result: null,
            }));
        });

        await page.goto('/agent?jobId=cwv-agent-job', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        // Simulate user interactions to trigger INP measurement
        const chatInput = page.locator('textarea, input[type="text"], [contenteditable="true"]').first();
        await chatInput.waitFor({ state: 'visible', timeout: 10000 });

        // Type and interact to measure INP
        const startTime = Date.now();
        await chatInput.click();
        await chatInput.fill('Test message for INP measurement');
        await page.keyboard.press('Enter');
        const interactionTime = Date.now() - startTime;

        console.log(`[CWV] Agent INP: ${interactionTime}ms`);
        expect(interactionTime).toBeLessThan(INP_THRESHOLD_MS);
    });

    test('First paint under 1s', async ({ page }) => {
        // Use performance timing API for first paint
        const startTime = Date.now();

        await page.goto('/', { waitUntil: 'domcontentloaded' });

        const fpTime = Date.now() - startTime;

        // Also get Paint Timing API
        const paintEntries = await page.evaluate(() => {
            return performance.getEntriesByType('paint').map((e) => ({
                name: e.name,
                startTime: e.startTime,
            }));
        });

        const firstPaint = paintEntries.find((e) => e.name === 'first-paint');
        const fpFromApi = firstPaint ? firstPaint.startTime : null;

        console.log(`[CWV] First Paint: ${fpFromApi?.toFixed(1) ?? fpTime}ms (API: ${fpFromApi ?? 'N/A'}, wall: ${fpTime}ms)`);

        // Use whichever measurement is available
        const measuredFp = fpFromApi ?? fpTime;
        expect(measuredFp).toBeLessThan(FCP_THRESHOLD_MS);
    });

});
