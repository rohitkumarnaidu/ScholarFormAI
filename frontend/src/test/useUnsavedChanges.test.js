// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useUnsavedChanges } from '@/src/hooks/useUnsavedChanges';

describe('useUnsavedChanges', () => {
    beforeEach(() => {
        vi.spyOn(window, 'addEventListener');
        vi.spyOn(window, 'removeEventListener');
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('registers beforeunload when isDirty is true', () => {
        renderHook(() => useUnsavedChanges(true));
        expect(window.addEventListener).toHaveBeenCalledWith('beforeunload', expect.any(Function));
    });

    it('does not register beforeunload when isDirty is false', () => {
        renderHook(() => useUnsavedChanges(false));
        expect(window.addEventListener).not.toHaveBeenCalled();
    });

    it('removes beforeunload on unmount when isDirty is true', () => {
        const { unmount } = renderHook(() => useUnsavedChanges(true));
        unmount();
        expect(window.removeEventListener).toHaveBeenCalledWith('beforeunload', expect.any(Function));
    });

    it('calls preventDefault on beforeunload', () => {
        renderHook(() => useUnsavedChanges(true));
        const handler = window.addEventListener.mock.calls.find(
            ([name]) => name === 'beforeunload'
        )[1];
        const event = new Event('beforeunload');
        const preventDefaultSpy = vi.spyOn(event, 'preventDefault');
        handler(event);
        expect(preventDefaultSpy).toHaveBeenCalled();
    });

    it('prevents default on beforeunload', () => {
        renderHook(() => useUnsavedChanges(true));
        const handler = window.addEventListener.mock.calls.find(
            ([name]) => name === 'beforeunload'
        )[1];
        const event = new Event('beforeunload');
        const preventDefaultSpy = vi.spyOn(event, 'preventDefault');
        handler(event);
        expect(preventDefaultSpy).toHaveBeenCalled();
    });

    it('updates listener when isDirty changes', () => {
        const { rerender } = renderHook(({ dirty }) => useUnsavedChanges(dirty), {
            initialProps: { dirty: false },
        });
        expect(window.addEventListener).not.toHaveBeenCalled();
        rerender({ dirty: true });
        expect(window.addEventListener).toHaveBeenCalledWith('beforeunload', expect.any(Function));
    });
});
