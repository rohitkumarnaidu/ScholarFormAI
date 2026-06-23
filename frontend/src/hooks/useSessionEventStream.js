// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabaseClient';

export function useSessionEventStream(sessionId, getEventsUrl, streamName) {
    const [stages, setStages] = useState([]);
    const [currentStage, setCurrentStage] = useState('');
    const [progress, setProgress] = useState(0);
    const [isComplete, setIsComplete] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!sessionId) return;

        let eventSource = null;
        let reconnectTimeout = null;
        let retryCount = 0;
        const maxRetries = 5;
        let isMounted = true;

        const connect = async () => {
            if (!isMounted) return;

            let token = null;
            if (supabase) {
                try {
                    const { data: { session } } = await supabase.auth.getSession();
                    token = session?.access_token;
                } catch (err) {
                    console.error(`[${streamName}] Auth session retrieval failed:`, err);
                }
            }

            const url = new URL(getEventsUrl(sessionId));
            if (token) {
                url.searchParams.set('token', token);
            }

            eventSource = new EventSource(url.toString(), { withCredentials: true });

            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    if (data.name) {
                        setStages(prev => {
                            const newStages = [...prev];
                            const existingIndex = newStages.findIndex(s => s.name === data.name);
                            if (existingIndex >= 0) {
                                newStages[existingIndex] = { ...newStages[existingIndex], ...data };
                            } else {
                                newStages.push(data);
                            }
                            return newStages;
                        });

                        setCurrentStage(data.name);
                    }

                    if (data.progress !== undefined) {
                        setProgress(data.progress);
                    }

                    if (data.progress >= 100 || (data.status === 'done' && !data.name) || (data.name === 'Template Rendering' && data.status === 'done')) {
                        setIsComplete(true);
                    }

                    if (data.status === 'error') {
                        setError(new Error(data.message || 'Error during synthesis'));
                    }

                } catch (err) {
                    console.error('Error parsing SSE data', err);
                }
            };

            eventSource.onerror = (err) => {
                console.error('SSE Error', err);
                eventSource.close();

                if (retryCount < maxRetries && isMounted) {
                    retryCount++;
                    const backoff = Math.pow(2, retryCount) * 1000;
                    reconnectTimeout = setTimeout(connect, backoff);
                } else if (isMounted) {
                    setError(new Error('Lost connection to synthesis stream. Please refresh.'));
                }
            };
        };

        connect();

        return () => {
            isMounted = false;
            if (eventSource) eventSource.close();
            if (reconnectTimeout) clearTimeout(reconnectTimeout);
        };
    }, [sessionId, getEventsUrl, streamName]);

    return { stages, currentStage, progress, isComplete, error };
}
