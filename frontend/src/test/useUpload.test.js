import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';

vi.mock('next/navigation', () => ({
    useRouter: vi.fn(() => ({ push: vi.fn() })),
}));

vi.mock('@/context/AuthContext', () => ({
    useAuth: vi.fn(() => ({ isLoggedIn: true, user: { plan_tier: 'free' } })),
}));

vi.mock('@/context/DocumentContext', () => ({
    useDocument: vi.fn(() => ({ job: null, setJob: vi.fn() })),
}));

vi.mock('@/constants/status', () => ({
    isCompleted: vi.fn(() => false),
    isFailed: vi.fn(() => false),
    isProcessing: vi.fn(() => false),
}));

vi.mock('@/services/api', () => ({
    CHUNK_UPLOAD_THRESHOLD_BYTES: 10485760,
    uploadChunked: vi.fn(() => Promise.resolve({ job_id: '123' })),
    uploadDocumentWithProgress: vi.fn(() => Promise.resolve({ job_id: '456' })),
    useDocumentStatus: vi.fn(() => ({ data: null, isLoading: false })),
}));

vi.mock('@/lib/planTier', () => ({
    getRemainingQuota: vi.fn(() => ({ remaining: Infinity })),
}));

vi.mock('@/lib/schemas', () => ({
    UploadStartSchema: {
        safeParse: vi.fn(() => ({ success: true, data: {} })),
    },
}));

vi.mock('@/lib/analytics', () => ({
    trackEvent: vi.fn(),
}));

describe('useUpload', () => {
    it('returns initial state', async () => {
        const { useUpload } = await import('../hooks/useUpload');
        const { result } = renderHook(() => useUpload());

        expect(result.current.isProcessing).toBe(false);
        expect(result.current.progress).toBe(0);
        expect(typeof result.current.startUpload).toBe('function');
        expect(typeof result.current.cancelUpload).toBe('function');
    });

    it('returns formatting options with defaults', async () => {
        const { useUpload } = await import('../hooks/useUpload');
        const { result } = renderHook(() => useUpload());

        expect(result.current.formattingOptions).toBeDefined();
        expect(result.current.formattingOptions.fastMode).toBe(false);
    });

    it('updates formatting options via updateFormattingOption', async () => {
        const { useUpload } = await import('../hooks/useUpload');
        const { result } = renderHook(() => useUpload());

        act(() => {
            result.current.updateFormattingOption('fastMode', true);
        });
        expect(result.current.formattingOptions.fastMode).toBe(true);
    });

    it('cancelUpload resets processing state', async () => {
        const { useUpload } = await import('../hooks/useUpload');
        const { result } = renderHook(() => useUpload());

        act(() => {
            result.current.cancelUpload();
        });
        expect(result.current.isProcessing).toBe(false);
    });

    it('startUpload is a function', async () => {
        const { useUpload } = await import('../hooks/useUpload');
        const { result } = renderHook(() => useUpload());

        expect(typeof result.current.startUpload).toBe('function');
    });
});
