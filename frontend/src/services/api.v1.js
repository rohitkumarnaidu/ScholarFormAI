// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import {
    fetchWithRetry,
    getAuthorizedHeaders,
    getFriendlyErrorMessage,
    parseResponseData,
    parseApiResponse,
    handleUnauthorizedSession,
    generateRequestId,
} from './api.core';
import { GeneratorSessionsResponseSchema } from '../lib/schemas';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const BASE_V1_URL = `${API_BASE_URL}/api/v1`;

const generateIdempotencyHash = async (text) => {
    if (typeof crypto !== 'undefined' && crypto.subtle) {
        const msgUint8 = new TextEncoder().encode(text);
        const hashBuffer = await crypto.subtle.digest('SHA-256', msgUint8);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
    }
    // Fallback for non-secure contexts
    let hash = 0;
    for (let i = 0; i < text.length; i += 1) {
        const char = text.charCodeAt(i);
        hash = (hash << 5) - hash + char;
        hash |= 0;
    }
    return hash.toString(16);
};

/**
 * Get an idempotency key tied to a specific path and request body.
 * Caches it in sessionStorage for 5 minutes.
 */
const getIdempotencyKey = async (path, bodyStr) => {
    try {
        const hashInput = `${path}:${bodyStr}`;
        const hash = await generateIdempotencyHash(hashInput);
        const cacheKey = `idemp_${hash}`;
        
        const existing = sessionStorage.getItem(cacheKey);
        if (existing) {
            const parsed = JSON.parse(existing);
            // 5 minute TTL
            if (Date.now() - parsed.timestamp < 300000) {
                return parsed.key;
            }
        }
        
        const newKey = generateRequestId();
        sessionStorage.setItem(cacheKey, JSON.stringify({ key: newKey, timestamp: Date.now() }));
        return newKey;
    } catch (e) {
        // Fallback safely if sessionStorage goes wrong (e.g., SSR)
        return generateRequestId();
    }
};

/**
 * Core wrapper for v1 API fetch ensuring consistent headers and response mapping.
 */
const fetchV1 = async (endpoint, options = {}) => {
    const {
        suppressConsoleError = false,
        ...requestOptions
    } = options;

    const url = `${BASE_V1_URL}${endpoint}`;
    const requestId = generateRequestId();
    const method = (requestOptions.method || 'GET').toUpperCase();

    // Base specific headers for v1
    const v1Headers = {
        'X-Request-Id': requestId,
        ...requestOptions.headers,
    };

    // Apply Idempotency-Key for POSTs automatically
    if (method === 'POST') {
        const bodyStr = requestOptions.body ? String(requestOptions.body) : '';
        v1Headers['Idempotency-Key'] = await getIdempotencyKey(endpoint, bodyStr);
    }

    try {
        const headers = await getAuthorizedHeaders(v1Headers);
        const { retryConfig, ...fetchOptions } = requestOptions;
        
        const finalOptions = {
            ...fetchOptions,
            headers,
            credentials: fetchOptions.credentials || 'include',
            method
        };

        const response = await fetchWithRetry(url, finalOptions, retryConfig);
        
        // v1 envelope parsing mapping
        let payload;
        try {
            payload = await parseResponseData(response);
        } catch {
            payload = null;
        }

        if (!response.ok) {
            if (response.status === 401) {
                await handleUnauthorizedSession({ endpoint });
            }
            throw new Error(
                getFriendlyErrorMessage({
                    status: response.status,
                    errorData: payload?.error || payload, // Try pulling .error out of envelope if available
                    fallbackMessage: `Request failed (${response.status})`,
                    endpoint,
                })
            );
        }

        // Return standardized Envelope
        return {
            data: payload?.data ?? payload,
            error: payload?.error ?? null,
            requestId: payload?.request_id || payload?.requestId || response.headers?.get?.('X-Request-Id') || requestId,
            timestamp: payload?.timestamp || new Date().toISOString(),
        };

    } catch (error) {
        const finalMessage = getFriendlyErrorMessage({
            error,
            fallbackMessage: typeof error?.message === 'string' ? error.message : String(error || ''),
            endpoint,
        });

        if (!suppressConsoleError) {
            console.error(`API V1 Error [${endpoint}]:`, finalMessage, error);
        }

        throw new Error(finalMessage);
    }
};

/**
 * Unwrap function unboxes envelope and purely returns `data` payload or explicitly throws wrapped `error`.
 */
export const unwrapResponse = (envelope) => {
    if (envelope?.error) {
        throw new Error(envelope.error.message || String(envelope.error));
    }
    return envelope?.data;
};

// V1 Helper Exports
export const getV1 = (path, options = {}) => fetchV1(path, { ...options, method: 'GET' });
export const postV1 = (path, body, options = {}) => fetchV1(path, { ...options, method: 'POST', body: typeof body === 'string' ? body : JSON.stringify(body), headers: { ...options.headers, 'Content-Type': 'application/json' }});
export const putV1 = (path, body, options = {}) => fetchV1(path, { ...options, method: 'PUT', body: typeof body === 'string' ? body : JSON.stringify(body), headers: { ...options.headers, 'Content-Type': 'application/json' }});
export const deleteV1 = (path, options = {}) => fetchV1(path, { ...options, method: 'DELETE' });

// ── Generator session helpers ────────────────────────────────
/**
 * Fetch the current user's generator session list.
 * Replaces previous naked fetch in SessionHistory.jsx.
 */
export const getGeneratorSessions = async (options = {}) => {
    const envelope = await getV1('/generator/sessions', {
        suppressConsoleError: true,
        ...options,
    });
    const raw = unwrapResponse(envelope);
    return parseApiResponse(GeneratorSessionsResponseSchema, raw, { fallback: { sessions: [] } });
};

/**
 * Delete a generator session by ID.
 * Replaces previous naked fetch in SessionHistory.jsx.
 */
export const deleteGeneratorSession = async (sessionId) => {
    const envelope = await deleteV1(`/generator/sessions/${encodeURIComponent(sessionId)}`);
    return unwrapResponse(envelope);
};
