// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { supabase } from '../lib/supabaseClient';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const API_BASE = API_BASE_URL;

const SUPPORTED_EXPORT_FORMATS = ['docx', 'pdf', 'tex'];
const RETRYABLE_STATUS_CODES = [408, 429, 500, 502, 503, 504];
const DEFAULT_MAX_RETRIES = 2;
const BASE_RETRY_DELAY_MS = 500;
const SENSITIVE_INPUT_KEYS = /(password|otp|token|secret)/i;
const APP_SESSION_STORAGE_KEYS = [
    'scholarform_currentJob',
    'scholarform_job',
    'scholarform_active_job',
    'scholarform_e2e_user',
];
export const CHUNK_SIZE_BYTES = 5 * 1024 * 1024;
export const CHUNK_UPLOAD_THRESHOLD_BYTES = 10 * 1024 * 1024;

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const AUTH_RECOVERY_IN_FLIGHT = new Map();

/**
 * Generate a UUID v4 for Request IDs.
 * Falls back to Math.random() if crypto.randomUUID is unavailable (e.g. older browsers / non-secure contexts).
 */
export const generateRequestId = () => {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
        return crypto.randomUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        const v = c === 'x' ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
};

export const unwrapV1Payload = (payload) => {
    if (payload && typeof payload === 'object' && 'data' in payload) {
        return payload.data;
    }
    return payload;
};

const removeControlChars = (input) => (
    Array.from(String(input ?? ''))
        .filter((char) => {
            const code = char.charCodeAt(0);
            return code >= 32 && code !== 127;
        })
        .join('')
);

