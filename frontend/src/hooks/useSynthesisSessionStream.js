// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { supabase } from '../lib/supabaseClient';
import { getSynthesisEventsEndpoint } from '../services/api.synthesis';

export function useSynthesisSessionStream(sessionId, callbacks = {}) {
    const [status, setStatus] = useState('idle');
    const [stages, setStages] = useState([]);
    const [reconnectCount, setReconnectCount] = useState(0);
    const [latencyMs, setLatencyMs] = useState(null);

    const callbacksRef = useRef(callbacks);
    useEffect(() => { callbacksRef.current = callbacks; }, [callbacks]);

    const getEventsUrl = useCallback(
        (id) => getSynthesisEventsEndpoint(id),
        []
    );

    useEffect(() => {
        if (!sessionId) return;

        let eventSource = null;
        let reconnectTimer = null;
        let attempt = 0;
        let isMounted = true;
        let connectionStartTime = null;
        const maxRetries = 5;

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

            eventSource.addEventListener('connected', (e) => {
                setStatus('streaming');
                attempt = 0;
                setReconnectCount(0);
                if (connectionStartTime) {
                    setLatencyMs(Date.now() - connectionStartTime);
                    connectionStartTime = null;
                }
                if (callbacksRef.current.onConnected) callbacksRef.current.onConnected(e.data);
            });

            eventSource.addEventListener('stage_start', (e) => {
                try {
                    const data = JSON.parse(e.data);
                    setStages(prev => {
                        const newStages = [...prev];
                        const idx = newStages.findIndex(s => s.name === data.name);
                        if (idx >= 0) newStages[idx] = { ...newStages[idx], ...data, status: 'in_progress' };
                        else newStages.push({ ...data, status: 'in_progress' });
                        return newStages;
                    });
                    if (callbacksRef.current.onStageStart) callbacksRef.current.onStageStart(data);
                } catch { /* ignore malformed JSON */ }
            });

            eventSource.addEventListener('stage_complete', (e) => {
                try {
                    const data = JSON.parse(e.data);
                    setStages(prev => {
                        const newStages = [...prev];
                        const idx = newStages.findIndex(s => s.name === data.name);
                        if (idx >= 0) newStages[idx] = { ...newStages[idx], ...data, status: 'done' };
                        else newStages.push({ ...data, status: 'done' });
                        return newStages;
                    });
                    if (callbacksRef.current.onStageComplete) callbacksRef.current.onStageComplete(data);
                } catch { /* ignore malformed JSON */ }
            });

            eventSource.addEventListener('synthesis_complete', (e) => {
                setStatus('done');
                try {
                    const doc = JSON.parse(e.data);
                    if (callbacksRef.current.onSynthesisComplete) callbacksRef.current.onSynthesisComplete(doc);
                } catch { /* ignore malformed JSON */ }
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
                
                if (attempt < maxRetries) {
                    attempt++;
                    setReconnectCount(attempt);
                    // Backoff: 2s -> 4s -> 8s -> 16s -> 32s
                    const backoff = Math.pow(2, attempt) * 1000;
                    
                    reconnectTimer = setTimeout(connect, backoff);
                }
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
