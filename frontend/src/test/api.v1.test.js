import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BASE_V1_URL, unwrapResponse, getGeneratorSessions, deleteGeneratorSession, getV1, postV1, putV1, deleteV1 } from '../services/api.v1';

const { handleUnauthorizedSession, parseResponseData, getAuthorizedHeaders, fetchWithRetry, getFriendlyErrorMessage } = vi.hoisted(() => ({
    handleUnauthorizedSession: vi.fn(),
    parseResponseData: vi.fn(() => ({ data: { success: true } })),
    getAuthorizedHeaders: vi.fn(() => Promise.resolve({ 'Authorization': 'Bearer test', 'Content-Type': 'application/json' })),
    fetchWithRetry: vi.fn(() => Promise.resolve({ ok: true, status: 200, headers: { get: vi.fn() } })),
    getFriendlyErrorMessage: vi.fn(({ fallbackMessage }) => fallbackMessage),
}));

vi.mock('../services/api.core', () => ({
    fetchWithRetry,
    getAuthorizedHeaders,
    getFriendlyErrorMessage,
    parseResponseData,
    parseApiResponse: vi.fn((schema, raw, { fallback }) => fallback),
    handleUnauthorizedSession,
    generateRequestId: vi.fn(() => 'req-123'),
}));

vi.mock('../lib/supabaseClient', () => ({
    supabase: { auth: { getUser: vi.fn() } },
}));

vi.mock('../lib/schemas', () => ({
    GeneratorSessionsResponseSchema: {},
}));

describe('API URLs', () => {
    it('has correct base URL', () => {
        expect(BASE_V1_URL).toBe('http://localhost:8000/api/v1');
    });
});

describe('unwrapResponse', () => {
    it('returns data when no error', () => {
        expect(unwrapResponse({ data: { id: 1 }, error: null })).toEqual({ id: 1 });
    });

    it('throws when error present', () => {
        expect(() => unwrapResponse({ data: null, error: { message: 'Fail' } })).toThrow('Fail');
    });

    it('throws with string error', () => {
        expect(() => unwrapResponse({ data: null, error: 'Error occurred' })).toThrow('Error occurred');
    });
});

describe('getGeneratorSessions', () => {
    it('returns fallback on error', async () => {
        const result = await getGeneratorSessions();
        expect(result).toEqual({ sessions: [] });
    });
});

describe('deleteGeneratorSession', () => {
    it('calls deleteV1 with session ID', async () => {
        parseResponseData.mockResolvedValueOnce({});
        fetchWithRetry.mockResolvedValueOnce({ ok: true, status: 200, headers: { get: vi.fn() } });
        const result = await deleteGeneratorSession('session-1');
        expect(result).toEqual({});
    });
});

describe('getV1', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        parseResponseData.mockResolvedValue({ data: { items: [] } });
        fetchWithRetry.mockResolvedValue({ ok: true, status: 200, headers: { get: vi.fn() } });
    });

    it('calls fetchWithRetry with correct URL', async () => {
        await getV1('/test');
        expect(fetchWithRetry).toHaveBeenCalledWith(
            'http://localhost:8000/api/v1/test',
            expect.objectContaining({ method: 'GET' }),
            undefined
        );
    });
});

describe('postV1', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        sessionStorage.clear();
        parseResponseData.mockResolvedValue({ data: { id: 1 } });
        fetchWithRetry.mockResolvedValue({ ok: true, status: 200, headers: { get: vi.fn() } });
    });

    it('adds Idempotency-Key header for POST', async () => {
        await postV1('/test', { key: 'value' });
        expect(getAuthorizedHeaders).toHaveBeenCalledWith(
            expect.objectContaining({
                'Idempotency-Key': expect.any(String),
            })
        );
    });

    it('caches idempotency key in sessionStorage', async () => {
        sessionStorage.clear();
        await postV1('/test', { key: 'value' });
        const keys = Object.keys(sessionStorage).filter(k => k.startsWith('idemp_'));
        expect(keys.length).toBeGreaterThanOrEqual(1);
    });
});

