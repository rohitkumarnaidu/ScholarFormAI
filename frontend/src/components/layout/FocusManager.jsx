// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import { usePathname } from 'next/navigation';
import { useEffect } from 'react';

/**
 * Ensures focus moves to the main content area after route transitions.
 * Important for screen readers to know context has changed.
 */
export default function FocusManager() {
    const pathname = usePathname();

    useEffect(() => {
        const main = document.getElementById('main-content');
        if (main) {
            main.focus({ preventScroll: true });
        }
    }, [pathname]);

    return null;
}
