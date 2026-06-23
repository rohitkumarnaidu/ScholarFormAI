// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

/**
 * ReconnectingWebSocket wraps native WebSocket with automatic reconnection.
 * Retries use exponential backoff with jitter.
 */
export default class ReconnectingWebSocket {
    constructor(url, options = {}) {
        this.url = url;
        this.options = {
            initialDelay: 1000,
            maxDelay: 30000,
            factor: 2,
            jitter: 0.3,
            maxRetries: Number.POSITIVE_INFINITY,
            shouldReconnect: null,
            ...options,
        };

        this.ws = null;
        this.forcedClose = false;
        this.reconnectTimer = null;
        this.reconnectAttempt = 0;

        // Event listeners exposed to consumers
        this.onopen = null;
        this.onmessage = null;
        this.onclose = null;
        this.onerror = null;
        this.onreconnect = null;

        this.open();
    }

    open() {
        if (this.forcedClose) return;

        try {
            this.ws = new WebSocket(this.url);
        } catch (err) {
            this.handleError(err);
            return;
        }

        this.ws.onopen = (event) => {
            this.reconnectAttempt = 0;
            if (this.reconnectTimer) {
                clearTimeout(this.reconnectTimer);
                this.reconnectTimer = null;
            }
            if (this.onopen) this.onopen(event);
        };

        this.ws.onmessage = (event) => {
            if (this.onmessage) this.onmessage(event);
        };

        this.ws.onclose = (event) => {
            if (this.onclose) this.onclose(event);
            if (this.forcedClose) return;
            if (!this.canReconnect(event)) return;
            this.scheduleReconnect();
        };

        this.ws.onerror = (event) => {
            if (this.onerror) this.onerror(event);
            // Browsers usually emit close after error. Reconnect is triggered by onclose.
        };
    }

    canReconnect(closeEvent) {
        if (this.reconnectAttempt >= this.options.maxRetries) return false;
        if (typeof this.options.shouldReconnect === 'function') {
            try {
                return Boolean(this.options.shouldReconnect(closeEvent));
            } catch {
                return true;
            }
        }
        return true;
    }

    computeReconnectDelay(attemptNumber) {
        const cappedAttempt = Math.max(0, attemptNumber - 1);
        const expDelay = this.options.initialDelay * Math.pow(this.options.factor, cappedAttempt);
        const baseDelay = Math.min(expDelay, this.options.maxDelay);

        const jitterRatio = Math.max(0, Math.min(1, this.options.jitter));
        const minDelay = baseDelay * (1 - jitterRatio);
        const maxDelay = baseDelay * (1 + jitterRatio);
        const jitteredDelay = minDelay + Math.random() * (maxDelay - minDelay);

        return Math.min(this.options.maxDelay, Math.max(0, jitteredDelay));
    }

    scheduleReconnect() {
        if (this.forcedClose || this.reconnectTimer) return;

        const nextAttempt = this.reconnectAttempt + 1;
        const delay = this.computeReconnectDelay(nextAttempt);

        if (this.onreconnect) {
            this.onreconnect({ attempt: nextAttempt, delay });
        }

        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.reconnectAttempt = nextAttempt;
            this.open();
        }, delay);
    }

    handleError(err) {
        if (this.onerror) this.onerror(err);
        this.scheduleReconnect();
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(data);
            return true;
        }
        return false;
    }

    close() {
        this.forcedClose = true;
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (!this.ws) return;

        this.ws.onopen = null;
        this.ws.onmessage = null;
        this.ws.onclose = null;
        this.ws.onerror = null;

        if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
            this.ws.close();
        }

        this.ws = null;
    }

    get readyState() {
        return this.ws ? this.ws.readyState : WebSocket.CLOSED;
    }
}