const decodeHtmlEntities = (text) => (
    String(text)
        .replace(/&#60;/g, '<')
        .replace(/&#62;/g, '>')
        .replace(/&#38;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&amp;/g, '&')
        .replace(/&quot;/g, '"')
        .replace(/&#x27;/g, "'")
        .replace(/&#039;/g, "'")
);

export const sanitizeText = (value) => (
    removeControlChars(decodeHtmlEntities(value))
        .replace(/[<>]/g, '')
        .trim()
);

const sanitizeValue = (value, path = '') => {
    if (typeof value === 'string') {
        if (SENSITIVE_INPUT_KEYS.test(path)) {
            return value.trim();
        }
        return sanitizeText(value);
    }

    if (Array.isArray(value)) {
        return value.map((entry, index) => sanitizeValue(entry, `${path}.${index}`));
    }

    if (value && typeof value === 'object') {
        return Object.entries(value).reduce((accumulator, [key, nestedValue]) => {
            const nextPath = path ? `${path}.${key}` : key;
            accumulator[key] = sanitizeValue(nestedValue, nextPath);
            return accumulator;
        }, {});
    }

    return value;
};

export const sanitizePayload = (payload) => sanitizeValue(payload);

export const isNetworkError = (error) => {
    if (!error) return false;

    const message = String(error.message || error).toLowerCase();
    return (
        error.name === 'TypeError'
        || message.includes('failed to fetch')
        || message.includes('networkerror')
        || message.includes('network request failed')
        || message.includes('load failed')
        || message.includes('timeout')
    );
};

const extractServerErrorMessage = (errorData, fallbackMessage = '') => {
    if (!errorData || typeof errorData !== 'object') {
        return fallbackMessage;
    }

    if (typeof errorData.detail === 'string') {
        return errorData.detail;
    }

    if (Array.isArray(errorData.detail)) {
        return errorData.detail
            .map((entry) => entry.msg || JSON.stringify(entry))
            .join('. ');
    }

    if (typeof errorData.detail === 'object') {
        return JSON.stringify(errorData.detail);
    }

    return fallbackMessage;
};

export const getFriendlyErrorMessage = ({
    status,
    errorData,
    fallbackMessage = '',
    error,
    endpoint = '',
} = {}) => {
    if (status === 401) {
        if (typeof endpoint === 'string' && endpoint.startsWith('/api/v1/auth/login')) {
            return 'Invalid email or password.';
        }
        return 'Your session has expired. Please log in again.';
    }

    if (status === 403) {
        return 'You do not have permission to perform this action.';
    }

    if (status === 404) {
        return 'The requested resource could not be found.';
    }

    if (status === 429) {
        return 'Too many requests right now. Please wait a moment and try again.';
    }

    if (typeof status === 'number' && status >= 500) {
        return 'The server is temporarily unavailable. Please try again shortly.';
    }

    if (isNetworkError(error)) {
        return 'Unable to reach the server. Please check your internet connection and try again.';
    }

    const serverMessage = extractServerErrorMessage(errorData, '');
    if (serverMessage) {
        return serverMessage;
    }

    if (typeof fallbackMessage === 'string' && fallbackMessage.trim()) {
        return fallbackMessage;
    }

    return 'Something went wrong. Please try again.';
};
export const friendlyErrorMessage = getFriendlyErrorMessage;

const isLoginEndpoint = (endpoint = '') => (
    String(endpoint || '').toLowerCase().startsWith('/api/v1/auth/login')
    || String(endpoint || '').toLowerCase().startsWith('/auth/login')
);

const clearSupabaseAuthStorage = () => {
    if (typeof window === 'undefined') return;

    const clearStorageKeys = (storage) => {
        if (!storage) return;
        const toDelete = [];
        for (let idx = 0; idx < storage.length; idx += 1) {
            const key = storage.key(idx);
            if (!key) continue;
            if (key.startsWith('sb-') && key.includes('-auth-token')) {
                toDelete.push(key);
            }
        }
        toDelete.forEach((key) => storage.removeItem(key));
    };

    clearStorageKeys(window.localStorage);
    clearStorageKeys(window.sessionStorage);
};

const clearAppSessionStorage = () => {
    if (typeof window === 'undefined') return;
    APP_SESSION_STORAGE_KEYS.forEach((key) => {
        window.sessionStorage.removeItem(key);
    });
};

const buildNextParam = () => {
    if (typeof window === 'undefined') return '';
    const path = window.location?.pathname || '';
    const search = window.location?.search || '';
    const hash = window.location?.hash || '';
    const nextTarget = `${path}${search}${hash}`;
    if (!nextTarget || nextTarget === '/' || nextTarget.startsWith('/login')) {
        return '';
    }
    return `?next=${encodeURIComponent(nextTarget)}`;
};

const isJsdomEnvironment = () => (
    typeof navigator !== 'undefined'
    && /jsdom/i.test(String(navigator.userAgent || ''))
);

export const handleUnauthorizedSession = async ({ endpoint = '' } = {}) => {
    if (typeof window === 'undefined' || isLoginEndpoint(endpoint)) {
        return;
    }

    const recoveryKey = endpoint || '__default__';
    if (AUTH_RECOVERY_IN_FLIGHT.has(recoveryKey)) return;

    const recoveryPromise = (async () => {
        try {
            if (supabase?.auth?.signOut) {
                await supabase.auth.signOut({ scope: 'local' });
            }
        } catch (error) {
            console.warn('Auth teardown failed after unauthorized response:', error);
        } finally {
            clearAppSessionStorage();
            clearSupabaseAuthStorage();

            try {
                window.dispatchEvent(new CustomEvent('scholarform:session-expired'));
            } catch {
                // no-op in environments without CustomEvent support
            }

            const onLoginRoute = window.location?.pathname?.startsWith('/login');
            if (!onLoginRoute && !isJsdomEnvironment() && typeof window.location?.replace === 'function') {
                const nextParam = buildNextParam();
                try {
                    window.location.replace(`/login${nextParam}`);
                } catch {
                    // Some test runners/JSDOM environments do not implement navigation.
                }
            }
        }
    })();

    AUTH_RECOVERY_IN_FLIGHT.set(recoveryKey, recoveryPromise);

    try {
        await recoveryPromise;
    } finally {
        AUTH_RECOVERY_IN_FLIGHT.delete(recoveryKey);
    }
};

const shouldRetryRequest = ({ method = 'GET', status, error, attempt, maxRetries }) => {
    if (attempt >= maxRetries) {
        return false;
    }

    const normalizedMethod = String(method || 'GET').toUpperCase();
    const isSafeMethod = ['GET', 'HEAD', 'OPTIONS'].includes(normalizedMethod);
    if (!isSafeMethod) {
        return false;
    }

    if (isNetworkError(error)) {
        return true;
    }

    if (typeof status === 'number' && RETRYABLE_STATUS_CODES.includes(status)) {
        return true;
    }

    return false;
};

export const fetchWithRetry = async (url, options = {}, retryConfig = {}) => {
    const maxRetries = retryConfig.maxRetries ?? DEFAULT_MAX_RETRIES;
    const method = options.method || 'GET';
    let lastError = null;

    for (let attempt = 0; attempt <= maxRetries; attempt += 1) {
        try {
            const response = await fetch(url, options);

            if (response.ok) {
                return response;
            }

            if (!shouldRetryRequest({ method, status: response.status, attempt, maxRetries })) {
                return response;
            }
        } catch (error) {
            lastError = error;

            if (!shouldRetryRequest({ method, error, attempt, maxRetries })) {
                throw error;
            }
        }

        await wait(BASE_RETRY_DELAY_MS * (2 ** attempt));
    }

    throw lastError || new Error('Request failed after retries.');
};

const withAuthHeader = async (initialHeaders = {}) => {
    const headers = { ...initialHeaders };

    if (!headers['X-Request-Id']) {
        headers['X-Request-Id'] = generateRequestId();
    }

    if (!supabase?.auth?.getSession) {
        return headers;
    }

    try {
        let session = null;

        // First attempt
        const { data: first } = await supabase.auth.getSession();
        session = first?.session;

        // If no session yet, wait briefly and retry once.
        // This handles the race where the API call fires before Supabase
        // finishes reading the session from localStorage on page load.
        if (!session?.access_token) {
            await new Promise((resolve) => setTimeout(resolve, 300));
            const { data: second } = await supabase.auth.getSession();
            session = second?.session;
        }

        if (session?.access_token) {
            headers.Authorization = `Bearer ${session.access_token}`;
        }
    } catch (error) {
        console.warn('Auth header injection skipped:', error);
    }

    return headers;
};

export const getAuthorizedHeaders = withAuthHeader;
export const getAuthHeaders = getAuthorizedHeaders;

export const parseResponseData = async (response) => {
    if (!response || response.status === 204) {
        return null;
    }

    const contentType = response.headers?.get?.('content-type') || '';
    if (
        typeof response.json === 'function'
        && (contentType.includes('application/json') || typeof response.text !== 'function')
    ) {
        return response.json();
    }

    if (typeof response.text !== 'function') {
        return null;
    }

    const text = await response.text();
    if (!text) {
        return null;
    }

    try {
        return JSON.parse(text);
    } catch {
        return text;
    }
};

export const sendFrontendErrorLog = async (errorInfo) => {
    try {
        const headers = await withAuthHeader({ 'Content-Type': 'application/json' });
        await fetch(`${API_BASE_URL}/api/v1/metrics/log-error`, {
            method: 'POST',
            headers,
            body: JSON.stringify({
                message: errorInfo?.message || String(errorInfo),
                stack: errorInfo?.stack,
                url: typeof window !== 'undefined' ? window.location?.href : '',
                timestamp: new Date().toISOString(),
            }),
        });
    } catch (error) {
        console.warn('Failed to log frontend error to backend:', error);
    }
};

export const fetchWithAuth = async (endpoint, options = {}) => {
    const {
        suppressConsoleError = false,
        suppressMonitoring = false,
        ...requestOptions
    } = options;

    try {
        if (
            typeof navigator !== 'undefined'
            && navigator.onLine === false
            && ['POST', 'PUT', 'DELETE', 'PATCH'].includes((requestOptions.method || 'GET').toUpperCase())
        ) {
            throw new Error('You are currently offline. This action will be queued and retried when you reconnect.');
        }

        const headers = await withAuthHeader(requestOptions.headers);
        const { retryConfig, ...fetchOptions } = requestOptions;
        const finalOptions = {
            ...fetchOptions,
            headers,
            credentials: fetchOptions.credentials || 'include',
        };

        const response = await fetchWithRetry(
            `${API_BASE_URL}${endpoint}`,
            finalOptions,
            retryConfig
        );

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            if (response.status === 401) {
                await handleUnauthorizedSession({ endpoint });
            }
            throw new Error(
                getFriendlyErrorMessage({
                    status: response.status,
                    errorData,
                    fallbackMessage: `Request failed (${response.status})`,
                    endpoint,
                })
            );
        }

        return parseResponseData(response);
    } catch (error) {
        const finalMessage = getFriendlyErrorMessage({
            error,
            fallbackMessage: typeof error?.message === 'string' ? error.message : String(error || ''),
            endpoint,
        });

        if (!suppressConsoleError) {
            console.error(`API Error [${endpoint}]:`, finalMessage, error);
        }

        if (!suppressMonitoring && endpoint !== '/api/v1/metrics/log-error') {
            sendFrontendErrorLog({
                message: `API Error [${endpoint}]: ${finalMessage}`,
                stack: error?.stack,
            });
        }

        throw new Error(finalMessage);
    }
};

export const normalizeExportFormat = (format = 'docx') => {
    const normalized = String(format || 'docx').toLowerCase();
    return SUPPORTED_EXPORT_FORMATS.includes(normalized) ? normalized : 'docx';
};

// ── Newsletter subscription ──────────────────────────────────
/**
 * Subscribe an email to the marketing newsletter.
 * Replaces the naked fetch in Footer.jsx — routes through fetchWithAuth
 * for consistent auth headers and retry behaviour.
 */
export const subscribeNewsletter = async (email) => {
    return fetchWithAuth('/api/v1/marketing/newsletter', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: String(email || '').trim() }),
        // Newsletter endpoint is public-friendly — suppress auth-noise in console
        suppressConsoleError: true,
        suppressMonitoring: true,
    });
};

// ── Runtime Zod response validation ─────────────────────────
/**
 * Parse an API response payload against a Zod schema.
 * On success returns the parsed (and possibly transformed) data.
 * On failure throws a friendly Error so callers don't need to handle
 * subtle undefined-field bugs from contract drift.
 *
 * @param {import('zod').ZodTypeAny} schema - Zod schema to validate against
 * @param {unknown} data - Raw API response payload
 * @param {{ fallback?: unknown }} [opts]
 * @returns {unknown} Validated (and Zod-transformed) data
 */
export const parseApiResponse = (schema, data, opts = {}) => {
    if (!schema || typeof schema.safeParse !== 'function') {
        return data;
    }

    const result = schema.safeParse(data);
    if (result.success) {
        return result.data;
    }

    if ('fallback' in opts) {
        return opts.fallback;
    }

    const firstIssue = result.error?.issues?.[0];
    const fieldPath = firstIssue?.path?.join('.') || 'response';
    const message = firstIssue?.message || 'Unexpected response format.';
    throw new Error(`API contract error at "${fieldPath}": ${message}`);
};
