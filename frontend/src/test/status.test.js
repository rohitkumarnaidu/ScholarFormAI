import { describe, it, expect } from 'vitest';
import { STATUS, isCompleted, isProcessing, isFailed } from '../constants/status';

describe('status constants', () => {
    it('has correct enum values', () => {
        expect(STATUS.PENDING).toBe('PENDING');
        expect(STATUS.PROCESSING).toBe('PROCESSING');
        expect(STATUS.COMPLETED).toBe('COMPLETED');
        expect(STATUS.COMPLETED_WITH_WARNINGS).toBe('COMPLETED_WITH_WARNINGS');
        expect(STATUS.FAILED).toBe('FAILED');
        expect(STATUS.CANCELLED).toBe('CANCELLED');
    });
});

describe('isCompleted', () => {
    it('returns true for COMPLETED', () => {
        expect(isCompleted('COMPLETED')).toBe(true);
    });

    it('returns true for COMPLETED_WITH_WARNINGS', () => {
        expect(isCompleted('COMPLETED_WITH_WARNINGS')).toBe(true);
    });

    it('returns true for lowercase values', () => {
        expect(isCompleted('completed')).toBe(true);
    });

    it('returns false for PROCESSING', () => {
        expect(isCompleted('PROCESSING')).toBe(false);
    });

    it('returns false for FAILED', () => {
        expect(isCompleted('FAILED')).toBe(false);
    });

    it('returns false for null/undefined', () => {
        expect(isCompleted(null)).toBe(false);
        expect(isCompleted(undefined)).toBe(false);
    });
});

describe('isProcessing', () => {
    it('returns true for PROCESSING', () => {
        expect(isProcessing('PROCESSING')).toBe(true);
    });

    it('returns true for lowercase processing', () => {
        expect(isProcessing('processing')).toBe(true);
    });

    it('returns false for PENDING', () => {
        expect(isProcessing('PENDING')).toBe(false);
    });

    it('returns false for COMPLETED', () => {
        expect(isProcessing('COMPLETED')).toBe(false);
    });

    it('returns false for null/undefined', () => {
        expect(isProcessing(null)).toBe(false);
        expect(isProcessing(undefined)).toBe(false);
    });
});

describe('isFailed', () => {
    it('returns true for FAILED', () => {
        expect(isFailed('FAILED')).toBe(true);
    });

    it('returns true for lowercase failed', () => {
        expect(isFailed('failed')).toBe(true);
    });

    it('returns false for COMPLETED', () => {
        expect(isFailed('COMPLETED')).toBe(false);
    });

    it('returns false for null/undefined', () => {
        expect(isFailed(null)).toBe(false);
        expect(isFailed(undefined)).toBe(false);
    });
});
