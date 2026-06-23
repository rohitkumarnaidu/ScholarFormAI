// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { fetchWithAuth } from './api.core';

export async function createSession(files, sessionType, template, config) {
    const formData = new FormData();
    formData.append('session_type', sessionType);
    if (template) formData.append('template_id', template);
    if (config) formData.append('config', JSON.stringify(config));

    files.forEach(file => {
        formData.append('files', file);
    });

    return fetchWithAuth('/api/v1/generator/sessions', {
        method: 'POST',
        body: formData,
    });
}

export async function createAgentSession(prompt, template, config) {
    return fetchWithAuth('/api/v1/generator/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_type: 'agent',
            prompt,
            template,
            config: config || {},
        }),
    });
}

export async function getSession(sessionId) {
    return fetchWithAuth(`/api/v1/generator/sessions/${sessionId}`, { method: 'GET' });
}

export async function getSessionMessages(sessionId, limit = 100) {
    return fetchWithAuth(`/api/v1/generator/sessions/${sessionId}/messages?limit=${limit}`, { method: 'GET' });
}

export async function getSessionDocument(sessionId) {
    return fetchWithAuth(`/api/v1/generator/sessions/${sessionId}/document`, { method: 'GET' });
}

export async function sendMessage(sessionId, content) {
    return fetchWithAuth(`/api/v1/generator/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
    });
}

export async function approveOutline(sessionId, outline) {
    const payload = outline ? { outline } : {};
    return fetchWithAuth(`/api/v1/generator/sessions/${sessionId}/outline/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
}

export async function stopSession(sessionId) {
    return fetchWithAuth(`/api/v1/generator/sessions/${sessionId}/stop`, { method: 'POST' });
}
