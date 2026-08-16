import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';

const mockJob = { id: '123', status: 'COMPLETED', originalFileName: 'test.docx' };

vi.mock('next/navigation', () => ({
    useParams: vi.fn(() => ({ jobId: '123' })),
    useSearchParams: vi.fn(() => new URLSearchParams()),
}));

vi.mock('../context/DocumentContext', () => ({
    useDocument: vi.fn(() => ({ job: mockJob, setJob: vi.fn() })),
}));

vi.mock('../services/api', () => ({
    getJobSummary: vi.fn(() => Promise.resolve({
        id: '999',
        filename: 'other.docx',
        original_file_name: 'other.docx',
        created_at: new Date().toISOString(),
        status: 'PROCESSING',
    })),
}));

describe('useJobFromUrl', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('returns the job from context when id matches', async () => {
        const { useSearchParams } = await import('next/navigation');
        useSearchParams.mockReturnValue(new URLSearchParams('?jobId=123'));

        const { useDocument } = await import('../context/DocumentContext');
        useDocument.mockReturnValue({ job: mockJob, setJob: vi.fn() });

        const { default: useJobFromUrl } = await import('../hooks/useJobFromUrl');
        const { result } = renderHook(() => useJobFromUrl());
        expect(result.current.job).toEqual(mockJob);
        expect(result.current.isLoading).toBe(false);
        expect(result.current.error).toBe('');
    });

    it('fetches job when context id does not match', async () => {
        const { useSearchParams } = await import('next/navigation');
        useSearchParams.mockReturnValue(new URLSearchParams('?jobId=999'));

        const { useDocument } = await import('../context/DocumentContext');
        useDocument.mockReturnValue({ job: mockJob, setJob: vi.fn() });

        const { default: useJobFromUrl } = await import('../hooks/useJobFromUrl');
        const { result } = renderHook(() => useJobFromUrl());
        expect(result.current.job).toBeNull();
        expect(result.current.isLoading).toBe(true);
    });

    it('returns empty state when no jobId', async () => {
        const { useSearchParams } = await import('next/navigation');
        useSearchParams.mockReturnValue(new URLSearchParams());

        const { useDocument } = await import('../context/DocumentContext');
        useDocument.mockReturnValue({ job: null, setJob: vi.fn() });

        const { default: useJobFromUrl } = await import('../hooks/useJobFromUrl');
        const { result } = renderHook(() => useJobFromUrl());
        expect(result.current.job).toBeNull();
        expect(result.current.isLoading).toBe(false);
        expect(result.current.error).toBe('');
    });
});
