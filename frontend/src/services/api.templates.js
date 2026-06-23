// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { fetchWithAuth } from './api.core';

const FALLBACK_TEMPLATES = [
    { id: 'none', name: 'None (No formatting)', description: 'No formatting applied' },
    { id: 'ieee', name: 'IEEE', description: 'IEEE manuscript style' },
    { id: 'apa', name: 'APA (7th Edition)', description: 'APA style' },
    { id: 'acm', name: 'ACM', description: 'ACM manuscript style' },
    { id: 'springer', name: 'Springer', description: 'Springer journal style' },
    { id: 'elsevier', name: 'Elsevier', description: 'Elsevier template' },
    { id: 'nature', name: 'Nature', description: 'Nature style' },
    { id: 'harvard', name: 'Harvard', description: 'Harvard citation style' },
    { id: 'chicago', name: 'Chicago (17th)', description: 'Chicago style' },
    { id: 'mla', name: 'MLA (9th)', description: 'MLA style' },
    { id: 'vancouver', name: 'Vancouver', description: 'Vancouver citation style' },
    { id: 'numeric', name: 'Numeric', description: 'Numeric citation style' },
    { id: 'modern_blue', name: 'Modern Blue', description: 'Modern Blue design' },
    { id: 'modern_gold', name: 'Modern Gold', description: 'Modern Gold design' },
    { id: 'modern_red', name: 'Modern Red', description: 'Modern Red design' },
];

export async function fetchTemplates() {
    try {
        const data = await fetchWithAuth('/api/v1/templates/builtin');
        const templates = data?.templates;
        if (Array.isArray(templates) && templates.length > 0) {
            return templates;
        }
        return FALLBACK_TEMPLATES;
    } catch {
        return FALLBACK_TEMPLATES;
    }
}
