// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSynthesisSessionStream } from '@/hooks/useSynthesisSessionStream';

vi.mock('@/lib/supabaseClient', () => ({
    supabase: {
        auth: {
            getSession: vi.fn().mockResolvedValue({
                data: { session: { access_token: 'test-token' } },
            }),
        },
    },
}));

vi.mock('@/services/api.synthesis', () => ({
    getSynthesisEventsEndpoint: vi.fn((id) => `http://test/api/v1/synthesis/sessions/${id}/events`),
}));

describe('useSynthesisSessionStream', () => {
    let mockEventSource;

    beforeEach(() => {
        vi.useFakeTimers();
        mockEventSource = {
            addEventListener: vi.fn(),
            close: vi.fn(),
        };
        function MockES(url, opts) {
            mockEventSource.url = url;
            mockEventSource.opts = opts;
            return mockEventSource;
        }
        MockES.prototype = {};
        vi.stubGlobal('EventSource', MockES);
    });

    afterEach(() => {
        vi.useRealTimers();
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('returns idle status when no sessionId', () => {
        const { result } = renderHook(() => useSynthesisSessionStream(null));
        expect(result.current.status).toBe('idle');
    });

    it('connects when sessionId is provided', async () => {
        renderHook(() => useSynthesisSessionStream('syn-123'));
        await vi.advanceTimersToNextTimerAsync();
        expect(mockEventSource.url).toContain('/api/v1/synthesis/sessions/syn-123/events');
    });

    it('sets streaming on connected event', async () => {
        const { result } = renderHook(() => useSynthesisSessionStream('syn-123'));
        await vi.advanceTimersToNextTimerAsync();
        act(() => {
            const handler = mockEventSource.addEventListener.mock.calls.find(
                ([e]) => e === 'connected'
            );
            if (handler) handler[1]({ data: 'connected' });
        });
        expect(result.current.status).toBe('streaming');
    });

    it('adds stage on stage_start event', async () => {
        const { result } = renderHook(() => useSynthesisSessionStream('syn-123'));
        await vi.advanceTimersToNextTimerAsync();
        act(() => {
            const handler = mockEventSource.addEventListener.mock.calls.find(
                ([e]) => e === 'stage_start'
            );
            if (handler) handler[1]({ data: JSON.stringify({ name: 'Extraction' }) });
        });
        expect(result.current.stages).toHaveLength(1);
        expect(result.current.stages[0].name).toBe('Extraction');
        expect(result.current.stages[0].status).toBe('in_progress');
    });

    it('marks stage as done on stage_complete event', async () => {
        const { result } = renderHook(() => useSynthesisSessionStream('syn-123'));
        await vi.advanceTimersToNextTimerAsync();
        act(() => {
            const start = mockEventSource.addEventListener.mock.calls.find(
                ([e]) => e === 'stage_start'
            );
            if (start) start[1]({ data: JSON.stringify({ name: 'Embedding' }) });
        });
        act(() => {
            const complete = mockEventSource.addEventListener.mock.calls.find(
                ([e]) => e === 'stage_complete'
            );
            if (complete) complete[1]({ data: JSON.stringify({ name: 'Embedding' }) });
        });
        expect(result.current.stages[0].status).toBe('done');
    });

    it('sets status done on synthesis_complete event', async () => {
        const onComplete = vi.fn();
        const { result } = renderHook(() => useSynthesisSessionStream('syn-123', { onSynthesisComplete: onComplete }));
        await vi.advanceTimersToNextTimerAsync();
        act(() => {
            const handler = mockEventSource.addEventListener.mock.calls.find(
                ([e]) => e === 'synthesis_complete'
            );
            if (handler) handler[1]({ data: JSON.stringify({ content: 'Final doc' }) });
        });
        expect(result.current.status).toBe('done');
        expect(onComplete).toHaveBeenCalledWith({ content: 'Final doc' });
    });

    it('sets status error on error event', async () => {
        const onError = vi.fn();
        const { result } = renderHook(() => useSynthesisSessionStream('syn-123', { onError }));
        await vi.advanceTimersToNextTimerAsync();
        act(() => {
            const handler = mockEventSource.addEventListener.mock.calls.find(
                ([e]) => e === 'error'
            );
            if (handler) handler[1]({ data: JSON.stringify({ message: 'Failed' }) });
        });
        expect(result.current.status).toBe('error');
        expect(onError).toHaveBeenCalledWith({ message: 'Failed' });
    });

    it('reconnects on error with backoff up to 5 retries', async () => {
        const { result } = renderHook(() => useSynthesisSessionStream('syn-123'));
        await vi.advanceTimersToNextTimerAsync();
        for (let i = 0; i < 5; i++) {
            act(() => { mockEventSource.onerror(); });
        }
        expect(result.current.reconnectCount).toBe(5);
        act(() => { mockEventSource.onerror(); });
        expect(result.current.reconnectCount).toBe(5);
    });

    it('cleans up on unmount', async () => {
        const { unmount } = renderHook(() => useSynthesisSessionStream('syn-123'));
        await vi.advanceTimersToNextTimerAsync();
        unmount();
        expect(mockEventSource.close).toHaveBeenCalled();
    });

    it('calls callbacks on stage events', async () => {
        const onStageStart = vi.fn();
        const onStageComplete = vi.fn();
        renderHook(() => useSynthesisSessionStream('syn-123', { onStageStart, onStageComplete }));
        await vi.advanceTimersToNextTimerAsync();
        act(() => {
            const start = mockEventSource.addEventListener.mock.calls.find(([e]) => e === 'stage_start');
            if (start) start[1]({ data: JSON.stringify({ name: 'Validation' }) });
        });
        expect(onStageStart).toHaveBeenCalledWith({ name: 'Validation' });
        act(() => {
            const complete = mockEventSource.addEventListener.mock.calls.find(([e]) => e === 'stage_complete');
            if (complete) complete[1]({ data: JSON.stringify({ name: 'Validation' }) });
        });
        expect(onStageComplete).toHaveBeenCalledWith({ name: 'Validation' });
    });
});
