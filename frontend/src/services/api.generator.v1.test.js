// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as api from '../services/api.generator.v1';

const { mockFetchWithAuth } = vi.hoisted(() => ({
    mockFetchWithAuth: vi.fn(),
}));

vi.mock('../services/api.core', () => ({
    fetchWithAuth: mockFetchWithAuth,
}));

describe('api.generator.v1', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('createSession', () => {
        it('sends POST with formData', async () => {
            mockFetchWithAuth.mockResolvedValue({ session_id: 'sess-1' });
            const files = [new File([''], 'test.pdf')];
            const result = await api.createSession(files, 'agent', 'ieee', { opt: true });
            expect(mockFetchWithAuth).toHaveBeenCalledWith(
                '/api/v1/generator/sessions',
                expect.objectContaining({ method: 'POST' })
            );
            expect(result.session_id).toBe('sess-1');
        });

        it('includes config as JSON string in formData', async () => {
            mockFetchWithAuth.mockResolvedValue({ session_id: 'sess-1' });
            const files = [new File([''], 'test.pdf')];
            await api.createSession(files, 'batch', null, { key: 'val' });
            const callArgs = mockFetchWithAuth.mock.calls[0][1];
            expect(callArgs.body).toBeInstanceOf(FormData);
        });
    });

    describe('createAgentSession', () => {
        it('sends POST with JSON body', async () => {
            mockFetchWithAuth.mockResolvedValue({ session_id: 'sess-1' });
            const result = await api.createAgentSession('Write a paper', 'ieee', { doc_type: 'academic' });
            expect(mockFetchWithAuth).toHaveBeenCalledWith(
                '/api/v1/generator/sessions',
                expect.objectContaining({
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                })
            );
            expect(result.session_id).toBe('sess-1');
        });

        it('sends prompt and template in body', async () => {
            mockFetchWithAuth.mockResolvedValue({});
            await api.createAgentSession('My prompt', 'nature');
            const body = JSON.parse(mockFetchWithAuth.mock.calls[0][1].body);
            expect(body.prompt).toBe('My prompt');
            expect(body.template).toBe('nature');
            expect(body.session_type).toBe('agent');
        });

        it('defaults config to empty object', async () => {
            mockFetchWithAuth.mockResolvedValue({});
            await api.createAgentSession('Test');
            const body = JSON.parse(mockFetchWithAuth.mock.calls[0][1].body);
            expect(body.config).toEqual({});
        });
    });

    describe('getSession', () => {
        it('sends GET request', async () => {
            mockFetchWithAuth.mockResolvedValue({ id: 'sess-1', status: 'active' });
            const result = await api.getSession('sess-1');
            expect(mockFetchWithAuth).toHaveBeenCalledWith(
                '/api/v1/generator/sessions/sess-1',
                { method: 'GET' }
            );
            expect(result.id).toBe('sess-1');
        });
    });

    describe('getSessionMessages', () => {
        it('sends GET with limit parameter', async () => {
            mockFetchWithAuth.mockResolvedValue({ messages: [] });
            await api.getSessionMessages('sess-1', 50);
            expect(mockFetchWithAuth).toHaveBeenCalledWith(
                '/api/v1/generator/sessions/sess-1/messages?limit=50',
                { method: 'GET' }
            );
        });

        it('uses default limit of 100', async () => {
            mockFetchWithAuth.mockResolvedValue({ messages: [] });
            await api.getSessionMessages('sess-1');
            expect(mockFetchWithAuth).toHaveBeenCalledWith(
                '/api/v1/generator/sessions/sess-1/messages?limit=100',
                { method: 'GET' }
            );
        });
    });

    describe('getSessionDocument', () => {
        it('sends GET for document endpoint', async () => {
            mockFetchWithAuth.mockResolvedValue({ content: 'doc content' });
            const result = await api.getSessionDocument('sess-1');
            expect(mockFetchWithAuth).toHaveBeenCalledWith(
                '/api/v1/generator/sessions/sess-1/document',
                { method: 'GET' }
            );
            expect(result.content).toBe('doc content');
        });
    });

    describe('sendMessage', () => {
        it('sends POST with content and model', async () => {
            mockFetchWithAuth.mockResolvedValue({ message: { id: 'msg-1' } });
            await api.sendMessage('sess-1', 'Hello', 'gpt-4');
            expect(mockFetchWithAuth).toHaveBeenCalledWith(
                '/api/v1/generator/sessions/sess-1/messages',
                expect.objectContaining({ method: 'POST' })
            );
            const body = JSON.parse(mockFetchWithAuth.mock.calls[0][1].body);
            expect(body.content).toBe('Hello');
            expect(body.model).toBe('gpt-4');
        });

        it('handles content object with model property', async () => {
            mockFetchWithAuth.mockResolvedValue({});
            await api.sendMessage('sess-1', { content: 'Hello', model: 'claude-3' });
            const body = JSON.parse(mockFetchWithAuth.mock.calls[0][1].body);
            expect(body.content).toBe('Hello');
            expect(body.model).toBe('claude-3');
        });
    });

    describe('approveOutline', () => {
        it('sends POST with outline body', async () => {
            mockFetchWithAuth.mockResolvedValue({ status: 'generating' });
            const outline = { sections: [{ title: 'Intro', expectedWordCount: 500 }] };
            const result = await api.approveOutline('sess-1', outline);
            expect(mockFetchWithAuth).toHaveBeenCalledWith(
                '/api/v1/generator/sessions/sess-1/outline/approve',
                expect.objectContaining({ method: 'POST' })
            );
            const body = JSON.parse(mockFetchWithAuth.mock.calls[0][1].body);
            expect(body.outline).toEqual(outline);
            expect(result.status).toBe('generating');
        });

        it('sends empty body when outline is null', async () => {
            mockFetchWithAuth.mockResolvedValue({});
            await api.approveOutline('sess-1', null);
            const body = JSON.parse(mockFetchWithAuth.mock.calls[0][1].body);
            expect(body).toEqual({});
        });
    });

    describe('stopSession', () => {
        it('sends POST to stop endpoint', async () => {
            mockFetchWithAuth.mockResolvedValue({ status: 'stopped' });
            const result = await api.stopSession('sess-1');
            expect(mockFetchWithAuth).toHaveBeenCalledWith(
                '/api/v1/generator/sessions/sess-1/stop',
                { method: 'POST' }
            );
            expect(result.status).toBe('stopped');
        });
    });

    describe('error handling', () => {
        it('propagates fetchWithAuth errors', async () => {
            mockFetchWithAuth.mockRejectedValue(new Error('Network error'));
            await expect(api.getSession('bad-id')).rejects.toThrow('Network error');
        });

        it('propagates 404 errors', async () => {
            mockFetchWithAuth.mockRejectedValue(new Error('The requested resource could not be found.'));
            await expect(api.getSession('nonexistent')).rejects.toThrow('The requested resource could not be found.');
        });
    });
});
