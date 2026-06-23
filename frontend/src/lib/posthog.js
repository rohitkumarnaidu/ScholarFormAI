// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

let initialized = false;
let initPromise = null;
const pendingEvents = [];

function getPostHogConfig() {
    const apiKey = process.env.NEXT_PUBLIC_POSTHOG_KEY;
    const apiHost = process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://app.posthog.com';
    return { apiKey, apiHost };
}

function hasCaptureClient() {
    return Boolean(
        typeof window !== 'undefined'
        && window.posthog
        && typeof window.posthog.capture === 'function'
    );
}

function enqueueEvent(eventName, properties) {
    pendingEvents.push({ eventName, properties });
}

function flushPendingEvents() {
    if (!hasCaptureClient()) return;
    while (pendingEvents.length > 0) {
        const event = pendingEvents.shift();
        window.posthog.capture(event.eventName, event.properties);
    }
}

export function isPostHogConfigured() {
    const { apiKey } = getPostHogConfig();
    return Boolean(apiKey);
}

function loadPostHogScript() {
    return new Promise((resolve, reject) => {
        if (typeof window === 'undefined') {
            resolve(false);
            return;
        }

        if (window.posthog) {
            resolve(true);
            return;
        }

        const existing = document.querySelector('script[data-posthog-loader="true"]');
        if (existing) {
            existing.addEventListener('load', () => resolve(true), { once: true });
            existing.addEventListener('error', () => reject(new Error('Failed to load PostHog script')), { once: true });
            return;
        }

        const script = document.createElement('script');
        script.async = true;
        script.src = 'https://cdn.jsdelivr.net/npm/posthog-js@1.251.0/dist/posthog.min.js';
        script.setAttribute('data-posthog-loader', 'true');
        script.onload = () => resolve(true);
        script.onerror = () => reject(new Error('Failed to load PostHog script'));
        document.head.appendChild(script);
    });
}

export async function initPostHog() {
    if (typeof window === 'undefined') {
        return false;
    }
    if (initialized) {
        return true;
    }
    if (initPromise) {
        return initPromise;
    }

    const { apiKey, apiHost } = getPostHogConfig();
    if (!apiKey) {
        return false;
    }

    initPromise = (async () => {
        try {
            await loadPostHogScript();
            if (!window.posthog || typeof window.posthog.init !== 'function') {
                return false;
            }

            window.posthog.init(apiKey, {
                api_host: apiHost,
                capture_pageview: false,
                capture_pageleave: true,
                person_profiles: 'identified_only',
            });
            initialized = true;
            flushPendingEvents();
            return true;
        } catch {
            // Analytics must never block app boot.
            return false;
        } finally {
            if (!initialized) {
                initPromise = null;
            }
        }
    })();

    return initPromise;
}

export function capturePostHogEvent(eventName, properties = {}, { queueIfNotReady = false } = {}) {
    if (!eventName || typeof window === 'undefined') {
        return false;
    }
    if (hasCaptureClient()) {
        window.posthog.capture(eventName, properties);
        return true;
    }
    if (queueIfNotReady && isPostHogConfigured()) {
        enqueueEvent(eventName, properties);
    }
    return false;
}

export function capturePostHogPageView(pathnameWithQuery) {
    if (!pathnameWithQuery) return;
    const captured = capturePostHogEvent('$pageview', {
        path: pathnameWithQuery,
        $current_url: window.location.href,
    }, { queueIfNotReady: true });
    if (!captured) {
        void initPostHog();
    }
}

export function _resetPostHogStateForTests() {
    initialized = false;
    initPromise = null;
    pendingEvents.length = 0;
}
