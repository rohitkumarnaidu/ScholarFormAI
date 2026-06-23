// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

/**
 * Lightweight analytics wrapper.
 * Keeps event tracking optional and non-blocking when PostHog is not configured.
 */
import { capturePostHogEvent, initPostHog, isPostHogConfigured } from '@/src/lib/posthog';

export function trackEvent(eventName, properties = {}) {
    if (typeof window === 'undefined' || !eventName) return false;

    try {
        const captured = capturePostHogEvent(eventName, properties, { queueIfNotReady: true });
        if (!captured && isPostHogConfigured()) {
            void initPostHog();
        }
        return captured;
    } catch {
        return false;
    }
}
