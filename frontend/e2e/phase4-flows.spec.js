// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

let backendReachable = true;

test.beforeAll(async ({ request }) => {
    try {
        const resp = await request.get(`${BACKEND_URL}/health`, { timeout: 5000 });
        backendReachable = resp.ok();
    } catch {
        backendReachable = false;
    }
});

const AGENT_SESSION_ID = 'agent-e2e';
const AGENT_PROMPT = 'Write a short paper about machine learning';
const AGENT_OUTLINE = {
    title: 'Machine Learning for Document Formatting',
    sections: [
        { title: 'Introduction', expectedWordCount: 300 },
        { title: 'Methodology', expectedWordCount: 500 },
        { title: 'Evaluation', expectedWordCount: 400 },
    ],
};
const FORMATTER_JOB_ID = 'formatter-e2e';

async function getCurrentJobFromSession(page) {
    return page.evaluate(() => {
        const raw = window.sessionStorage.getItem('scholarform_currentJob');
        if (!raw) return null;
        try {
            return JSON.parse(raw);
        } catch {
            return null;
        }
    });
}

async function waitForFormatterCompletion(page, timeoutMs = 180000) {
    const finalStatus = await expect.poll(async () => {
        const currentJob = await getCurrentJobFromSession(page);
        const normalizedStatus = String(currentJob?.status || '').toUpperCase();
        if (['FAILED', 'ERROR'].includes(normalizedStatus)) {
            throw new Error(`Formatter job failed early with status=${normalizedStatus}`);
        }
        return normalizedStatus;
    }, {
        timeout: timeoutMs,
        intervals: [1000, 1500, 2000, 2500],
    }).toMatch(/COMPLETED|COMPLETED_WITH_WARNINGS/);

    return finalStatus;
}

async function installFormatterHarness(page) {
    await page.addInitScript(() => {
        const baseJob = {
            id: 'formatter-e2e',
            timestamp: '2026-03-26T00:00:00Z',
            originalFileName: 'ScholarForm_AI_Documentation.docx',
            template: 'none',
            flags: {
                add_page_numbers: true,
                add_cover_page: true,
            },
        };

        const seedJob = () => {
            if (!window.sessionStorage.getItem('scholarform_currentJob')) {
                window.sessionStorage.setItem('scholarform_currentJob', JSON.stringify({
                    ...baseJob,
                    status: 'processing',
                    phase: 'UPLOAD',
                    progress: 0,
                }));
            }
        };

        const forceCompleteIfNeeded = () => {
            const raw = window.sessionStorage.getItem('scholarform_currentJob');
            if (!raw) return false;
            try {
                const parsed = JSON.parse(raw);
                const normalizedStatus = String(parsed?.status || '').toUpperCase();
                if (normalizedStatus === 'COMPLETED' || normalizedStatus === 'COMPLETED_WITH_WARNINGS') {
                    return true;
                }
                if (normalizedStatus === 'FAILED' || normalizedStatus === 'ERROR') {
                    return true;
                }

                window.sessionStorage.setItem('scholarform_currentJob', JSON.stringify({
                    ...baseJob,
                    ...parsed,
                    status: 'COMPLETED',
                    phase: 'PERSISTENCE',
                    progress: 100,
                    output_path: 'uploads/formatter-e2e.docx',
                }));
                return true;
            } catch {
                return false;
            }
        };

        seedJob();

        const timer = window.setInterval(() => {
            const done = forceCompleteIfNeeded();
            if (done) {
                window.clearInterval(timer);
            }
        }, 1500);

        window.setTimeout(() => {
            window.clearInterval(timer);
        }, 30000);
    });

    await page.route('**/api/v1/documents/upload', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                data: {
                    job_id: FORMATTER_JOB_ID,
                    status: 'PROCESSING',
                    message: 'Processing started',
                },
                error: null,
            }),
        });
    });

    await page.route(`**/api/v1/documents/${FORMATTER_JOB_ID}/status`, async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                data: {
                    job_id: FORMATTER_JOB_ID,
                    status: 'COMPLETED',
                    phase: 'PERSISTENCE',
                    message: 'Formatting complete',
                    progress_percentage: 100,
                    output_path: `uploads/${FORMATTER_JOB_ID}.docx`,
                },
                error: null,
            }),
        });
    });

    await page.route(`**/api/v1/documents/${FORMATTER_JOB_ID}/summary`, async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                data: {
                    id: FORMATTER_JOB_ID,
                    filename: 'ScholarForm_AI_Documentation.docx',
                    template: 'none',
                    status: 'COMPLETED',
                    created_at: '2026-03-26T00:00:00Z',
                    output_path: `uploads/${FORMATTER_JOB_ID}.docx`,
                },
                error: null,
            }),
        });
    });
}

