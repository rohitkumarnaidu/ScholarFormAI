import { describe, it, expect, vi, beforeEach } from 'vitest';

const { mockGetV1, mockPostV1, mockPutV1, mockDeleteV1, mockUnwrapResponse } = vi.hoisted(() => ({
    mockGetV1: vi.fn(() => Promise.resolve({ data: { keys: [] }, error: null })),
    mockPostV1: vi.fn(() => Promise.resolve({ data: { key: 'new-key' }, error: null })),
    mockPutV1: vi.fn(() => Promise.resolve({ data: { updated: true }, error: null })),
    mockDeleteV1: vi.fn(() => Promise.resolve({ data: null, error: null })),
    mockUnwrapResponse: vi.fn((envelope) => envelope.data),
}));

vi.mock('../services/api.v1', () => ({
    getV1: mockGetV1,
    postV1: mockPostV1,
    putV1: mockPutV1,
    deleteV1: mockDeleteV1,
    unwrapResponse: mockUnwrapResponse,
}));

describe('api.keys', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('listApiKeys calls getV1 with correct path', async () => {
        const { listApiKeys } = await import('../services/api.keys');

        await listApiKeys('openai');
        expect(mockGetV1).toHaveBeenCalledWith('/keys?provider=openai');
    });

    it('listApiKeys handles no provider', async () => {
        const { listApiKeys } = await import('../services/api.keys');

        await listApiKeys();
        expect(mockGetV1).toHaveBeenCalledWith('/keys');
    });

    it('getApiKey calls getV1 with key ID', async () => {
        const { getApiKey } = await import('../services/api.keys');

        await getApiKey('key-1');
        expect(mockGetV1).toHaveBeenCalledWith('/keys/key-1');
    });

    it('createApiKey calls postV1 with key data', async () => {
        const { createApiKey } = await import('../services/api.keys');

        await createApiKey({ provider: 'openai', api_key: 'sk-xxx', key_label: 'My Key' });
        expect(mockPostV1).toHaveBeenCalledWith('/keys', {
            provider: 'openai',
            api_key: 'sk-xxx',
            key_label: 'My Key',
            rate_limit_per_minute: undefined,
            rate_limit_per_hour: undefined,
            daily_quota: undefined,
        });
    });

    it('updateApiKey calls putV1 with key ID and updates', async () => {
        const { updateApiKey } = await import('../services/api.keys');

        await updateApiKey('key-1', { key_label: 'Renamed' });
        expect(mockPutV1).toHaveBeenCalledWith('/keys/key-1', { key_label: 'Renamed' });
    });

    it('deleteApiKey calls deleteV1', async () => {
        const { deleteApiKey } = await import('../services/api.keys');

        await deleteApiKey('key-1');
        expect(mockDeleteV1).toHaveBeenCalledWith('/keys/key-1');
    });

    it('testApiKey calls postV1 with provider and key', async () => {
        const { testApiKey } = await import('../services/api.keys');

        await testApiKey('openai', 'sk-test');
        expect(mockPostV1).toHaveBeenCalledWith('/keys/test', { provider: 'openai', api_key: 'sk-test' });
    });

    it('getApiKeyUsage calls getV1 with key ID usage path', async () => {
        const { getApiKeyUsage } = await import('../services/api.keys');

        await getApiKeyUsage('key-1');
        expect(mockGetV1).toHaveBeenCalledWith('/keys/key-1/usage');
    });

    it('getUsageStats calls getV1 with default hours', async () => {
        const { getUsageStats } = await import('../services/api.keys');

        await getUsageStats();
        expect(mockGetV1).toHaveBeenCalledWith('/keys/usage?hours=24');
    });

    it('getUsageStats calls getV1 with custom hours', async () => {
        const { getUsageStats } = await import('../services/api.keys');

        await getUsageStats(48);
        expect(mockGetV1).toHaveBeenCalledWith('/keys/usage?hours=48');
    });

    it('getSupportedProviders calls getV1', async () => {
        const { getSupportedProviders } = await import('../services/api.keys');

        await getSupportedProviders();
        expect(mockGetV1).toHaveBeenCalledWith('/keys/providers');
    });

    it('PROVIDERS map has expected entries', async () => {
        const { PROVIDERS } = await import('../services/api.keys');
        expect(PROVIDERS.openai.name).toBe('OpenAI');
        expect(PROVIDERS.anthropic.name).toBe('Anthropic');
        expect(PROVIDERS.groq.name).toBe('Groq');
        expect(PROVIDERS.deepseek.name).toBe('DeepSeek');
        expect(PROVIDERS.google.name).toBe('Google AI');
        expect(PROVIDERS.cohere.name).toBe('Cohere');
        expect(PROVIDERS.mistral.name).toBe('Mistral');
    });

    it('createApiKey returns the created key data', async () => {
        const { createApiKey } = await import('../services/api.keys');

        const result = await createApiKey({ provider: 'anthropic', api_key: 'sk-ant-xxx' });
        expect(result).toEqual({ key: 'new-key' });
    });

    it('getApiKey returns key data', async () => {
        mockGetV1.mockResolvedValueOnce({ data: { id: 'key-1', provider: 'openai' }, error: null });

        const { getApiKey } = await import('../services/api.keys');
        const result = await getApiKey('key-1');
        expect(result).toEqual({ id: 'key-1', provider: 'openai' });
    });
});
