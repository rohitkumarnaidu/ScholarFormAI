import { describe, it, expect } from 'vitest';
import { getUserTier, canAccess, getRemainingQuota, ENABLE_PRO_RESTRICTIONS } from '../lib/planTier';

describe('getUserTier', () => {
    it('returns guest for null user', () => {
        expect(getUserTier(null)).toBe('guest');
    });

    it('returns guest for undefined user', () => {
        expect(getUserTier(undefined)).toBe('guest');
    });

    it('returns plan_tier when present', () => {
        expect(getUserTier({ plan_tier: 'pro' })).toBe('pro');
    });

    it('returns free for user without plan_tier', () => {
        expect(getUserTier({ email: 'test@test.com' })).toBe('free');
    });
});

describe('canAccess', () => {
    it('returns true for pro users on any feature', () => {
        expect(canAccess({ plan_tier: 'pro' }, 'batch_upload')).toBe(true);
        expect(canAccess({ plan_tier: 'pro' }, 'generator_agent')).toBe(true);
    });

    it('returns true for free users if restrictions disabled', () => {
        if (!ENABLE_PRO_RESTRICTIONS) {
            expect(canAccess({}, 'batch_upload')).toBe(true);
        }
    });

    it('returns false for guest users on free features', () => {
        expect(canAccess(null, 'formatter_live')).toBe(false);
    });

    it('returns false for guest on pro features', () => {
        expect(canAccess(null, 'batch_upload')).toBe(false);
    });
});

describe('getRemainingQuota', () => {
    it('returns Infinity for pro users', () => {
        const q = getRemainingQuota({ plan_tier: 'pro' }, 100);
        expect(q.limit).toBe(Infinity);
        expect(q.remaining).toBe(Infinity);
    });

    it('returns correct used count', () => {
        const q = getRemainingQuota({}, 5);
        expect(q.used).toBe(5);
    });

    it('returns Infinity for free users when restrictions disabled', () => {
        if (!ENABLE_PRO_RESTRICTIONS) {
            const q = getRemainingQuota({}, 10);
            expect(q.remaining).toBe(Infinity);
        }
    });

    it('handles zero used count', () => {
        const q = getRemainingQuota({ plan_tier: 'pro' }, 0);
        expect(q.used).toBe(0);
        expect(q.remaining).toBe(Infinity);
    });
});
