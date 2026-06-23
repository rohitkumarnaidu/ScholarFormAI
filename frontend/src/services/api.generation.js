// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import {
    API_BASE_URL,
    fetchWithAuth,
    fetchWithRetry,
    getAuthorizedHeaders,
    getFriendlyErrorMessage,
    normalizeExportFormat,
    sanitizePayload,
    unwrapV1Payload,
} from './api.core';

const buildV1SessionPayload = (rawPayload) => {
    const sanitizedPayload = sanitizePayload(rawPayload || {});
    const sessionType = String(sanitizedPayload?.session_type || 'agent');

    if (
        sanitizedPayload?.prompt
        || sanitizedPayload?.user_prompt
        || sanitizedPayload?.content
        || sanitizedPayload?.session_type
    ) {
        return {
            session_type: sessionType,
            ...sanitizedPayload,
        };
    }

    const docType = String(sanitizedPayload?.doc_type || 'document').trim();
    const template = sanitizedPayload?.template;
    const metadata = sanitizedPayload?.metadata && typeof sanitizedPayload.metadata === 'object'
        ? sanitizedPayload.metadata
        : {};
    const summaryPrompt = String(
        metadata?.abstract
        || metadata?.summary
        || metadata?.objective
        || metadata?.title
        || `Generate a ${docType.replace(/_/g, ' ')}.`
    );

    return {
        session_type: 'agent',
        template,
        prompt: summaryPrompt,
        config: {
            doc_type: docType,
            metadata,
            options: sanitizedPayload?.options || {},
        },
    };
};

export const generateDocument = async (payload) => {
    const v1Payload = buildV1SessionPayload(payload);
    const response = await fetchWithAuth('/api/v1/generator/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(v1Payload),
    });
    const data = unwrapV1Payload(response) || {};
    const sessionId = data.session_id || data.id || null;
    return sessionId ? { ...data, id: sessionId, job_id: sessionId } : data;
};

export const getGenerationStatus = async (jobId) => (
    fetchWithAuth(`/api/v1/generator/sessions/${encodeURIComponent(jobId)}`).then((payload) => {
        const data = unwrapV1Payload(payload) || {};
        const id = data.id || data.session_id || jobId;
        return { ...data, id, job_id: id };
    })
);

export const streamGenerationStatus = (jobId, onEvent, onError) => {
    const abortController = new AbortController();
    let closed = false;

    const closeStream = () => {
        if (closed) return;
        closed = true;
        abortController.abort();
    };

    (async () => {
        try {
            const headers = await getAuthorizedHeaders({ Accept: 'text/event-stream' });
            if (abortController.signal.aborted) return;

            const response = await fetchWithRetry(`${API_BASE_URL}/api/v1/stream/${encodeURIComponent(jobId)}`, {
                method: 'GET',
                headers,
                credentials: 'include',
                signal: abortController.signal,
            });

            if (!response.ok || !response.body) {
                throw new Error(`Failed to open generation stream (${response.status})`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (!abortController.signal.aborted) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });

                let boundaryIndex = buffer.indexOf('\n\n');
                while (boundaryIndex !== -1) {
                    const frame = buffer.slice(0, boundaryIndex);
                    buffer = buffer.slice(boundaryIndex + 2);
                    boundaryIndex = buffer.indexOf('\n\n');

                    let eventType = 'message';
                    const dataLines = [];

                    for (const lineRaw of frame.split(/\r?\n/)) {
                        const line = lineRaw.trimEnd();
                        if (line.startsWith('event:')) {
                            eventType = line.slice(6).trim();
                        } else if (line.startsWith('data:')) {
                            dataLines.push(line.slice(5).trim());
                        }
                    }

                    if (!dataLines.length) continue;

                    const payloadRaw = dataLines.join('\n');
                    let payload = payloadRaw;
                    try {
                        payload = JSON.parse(payloadRaw);
                    } catch {
                        // Keep raw payload if not JSON.
                    }

                    if (typeof onEvent === 'function') {
                        onEvent({ event: eventType, data: payload });
                    }
                }
            }
        } catch (error) {
            if (abortController.signal.aborted) return;
            if (typeof onError === 'function') {
                onError(error instanceof Error ? error : new Error(String(error)));
            }
        }
    })();

    return closeStream;
};

export const downloadGeneratedDocument = async (jobId, format = 'docx') => {
    const normalizedFormat = normalizeExportFormat(format);
    const headers = await getAuthorizedHeaders();
    const response = await fetchWithRetry(
        `${API_BASE_URL}/api/v1/generator/sessions/${encodeURIComponent(jobId)}/download?format=${normalizedFormat}`,
        { headers, method: 'GET', credentials: 'include' }
    );

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
            getFriendlyErrorMessage({
                status: response.status,
                errorData,
                fallbackMessage: 'Generation download failed.',
            })
        );
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    return {
        url,
        cleanup: () => window.URL.revokeObjectURL(url),
    };
};
