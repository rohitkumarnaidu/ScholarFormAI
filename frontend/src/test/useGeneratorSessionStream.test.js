// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useGeneratorSessionStream } from '@/src/hooks/useGeneratorSessionStream';

vi.mock('@/src/lib/supabaseClient', () => ({
    supabase: {
        auth: {
            getSession: vi.fn().mockResolvedValue({
                data: { session: { access_token: 'test-token' } },
            }),
        },
    },
}));

describe('useGeneratorSessionStream', () => {
    let mockEventSource;
    let MockEventSource;

    beforeEach(() => {
        vi.useFakeTimers();
        mockEventSource = {
            addEventListener: vi.fn(),
            close: vi.fn(),
        };
        MockEventSource = function MockES(url, opts) {
            mockEventSource.url = url;
            mockEventSource.opts = opts;
            return mockEventSource;
        };
        MockEventSource.prototype = {};
        vi.stubGlobal('EventSource', MockEventSource);
    });

    afterEach(() => {
        vi.useRealTimers();
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('returns idle status when no sessionId', () => {
        const { result } = renderHook(() => useGeneratorSessionStream(null));
        expect(result.current.status).toBe('idle');
    });

    it('connects to events endpoint when sessionId is provided', async () => {
        renderHook(() => useGeneratorSessionStream('sess-123'));
        await vi.advanceTimersToNextTimerAsync();
        expect(mockEventSource.url).toContain('/api/v1/generator/sessions/sess-123/events');
    });

    it('sets streaming status on connected event', async () => {
        const { result } = renderHook(() => useGeneratorSessionStream('sess-123'));
        await vi.advanceTimersToNextTimerAsync();
        act(() => {
            const handler = mockEventSource.addEventListener.mock.calls.find(
                ([e]) => e === 'connected'
            );
            if (handler) handler[1]({});
        });
        expect(result.current.status).toBe('streaming');
    });

    it('calls onToken callback on token event', async () => {
        const onToken = vi.fn();
        renderHook(() => useGeneratorSessionStream('sess-123', { onToken }));
        await vi.advanceTimersToNextTimerAsync();
        act(() => {
            const handler = mockEventSource.addEventListener.mock.calls.find(
                ([e]) => e === 'token'
            );
            if (handler) handler[1]({ data: JSON.stringify({ token: 'hello' }) });
        });
        expect(onToken).toHaveBeenCalledWith('hello');
    });

    it('calls onOutline callback on outline event', async () => {
        const onOutline = vi.fn();
        renderHook(() => useGeneratorSessionStream('sess-123', { onOutline }));
        await vi.advanceTimersToNextTimerAsync();
        act(() => {
            const handler = mockEventSource.addEventListener.mock.calls.find(
                ([e]) => e === 'outline'
            );
            if (handler) handler[1]({ data: JSON.stringify({ sections: [] }) });
        });
        expect(onOutline).toHaveBeenCalledWith({ sections: [] });
    });

    it('sets status done on complete event', async () => {
        const onComplete = vi.fn();
        const { result } = renderHook(() => useGeneratorSessionStream('sess-123', { onComplete }));
        await vi.advanceTimersToNextTimerAsync();
        act(() => {
            const handler = mockEventSource.addEventListener.mock.calls.find(
                ([e]) => e === 'complete'
            );
            if (handler) handler[1]({ data: JSON.stringify({ status: 'done' }) });
        });
        expect(result.current.status).toBe('done');
        expect(onComplete).toHaveBeenCalledWith({ status: 'done' });
    });

    it('sets status error on error event', async () => {
        const onError = vi.fn();
        const { result } = renderHook(() => useGeneratorSessionStream('sess-123', { onError }));
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

    it('handles stage events and updates stages array', async () => {
        const { result } = renderHook(() => useGeneratorSessionStream('sess-123'));
        await vi.advanceTimersToNextTimerAsync();
        act(() => {
            const handler = mockEventSource.addEventListener.mock.calls.find(
                ([e]) => e === 'stage'
            );
            if (handler) handler[1]({ data: JSON.stringify({ name: 'Writing', progress: 50 }) });
        });
        expect(result.current.stages).toHaveLength(1);
        expect(result.current.stages[0].name).toBe('Writing');
    });

    it('reconnects on error with exponential backoff', async () => {
        const { result } = renderHook(() => useGeneratorSessionStream('sess-123'));
        await vi.advanceTimersToNextTimerAsync();
        act(() => { mockEventSource.onerror(); });
        expect(result.current.status).toBe('error');
        expect(result.current.reconnectCount).toBe(1);
    });

    it('cleans up on unmount', async () => {
        const { unmount } = renderHook(() => useGeneratorSessionStream('sess-123'));
        await vi.advanceTimersToNextTimerAsync();
        unmount();
        expect(mockEventSource.close).toHaveBeenCalled();
    });

    it('passes raw data to onToken when JSON parse fails', async () => {
        const onToken = vi.fn();
        renderHook(() => useGeneratorSessionStream('sess-123', { onToken }));
        await vi.advanceTimersToNextTimerAsync();
        act(() => {
            const handler = mockEventSource.addEventListener.mock.calls.find(
                ([e]) => e === 'token'
            );
            if (handler) handler[1]({ data: 'raw-token-data' });
        });
        expect(onToken).toHaveBeenCalledWith('raw-token-data');
    });
});
