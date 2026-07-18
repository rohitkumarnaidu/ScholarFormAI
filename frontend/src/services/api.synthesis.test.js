// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as api from '../services/api.synthesis';

const { mockFetchWithAuth } = vi.hoisted(() => ({
    mockFetchWithAuth: vi.fn(),
}));

vi.mock('../services/api.core', () => ({
    fetchWithAuth: mockFetchWithAuth,
}));

describe('api.synthesis', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('createSynthesisSession', () => {
        it('sends POST with formData', async () => {
            mockFetchWithAuth.mockResolvedValue({ session_id: 'syn-1' });
            const files = [new File([''], 'doc1.pdf')];
            const result = await api.createSynthesisSession(files, 'ieee', { opt: true });
            expect(mockFetchWithAuth).toHaveBeenCalledWith(
                '/api/v1/synthesis/sessions',
                expect.objectContaining({ method: 'POST' })
            );
            expect(result.session_id).toBe('syn-1');
        });

        it('appends session_type multi_doc', async () => {
            mockFetchWithAuth.mockResolvedValue({ session_id: 'syn-1' });
            const files = [new File([''], 'doc1.pdf')];
            await api.createSynthesisSession(files, null, {});
            expect(mockFetchWithAuth).toHaveBeenCalledWith(
                '/api/v1/synthesis/sessions',
                expect.objectContaining({ method: 'POST' })
            );
        });

        it('sends config as JSON string', async () => {
            mockFetchWithAuth.mockResolvedValue({});
            const files = [new File([''], 'doc1.pdf')];
            await api.createSynthesisSession(files, 'nature', { language: 'en' });
            expect(mockFetchWithAuth).toHaveBeenCalledWith(
                '/api/v1/synthesis/sessions',
                expect.objectContaining({ method: 'POST' })
            );
        });

        it('appends each file to formData', async () => {
            mockFetchWithAuth.mockResolvedValue({});
            const files = [new File(['a'], 'a.pdf'), new File(['b'], 'b.pdf')];
            await api.createSynthesisSession(files);
            const callArgs = mockFetchWithAuth.mock.calls[0][1];
            expect(callArgs.body).toBeInstanceOf(FormData);
        });
    });

    describe('getSynthesisSession', () => {
        it('sends GET request', async () => {
            mockFetchWithAuth.mockResolvedValue({ id: 'syn-1', status: 'processing' });
            const result = await api.getSynthesisSession('syn-1');
            expect(mockFetchWithAuth).toHaveBeenCalledWith(
                '/api/v1/synthesis/sessions/syn-1',
                { method: 'GET' }
            );
            expect(result.id).toBe('syn-1');
        });
    });

    describe('sendSynthesisMessage', () => {
        it('sends POST with content', async () => {
            mockFetchWithAuth.mockResolvedValue({ message: { id: 'm-1' } });
            const result = await api.sendSynthesisMessage('syn-1', 'Summarize');
            expect(mockFetchWithAuth).toHaveBeenCalledWith(
                '/api/v1/synthesis/sessions/syn-1/messages',
                expect.objectContaining({ method: 'POST', headers: { 'Content-Type': 'application/json' } })
            );
            const body = JSON.parse(mockFetchWithAuth.mock.calls[0][1].body);
            expect(body.content).toBe('Summarize');
            expect(result.message.id).toBe('m-1');
        });
    });

    describe('getSynthesisEventsEndpoint', () => {
        it('returns events URL', () => {
            const url = api.getSynthesisEventsEndpoint('syn-1');
            expect(url).toContain('/api/v1/synthesis/sessions/syn-1/events');
        });

        it('uses API_BASE_URL from env if available', () => {
            const orig = process.env.NEXT_PUBLIC_API_URL;
            process.env.NEXT_PUBLIC_API_URL = 'https://api.example.com';
            const url = api.getSynthesisEventsEndpoint('syn-1');
            expect(url).toBe('https://api.example.com/api/v1/synthesis/sessions/syn-1/events');
            process.env.NEXT_PUBLIC_API_URL = orig;
        });

        it('defaults to localhost:8000', () => {
            const orig = process.env.NEXT_PUBLIC_API_URL;
            delete process.env.NEXT_PUBLIC_API_URL;
            const url = api.getSynthesisEventsEndpoint('syn-1');
            expect(url).toBe('http://localhost:8000/api/v1/synthesis/sessions/syn-1/events');
            process.env.NEXT_PUBLIC_API_URL = orig;
        });
    });

    describe('error handling', () => {
        it('propagates errors from fetchWithAuth', async () => {
            mockFetchWithAuth.mockRejectedValue(new Error('Server error'));
            await expect(api.getSynthesisSession('bad-id')).rejects.toThrow('Server error');
        });

        it('handles 404 for nonexistent session', async () => {
            mockFetchWithAuth.mockRejectedValue(new Error('The requested resource could not be found.'));
            await expect(api.getSynthesisSession('missing')).rejects.toThrow('The requested resource could not be found.');
        });
    });
});
