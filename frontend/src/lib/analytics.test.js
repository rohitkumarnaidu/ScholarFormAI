// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { beforeEach, describe, expect, it, vi } from 'vitest';

const {
    capturePostHogEventMock,
    initPostHogMock,
    isPostHogConfiguredMock,
} = vi.hoisted(() => ({
    capturePostHogEventMock: vi.fn(),
    initPostHogMock: vi.fn(),
    isPostHogConfiguredMock: vi.fn(),
}));

vi.mock('@/src/lib/posthog', () => ({
    capturePostHogEvent: capturePostHogEventMock,
    initPostHog: initPostHogMock,
    isPostHogConfigured: isPostHogConfiguredMock,
}));

import { trackEvent } from './analytics';

describe('analytics.trackEvent', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        isPostHogConfiguredMock.mockReturnValue(false);
        capturePostHogEventMock.mockReturnValue(false);
    });

    it('returns false for empty event names', () => {
        expect(trackEvent('')).toBe(false);
        expect(capturePostHogEventMock).not.toHaveBeenCalled();
    });

    it('returns true when event is captured immediately', () => {
        capturePostHogEventMock.mockReturnValue(true);

        const result = trackEvent('upload_completed', { job_id: 'job-1' });

        expect(result).toBe(true);
        expect(capturePostHogEventMock).toHaveBeenCalledWith(
            'upload_completed',
            { job_id: 'job-1' },
            { queueIfNotReady: true }
        );
        expect(initPostHogMock).not.toHaveBeenCalled();
    });

    it('initializes posthog lazily when configured but not yet ready', () => {
        isPostHogConfiguredMock.mockReturnValue(true);

        const result = trackEvent('generator_session_started', { session_id: 's-1' });

        expect(result).toBe(false);
        expect(initPostHogMock).toHaveBeenCalledTimes(1);
    });
});
