// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { postV1, unwrapResponse } from './api.v1';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * HTTP fallback for live preview when WebSocket is not connected.
 * POSTs content + templateId and returns rendered HTML.
 *
 * @param {string} content     - Plain text or HTML content
 * @param {string} templateId  - Template identifier slug
 * @returns {Promise<{html: string, warnings: string[]}>}
 */
export async function getPreviewHtml(content, templateId) {
    const response = await postV1('/preview/live', {
        content: content || '',
        template_id: templateId || null,
    });
    return unwrapResponse(response);
}

/**
 * Open an EventSource (SSE) stream for AI suggestions.
 * The caller must attach .onmessage / .onerror listeners and call .close() when done.
 *
 * @param {string} sessionId   - Session UUID
 * @param {string} content     - Current editor content (sent as query param)
 * @param {string} templateId  - Template identifier slug
 * @param {string} [token]     - Optional auth token for query-param auth
 * @returns {EventSource}
 */
export function getAiSuggestion(sessionId, content, templateId, token) {
    const params = new URLSearchParams({
        template_id: templateId || '',
        content_hash: String(content?.length ?? 0), // lightweight hint, not full content in URL
    });
    if (token) {
        params.set('token', token);
    }
    const url = `${API_BASE_URL}/api/v1/preview/${encodeURIComponent(sessionId)}/ai-suggest?${params.toString()}`;
    return new EventSource(url, { withCredentials: true });
}
