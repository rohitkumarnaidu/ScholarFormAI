// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { fetchWithRetry } from '../../services/api.core';

export default function LatencyObserver() {
    const pathname = usePathname();

    useEffect(() => {
        // We use the Performance Navigation Timing API to get accurate page load metrics
        const reportTiming = () => {
            const [navigation] = performance.getEntriesByType('navigation');
            if (navigation) {
                const duration = navigation.duration;
                
                fetchWithRetry('/api/internal/metrics/record', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        method: 'GET',
                        route: pathname,
                        status: 200,
                        duration: duration,
                    }),
                }).catch(() => {}); // Silent fail for monitoring
            }
        };

        // Only report on initial load or client-side navigation completion
        if (document.readyState === 'complete') {
            reportTiming();
        } else {
            window.addEventListener('load', reportTiming, { once: true });
        }
    }, [pathname]);

    return null;
}
