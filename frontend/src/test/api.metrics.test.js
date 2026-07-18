import { describe, it, expect, vi, beforeEach } from 'vitest';

const { mockFetchWithAuth, mockGetV1, mockUnwrapResponse } = vi.hoisted(() => ({
    mockFetchWithAuth: vi.fn(() => Promise.resolve({ ok: true, data: {} })),
    mockGetV1: vi.fn(() => Promise.resolve({ data: { ready: true, checks: { database: 'healthy', ai_models: 'healthy', grobid: 'healthy' } }, error: null })),
    mockUnwrapResponse: vi.fn((envelope) => envelope.data),
}));

vi.mock('../services/api.core', () => ({
    fetchWithAuth: mockFetchWithAuth,
    sanitizePayload: vi.fn((x) => x),
    sendFrontendErrorLog: vi.fn(() => Promise.resolve()),
}));

vi.mock('../services/api.v1', () => ({
    getV1: mockGetV1,
    unwrapResponse: mockUnwrapResponse,
}));

vi.mock('../lib/supabaseClient', () => ({
    supabase: { auth: { getUser: vi.fn() } },
}));

describe('api.metrics', () => {
    beforeEach(async () => {
        vi.clearAllMocks();
    });

    it('logFrontendError works', async () => {
        const { logFrontendError } = await import('../services/api.metrics');
        await logFrontendError({ error: 'test' });
    });

    it('submitFeedback posts feedback', async () => {
        const { submitFeedback } = await import('../services/api.metrics');

        await submitFeedback({ document_id: '123', field: 'title', corrected_value: 'New' });
        expect(mockFetchWithAuth).toHaveBeenCalledWith('/api/v1/feedback/', expect.objectContaining({
            method: 'POST',
        }));
    });

    it('getFeedbackSummary fetches summary', async () => {
        const { getFeedbackSummary } = await import('../services/api.metrics');

        await getFeedbackSummary('job-123');
        expect(mockFetchWithAuth).toHaveBeenCalledWith('/api/v1/feedback/summary?document_id=job-123');
    });

    it('getMetricsHealth returns null on error', async () => {
        mockGetV1.mockRejectedValueOnce(new Error('fail'));

        const { getMetricsHealth } = await import('../services/api.metrics');
        const result = await getMetricsHealth();
        expect(result).toBeNull();
    });

    it('getMetricsDashboard returns null on error', async () => {
        mockFetchWithAuth.mockRejectedValueOnce(new Error('fail'));

        const { getMetricsDashboard } = await import('../services/api.metrics');
        const result = await getMetricsDashboard();
        expect(result).toBeNull();
    });

    it('getMetricsDb returns null on error', async () => {
        mockFetchWithAuth.mockRejectedValueOnce(new Error('fail'));

        const { getMetricsDb } = await import('../services/api.metrics');
        const result = await getMetricsDb();
        expect(result).toBeNull();
    });

    it('getMetricsDb returns data on success', async () => {
        mockFetchWithAuth.mockResolvedValueOnce({ db_status: 'connected' });

        const { getMetricsDb } = await import('../services/api.metrics');
        const result = await getMetricsDb();
        expect(result).toEqual({ db_status: 'connected' });
    });

    it('getMetricsHealth returns normalized health payload', async () => {
        const healthPayload = {
            ready: true,
            checks: {
                database: 'healthy',
                ai_models: 'healthy',
                grobid: 'healthy',
                llm_status: { openai: 'healthy', anthropic: 'healthy' },
            },
        };
        mockGetV1.mockResolvedValueOnce({ data: healthPayload, error: null });

        const { getMetricsHealth } = await import('../services/api.metrics');
        const result = await getMetricsHealth();
        expect(result.status).toBe('healthy');
        expect(result.aiServicesStatus).toBe('healthy');
        expect(result.grobidStatus).toBe('healthy');
        expect(result.aiServicesDetails).toContain('OPENAI');
        expect(result.aiServicesDetails).toContain('ANTHROPIC');
    });

    it('getMetricsHealth returns degraded when not ready', async () => {
        mockGetV1.mockResolvedValueOnce({ data: { ready: false, checks: { database: 'healthy', ai_models: 'healthy', grobid: 'healthy' } }, error: null });

        const { getMetricsHealth } = await import('../services/api.metrics');
        const result = await getMetricsHealth();
        expect(result.status).toBe('degraded');
    });

    it('getMetricsDashboard returns null on error', async () => {
        mockFetchWithAuth.mockRejectedValueOnce(new Error('fail'));

        const { getMetricsDashboard } = await import('../services/api.metrics');
        const result = await getMetricsDashboard();
        expect(result).toBeNull();
    });

    it('getMetricsEnhancements calls fetchWithAuth', async () => {
        mockFetchWithAuth.mockResolvedValueOnce({ enhancements: [] });

        const { getMetricsEnhancements } = await import('../services/api.metrics');
        await getMetricsEnhancements();
        expect(mockFetchWithAuth).toHaveBeenCalledWith('/api/v1/metrics/enhancements');
    });

    it('getMetricsHealth handles degraded ai_models', async () => {
        mockGetV1.mockResolvedValueOnce({
            data: {
                ready: true,
                checks: {
                    database: 'healthy',
                    ai_models: 'model_missing',
                    grobid: 'degraded',
                    llm_status: { openai: 'healthy' },
                },
            },
            error: null,
        });

        const { getMetricsHealth } = await import('../services/api.metrics');
        const result = await getMetricsHealth();
        expect(result.aiServicesStatus).toBe('degraded');
        expect(result.grobidStatus).toBe('degraded');
    });

    it('getMetricsHealth handles unavailable ai services', async () => {
        mockGetV1.mockResolvedValueOnce({
            data: {
                ready: true,
                checks: {
                    database: 'healthy',
                    ai_models: 'unavailable',
                    grobid: 'healthy',
                    llm_status: { openai: 'unavailable' },
                },
            },
            error: null,
        });

        const { getMetricsHealth } = await import('../services/api.metrics');
        const result = await getMetricsHealth();
        expect(result.aiServicesStatus).toBe('unavailable');
    });

    it('getMetricsHealth handles unknown indicator status', async () => {
        mockGetV1.mockResolvedValueOnce({
            data: {
                ready: true,
                checks: {
                    database: 'unknown_status',
                    ai_models: 'healthy',
                    grobid: 'healthy',
                    llm_status: {},
                },
            },
            error: null,
        });

        const { getMetricsHealth } = await import('../services/api.metrics');
        const result = await getMetricsHealth();
        expect(result.details).toContain('unknown status');
    });

    it('getMetricsHealth handles empty llm_status', async () => {
        mockGetV1.mockResolvedValueOnce({
            data: {
                ready: true,
                checks: {
                    database: 'healthy',
                    ai_models: 'healthy',
                    grobid: 'healthy',
                    llm_status: {},
                },
            },
            error: null,
        });

        const { getMetricsHealth } = await import('../services/api.metrics');
        const result = await getMetricsHealth();
        expect(result.aiServicesDetails).toBe('No provider data');
    });

    it('getMetricsHealth handles fallback when checks is missing', async () => {
        mockGetV1.mockResolvedValueOnce({
            data: { ready: true },
            error: null,
        });

        const { getMetricsHealth } = await import('../services/api.metrics');
        const result = await getMetricsHealth();
        expect(result.status).toBe('healthy');
        expect(result.aiServicesStatus).toBe('unknown');
        expect(result.grobidStatus).toBe('unknown');
    });
});
