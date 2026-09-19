// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { postV1, unwrapResponse } from './api.v1';
import { fetchWithAuth } from './api.core';

export const formatManuscript = async (payload) => {
    // We cannot use standard unwrapResponse for formatManuscript because it returns a blob (the DOCX file)
    // The previous code in page.tsx did a custom fetch.
    const response = await fetchWithAuth(`/api/v1/format/format`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.message || 'Formatting failed');
    }

    return response.blob();
};

export const previewManuscript = async (payload) => {
    const envelope = await postV1('/format/preview', payload);
    return unwrapResponse(envelope);
};
