// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { useEffect, useCallback } from 'react';

const STORAGE_KEY = 'scholarform_generator_draft';

export function useAutosave(formData, currentStep) {
    // Save every 10 seconds
    useEffect(() => {
        const timer = setInterval(() => {
            try {
                localStorage.setItem(STORAGE_KEY, JSON.stringify({ formData, currentStep, savedAt: Date.now() }));
            } catch (e) { /* quota exceeded — silently fail */ }
        }, 10000);
        return () => clearInterval(timer);
    }, [formData, currentStep]);

    // Restore on mount
    const restoreDraft = useCallback(() => {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (!saved) return null;
            const parsed = JSON.parse(saved);
            // Only restore if saved within 24 hours
            if (Date.now() - parsed.savedAt > 86400000) {
                localStorage.removeItem(STORAGE_KEY);
                return null;
            }
            return parsed;
        } catch { return null; }
    }, []);

    const clearDraft = useCallback(() => {
        localStorage.removeItem(STORAGE_KEY);
    }, []);

    return { restoreDraft, clearDraft };
}
