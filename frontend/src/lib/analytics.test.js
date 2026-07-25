// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, expect, it } from 'vitest';

import { trackEvent } from './analytics';

describe('analytics.trackEvent', () => {
    it('returns false for any event', () => {
        expect(trackEvent('')).toBe(false);
        expect(trackEvent('upload_completed', { job_id: 'job-1' })).toBe(false);
        expect(trackEvent('generator_session_started', { session_id: 's-1' })).toBe(false);
    });
});
