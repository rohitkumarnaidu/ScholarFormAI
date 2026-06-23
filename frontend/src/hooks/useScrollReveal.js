// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { useEffect, useMemo, useRef } from 'react';

/**
 * Lightweight scroll-reveal hook using IntersectionObserver.
 * Adds 'revealed' class when element enters viewport, then disconnects.
 * Respects prefers-reduced-motion by revealing immediately.
 */
export default function useScrollReveal(options = {}) {
    const ref = useRef(null);
    const observerOptions = useMemo(
        () => ({ threshold: 0.15, ...options }),
        [options]
    );

    useEffect(() => {
        const el = ref.current;
        if (!el) return;

        // Respect reduced-motion preference
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            el.classList.add('revealed');
            return;
        }

        // If route restores a scrolled position and element is already above/inside viewport,
        // reveal immediately so sections don't appear inconsistent.
        const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
        const rect = el.getBoundingClientRect();
        if (rect.top <= viewportHeight * 0.85) {
            el.classList.add('revealed');
            return;
        }

        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting) {
                    el.classList.add('revealed');
                    observer.disconnect();
                }
            },
            observerOptions
        );

        observer.observe(el);
        return () => observer.disconnect();
    }, [observerOptions]);

    return ref;
}
