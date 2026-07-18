// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSessionEventStream } from '@/src/hooks/useSessionEventStream';

vi.mock('@/src/lib/supabaseClient', () => ({
    supabase: {
        auth: {
            getSession: vi.fn().mockResolvedValue({
                data: { session: { access_token: 'test-token' } },
            }),
        },
    },
}));

describe('useSessionEventStream', () => {
    let mockEventSource;

    beforeEach(() => {
        vi.useFakeTimers();
        mockEventSource = {
            onmessage: null,
            onerror: null,
            close: vi.fn(),
        };
        function MockES(url) {
            mockEventSource.url = url;
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

    it('returns empty state when no sessionId', () => {
        const { result } = renderHook(() => useSessionEventStream(null, vi.fn(), 'test'));
        expect(result.current.stages).toEqual([]);
        expect(result.current.currentStage).toBe('');
        expect(result.current.progress).toBe(0);
        expect(result.current.isComplete).toBe(false);
        expect(result.current.error).toBeNull();
    });

    it('connects to events URL with token param', async () => {
        const getUrl = vi.fn(() => 'http://test/api/v1/stream/test-session');
        renderHook(() => useSessionEventStream('test-session', getUrl, 'test-stream'));
        await vi.advanceTimersToNextTimerAsync();
        expect(mockEventSource.url).toBe('http://test/api/v1/stream/test-session?token=test-token');
    });

    it('updates stages from onmessage events', async () => {
        const getUrl = vi.fn(() => 'http://test/events');
        const { result } = renderHook(() => useSessionEventStream('sess-1', getUrl, 'synthesis'));
        await vi.advanceTimersToNextTimerAsync();
        act(() => {
            mockEventSource.onmessage({
                data: JSON.stringify({ name: 'Extraction', progress: 10 }),
            });
        });
        expect(result.current.stages).toHaveLength(1);
        expect(result.current.stages[0].name).toBe('Extraction');
        expect(result.current.currentStage).toBe('Extraction');
    });

    it('updates progress from onmessage events', async () => {
        const getUrl = vi.fn(() => 'http://test/events');
        const { result } = renderHook(() => useSessionEventStream('sess-1', getUrl, 'synthesis'));
        await vi.advanceTimersToNextTimerAsync();
        act(() => {
            mockEventSource.onmessage({
                data: JSON.stringify({ name: 'Writing', progress: 75 }),
            });
        });
        expect(result.current.progress).toBe(75);
    });

    it('sets isComplete when progress reaches 100', async () => {
        const getUrl = vi.fn(() => 'http://test/events');
        const { result } = renderHook(() => useSessionEventStream('sess-1', getUrl, 'synthesis'));
        await vi.advanceTimersToNextTimerAsync();
        act(() => {
            mockEventSource.onmessage({
                data: JSON.stringify({ status: 'done' }),
            });
        });
        expect(result.current.isComplete).toBe(true);
    });

    it('sets error when status is error', async () => {
        const getUrl = vi.fn(() => 'http://test/events');
        const { result } = renderHook(() => useSessionEventStream('sess-1', getUrl, 'synthesis'));
        await vi.advanceTimersToNextTimerAsync();
        act(() => {
            mockEventSource.onmessage({
                data: JSON.stringify({ status: 'error', message: 'Processing failed' }),
            });
        });
        expect(result.current.error).toBeDefined();
        expect(result.current.error.message).toBe('Processing failed');
    });

    it('reconnects on error with backoff up to 5 retries', async () => {
        const getUrl = vi.fn(() => 'http://test/events');
        const { result } = renderHook(() => useSessionEventStream('sess-1', getUrl, 'synthesis'));
        await vi.advanceTimersToNextTimerAsync();
        for (let i = 0; i < 6; i++) {
            act(() => { mockEventSource.onerror(new Event('error')); });
        }
        expect(result.current.error).toBeDefined();
        expect(result.current.error.message).toContain('Lost connection');
    });

    it('cleans up on unmount', async () => {
        const getUrl = vi.fn(() => 'http://test/events');
        const { unmount } = renderHook(() => useSessionEventStream('sess-1', getUrl, 'synthesis'));
        await vi.advanceTimersToNextTimerAsync();
        unmount();
        expect(mockEventSource.close).toHaveBeenCalled();
    });

    it('does not reconnect when unmounted during reconnect', async () => {
        const getUrl = vi.fn(() => 'http://test/events');
        const { unmount } = renderHook(() => useSessionEventStream('sess-1', getUrl, 'synthesis'));
        await vi.advanceTimersToNextTimerAsync();
        unmount();
        expect(mockEventSource.close).toHaveBeenCalled();
        vi.advanceTimersByTime(10000);
    });
});
