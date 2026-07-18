// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import useLivePreviewSocket from '@/src/hooks/useLivePreviewSocket';

const { mockRws, constructorSpy } = vi.hoisted(() => ({
    mockRws: {
        onopen: null,
        onmessage: null,
        onclose: null,
        onerror: null,
        onreconnect: null,
        send: vi.fn(),
        close: vi.fn(),
        readyState: 1,
    },
    constructorSpy: vi.fn(),
}));

vi.mock('@/src/lib/ReconnectingWebSocket', () => {
    function MockRwsConstructor(...args) {
        constructorSpy(...args);
        return mockRws;
    }
    MockRwsConstructor.prototype = {};
    return { default: MockRwsConstructor };
});

describe('useLivePreviewSocket', () => {
    beforeEach(() => {
        vi.useFakeTimers();
        mockRws.onopen = null;
        mockRws.onmessage = null;
        mockRws.onclose = null;
        mockRws.onerror = null;
        mockRws.onreconnect = null;
        mockRws.send.mockClear();
        mockRws.close.mockClear();
        mockRws.readyState = 1;
        constructorSpy.mockClear();
    });

    afterEach(() => {
        vi.useRealTimers();
        vi.restoreAllMocks();
    });

    it('does not connect when sessionId is null', () => {
        renderHook(() => useLivePreviewSocket(null));
        expect(constructorSpy).not.toHaveBeenCalled();
    });

    it('creates ReconnectingWebSocket when sessionId is provided', () => {
        renderHook(() => useLivePreviewSocket('sess-123'));
        expect(constructorSpy).toHaveBeenCalledWith(
            expect.stringContaining('/api/v1/ws/preview/sess-123'),
            expect.objectContaining({ initialDelay: 1000, maxDelay: 30000 })
        );
    });

    it('sets isConnected on open', () => {
        const { result } = renderHook(() => useLivePreviewSocket('sess-123'));
        act(() => { mockRws.onopen({}); });
        expect(result.current.isConnected).toBe(true);
        expect(result.current.isReconnecting).toBe(false);
    });

    it('updates html from message events', () => {
        const { result } = renderHook(() => useLivePreviewSocket('sess-123'));
        act(() => {
            mockRws.onmessage({ data: JSON.stringify({ html: '<p>Hello</p>' }) });
        });
        expect(result.current.html).toBe('<p>Hello</p>');
    });

    it('updates warnings from message events', () => {
        const { result } = renderHook(() => useLivePreviewSocket('sess-123'));
        act(() => {
            mockRws.onmessage({ data: JSON.stringify({ html: '', warnings: ['Missing font'] }) });
        });
        expect(result.current.warnings).toEqual(['Missing font']);
    });

    it('sets isConnected false on close', () => {
        const { result } = renderHook(() => useLivePreviewSocket('sess-123'));
        act(() => { mockRws.onopen({}); });
        expect(result.current.isConnected).toBe(true);
        act(() => { mockRws.onclose({}); });
        expect(result.current.isConnected).toBe(false);
    });

    it('sets isConnected false on error', () => {
        const { result } = renderHook(() => useLivePreviewSocket('sess-123'));
        act(() => { mockRws.onopen({}); });
        expect(result.current.isConnected).toBe(true);
        act(() => { mockRws.onerror({}); });
        expect(result.current.isConnected).toBe(false);
    });

    it('sets reconnecting state on reconnect event', () => {
        const { result } = renderHook(() => useLivePreviewSocket('sess-123'));
        act(() => {
            mockRws.onreconnect({ attempt: 2 });
        });
        expect(result.current.isReconnecting).toBe(true);
        expect(result.current.reconnectAttempt).toBe(2);
    });

    it('sendContent sends payload through WebSocket', () => {
        const { result } = renderHook(() => useLivePreviewSocket('sess-123'));
        act(() => { mockRws.onopen({}); });
        act(() => {
            result.current.sendContent('Hello world', 'ieee');
        });
        act(() => { vi.advanceTimersByTime(200); });
        expect(mockRws.send).toHaveBeenCalled();
        const callArg = JSON.parse(mockRws.send.mock.calls[0][0]);
        expect(callArg.content).toBe('Hello world');
        expect(callArg.templateId).toBe('ieee');
        expect(callArg).toHaveProperty('checksum');
        expect(callArg).toHaveProperty('seq', 1);
    });

    it('queues payload when socket not open and resends on reconnect', () => {
        const { result } = renderHook(() => useLivePreviewSocket('sess-123'));
        mockRws.readyState = 0;
        act(() => {
            result.current.sendContent('Queued content', 'ieee');
        });
        act(() => { vi.advanceTimersByTime(200); });
        expect(mockRws.send).not.toHaveBeenCalled();
        mockRws.readyState = 1;
        act(() => { mockRws.onopen({}); });
        expect(mockRws.send).toHaveBeenCalled();
        const callArg = JSON.parse(mockRws.send.mock.calls[0][0]);
        expect(callArg.content).toBe('Queued content');
    });

    it('sets isAnalyzing when diff > 1000', () => {
        const { result } = renderHook(() => useLivePreviewSocket('sess-123'));
        act(() => { result.current.sendContent('x'.repeat(1500), ''); });
        expect(result.current.isAnalyzing).toBe(true);
    });

    it('ignores malformed message data', () => {
        const { result } = renderHook(() => useLivePreviewSocket('sess-123'));
        act(() => {
            mockRws.onmessage({ data: 'not-json' });
        });
        expect(result.current.html).toBe('');
    });

    it('cleans up on unmount', () => {
        const { unmount } = renderHook(() => useLivePreviewSocket('sess-123'));
        unmount();
        expect(mockRws.close).toHaveBeenCalled();
    });

    it('computes latency from message timing', () => {
        const { result } = renderHook(() => useLivePreviewSocket('sess-123'));
        act(() => { mockRws.onopen({}); });
        act(() => {
            result.current.sendContent('test', '');
        });
        act(() => { vi.advanceTimersByTime(200); });
        act(() => {
            mockRws.onmessage({ data: JSON.stringify({ html: '<p>Done</p>' }) });
        });
        expect(result.current.latencyMs).toBeGreaterThanOrEqual(0);
    });
});
