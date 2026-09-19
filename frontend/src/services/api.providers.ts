import { getV1, postV1, putV1, deleteV1, unwrapResponse } from "./api.v1";

export async function getBuiltinProviders() {
    const envelope = await getV1('/providers');
    return unwrapResponse(envelope);
}

export async function getCustomProviders() {
    const envelope = await getV1('/providers/custom');
    return unwrapResponse(envelope);
}

export async function createCustomProvider(data: { name: string; base_url: string; api_key?: string | null; models?: string[]; is_local?: boolean; description?: string | null }) {
    const envelope = await postV1('/providers/custom', data);
    return unwrapResponse(envelope);
}

export async function updateCustomProvider(id: string, data: any) {
    const envelope = await putV1(`/providers/custom/${id}`, data);
    return unwrapResponse(envelope);
}

export async function deleteCustomProvider(id: string) {
    await deleteV1(`/providers/custom/${id}`);
}

export async function discoverModels(providerId: string, baseUrl?: string) {
    const params = new URLSearchParams();
    if (baseUrl) params.set('base_url', baseUrl);
    const url = `/providers/${providerId}/models${params.toString() ? '?' + params.toString() : ''}`;
    const envelope = await getV1(url);
    return unwrapResponse(envelope);
}

export async function testProvider(providerId: string, baseUrl?: string, apiKey?: string) {
    const params = new URLSearchParams({ provider_id: providerId });
    if (baseUrl) params.set('base_url', baseUrl);
    if (apiKey) params.set('api_key', apiKey);
    const envelope = await postV1(`/providers/test?${params.toString()}`);
    return unwrapResponse(envelope);
}

export async function syncModels(providerId: string, models: string[]) {
    const envelope = await postV1(`/providers/${providerId}/models/sync`, { models });
    return unwrapResponse(envelope);
}