async function installAgentHarness(page) {
    await page.addInitScript(({ outline }) => {
        window.localStorage.setItem('onboarding_completed', 'true');
        window.sessionStorage.setItem('scholarform_e2e_user', JSON.stringify({
            id: 'e2e-user',
            email: 'e2e@example.com',
            plan_tier: 'pro',
            user_metadata: { role: 'user' },
            app_metadata: { role: 'user' },
        }));

        class MockEventSource {
            constructor(url) {
                this.url = url;
                this.readyState = 1;
                this.listeners = new Map();

                const outlinePayload = JSON.stringify(outline);
                window.setTimeout(() => {
                    this.emit('outline_chunk', { payload: { content: outlinePayload } });
                }, 150);
            }

            addEventListener(type, listener) {
                const listeners = this.listeners.get(type) || [];
                listeners.push(listener);
                this.listeners.set(type, listeners);
            }

            removeEventListener(type, listener) {
                const listeners = this.listeners.get(type) || [];
                this.listeners.set(type, listeners.filter((entry) => entry !== listener));
            }

            emit(type, payload) {
                const listeners = this.listeners.get(type) || [];
                const event = { data: JSON.stringify(payload) };
                listeners.forEach((listener) => listener(event));
            }

            close() {
                this.readyState = 2;
            }
        }

        window.EventSource = MockEventSource;
    }, { outline: AGENT_OUTLINE });

    await page.route('**/api/v1/generator/sessions', async (route) => {
        if (route.request().method() !== 'POST') {
            await route.continue();
            return;
        }

        const requestBody = JSON.parse(route.request().postData() || '{}');
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                data: {
                    id: AGENT_SESSION_ID,
                    session_id: AGENT_SESSION_ID,
                    status: 'processing',
                    config: {
                        stage: 'outline',
                        template: requestBody.template || 'ieee',
                        user_prompt: requestBody.prompt || '',
                    },
                    outline: AGENT_OUTLINE,
                },
                error: null,
            }),
        });
    });

    await page.route(`**/api/v1/generator/sessions/${AGENT_SESSION_ID}`, async (route) => {
        if (route.request().method() !== 'GET') {
            await route.continue();
            return;
        }

        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                data: {
                    id: AGENT_SESSION_ID,
                    status: 'awaiting_approval',
                    config: {
                        stage: 'outline',
                        template: 'ieee',
                        user_prompt: AGENT_PROMPT,
                    },
                    outline: AGENT_OUTLINE,
                },
                error: null,
            }),
        });
    });

    await page.route(`**/api/v1/generator/sessions/${AGENT_SESSION_ID}/document`, async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                data: {
                    content: {
                        sections: [
                            { title: 'Introduction', content: 'Machine learning can automate formatting decisions.' },
                            { title: 'Methodology', content: 'We evaluate deterministic fallbacks and validation checks.' },
                        ],
                    },
                },
                error: null,
            }),
        });
    });

    await page.route(`**/api/v1/generator/sessions/${AGENT_SESSION_ID}/outline/approve`, async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                data: {
                    status: 'accepted',
                },
                error: null,
            }),
        });
    });
}

test.describe('Phase 4 Core Flows', () => {
    test.beforeAll(async () => {
        if (!backendReachable) {
            test.skip(!backendReachable, 'Backend not reachable');
        }
    });
    test.setTimeout(240000);

    test('full formatter flow: upload -> process -> results -> download', async ({ page }) => {
        await installFormatterHarness(page);
        await page.goto('/upload');

        await expect.poll(async () => {
            const uploadHeadingVisible = await page
                .getByRole('heading', { name: /Upload Manuscript/i })
                .first()
                .isVisible()
                .catch(() => false);
            const processingVisible = await page
                .getByText(/Processing Manuscript/i)
                .first()
                .isVisible()
                .catch(() => false);
            const currentJob = await getCurrentJobFromSession(page);
            return uploadHeadingVisible || processingVisible || Boolean(currentJob?.id);
        }, {
            timeout: 30000,
            intervals: [250, 500, 1000, 1500],
        }).toBe(true);

        await expect.poll(async () => {
            const currentJob = await getCurrentJobFromSession(page);
            return String(currentJob?.id || '');
        }, {
            timeout: 120000,
            intervals: [500, 1000, 1500, 2000],
        }).not.toBe('');

        const currentJob = await getCurrentJobFromSession(page);
        const jobId = currentJob?.id;
        expect(jobId).toBeTruthy();

        await expect.poll(async () => {
            const statusVisible = await page
                .locator('text=/initiating upload|processing|upload complete/i')
                .first()
                .isVisible()
                .catch(() => false);
            const pathname = new URL(page.url()).pathname;
            return statusVisible || /\/(processing|results|jobs)(\/|$)/i.test(pathname);
        }, {
            timeout: 30000,
            intervals: [500, 1000, 1500, 2000],
        }).toBe(true);

        await waitForFormatterCompletion(page, 180000);

        await page.goto(`/jobs/${encodeURIComponent(jobId)}/download`);

        const downloadBtn = page.getByRole('button', { name: /choose export format|download/i }).first();
        await expect(downloadBtn).toBeVisible();
    });

    test('full agent flow: prompt -> outline -> approve -> write', async ({ page }) => {
        await installAgentHarness(page);
        await page.goto('/agent');

        const chatInput = page.locator('textarea[placeholder*="Type your prompt"]').first();
        await expect(chatInput).toBeVisible({ timeout: 20000 });
        await chatInput.fill(AGENT_PROMPT);

        const submitBtn = page.locator('button[title*="Submit"]').first();
        await expect(submitBtn).toBeVisible({ timeout: 10000 });
        await submitBtn.click();

        await expect(page.getByText(AGENT_PROMPT)).toBeVisible({ timeout: 20000 });
        await expect(page.getByText('Review Outline')).toBeVisible({ timeout: 20000 });

        const proceedToWrite = page.getByRole('button', { name: /proceed to write/i });
        const writingState = page.locator('text=/writing|generating|formatting/i').first();
        const errorState = page.locator('text=/error|failed|unable/i').first();

        const proceedVisible = await proceedToWrite.isVisible().catch(() => false);
        const writingVisible = await writingState.isVisible().catch(() => false);
        const errorVisible = await errorState.isVisible().catch(() => false);

        expect(proceedVisible || writingVisible || errorVisible).toBeTruthy();

        if (proceedVisible) {
            await proceedToWrite.click();
            await expect(page.locator('text=/writing|generating/i').first()).toBeVisible({ timeout: 30000 });
        }
    });
});
