// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { supabase } from '../lib/supabaseClient';
import { API_BASE_URL } from '../services/api.v1';

export function useGeneratorSessionStream(sessionId, callbacks = {}) {
    const [status, setStatus] = useState('idle');
    const [stages, setStages] = useState([]);
    const [reconnectCount, setReconnectCount] = useState(0);
    const [latencyMs, setLatencyMs] = useState(null);

    const callbacksRef = useRef(callbacks);
    useEffect(() => { callbacksRef.current = callbacks; }, [callbacks]);

    const getEventsUrl = useCallback(
        (id) => `${API_BASE_URL}/api/v1/generator/sessions/${id}/events`,
        []
    );

    useEffect(() => {
        if (!sessionId) return;

        let eventSource = null;
        let reconnectTimer = null;
        let attempt = 0;
        let isMounted = true;
        let connectionStartTime = null;

        const connect = async () => {
            if (!isMounted) return;
            
            setStatus(attempt === 0 ? 'connecting' : 'reconnecting');
            
            let token = null;
            if (supabase) {
                try {
                    const { data: { session } } = await supabase.auth.getSession();
                    token = session?.access_token;
                } catch (err) {
                    console.error('Auth session retrieval failed:', err);
                }
            }

            const url = new URL(getEventsUrl(sessionId));
            if (token) {
                url.searchParams.set('token', token);
            }

            connectionStartTime = Date.now();
            eventSource = new EventSource(url.toString(), { withCredentials: true });

            eventSource.addEventListener('connected', () => {
                setStatus('streaming');
                attempt = 0;
                setReconnectCount(0);
                if (connectionStartTime) {
                    setLatencyMs(Date.now() - connectionStartTime);
                    connectionStartTime = null;
                }
            });
            
            eventSource.addEventListener('stage', (e) => {
                try {
                    const data = JSON.parse(e.data);
                    setStages(prev => {
                        const newStages = [...prev];
                        const idx = newStages.findIndex(s => s.name === data.name);
                        if (idx >= 0) newStages[idx] = { ...newStages[idx], ...data };
                        else newStages.push(data);
                        return newStages;
                    });
                    if (callbacksRef.current.onStageChange) {
                        callbacksRef.current.onStageChange(data);
                    }
                } catch { /* ignore malformed JSON */ }
            });

            eventSource.addEventListener('token', (e) => {
                try {
                    const tokenData = e.data.startsWith('{') ? JSON.parse(e.data).token : e.data;
                    if (callbacksRef.current.onToken) callbacksRef.current.onToken(tokenData);
                } catch(err) {
                    if (callbacksRef.current.onToken) callbacksRef.current.onToken(e.data);
                }
            });

            eventSource.addEventListener('outline', (e) => {
                try {
                    const outlineData = JSON.parse(e.data);
                    if (callbacksRef.current.onOutline) callbacksRef.current.onOutline(outlineData);
                } catch { /* ignore malformed JSON */ }
            });

            eventSource.addEventListener('complete', (e) => {
                setStatus('done');
                try {
                    const res = JSON.parse(e.data);
                    if (callbacksRef.current.onComplete) callbacksRef.current.onComplete(res);
                } catch(err) {
                    if (callbacksRef.current.onComplete) callbacksRef.current.onComplete(e.data);
                }
            });
            
            eventSource.addEventListener('error', (e) => {
                setStatus('error');
                try {
                    const errData = JSON.parse(e.data);
                    if (callbacksRef.current.onError) callbacksRef.current.onError(errData);
                } catch(err) {
                    if (callbacksRef.current.onError) callbacksRef.current.onError(e.data);
                }
            });

            eventSource.onerror = () => {
                if (!isMounted) return;
                eventSource.close();
                
                setStatus('error');
                
                attempt++;
                setReconnectCount(attempt);
                // Backoff: 1s -> 2s -> 4s -> 8s -> max 30s
                const rawBackoff = Math.pow(2, attempt - 1) * 1000;
                const backoff = Math.min(rawBackoff, 30000);
                
                reconnectTimer = setTimeout(connect, backoff);
            };
        };

        connect();

        return () => {
            isMounted = false;
            if (eventSource) eventSource.close();
            if (reconnectTimer) clearTimeout(reconnectTimer);
        };
    }, [sessionId, getEventsUrl]);

    return { status, stages, reconnectCount, latencyMs };
}
