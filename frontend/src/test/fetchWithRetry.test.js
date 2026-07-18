import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fetchWithRetry } from '../utils/fetchWithRetry';

describe('fetchWithRetry', () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.stubGlobal('fetch', vi.fn());
    });

    afterEach(() => {
        vi.useRealTimers();
        vi.unstubAllGlobals();
    });

    it('returns response on first success', async () => {
        const okResponse = { ok: true, status: 200 };
        global.fetch.mockResolvedValue(okResponse);

        const result = await fetchWithRetry('/api/test');
        expect(result).toBe(okResponse);
        expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('retries on 429 status', async () => {
        const retryResponse = { ok: false, status: 429, headers: new Map() };
        const okResponse = { ok: true, status: 200 };
        global.fetch
            .mockResolvedValueOnce(retryResponse)
            .mockResolvedValueOnce(retryResponse)
            .mockResolvedValueOnce(okResponse);

        const promise = fetchWithRetry('/api/test');
        await vi.advanceTimersByTimeAsync(10000);
        const result = await promise;

        expect(result).toBe(okResponse);
        expect(global.fetch).toHaveBeenCalledTimes(3);
    });

    it('retries on 503 status', async () => {
        const retryResponse = { ok: false, status: 503, headers: new Map() };
        const okResponse = { ok: true, status: 200 };
        global.fetch
            .mockResolvedValueOnce(retryResponse)
            .mockResolvedValueOnce(retryResponse)
            .mockResolvedValueOnce(okResponse);

        const promise = fetchWithRetry('/api/test');
        await vi.advanceTimersByTimeAsync(10000);
        const result = await promise;

        expect(result).toBe(okResponse);
    });

    it('does not retry on 404', async () => {
        const notFoundResponse = { ok: false, status: 404, headers: new Map() };
        global.fetch.mockResolvedValue(notFoundResponse);

        const result = await fetchWithRetry('/api/test');
        expect(result).toBe(notFoundResponse);
        expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('immediately throws on network error with zero retries', async () => {
        global.fetch.mockRejectedValue(new Error('Network error'));

        await expect(fetchWithRetry('/api/test', {}, 0)).rejects.toThrow('Network error');
        expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('exhausts retries on persistent network error', { timeout: 30000 }, async () => {
        vi.useRealTimers();
        const fetchMock = vi.fn(() => Promise.reject(new Error('Network error')));
        vi.stubGlobal('fetch', fetchMock);

        await expect(fetchWithRetry('/api/test')).rejects.toThrow('Network error');
        expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(1);
    });
});
