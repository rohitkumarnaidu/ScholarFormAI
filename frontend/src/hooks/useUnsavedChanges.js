// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { useEffect } from 'react';

/**
 * Warns the user before leaving the page when there are unsaved changes.
 * Uses the browser's beforeunload event to show a native "Leave site?" dialog.
 *
 * @param {boolean} isDirty - Whether there are unsaved changes
 */
export function useUnsavedChanges(isDirty) {
    useEffect(() => {
        if (!isDirty) return;

        const handler = (e) => {
            e.preventDefault();
            // Modern browsers require returnValue to be set
            e.returnValue = '';
        };

        window.addEventListener('beforeunload', handler);
        return () => window.removeEventListener('beforeunload', handler);
    }, [isDirty]);
}
