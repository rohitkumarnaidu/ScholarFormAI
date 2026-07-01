// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { getV1, postV1, putV1, deleteV1, unwrapResponse } from './api.v1';

export const PROVIDERS = {
    openai: { name: 'OpenAI', docs: 'https://platform.openai.com/api-keys' },
    anthropic: { name: 'Anthropic', docs: 'https://console.anthropic.com/settings/keys' },
    groq: { name: 'Groq', docs: 'https://console.groq.com/keys' },
    deepseek: { name: 'DeepSeek', docs: 'https://platform.deepseek.com/api_keys' },
    google: { name: 'Google AI', docs: 'https://aistudio.google.com/app/apikey' },
    cohere: { name: 'Cohere', docs: 'https://dashboard.cohere.com/api-keys' },
    mistral: { name: 'Mistral', docs: 'https://console.mistral.ai/api-keys/' },
};

export async function listApiKeys(provider) {
    const path = provider ? `/keys?provider=${encodeURIComponent(provider)}` : '/keys';
    const envelope = await getV1(path);
    return unwrapResponse(envelope);
}

export async function getApiKey(keyId) {
    const envelope = await getV1(`/keys/${encodeURIComponent(keyId)}`);
    return unwrapResponse(envelope);
}

export async function createApiKey({ provider, api_key, key_label, rate_limit_per_minute, rate_limit_per_hour, daily_quota }) {
    const envelope = await postV1('/keys', {
        provider,
        api_key,
        key_label,
        rate_limit_per_minute,
        rate_limit_per_hour,
        daily_quota,
    });
    return unwrapResponse(envelope);
}

export async function updateApiKey(keyId, updates) {
    const envelope = await putV1(`/keys/${encodeURIComponent(keyId)}`, updates);
    return unwrapResponse(envelope);
}

export async function deleteApiKey(keyId) {
    await deleteV1(`/keys/${encodeURIComponent(keyId)}`);
}

export async function testApiKey(provider, apiKey) {
    const envelope = await postV1('/keys/test', { provider, api_key: apiKey });
    return unwrapResponse(envelope);
}

export async function getApiKeyUsage(keyId) {
    const envelope = await getV1(`/keys/${encodeURIComponent(keyId)}/usage`);
    return unwrapResponse(envelope);
}

export async function getUsageStats(hours = 24) {
    const envelope = await getV1(`/keys/usage?hours=${hours}`);
    return unwrapResponse(envelope);
}

export async function getSupportedProviders() {
    const envelope = await getV1('/keys/providers');
    return unwrapResponse(envelope);
}
