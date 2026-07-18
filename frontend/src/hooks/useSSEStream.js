'use client';
import { useState, useEffect, useRef } from 'react';
import { supabase } from '../lib/supabaseClient';

export function useSSEStream(sessionId, getEventsUrl, { maxRetries = Infinity, streamName = 'SSE', onMaxRetriesExceeded } = {}) {
    const [eventSource, setEventSource] = useState(null);
    const [status, setStatus] = useState('idle');
    const [reconnectCount, setReconnectCount] = useState(0);

    const getEventsUrlRef = useRef(getEventsUrl);
    const onMaxRetriesExceededRef = useRef(onMaxRetriesExceeded);
    getEventsUrlRef.current = getEventsUrl;
    onMaxRetriesExceededRef.current = onMaxRetriesExceeded;

    useEffect(() => {
        if (!sessionId) return;

        let es = null;
        let reconnectTimer = null;
        let attempt = 0;
        let isMounted = true;

        const connect = async () => {
            if (!isMounted) return;

            setStatus(attempt === 0 ? 'connecting' : 'reconnecting');

            let token = null;
            if (supabase) {
                try {
                    const { data: { session } } = await supabase.auth.getSession();
                    token = session?.access_token;
                } catch (err) {
                    console.error(`[${streamName}] Auth session retrieval failed:`, err);
                }
            }

            const url = new URL(getEventsUrlRef.current(sessionId));
            if (token) url.searchParams.set('token', token);

            es = new EventSource(url.toString(), { withCredentials: true });
            setEventSource(es);

            es.onopen = () => {
                if (!isMounted) return;
                setStatus('streaming');
                attempt = 0;
                setReconnectCount(0);
            };

            es.onerror = () => {
                if (!isMounted) return;
                es.close();
                setEventSource(null);
                setStatus('error');

                if (maxRetries === Infinity || attempt < maxRetries) {
                    attempt++;
                    setReconnectCount(attempt);
                    const rawBackoff = maxRetries === Infinity
                        ? Math.min(Math.pow(2, attempt - 1) * 1000, 30000)
                        : Math.pow(2, attempt) * 1000;
                    reconnectTimer = setTimeout(connect, rawBackoff);
                } else {
                    if (onMaxRetriesExceededRef.current) onMaxRetriesExceededRef.current();
                }
            };
        };

        connect();

        return () => {
            isMounted = false;
            if (es) es.close();
            if (reconnectTimer) clearTimeout(reconnectTimer);
        };
    }, [sessionId, maxRetries, streamName]);

    return { status, reconnectCount, eventSource, setStatus };
}
