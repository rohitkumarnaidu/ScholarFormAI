// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { fetchWithAuth } from './api.core';

export async function createSynthesisSession(files, template, config) {
    const formData = new FormData();
    formData.append('session_type', 'multi_doc');
    if (template) formData.append('template', template);
    if (config) formData.append('config', JSON.stringify(config));

    files.forEach(file => {
        formData.append('files', file);
    });

    const response = await fetchWithAuth('/api/v1/synthesis/sessions', {
        method: 'POST',
        body: formData,
    });

    return response;
}

export async function getSynthesisSession(sessionId) {
    return fetchWithAuth(`/api/v1/synthesis/sessions/${sessionId}`, { method: 'GET' });
}

export async function sendSynthesisMessage(sessionId, content) {
    return fetchWithAuth(`/api/v1/synthesis/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
    });
}

export function getSynthesisEventsEndpoint(sessionId) {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return `${API_BASE_URL}/api/v1/synthesis/sessions/${sessionId}/events`;
}
