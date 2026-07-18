import { describe, it, expect, vi } from 'vitest';
import { getPreviewHtml, getAiSuggestion } from '../services/api.preview.v1';

vi.mock('../services/api.v1', () => ({
    postV1: vi.fn(() => Promise.resolve({ data: { html: '<p>Preview</p>', warnings: [] }, error: null })),
    unwrapResponse: vi.fn((envelope) => envelope.data),
}));

describe('getPreviewHtml', () => {
    it('posts content and template to /preview/live', async () => {
        const { postV1 } = await import('../services/api.v1');
        const result = await getPreviewHtml('<p>Test</p>', 'apa');

        expect(postV1).toHaveBeenCalledWith('/preview/live', {
            content: '<p>Test</p>',
            template_id: 'apa',
        });
        expect(result).toEqual({ html: '<p>Preview</p>', warnings: [] });
    });

    it('handles empty content', async () => {
        const { postV1 } = await import('../services/api.v1');
        await getPreviewHtml('', null);
        expect(postV1).toHaveBeenCalledWith('/preview/live', {
            content: '',
            template_id: null,
        });
    });
});

describe('getAiSuggestion', () => {
    it('returns an EventSource with correct URL', () => {
        const EventSource = vi.fn();
        vi.stubGlobal('EventSource', EventSource);

        getAiSuggestion('session-1', 'content', 'apa');

        expect(EventSource).toHaveBeenCalledWith(
            expect.stringContaining('/api/v1/preview/session-1/ai-suggest'),
            { withCredentials: true }
        );
    });

});
