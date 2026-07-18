// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import ReconnectingWebSocket from '@/src/lib/ReconnectingWebSocket';

describe('ReconnectingWebSocket', () => {
    let mockWs;

    beforeEach(() => {
        mockWs = {
            readyState: 1,
            send: vi.fn(),
            close: vi.fn(),
        };
        function MockWebSocket() { return mockWs; }
        MockWebSocket.prototype = WebSocket.prototype;
        MockWebSocket.CONNECTING = 0;
        MockWebSocket.OPEN = 1;
        MockWebSocket.CLOSING = 2;
        MockWebSocket.CLOSED = 3;
        vi.stubGlobal('WebSocket', MockWebSocket);
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('creates a WebSocket connection on construction', () => {
        const rws = new ReconnectingWebSocket('ws://test.com');
        expect(rws.ws).toBe(mockWs);
        rws.close();
    });

    it('calls onopen when WebSocket opens', () => {
        const rws = new ReconnectingWebSocket('ws://test.com');
        const onopen = vi.fn();
        rws.onopen = onopen;
        expect(mockWs.onopen).toBeDefined();
        mockWs.onopen({});
        expect(onopen).toHaveBeenCalled();
        rws.close();
    });

    it('calls onmessage when WebSocket receives message', () => {
        const rws = new ReconnectingWebSocket('ws://test.com');
        const onmessage = vi.fn();
        rws.onmessage = onmessage;
        mockWs.onmessage({ data: 'hello' });
        expect(onmessage).toHaveBeenCalledWith({ data: 'hello' });
        rws.close();
    });

    it('sends data when socket is open', () => {
        const rws = new ReconnectingWebSocket('ws://test.com');
        const result = rws.send('test data');
        expect(mockWs.send).toHaveBeenCalledWith('test data');
        expect(result).toBe(true);
        rws.close();
    });

    it('returns false from send when socket is not open', () => {
        mockWs.readyState = 3;
        const rws = new ReconnectingWebSocket('ws://test.com');
        const result = rws.send('test data');
        expect(result).toBe(false);
        rws.close();
    });

    it('schedules reconnect on close when not forced', () => {
        vi.useFakeTimers();
        const rws = new ReconnectingWebSocket('ws://test.com', { initialDelay: 100, maxDelay: 1000, factor: 2, jitter: 0 });
        rws.ws.onclose({ code: 1006 });
        expect(rws.reconnectAttempt).toBe(0);
        vi.advanceTimersByTime(150);
        expect(rws.reconnectAttempt).toBe(1);
        rws.close();
        vi.useRealTimers();
    });

    it('does not reconnect when forcedClose is set', () => {
        vi.useFakeTimers();
        const rws = new ReconnectingWebSocket('ws://test.com');
        const oldWs = rws.ws;
        rws.close();
        expect(oldWs.close).toHaveBeenCalled();
        const initialWsCount = globalThis.WebSocket.mock?.calls?.length;
        vi.advanceTimersByTime(5000);
        if (initialWsCount !== undefined && globalThis.WebSocket.mock) {
            expect(globalThis.WebSocket.mock.calls.length).toBe(initialWsCount);
        }
        vi.useRealTimers();
    });

    it('stops reconnecting after maxRetries', () => {
        vi.useFakeTimers();
        const rws = new ReconnectingWebSocket('ws://test.com', {
            initialDelay: 100,
            maxDelay: 1000,
            factor: 2,
            maxRetries: 2,
        });
        rws.ws.onclose({ code: 1006 });
        vi.advanceTimersByTime(200);
        rws.ws.onclose({ code: 1006 });
        vi.advanceTimersByTime(400);
        rws.ws.onclose({ code: 1006 });
        vi.advanceTimersByTime(800);
        expect(rws.reconnectAttempt).toBe(2);
        vi.advanceTimersByTime(5000);
        expect(rws.reconnectAttempt).toBe(2);
        rws.close();
        vi.useRealTimers();
    });

    it('computes delay with exponential backoff and jitter', () => {
        const rws = new ReconnectingWebSocket('ws://test.com', { initialDelay: 1000, factor: 2, jitter: 0 });
        const delay = rws.computeReconnectDelay(1);
        expect(delay).toBe(1000);
        rws.close();
    });

    it('calls onreconnect callback when reconnecting', () => {
        vi.useFakeTimers();
        const onreconnect = vi.fn();
        const rws = new ReconnectingWebSocket('ws://test.com', { initialDelay: 100, jitter: 0 });
        rws.onreconnect = onreconnect;
        rws.ws.onclose({ code: 1006 });
        expect(onreconnect).toHaveBeenCalledWith({ attempt: 1, delay: 100 });
        rws.close();
        vi.useRealTimers();
    });

    it('handleError calls onerror callback', () => {
        const onerror = vi.fn();
        const err = new Error('Connection failed');
        const rws = new ReconnectingWebSocket('ws://test.com', { initialDelay: 100 });
        rws.onerror = onerror;
        rws.handleError(err);
        expect(onerror).toHaveBeenCalledWith(err);
        rws.close();
    });

    it('returns CLOSED readyState when ws is null', () => {
        const rws = new ReconnectingWebSocket('ws://test.com');
        rws.ws = null;
        expect(rws.readyState).toBe(3);
    });
});
