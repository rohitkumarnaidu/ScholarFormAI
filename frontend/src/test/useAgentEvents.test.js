// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAgentEvents } from '@/src/hooks/useAgentEvents';

const { mockEventSource } = vi.hoisted(() => ({
    mockEventSource: {
        addEventListener: vi.fn(),
        close: vi.fn(),
    },
}));

vi.mock('@/src/lib/supabaseClient', () => ({
    supabase: {
        auth: {
            getSession: vi.fn().mockResolvedValue({
                data: { session: { access_token: 'test-token' } },
            }),
        },
    },
}));

describe('useAgentEvents', () => {
    let setOutlineData;
    let setSessionState;
    let setIsTyping;
    let setMessages;
    let fetchSessionData;
    let fetchLatestDocument;

    beforeEach(() => {
        vi.useFakeTimers();
        mockEventSource.addEventListener.mockClear();
        mockEventSource.close.mockClear();
        mockEventSource.url = '';
        function MockES(url, opts) {
            mockEventSource.url = url;
            mockEventSource.opts = opts;
            return mockEventSource;
        }
        MockES.prototype = {};
        vi.stubGlobal('EventSource', MockES);
        setOutlineData = vi.fn();
        setSessionState = vi.fn();
        setIsTyping = vi.fn();
        setMessages = vi.fn();
        fetchSessionData = vi.fn().mockResolvedValue({ outline: { sections: [] } });
        fetchLatestDocument = vi.fn().mockResolvedValue({});
    });

    afterEach(() => {
        vi.useRealTimers();
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('does nothing when activeSessionId is null', () => {
        const eventSourceBefore = globalThis.EventSource;
        renderHook(() => useAgentEvents({
            activeSessionId: null,
            setOutlineData,
            setSessionState,
            setIsTyping,
            setMessages,
            fetchSessionData,
            fetchLatestDocument,
            selectedTemplate: 'ieee',
            lastPrompt: 'test',
        }));
        expect(globalThis.EventSource).toBe(eventSourceBefore);
    });

    it('connects to events endpoint when sessionId is provided', () => {
        renderHook(() => useAgentEvents({
            activeSessionId: 'sess-1',
            setOutlineData,
            setSessionState,
            setIsTyping,
            setMessages,
            fetchSessionData,
            fetchLatestDocument,
            selectedTemplate: 'ieee',
            lastPrompt: 'test',
        }));
        expect(mockEventSource.url).toContain('/api/v1/generator/sessions/sess-1/events');
    });

    it('handles outline_chunk and sets outline when complete JSON parsed', () => {
        renderHook(() => useAgentEvents({
            activeSessionId: 'sess-1',
            setOutlineData,
            setSessionState,
            setIsTyping,
            setMessages,
            fetchSessionData,
            fetchLatestDocument,
            selectedTemplate: 'ieee',
            lastPrompt: 'test paper',
        }));
        const chunkHandler = mockEventSource.addEventListener.mock.calls.find(
            ([e]) => e === 'outline_chunk'
        );
        expect(chunkHandler).toBeDefined();
        const outlineData = { title: 'Test', sections: [{ title: 'Intro' }] };
        act(() => {
            chunkHandler[1]({
                data: JSON.stringify({
                    payload: { content: JSON.stringify(outlineData) },
                }),
            });
        });
        expect(setOutlineData).toHaveBeenCalledWith(outlineData);
        expect(setSessionState).toHaveBeenCalledWith('outline_review');
        expect(setIsTyping).toHaveBeenCalledWith(false);
    });

    it('handles stage_update for outline stage', async () => {
        renderHook(() => useAgentEvents({
            activeSessionId: 'sess-1',
            setOutlineData,
            setSessionState,
            setIsTyping,
            setMessages,
            fetchSessionData,
            fetchLatestDocument,
            selectedTemplate: 'ieee',
            lastPrompt: 'test',
        }));
        const stageHandler = mockEventSource.addEventListener.mock.calls.find(
            ([e]) => e === 'stage_update'
        );
        expect(stageHandler).toBeDefined();
        await act(async () => {
            stageHandler[1]({
                data: JSON.stringify({ stage: 'outline' }),
            });
        });
        expect(setSessionState).toHaveBeenCalledWith('outline_review');
    });

    it('handles stage_update for writing/generating stage', () => {
        renderHook(() => useAgentEvents({
            activeSessionId: 'sess-1',
            setOutlineData,
            setSessionState,
            setIsTyping,
            setMessages,
            fetchSessionData,
            fetchLatestDocument,
            selectedTemplate: 'ieee',
            lastPrompt: 'test',
        }));
        const stageHandler = mockEventSource.addEventListener.mock.calls.find(
            ([e]) => e === 'stage_update'
        );
        act(() => {
            stageHandler[1]({
                data: JSON.stringify({ stage: 'writing' }),
            });
        });
        expect(setSessionState).toHaveBeenCalledWith('generating');
    });

    it('handles stage_update for done/completed stage', async () => {
        fetchSessionData.mockResolvedValue({ status: 'completed' });
        renderHook(() => useAgentEvents({
            activeSessionId: 'sess-1',
            setOutlineData,
            setSessionState,
            setIsTyping,
            setMessages,
            fetchSessionData,
            fetchLatestDocument,
            selectedTemplate: 'ieee',
            lastPrompt: 'test',
        }));
        const stageHandler = mockEventSource.addEventListener.mock.calls.find(
            ([e]) => e === 'stage_update'
        );
        await act(async () => {
            stageHandler[1]({
                data: JSON.stringify({ stage: 'done', status: 'completed' }),
            });
        });
        expect(setSessionState).toHaveBeenCalledWith('complete');
    });

    it('handles stage_update for stopped/canceled stage', () => {
        renderHook(() => useAgentEvents({
            activeSessionId: 'sess-1',
            setOutlineData,
            setSessionState,
            setIsTyping,
            setMessages,
            fetchSessionData,
            fetchLatestDocument,
            selectedTemplate: 'ieee',
            lastPrompt: 'test',
        }));
        const stageHandler = mockEventSource.addEventListener.mock.calls.find(
            ([e]) => e === 'stage_update'
        );
        act(() => {
            stageHandler[1]({
                data: JSON.stringify({ stage: 'stopped', status: 'canceled' }),
            });
        });
        expect(setSessionState).toHaveBeenCalledWith('idle');
        expect(setIsTyping).toHaveBeenCalledWith(false);
    });

    it('closes event source on unmount', () => {
        const { unmount } = renderHook(() => useAgentEvents({
            activeSessionId: 'sess-1',
            setOutlineData,
            setSessionState,
            setIsTyping,
            setMessages,
            fetchSessionData,
            fetchLatestDocument,
            selectedTemplate: 'ieee',
            lastPrompt: 'test',
        }));
        unmount();
        expect(mockEventSource.close).toHaveBeenCalled();
    });

    it('returns eventSource and isOutlineReady values', () => {
        const { result } = renderHook(() => useAgentEvents({
            activeSessionId: 'sess-1',
            setOutlineData,
            setSessionState,
            setIsTyping,
            setMessages,
            fetchSessionData,
            fetchLatestDocument,
            selectedTemplate: 'ieee',
            lastPrompt: 'test',
        }));
        expect(result.current).toHaveProperty('eventSource');
        expect(result.current).toHaveProperty('isOutlineReady');
    });

    it('handles SSE parse errors gracefully', () => {
        renderHook(() => useAgentEvents({
            activeSessionId: 'sess-1',
            setOutlineData,
            setSessionState,
            setIsTyping,
            setMessages,
            fetchSessionData,
            fetchLatestDocument,
            selectedTemplate: 'ieee',
            lastPrompt: 'test',
        }));
        const chunkHandler = mockEventSource.addEventListener.mock.calls.find(
            ([e]) => e === 'outline_chunk'
        );
        expect(() => {
            chunkHandler[1]({ data: 'invalid-json' });
        }).not.toThrow();
    });
});
