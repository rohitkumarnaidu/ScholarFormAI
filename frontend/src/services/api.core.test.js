// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
    fetchWithRetry,
    getFriendlyErrorMessage,
    isNetworkError,
    sanitizePayload,
} from './api.core';

describe('api.core', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('sanitizes payload fields while preserving sensitive values', () => {
        const payload = {
            title: '<b>Paper</b>\u0000',
            nested: {
                summary: '&lt;safe&gt;',
                password: '  sample-password-value  ',
            },
            list: ['<i>A</i>', 'B'],
        };

        const sanitized = sanitizePayload(payload);

        expect(sanitized).toEqual({
            title: 'bPaper/b',
            nested: {
                summary: 'safe',
                password: 'sample-password-value',
            },
            list: ['iA/i', 'B'],
        });
    });

    it('retries transient GET failures and returns successful response', async () => {
        const fetchMock = vi
            .spyOn(globalThis, 'fetch')
            .mockResolvedValueOnce({ ok: false, status: 500 })
            .mockResolvedValueOnce({ ok: false, status: 503 })
            .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ ok: true }) });

        vi.useFakeTimers();
        const request = fetchWithRetry('https://api.test/retry', { method: 'GET' }, { maxRetries: 2 });
        await vi.runAllTimersAsync();
        const response = await request;

        expect(fetchMock).toHaveBeenCalledTimes(3);
        expect(response.ok).toBe(true);
    });

    it('does not retry non-idempotent requests', async () => {
        const fetchMock = vi
            .spyOn(globalThis, 'fetch')
            .mockResolvedValue({ ok: false, status: 500 });

        const response = await fetchWithRetry('https://api.test/no-retry', { method: 'POST' }, { maxRetries: 3 });
        expect(fetchMock).toHaveBeenCalledTimes(1);
        expect(response.status).toBe(500);
    });

    it('returns friendly error messages for auth and network failures', () => {
        expect(
            getFriendlyErrorMessage({ status: 401, endpoint: '/api/v1/auth/login' })
        ).toBe('Invalid email or password.');
        expect(
            getFriendlyErrorMessage({ status: 401, endpoint: '/api/v1/documents' })
        ).toBe('Your session has expired. Please log in again.');
        expect(
            getFriendlyErrorMessage({ error: new TypeError('Failed to fetch') })
        ).toBe('Unable to reach the server. Please check your internet connection and try again.');
        expect(isNetworkError(new TypeError('Failed to fetch'))).toBe(true);
    });
});
