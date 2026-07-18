import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchTemplates, getBuiltinTemplates, searchCSLStyles, fetchCSLStyle, getCustomTemplates, saveCustomTemplate } from '../services/api.templates';

const { mockFetchWithAuth } = vi.hoisted(() => ({
    mockFetchWithAuth: vi.fn(),
}));

vi.mock('../services/api.core', () => ({
    fetchWithAuth: mockFetchWithAuth,
}));

describe('fetchTemplates', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('returns templates from API when available', async () => {
        const mockTemplates = [{ id: 'ieee', name: 'IEEE' }];
        mockFetchWithAuth.mockResolvedValue({ templates: mockTemplates });

        const result = await fetchTemplates();
        expect(mockFetchWithAuth).toHaveBeenCalledWith('/api/v1/templates');
        expect(result).toEqual(mockTemplates);
    });

    it('returns fallback templates when API returns empty array', async () => {
        mockFetchWithAuth.mockResolvedValue({ templates: [] });

        const result = await fetchTemplates();
        expect(result.length).toBeGreaterThan(0);
        expect(result[0].id).toBe('none');
    });

    it('returns fallback templates on API error', async () => {
        mockFetchWithAuth.mockRejectedValue(new Error('Network error'));

        const result = await fetchTemplates();
        expect(result.length).toBeGreaterThan(0);
        expect(result[0].id).toBe('none');
    });

    it('includes common template IDs in fallback', async () => {
        mockFetchWithAuth.mockRejectedValue(new Error('error'));

        const result = await fetchTemplates();
        const ids = result.map(t => t.id);
        expect(ids).toContain('ieee');
        expect(ids).toContain('apa');
        expect(ids).toContain('nature');
    });
});

describe('getBuiltinTemplates', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('returns templates from API', async () => {
        const mockTemplates = [{ id: 'acm', name: 'ACM' }];
        mockFetchWithAuth.mockResolvedValue({ templates: mockTemplates });

        const result = await getBuiltinTemplates();
        expect(mockFetchWithAuth).toHaveBeenCalledWith('/api/v1/templates');
        expect(result).toEqual(mockTemplates);
    });

    it('returns fallback when API returns empty array', async () => {
        mockFetchWithAuth.mockResolvedValue({ templates: [] });

        const result = await getBuiltinTemplates();
        expect(result[0].id).toBe('none');
    });

    it('returns fallback on API error', async () => {
        mockFetchWithAuth.mockRejectedValue(new Error('fail'));

        const result = await getBuiltinTemplates();
        expect(result[0].id).toBe('none');
    });
});

describe('searchCSLStyles', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('calls fetchWithAuth with search param', async () => {
        mockFetchWithAuth.mockResolvedValue({ styles: [] });
        await searchCSLStyles('apa');
        expect(mockFetchWithAuth).toHaveBeenCalledWith('/api/v1/templates/csl?search=apa');
    });

    it('calls fetchWithAuth without search param when query is empty', async () => {
        mockFetchWithAuth.mockResolvedValue({ styles: [] });
        await searchCSLStyles();
        expect(mockFetchWithAuth).toHaveBeenCalledWith('/api/v1/templates/csl?');
    });

    it('returns data from API', async () => {
        mockFetchWithAuth.mockResolvedValue({ styles: [{ id: 'apa-6th' }] });
        const result = await searchCSLStyles('apa');
        expect(result).toEqual({ styles: [{ id: 'apa-6th' }] });
    });
});

describe('fetchCSLStyle', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('calls fetchWithAuth with style ID encoded', async () => {
        mockFetchWithAuth.mockResolvedValue({ xml: '<style/>' });
        await fetchCSLStyle('apa-6th');
        expect(mockFetchWithAuth).toHaveBeenCalledWith('/api/v1/templates/csl/apa-6th');
    });

    it('returns the CSL style data', async () => {
        mockFetchWithAuth.mockResolvedValue({ xml: '<style/>' });
        const result = await fetchCSLStyle('ieee');
        expect(result).toEqual({ xml: '<style/>' });
    });
});

describe('getCustomTemplates', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('calls fetchWithAuth with custom templates path', async () => {
        mockFetchWithAuth.mockResolvedValue({ templates: [] });
        await getCustomTemplates();
        expect(mockFetchWithAuth).toHaveBeenCalledWith('/api/v1/templates/custom');
    });
});

describe('saveCustomTemplate', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('posts custom template data', async () => {
        mockFetchWithAuth.mockResolvedValue({ id: 'custom-1' });
        const data = { name: 'My Template', styles: { font: 'Times' } };
        const result = await saveCustomTemplate(data);
        expect(mockFetchWithAuth).toHaveBeenCalledWith('/api/v1/templates/custom', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        expect(result).toEqual({ id: 'custom-1' });
    });
});
