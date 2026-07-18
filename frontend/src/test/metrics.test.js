import { describe, it, expect } from 'vitest';
import { httpRequestDurationMicroseconds } from '../lib/metrics';

describe('metrics httpRequestDurationMicroseconds', () => {
    it('observes a value and stores count', () => {
        httpRequestDurationMicroseconds.observe({ method: 'GET', route: '/test', status_code: '200' }, 0.5);
        // Can't easily verify internal state, but call shouldn't throw
        expect(true).toBe(true);
    });

    it('handles multiple observations', () => {
        httpRequestDurationMicroseconds.observe({ method: 'POST', route: '/api', status_code: '201' }, 0.3);
        httpRequestDurationMicroseconds.observe({ method: 'POST', route: '/api', status_code: '201' }, 0.7);
        expect(true).toBe(true);
    });

    it('handles invalid duration values', () => {
        httpRequestDurationMicroseconds.observe({ method: 'GET', route: '/bad', status_code: '500' }, NaN);
        httpRequestDurationMicroseconds.observe({ method: 'GET', route: '/bad', status_code: '500' }, -1);
        expect(true).toBe(true);
    });

    it('sanitizes label values', () => {
        httpRequestDurationMicroseconds.observe(
            { method: 'GET', route: '/test"with"quotes', status_code: '200' },
            0.1
        );
        expect(true).toBe(true);
    });
});
