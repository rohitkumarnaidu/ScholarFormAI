// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useAgent } from '@/src/hooks/useAgent';

const mocks = vi.hoisted(() => ({
    createAgentSession: vi.fn(),
    getSession: vi.fn(),
    getSessionMessages: vi.fn(),
    getSessionDocument: vi.fn(),
    sendMessage: vi.fn(),
    stopSession: vi.fn(),
    approveOutline: vi.fn(),
    trackEvent: vi.fn(),
}));

vi.mock('@/src/services/api.generator.v1', () => ({
    createAgentSession: mocks.createAgentSession,
    getSession: mocks.getSession,
    getSessionMessages: mocks.getSessionMessages,
    getSessionDocument: mocks.getSessionDocument,
    sendMessage: mocks.sendMessage,
    stopSession: mocks.stopSession,
    approveOutline: mocks.approveOutline,
}));

vi.mock('@/src/lib/analytics', () => ({
    trackEvent: mocks.trackEvent,
}));

describe('useAgent', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('starts with idle state and empty state', () => {
        const { result } = renderHook(() => useAgent());
        expect(result.current.sessionState).toBe('idle');
        expect(result.current.messages).toEqual([]);
        expect(result.current.error).toBeNull();
        expect(result.current.isTyping).toBe(false);
        expect(result.current.activeSessionId).toBeNull();
    });

    it('derives outline_review state from status', () => {
        mocks.getSession.mockResolvedValue({ status: 'awaiting_approval' });
        const { result } = renderHook(() => useAgent());
        act(() => { result.current.fetchSessionData('sess-1'); });
        return waitFor(() => {
            expect(result.current.sessionState).toBe('outline_review');
        });
    });

    it('derives complete state from status', () => {
        mocks.getSession.mockResolvedValue({ status: 'completed' });
        const { result } = renderHook(() => useAgent());
        act(() => { result.current.fetchSessionData('sess-1'); });
        return waitFor(() => {
            expect(result.current.sessionState).toBe('complete');
        });
    });

    it('handleStartSession starts with parsing and creates session', async () => {
        mocks.createAgentSession.mockResolvedValue({ session_id: 'sess-new' });
        const { result } = renderHook(() => useAgent());
        await act(async () => {
            await result.current.handleStartSession('Write a paper', 'ieee');
        });
        expect(result.current.sessionState).toBe('parsing');
        expect(result.current.activeSessionId).toBe('sess-new');
        expect(mocks.createAgentSession).toHaveBeenCalledWith('Write a paper', 'ieee', {});
        expect(mocks.trackEvent).toHaveBeenCalledWith('generator_session_started', expect.any(Object));
    });

    it('handleStartSession sets error on API failure', async () => {
        mocks.createAgentSession.mockRejectedValue(new Error('API error'));
        const { result } = renderHook(() => useAgent());
        await act(async () => {
            try { await result.current.handleStartSession('Write a paper', 'ieee'); } catch (e) { /* expected */ }
        });
        expect(result.current.error).toBe('API error');
    });

    it('handleStartSession validates input with schema', async () => {
        const { result } = renderHook(() => useAgent());
        await act(async () => {
            try {
                await result.current.handleStartSession('', '');
            } catch (e) { /* expected */ }
        });
        expect(result.current.error).toBeTruthy();
        expect(mocks.createAgentSession).not.toHaveBeenCalled();
    });

    it('handleSendMessage sends message and updates messages', async () => {
        mocks.getSessionDocument.mockResolvedValue({});
        mocks.sendMessage.mockResolvedValue({ content: 'Response text', role: 'assistant' });
        const { result } = renderHook(() => useAgent());
        act(() => { result.current.setActiveSessionId('sess-1'); });
        await act(async () => {
            await result.current.handleSendMessage('Hello');
        });
        expect(result.current.messages.length).toBeGreaterThanOrEqual(2);
        expect(result.current.messages.some(m => m.content === 'Hello')).toBe(true);
        expect(result.current.messages.some(m => m.content === 'Response text')).toBe(true);
    });

    it('handleSendMessage validates message with schema', async () => {
        const { result } = renderHook(() => useAgent());
        act(() => { result.current.setActiveSessionId('sess-1'); });
        await act(async () => {
            await result.current.handleSendMessage('');
        });
        expect(result.current.error).toBeTruthy();
        expect(mocks.sendMessage).not.toHaveBeenCalled();
    });

    it('handleStop stops session and sets idle', async () => {
        mocks.stopSession.mockResolvedValue({});
        const { result } = renderHook(() => useAgent());
        act(() => { result.current.setActiveSessionId('sess-1'); });
        await act(async () => {
            await result.current.handleStop();
        });
        expect(result.current.sessionState).toBe('idle');
        expect(mocks.stopSession).toHaveBeenCalledWith('sess-1');
    });

    it('handleApprove approves outline and sets generating state', async () => {
        mocks.approveOutline.mockResolvedValue({});
        const outline = { sections: [{ title: 'Intro' }] };
        const { result } = renderHook(() => useAgent());
        act(() => { result.current.setActiveSessionId('sess-1'); });
        await act(async () => {
            await result.current.handleApprove(outline);
        });
        expect(result.current.sessionState).toBe('generating');
        expect(result.current.outlineData).toEqual(outline);
        expect(mocks.approveOutline).toHaveBeenCalledWith('sess-1', outline);
    });

    it('handleStop does nothing without activeSessionId', async () => {
        const { result } = renderHook(() => useAgent());
        await act(async () => {
            await result.current.handleStop();
        });
        expect(mocks.stopSession).not.toHaveBeenCalled();
    });

    it('handleApprove does nothing without activeSessionId', async () => {
        const { result } = renderHook(() => useAgent());
        await act(async () => {
            await result.current.handleApprove({ sections: [] });
        });
        expect(mocks.approveOutline).not.toHaveBeenCalled();
    });

    it('loadSession fetches session data and messages', async () => {
        mocks.getSession.mockResolvedValue({ status: 'completed', config: { template: 'ieee', user_prompt: 'Hello' } });
        mocks.getSessionMessages.mockResolvedValue([]);
        mocks.getSessionDocument.mockResolvedValue({});
        const { result } = renderHook(() => useAgent());
        await act(async () => {
            await result.current.loadSession('sess-load');
        });
        expect(result.current.activeSessionId).toBe('sess-load');
        expect(mocks.getSession).toHaveBeenCalledWith('sess-load');
    });

    it('loadSession shows fallback message when no messages', async () => {
        mocks.getSession.mockResolvedValue({ status: 'completed' });
        mocks.getSessionMessages.mockResolvedValue([]);
        mocks.getSessionDocument.mockResolvedValue({});
        const { result } = renderHook(() => useAgent());
        await act(async () => {
            await result.current.loadSession('sess-load');
        });
        expect(result.current.messages.length).toBe(1);
        expect(result.current.messages[0].role).toBe('assistant');
        expect(result.current.messages[0].isStatus).toBe(true);
    });

    it('loadSession sets error on failure', async () => {
        mocks.getSession.mockRejectedValue(new Error('Not found'));
        const { result } = renderHook(() => useAgent());
        await act(async () => {
            try { await result.current.loadSession('sess-load'); } catch (e) { /* expected */ }
        });
        expect(result.current.error).toBe('Failed to load the selected session.');
    });

    it('fetchLatestDocument handles sections array', async () => {
        mocks.getSessionDocument.mockResolvedValue({
            content: { sections: [{ title: 'Intro', content: 'Hello world' }] },
        });
        const { result } = renderHook(() => useAgent());
        await act(async () => {
            await result.current.fetchLatestDocument('sess-1');
        });
        expect(result.current.documentSections).toHaveLength(1);
        expect(result.current.documentSections[0].title).toBe('Intro');
    });

    it('fetchLatestDocument handles sections object', async () => {
        mocks.getSessionDocument.mockResolvedValue({
            content: { sections: { Intro: 'Hello', Body: 'World' } },
        });
        const { result } = renderHook(() => useAgent());
        await act(async () => {
            await result.current.fetchLatestDocument('sess-1');
        });
        expect(result.current.documentSections).toHaveLength(2);
    });

    it('fetchLatestDocument includes references section', async () => {
        mocks.getSessionDocument.mockResolvedValue({
            content: {
                sections: [],
                references: ['Ref 1', 'Ref 2'],
            },
        });
        const { result } = renderHook(() => useAgent());
        await act(async () => {
            await result.current.fetchLatestDocument('sess-1');
        });
        expect(result.current.documentSections.length).toBeGreaterThan(0);
        expect(result.current.documentSections.some(s => s.title === 'References')).toBe(true);
    });

    it('handleSendMessage handles error from API', async () => {
        mocks.sendMessage.mockRejectedValue(new Error('Network error'));
        const { result } = renderHook(() => useAgent());
        act(() => { result.current.setActiveSessionId('sess-1'); });
        await act(async () => {
            await result.current.handleSendMessage('Hello');
        });
        expect(result.current.error).toBe('Network error');
    });

    it('includes selectedModel in session config when set', async () => {
        mocks.createAgentSession.mockResolvedValue({ session_id: 'sess-model' });
        const { result } = renderHook(() => useAgent());
        act(() => { result.current.setSelectedModel('gpt-4'); });
        await act(async () => {
            await result.current.handleStartSession('Write', 'ieee');
        });
        expect(mocks.createAgentSession).toHaveBeenCalledWith('Write', 'ieee', { model: 'gpt-4' });
    });

    it('derives parsing state from processing status', () => {
        mocks.getSession.mockResolvedValue({ status: 'processing' });
        const { result } = renderHook(() => useAgent());
        act(() => { result.current.fetchSessionData('sess-1'); });
        return waitFor(() => {
            expect(result.current.sessionState).toBe('parsing');
        });
    });
});
