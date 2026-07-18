import { describe, it, expect, vi, beforeEach } from 'vitest';
import { initRUM, trackPageView, trackEvent } from '../lib/rum';

describe('RUM utilities', () => {
    beforeEach(() => {
        vi.spyOn(console, 'debug').mockImplementation(() => {});
    });

    it('initRUM logs initialization', () => {
        initRUM();
        expect(console.debug).toHaveBeenCalledWith('[RUM] Real User Monitoring initialized');
    });

    it('trackPageView logs page view', () => {
        trackPageView('/dashboard');
        expect(console.debug).toHaveBeenCalledWith(
            '[RUM] PageView: /dashboard',
            expect.objectContaining({ url: expect.any(String) })
        );
    });

    it('trackEvent logs event with properties', () => {
        trackEvent('upload_started', { job_id: '123' });
        expect(console.debug).toHaveBeenCalledWith(
            '[RUM] Event: upload_started',
            expect.objectContaining({ job_id: '123' })
        );
    });

    it('trackEvent works without properties', () => {
        trackEvent('page_view');
        expect(console.debug).toHaveBeenCalledWith(
            '[RUM] Event: page_view',
            expect.any(Object)
        );
    });
});
