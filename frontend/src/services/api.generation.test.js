// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as api from '../services/api.generation';

const { mockCore } = vi.hoisted(() => ({
    mockCore: {
        API_BASE_URL: 'http://localhost:8000',
        fetchWithAuth: vi.fn(),
        fetchWithRetry: vi.fn(),
        getAuthorizedHeaders: vi.fn(),
        getFriendlyErrorMessage: vi.fn(),
        normalizeExportFormat: vi.fn(),
        sanitizePayload: vi.fn(),
        unwrapV1Payload: vi.fn(),
    },
}));

vi.mock('../services/api.core', () => mockCore);

describe('api.generation', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockCore.normalizeExportFormat.mockImplementation((f) => f || 'docx');
        mockCore.sanitizePayload.mockImplementation((p) => p || {});
        mockCore.unwrapV1Payload.mockImplementation((p) => p);
        mockCore.getFriendlyErrorMessage.mockImplementation(({ status, fallbackMessage }) =>
            fallbackMessage || `Error ${status}`
        );
        mockCore.getAuthorizedHeaders.mockResolvedValue({ Authorization: 'Bearer test-token' });
        mockCore.fetchWithRetry.mockResolvedValue({ ok: true });
    });

    describe('generateDocument', () => {
        it('sends POST to generator sessions', async () => {
            mockCore.fetchWithAuth.mockResolvedValue({ session_id: 'job-1' });
            const result = await api.generateDocument({ doc_type: 'paper', template: 'ieee' });
            expect(mockCore.fetchWithAuth).toHaveBeenCalledWith(
                '/api/v1/generator/sessions',
                expect.objectContaining({ method: 'POST' })
            );
            expect(result.job_id).toBe('job-1');
        });

        it('returns job_id when response has session_id', async () => {
            mockCore.fetchWithAuth.mockResolvedValue({ session_id: 'sess-42' });
            const result = await api.generateDocument({ doc_type: 'paper' });
            expect(result.job_id).toBe('sess-42');
        });

        it('returns id when no session_id in response', async () => {
            mockCore.fetchWithAuth.mockResolvedValue({});
            const result = await api.generateDocument({ doc_type: 'paper' });
            expect(result.job_id).toBeUndefined();
        });
    });

    describe('getGenerationStatus', () => {
        it('sends GET request with encoded jobId', async () => {
            mockCore.fetchWithAuth.mockResolvedValue({ id: 'job-1', status: 'processing' });
            const result = await api.getGenerationStatus('job-1');
            expect(mockCore.fetchWithAuth).toHaveBeenCalledWith(
                '/api/v1/generator/sessions/job-1'
            );
            expect(result.job_id).toBe('job-1');
        });

        it('adds job_id from session_id if absent', async () => {
            mockCore.fetchWithAuth.mockResolvedValue({ session_id: 'sess-99' });
            const result = await api.getGenerationStatus('sess-99');
            expect(result.job_id).toBe('sess-99');
        });
    });

    describe('streamGenerationStatus', () => {
        let abortFn;

        beforeEach(() => {
            abortFn = vi.fn();
            class MockAbortController {
                constructor() { this.signal = { aborted: false }; }
                abort() { this.signal.aborted = true; abortFn(); }
            }
            vi.stubGlobal('AbortController', MockAbortController);
            const reader = {
                read: vi.fn()
                    .mockResolvedValueOnce({ value: new TextEncoder().encode('data: {"progress":50}\n\n'), done: false })
                    .mockResolvedValueOnce({ value: new TextEncoder().encode('event:complete\ndata: {"status":"done"}\n\n'), done: false })
                    .mockResolvedValueOnce({ done: true }),
            };
            mockCore.fetchWithRetry.mockResolvedValue({
                ok: true,
                body: { getReader: () => reader },
            });
        });

        afterEach(() => {
            vi.unstubAllGlobals();
        });

        it('returns closeStream function', () => {
            const closeStream = api.streamGenerationStatus('job-1', vi.fn());
            expect(typeof closeStream).toBe('function');
        });

        it('calls onEvent with parsed SSE data', async () => {
            const onEvent = vi.fn();
            api.streamGenerationStatus('job-1', onEvent);
            await vi.waitFor(() => {
                expect(onEvent).toHaveBeenCalled();
            });
        });

        it('calls closeStream by aborting controller', () => {
            const closeStream = api.streamGenerationStatus('job-1', vi.fn());
            closeStream();
            expect(abortFn).toHaveBeenCalled();
        });

        it('calls onError when response is not ok', async () => {
            mockCore.fetchWithRetry.mockResolvedValue({ ok: false, status: 500 });
            const onError = vi.fn();
            api.streamGenerationStatus('job-1', vi.fn(), onError);
            await vi.waitFor(() => {
                expect(onError).toHaveBeenCalled();
            });
        });

        it('does not call onError when stream is closed before failure', async () => {
            const onError = vi.fn();
            const closeStream = api.streamGenerationStatus('job-1', vi.fn(), onError);
            closeStream();
            await vi.waitFor(() => {
                expect(onError).not.toHaveBeenCalled();
            });
        });
    });

    describe('downloadGeneratedDocument', () => {
        beforeEach(() => {
            globalThis.URL.createObjectURL = vi.fn(() => 'blob:url');
            globalThis.URL.revokeObjectURL = vi.fn();
        });

        it('downloads document as blob', async () => {
            mockCore.fetchWithRetry.mockResolvedValue({
                ok: true,
                blob: () => Promise.resolve(new Blob(['doc content'])),
            });
            const result = await api.downloadGeneratedDocument('job-1', 'docx');
            expect(result.url).toBe('blob:url');
            expect(typeof result.cleanup).toBe('function');
        });

        it('includes format query param', async () => {
            mockCore.fetchWithRetry.mockResolvedValue({
                ok: true,
                blob: () => Promise.resolve(new Blob([''])),
            });
            await api.downloadGeneratedDocument('job-1', 'pdf');
            expect(mockCore.fetchWithRetry).toHaveBeenCalledWith(
                expect.stringContaining('format=pdf'),
                expect.anything()
            );
        });

        it('normalizes export format', async () => {
            mockCore.normalizeExportFormat.mockImplementation(() => 'docx');
            mockCore.fetchWithRetry.mockResolvedValue({
                ok: true,
                blob: () => Promise.resolve(new Blob([''])),
            });
            await api.downloadGeneratedDocument('job-1', 'LATEX');
            expect(mockCore.normalizeExportFormat).toHaveBeenCalledWith('LATEX');
        });

        it('throws on failed download', async () => {
            mockCore.fetchWithRetry.mockResolvedValue({ ok: false, status: 500, json: () => Promise.resolve({}) });
            await expect(api.downloadGeneratedDocument('job-1')).rejects.toThrow();
        });

        it('cleanup revokes object URL', async () => {
            mockCore.fetchWithRetry.mockResolvedValue({
                ok: true,
                blob: () => Promise.resolve(new Blob([''])),
            });
            const result = await api.downloadGeneratedDocument('job-1');
            result.cleanup();
            expect(globalThis.URL.revokeObjectURL).toHaveBeenCalledWith('blob:url');
        });
    });
});
