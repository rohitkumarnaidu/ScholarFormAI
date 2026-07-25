// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

export const initRUM = () => {
    if (typeof window !== 'undefined') {
        // Placeholder for future RUM initialization
        console.debug('[RUM] Real User Monitoring initialized');
    }
};

export const trackPageView = (pageName) => {
    if (typeof window !== 'undefined') {
        console.debug(`[RUM] PageView: ${pageName}`, {
            url: window.location.href,
            timestamp: new Date().toISOString()
        });
        // TODO: Send to analytics provider
    }
};

export const trackEvent = (eventName, properties = {}) => {
    if (typeof window !== 'undefined') {
        console.debug(`[RUM] Event: ${eventName}`, {
            ...properties,
            timestamp: new Date().toISOString()
        });
        // TODO: Send to analytics provider
    }
};
