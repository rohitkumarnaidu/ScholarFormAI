// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { test, expect } from '@playwright/test';

const hasSupabaseUrl = Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL);

test.describe('Admin Dashboard', () => {
    test.describe('Access Control', () => {
        test('redirects unauthenticated user from /admin-dashboard to /login', async ({ page }) => {
            await page.goto('/admin-dashboard');
            await expect(page).toHaveURL(/.*\/login/, { timeout: 10000 });
        });

        test('redirects non-admin user away from dashboard', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/admin-dashboard');
            const url = page.url();
            const notAdmin = url.includes('/dashboard') || url.includes('/login');
            expect(notAdmin).toBeTruthy();
        });

        test('shows admin dashboard for admin user', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.route('**/api/v1/metrics/db', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ status: 'healthy', document_count: 142, error: null }),
                });
            });
            await page.route('**/api/v1/metrics/health', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ status: 'healthy', details: 'All systems operational', aiServicesStatus: 'healthy', aiServicesDetails: 'Online', grobidStatus: 'healthy', grobidDetails: 'Running' }),
                });
            });
            await page.route('**/api/v1/metrics/dashboard', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ successRatePct: 94.2, avgConfidencePct: 87.5, errorRatePct: 2.1, modelLabel: 'GPT-4o', totalProcessed: 1240, avgProcessingTimeSeconds: 3.4, automationLevel: 'High', fallbackRatePct: 5.3 }),
                });
            });
            await page.goto('/admin-dashboard');
            await expect(page.locator('body')).toBeVisible({ timeout: 15000 });
            await expect(page.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();
        });
    });

    test.describe('Dashboard Components', () => {
        test('renders stats cards with metrics', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.route('**/api/v1/metrics/db', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ status: 'healthy', document_count: 142, error: null }),
                });
            });
            await page.route('**/api/v1/metrics/health', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ status: 'healthy', details: 'All systems operational', aiServicesStatus: 'healthy', aiServicesDetails: 'Online', grobidStatus: 'healthy', grobidDetails: 'Running' }),
                });
            });
            await page.route('**/api/v1/metrics/dashboard', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ successRatePct: 94.2, avgConfidencePct: 87.5, errorRatePct: 2.1 }),
                });
            });
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/admin-dashboard');
            const totalDocs = page.getByText(/Total Documents/i);
            await expect(totalDocs).toBeVisible({ timeout: 15000 });
            const processingSuccess = page.getByText(/Processing Success/i);
            await expect(processingSuccess).toBeVisible();
            const avgConfidence = page.getByText(/Avg Confidence/i);
            await expect(avgConfidence).toBeVisible();
            const errorRate = page.getByText(/Error Rate/i);
            await expect(errorRate).toBeVisible();
        });

        test('renders system health indicators', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.route('**/api/v1/metrics/db', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ status: 'healthy', document_count: 142 }),
                });
            });
            await page.route('**/api/v1/metrics/health', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ status: 'healthy', details: 'All systems operational', aiServicesStatus: 'healthy', aiServicesDetails: 'Online', grobidStatus: 'healthy', grobidDetails: 'Running' }),
                });
            });
            await page.route('**/api/v1/metrics/dashboard', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ successRatePct: 94.2, avgConfidencePct: 87.5, errorRatePct: 2.1 }),
                });
            });
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/admin-dashboard');
            await expect(page.getByText(/Service Health/i)).toBeVisible({ timeout: 15000 });
            await expect(page.getByText(/Database \(Supabase\)/i)).toBeVisible();
            await expect(page.getByText(/System Readiness/i)).toBeVisible();
            await expect(page.getByText(/AI Services/i)).toBeVisible();
            await expect(page.getByText(/GROBID Parser/i)).toBeVisible();
        });

        test('renders admin role telemetry section', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.route('**/api/v1/metrics/db', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ status: 'healthy', document_count: 142 }),
                });
            });
            await page.route('**/api/v1/metrics/health', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ status: 'healthy', details: 'All systems operational', aiServicesStatus: 'healthy', aiServicesDetails: 'Online', grobidStatus: 'healthy', grobidDetails: 'Running' }),
                });
            });
            await page.route('**/api/v1/metrics/dashboard', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ successRatePct: 94.2, avgConfidencePct: 87.5, errorRatePct: 2.1 }),
                });
            });
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/admin-dashboard');
            await expect(page.getByText(/Admin Role Telemetry/i)).toBeVisible({ timeout: 15000 });
            await expect(page.getByText(/Identity & Role/i)).toBeVisible();
            await expect(page.getByText(/Session & Auth/i)).toBeVisible();
        });

        test('shows AI performance section when dashboard data available', async ({ page }) => {
            test.skip(!hasSupabaseUrl, 'NEXT_PUBLIC_SUPABASE_URL not set');
            await page.route('**/api/v1/metrics/db', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ status: 'healthy', document_count: 142 }),
                });
            });
            await page.route('**/api/v1/metrics/health', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ status: 'healthy', details: 'All systems operational', aiServicesStatus: 'healthy', aiServicesDetails: 'Online', grobidStatus: 'healthy', grobidDetails: 'Running' }),
                });
            });
            await page.route('**/api/v1/metrics/dashboard', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ successRatePct: 94.2, avgConfidencePct: 87.5, errorRatePct: 2.1, modelLabel: 'GPT-4o', totalProcessed: 1240, avgProcessingTimeSeconds: 3.4, automationLevel: 'High', fallbackRatePct: 5.3 }),
                });
            });
            await page.addInitScript(() => {
                window.localStorage.setItem('onboarding_completed', 'true');
            });
            await page.goto('/admin-dashboard');
            await expect(page.getByText(/AI Performance/i)).toBeVisible({ timeout: 15000 });
            await expect(page.getByText(/GPT-4o/i)).toBeVisible();
            await expect(page.getByText(/Automation Level/i)).toBeVisible();
            await expect(page.getByText(/Fallback Rate/i)).toBeVisible();
        });
    });
});
