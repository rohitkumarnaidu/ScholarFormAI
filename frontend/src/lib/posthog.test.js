// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
    _resetPostHogStateForTests,
    capturePostHogEvent,
    capturePostHogPageView,
    initPostHog,
    isPostHogConfigured,
} from './posthog';

describe('posthog', () => {
    beforeEach(() => {
        _resetPostHogStateForTests();
        vi.unstubAllEnvs();
        delete window.posthog;
    });

    it('is not configured when NEXT_PUBLIC_POSTHOG_KEY is absent', () => {
        vi.stubEnv('NEXT_PUBLIC_POSTHOG_KEY', '');
        expect(isPostHogConfigured()).toBe(false);
    });

    it('initializes with existing posthog client and flushes queued events', async () => {
        vi.stubEnv('NEXT_PUBLIC_POSTHOG_KEY', 'phc_test');
        const init = vi.fn();
        const capture = vi.fn();

        // Queue event before client is ready.
        const immediateCapture = capturePostHogEvent('upload_started', { flow: 'formatter' }, { queueIfNotReady: true });
        expect(immediateCapture).toBe(false);

        window.posthog = { init, capture };
        const initialized = await initPostHog();

        expect(initialized).toBe(true);
        expect(init).toHaveBeenCalledTimes(1);
        expect(capture).toHaveBeenCalledWith('upload_started', { flow: 'formatter' });
    });

    it('captures pageview when posthog client is available', () => {
        vi.stubEnv('NEXT_PUBLIC_POSTHOG_KEY', 'phc_test');
        const capture = vi.fn();
        window.posthog = { init: vi.fn(), capture };

        capturePostHogPageView('/dashboard?tab=recent');

        expect(capture).toHaveBeenCalledWith('$pageview', expect.objectContaining({
            path: '/dashboard?tab=recent',
        }));
    });
});
