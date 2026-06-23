// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as api from './api.js';
import { supabase } from '../lib/supabaseClient';

// Mock global fetch
globalThis.fetch = vi.fn();

// Mock supabase auth
vi.mock('../lib/supabaseClient', () => ({
    supabase: {
        auth: {
            getSession: vi.fn(),
        },
    },
}));

describe('API Service', () => {
    let consoleErrorSpy;

    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
        ['scholarform_currentJob', 'scholarform_job', 'scholarform_active_job'].forEach((key) => {
            sessionStorage.removeItem(key);
        });
        consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => { });

        // Default mock for successful session
        supabase.auth.getSession.mockResolvedValue({
            data: { session: { access_token: 'mock-token' } },
            error: null
        });
    });

    afterEach(() => {
        consoleErrorSpy?.mockRestore();
    });

    it('getDocuments calls the correct endpoint', async () => {
        fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ documents: [], total: 0 }),
        });

        const result = await api.getDocuments({ limit: 10 });

        expect(fetch).toHaveBeenCalledWith(
            expect.stringContaining('/api/v1/documents?limit=10'),
            expect.objectContaining({
                headers: expect.objectContaining({
                    Authorization: 'Bearer mock-token',
                }),
            })
        );
        expect(result.total).toBe(0);
    });

    it('retries on 500 errors', async () => {
        // Mock fail twice, then succeed
        fetch
            .mockResolvedValueOnce({ ok: false, status: 500, json: () => Promise.resolve({}) })
            .mockResolvedValueOnce({ ok: false, status: 500, json: () => Promise.resolve({}) })
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ success: true }) });

        // Speed up time for retries
        vi.useFakeTimers();

        const promise = api.getDocuments();

        // Wait for first fail, then advance timers
        await vi.runAllTimersAsync();

        const result = await promise;
        expect(fetch).toHaveBeenCalledTimes(3);
        expect(result.success).toBe(true);

        vi.useRealTimers();
    });

    it('maps friendly error messages for 401', async () => {
        fetch.mockResolvedValue({
            ok: false,
            status: 401,
            json: () => Promise.resolve({ detail: 'Unauthorized' }),
        });

        await expect(api.getDocuments()).rejects.toThrow('Your session has expired. Please log in again.');
    });

    it('sanitizes text input in template names', async () => {
        fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ job_id: '123' }),
        });

        const file = new File([''], 'test.docx');
        const dirtyTemplate = '<b>IEEE</b>\u0000';

        await api.uploadDocument(file, dirtyTemplate);

        const formData = fetch.mock.calls[0][1].body;
        expect(formData.get('template')).toBe('bIEEE/b');
    });

    it('normalizes unsupported export formats to docx', async () => {
        // Internal helper test via downloadFile or similar
        fetch.mockResolvedValue({
            ok: true,
            blob: () => Promise.resolve(new Blob([''])),
        });

        // Mock URL.createObjectURL
        globalThis.URL.createObjectURL = vi.fn(() => 'blob:url');

        await api.downloadFile('job-1', 'LATEX'); // unsupported, should fall back to docx
        expect(fetch).toHaveBeenCalledWith(
            expect.stringContaining('format=docx'),
            expect.anything()
        );
    });
});

