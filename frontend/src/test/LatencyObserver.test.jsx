import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '@testing-library/react';
import React from 'react';
import LatencyObserver from '../components/monitoring/LatencyObserver';

vi.mock('next/navigation', () => ({
    usePathname: vi.fn(() => '/dashboard'),
}));

vi.mock('../services/api.core', () => ({
    fetchWithRetry: vi.fn(() => Promise.resolve()),
}));

describe('LatencyObserver', () => {
    beforeEach(() => {
        vi.spyOn(performance, 'getEntriesByType').mockReturnValue([
            { duration: 150 },
        ]);
        Object.defineProperty(document, 'readyState', { value: 'complete', writable: true });
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('renders null', () => {
        const { container } = render(<LatencyObserver />);
        expect(container.innerHTML).toBe('');
    });

    it('reports timing data on mount', async () => {
        render(<LatencyObserver />);
        const { fetchWithRetry } = await import('../services/api.core');
        expect(fetchWithRetry).toHaveBeenCalledWith('/api/internal/metrics/record', expect.objectContaining({
            method: 'POST',
            body: expect.stringContaining('/dashboard'),
        }));
    });
});