describe('putV1', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        parseResponseData.mockResolvedValue({ data: { updated: true } });
        fetchWithRetry.mockResolvedValue({ ok: true, status: 200, headers: { get: vi.fn() } });
    });

    it('calls fetchWithRetry with PUT method', async () => {
        await putV1('/test/1', { name: 'updated' });
        expect(fetchWithRetry).toHaveBeenCalledWith(
            expect.any(String),
            expect.objectContaining({ method: 'PUT' }),
            undefined
        );
    });
});

describe('deleteV1', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        parseResponseData.mockResolvedValue({});
        fetchWithRetry.mockResolvedValue({ ok: true, status: 200, headers: { get: vi.fn() } });
    });

    it('calls fetchWithRetry with DELETE method', async () => {
        await deleteV1('/test/1');
        expect(fetchWithRetry).toHaveBeenCalledWith(
            expect.any(String),
            expect.objectContaining({ method: 'DELETE' }),
            undefined
        );
    });
});

describe('fetchV1 error paths', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('handles 401 status and calls handleUnauthorizedSession', async () => {
        parseResponseData.mockResolvedValueOnce({ error: 'Unauthorized' });
        fetchWithRetry.mockResolvedValueOnce({ ok: false, status: 401, headers: { get: vi.fn() } });

        const { getV1: g } = await import('../services/api.v1');
        await expect(g('/protected')).rejects.toThrow();
        expect(handleUnauthorizedSession).toHaveBeenCalled();
    });

    it('handles network error in catch block', async () => {
        getAuthorizedHeaders.mockRejectedValueOnce(new Error('Network failure'));
        getFriendlyErrorMessage.mockReturnValueOnce('Network error occurred');

        const { getV1: g } = await import('../services/api.v1');
        await expect(g('/test')).rejects.toThrow('Network error occurred');
    });

    it('re-throws error with friendly message for non-401 errors', async () => {
        parseResponseData.mockResolvedValueOnce({ error: 'Not Found' });
        getFriendlyErrorMessage.mockReturnValueOnce('The requested resource could not be found.');
        fetchWithRetry.mockResolvedValueOnce({ ok: false, status: 404, headers: { get: vi.fn() } });

        const { getV1: g } = await import('../services/api.v1');
        await expect(g('/missing')).rejects.toThrow('The requested resource could not be found.');
    });
});

describe('generateIdempotencyHash', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('generates a hex string for given input', async () => {
        const { generateIdempotencyHash: hash } = await import('../services/api.v1');
        const result = await hash('test-input');
        expect(typeof result).toBe('string');
        expect(result.length).toBeGreaterThan(0);
    });

    it('produces consistent output for same input', async () => {
        const { generateIdempotencyHash: hash } = await import('../services/api.v1');
        const a = await hash('same-string');
        const b = await hash('same-string');
        expect(a).toBe(b);
    });

    it('produces different output for different inputs', async () => {
        const { generateIdempotencyHash: hash } = await import('../services/api.v1');
        const a = await hash('input-a');
        const b = await hash('input-b');
        expect(a).not.toBe(b);
    });
});

describe('getIdempotencyKey', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        sessionStorage.clear();
    });

    it('returns a key and caches it in sessionStorage', async () => {
        const { getIdempotencyKey: getKey } = await import('../services/api.v1');
        const key = await getKey('/test', 'body');
        expect(typeof key).toBe('string');
        expect(key.length).toBeGreaterThan(0);

        const cacheEntries = Object.keys(sessionStorage).filter(k => k.startsWith('idemp_'));
        expect(cacheEntries.length).toBe(1);
        const cached = JSON.parse(sessionStorage.getItem(cacheEntries[0]));
        expect(cached.key).toBe(key);
    });

    it('returns cached key within TTL', async () => {
        const { getIdempotencyKey: getKey, generateIdempotencyHash: hash } = await import('../services/api.v1');
        const key1 = await getKey('/test', 'body');
        const key2 = await getKey('/test', 'body');
        expect(key2).toBe(key1);
    });

    it('returns a fallback key when sessionStorage throws', async () => {
        const setItem = sessionStorage.setItem;
        sessionStorage.setItem = vi.fn(() => { throw new Error('Storage full'); });
        const { getIdempotencyKey: getKey } = await import('../services/api.v1');
        const key = await getKey('/test', 'body');
        expect(typeof key).toBe('string');
        sessionStorage.setItem = setItem;
    });
});
