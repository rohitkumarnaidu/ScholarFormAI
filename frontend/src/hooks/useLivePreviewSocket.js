// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import ReconnectingWebSocket from '../lib/ReconnectingWebSocket';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Lightweight checksum to avoid importing a hashing dependency.
function simpleHash(str) {
    let h = 0;
    for (let i = 0; i < str.length; i++) {
        h = (Math.imul(31, h) + str.charCodeAt(i)) | 0;
    }
    return (h >>> 0).toString(16);
}

function getWsUrl(sessionId) {
    // Convert http(s):// to ws(s)://
    const base = API_BASE_URL.replace(/^http/, 'ws');
    return `${base}/api/v1/ws/preview/${sessionId}`;
}

/**
 * Connects to the backend preview WebSocket endpoint.
 *
 * @param {string} sessionId - UUID for this session
 * @returns {{ html: string, latencyMs: number|null, warnings: string[], isConnected: boolean, isReconnecting: boolean, reconnectAttempt: number, isAnalyzing: boolean, sendContent: Function }}
 */
export default function useLivePreviewSocket(sessionId) {
    const [html, setHtml] = useState('');
    const [latencyMs, setLatencyMs] = useState(null);
    const [warnings, setWarnings] = useState([]);
    const [isConnected, setIsConnected] = useState(false);
    const [isReconnecting, setIsReconnecting] = useState(false);
    const [reconnectAttempt, setReconnectAttempt] = useState(0);
    const [isAnalyzing, setIsAnalyzing] = useState(false);

    const wsRef = useRef(null);
    const debounceTimerRef = useRef(null);
    const seqRef = useRef(0);
    const sentAtRef = useRef(null);
    const lastContentRef = useRef('');
    const pendingPayloadRef = useRef(null);

    useEffect(() => {
        if (!sessionId) return;

        const url = getWsUrl(sessionId);
        const rws = new ReconnectingWebSocket(url, {
            initialDelay: 1000,
            maxDelay: 30000,
            factor: 2,
            jitter: 0.3,
        });
        wsRef.current = rws;

        rws.onopen = () => {
            setIsConnected(true);
            setIsReconnecting(false);
            setReconnectAttempt(0);
            const pendingPayload = pendingPayloadRef.current;
            if (pendingPayload) {
                sentAtRef.current = Date.now();
                setIsAnalyzing(true);
                rws.send(JSON.stringify(pendingPayload));
            }
        };

        rws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.html !== undefined) setHtml(msg.html);
                if (msg.warnings !== undefined) setWarnings(msg.warnings || []);
                if (sentAtRef.current) {
                    setLatencyMs(Date.now() - sentAtRef.current);
                    sentAtRef.current = null;
                }
                setIsAnalyzing(false);
            } catch {
                // Ignore malformed frames.
            }
        };

        rws.onclose = () => {
            setIsConnected(false);
        };

        rws.onerror = () => {
            setIsConnected(false);
        };

        rws.onreconnect = ({ attempt }) => {
            setIsConnected(false);
            setIsReconnecting(true);
            setReconnectAttempt(attempt);
        };

        return () => {
            clearTimeout(debounceTimerRef.current);
            rws.close();
            wsRef.current = null;
        };
    }, [sessionId]);

    // Debounced send. If the socket is down, keep the latest payload queued
    // and replay it on the next successful reconnect.
    const sendContent = useCallback((content, templateId) => {
        const diff = Math.abs((content?.length || 0) - (lastContentRef.current?.length || 0));
        if (diff > 1000) {
            setIsAnalyzing(true);
        }
        lastContentRef.current = content || '';

        clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = setTimeout(() => {
            seqRef.current += 1;
            const payload = {
                content: content || '',
                templateId: templateId || null,
                cursor: null,
                checksum: simpleHash(content || ''),
                seq: seqRef.current,
            };
            pendingPayloadRef.current = payload;

            if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
                setIsAnalyzing(true);
                return;
            }

            sentAtRef.current = Date.now();
            wsRef.current.send(JSON.stringify(payload));
        }, 200);
    }, []);

    return { html, latencyMs, warnings, isConnected, isReconnecting, reconnectAttempt, isAnalyzing, sendContent };
}
