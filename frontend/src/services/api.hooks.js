// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { useState, useEffect, useRef, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';

import {
    getDocuments,
    getJobStatus,
    mapDocumentRecord,
    normalizeDocumentsParams,
} from './api.documents';

import {
    getMetricsHealth,
    getMetricsDashboard,
} from './api.metrics';

import { streamGenerationStatus } from './api.generation';

export const useDocuments = (params = {}, queryOptions = {}) => {
    const normalizedParams = normalizeDocumentsParams(params);

    return useQuery({
        queryKey: ['documents', normalizedParams],
        queryFn: () => getDocuments(normalizedParams),
        select: (data) => ({
            ...data,
            documents: Array.isArray(data?.documents)
                ? data.documents.map(mapDocumentRecord)
                : [],
        }),
        ...queryOptions,
    });
};

export const useDocumentStatus = (jobId, queryOptions = {}) => (
    useQuery({
        queryKey: ['document-status', jobId],
        queryFn: ({ signal }) => getJobStatus(jobId, { signal }),
        ...queryOptions,
        enabled: Boolean(jobId) && (queryOptions.enabled ?? true),
    })
);

export const useMetricsHealth = (queryOptions = {}) => (
    useQuery({
        queryKey: ['metrics-health'],
        queryFn: () => getMetricsHealth(),
        retry: false,
        refetchOnWindowFocus: false,
        refetchOnReconnect: false,
        ...queryOptions,
    })
);

export const useMetricsDashboard = (queryOptions = {}) => (
    useQuery({
        queryKey: ['metrics-dashboard'],
        queryFn: () => getMetricsDashboard(),
        retry: false,
        refetchOnWindowFocus: false,
        refetchOnReconnect: false,
        ...queryOptions,
    })
);

// ── SSE-based job status hook ────────────────────────────────
/**
 * useJobStatusSSE — real-time job status via Server-Sent Events.
 *
 * Connects to /api/v1/stream/{jobId} using the existing `streamGenerationStatus`
 * fetch-SSE reader. Falls back to polling (via `useDocumentStatus`) when
 * ReadableStream is not available (HTTP/1.1 proxies, some mobile browsers).
 *
 * @param {string|null} jobId
 * @param {{ onEvent?: Function, onDone?: Function, onError?: Function,
 *           enabled?: boolean, pollFallbackMs?: number }} opts
 * @returns {{ data: object|null, error: Error|null, connected: boolean, isPolling: boolean }}
 */
export const useJobStatusSSE = (jobId, opts = {}) => {
    const {
        onEvent,
        onDone,
        onError,
        enabled = true,
        pollFallbackMs = 2500,
    } = opts;

    // Detect fetch-SSE support (ReadableStream + fetch body streaming)
    const sseSupported =
        typeof window !== 'undefined' &&
        typeof ReadableStream !== 'undefined';

    const [sseData, setSseData] = useState(null);
    const [sseError, setSseError] = useState(null);
    const [connected, setConnected] = useState(false);
    const closeRef = useRef(null);

    const handleEvent = useCallback(
        ({ event, data }) => {
            setSseData(data);
            if (event === 'done' || data?.status === 'COMPLETED' || data?.status === 'completed') {
                if (typeof onDone === 'function') onDone(data);
            } else {
                if (typeof onEvent === 'function') onEvent({ event, data });
            }
        },
        [onDone, onEvent]
    );

    const handleError = useCallback(
        (err) => {
            setSseError(err);
            setConnected(false);
            if (typeof onError === 'function') onError(err);
        },
        [onError]
    );

    useEffect(() => {
        if (!jobId || !enabled || !sseSupported) return;

        setConnected(true);
        setSseData(null);
        setSseError(null);

        const close = streamGenerationStatus(jobId, handleEvent, handleError);
        closeRef.current = close;

        return () => {
            if (typeof closeRef.current === 'function') closeRef.current();
            closeRef.current = null;
            setConnected(false);
        };
    // handleEvent/handleError are memoised; jobId/enabled/sseSupported are primitives.
    }, [jobId, enabled, sseSupported, handleEvent, handleError]);

    // Polling fallback – only active when SSE is not available
    const pollQuery = useDocumentStatus(
        !sseSupported ? jobId : null,
        {
            enabled: Boolean(jobId) && enabled && !sseSupported,
            refetchInterval: pollFallbackMs,
            staleTime: 0,
        }
    );

    if (!sseSupported) {
        return {
            data: pollQuery.data ?? null,
            error: pollQuery.error ?? null,
            connected: false,
            isPolling: true,
        };
    }

    return { data: sseData, error: sseError, connected, isPolling: false };
};
