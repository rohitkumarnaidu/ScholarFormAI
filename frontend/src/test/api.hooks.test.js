import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';

vi.mock('@tanstack/react-query', () => ({
    useQuery: vi.fn(({ select }) => ({
        data: select ? select({ documents: [] }) : { documents: [], data: null },
        isLoading: false,
        error: null,
    })),
}));

vi.mock('../services/api.documents', () => ({
    getDocuments: vi.fn(() => Promise.resolve({ documents: [] })),
    getJobStatus: vi.fn(() => Promise.resolve({ status: 'PENDING' })),
    mapDocumentRecord: vi.fn((doc) => doc),
    normalizeDocumentsParams: vi.fn((p) => p),
}));

vi.mock('../services/api.metrics', () => ({
    getMetricsHealth: vi.fn(() => Promise.resolve({ status: 'healthy' })),
    getMetricsDashboard: vi.fn(() => Promise.resolve({})),
}));

vi.mock('../services/api.generation', () => ({
    streamGenerationStatus: vi.fn(() => () => {}),
}));

describe('api.hooks', () => {
    it('useDocuments returns query result', async () => {
        const { useDocuments } = await import('../services/api.hooks');
        const { result } = renderHook(() => useDocuments());

        expect(result.current.data).toBeDefined();
        expect(result.current.data.documents).toEqual([]);
    });

    it('useDocumentStatus returns query result', async () => {
        const { useDocumentStatus } = await import('../services/api.hooks');
        const { result } = renderHook(() => useDocumentStatus('job-123'));

        expect(result.current).toBeDefined();
    });

    it('useMetricsHealth returns query result', async () => {
        const { useMetricsHealth } = await import('../services/api.hooks');
        const { result } = renderHook(() => useMetricsHealth());

        expect(result.current).toBeDefined();
    });

    it('useMetricsDashboard returns query result', async () => {
        const { useMetricsDashboard } = await import('../services/api.hooks');
        const { result } = renderHook(() => useMetricsDashboard());

        expect(result.current).toBeDefined();
    });

    it('useJobStatusSSE works with polling fallback', async () => {
        const { useJobStatusSSE } = await import('../services/api.hooks');
        const { result } = renderHook(() => useJobStatusSSE('job-123', { enabled: true }));

        expect(result.current).toBeDefined();
    });
});
