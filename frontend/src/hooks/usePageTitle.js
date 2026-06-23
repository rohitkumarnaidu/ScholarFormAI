// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { useEffect } from 'react';

const SUFFIX = ' — ScholarForm AI';

/**
 * Sets document.title on mount. Resets to default on unmount.
 * @param {string} title - Page-specific title (e.g. "Upload Document")
 */
export default function usePageTitle(title) {
    useEffect(() => {
        const prev = document.title;
        document.title = title ? `${title}${SUFFIX}` : `ScholarForm AI`;
        return () => { document.title = prev; };
    }, [title]);
}
