// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAutosave } from '@/hooks/useAutosave';

const STORAGE_KEY = 'scholarform_generator_draft';

describe('useAutosave', () => {
    beforeEach(() => {
        vi.useFakeTimers();
        localStorage.clear();
    });

    afterEach(() => {
        vi.useRealTimers();
        vi.restoreAllMocks();
    });

    it('saves form data to localStorage on interval', () => {
        const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');
        const formData = { title: 'Test' };
        renderHook(() => useAutosave(formData, 1));
        act(() => { vi.advanceTimersByTime(10000); });
        expect(setItemSpy).toHaveBeenCalledWith(
            STORAGE_KEY,
            expect.stringContaining('"formData":{"title":"Test"}')
        );
    });

    it('includes current step in saved data', () => {
        const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');
        renderHook(() => useAutosave({ foo: 'bar' }, 3));
        act(() => { vi.advanceTimersByTime(10000); });
        expect(setItemSpy).toHaveBeenCalledWith(
            STORAGE_KEY,
            expect.stringContaining('"currentStep":3')
        );
    });

    it('includes savedAt timestamp', () => {
        const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');
        renderHook(() => useAutosave({}, 1));
        act(() => { vi.advanceTimersByTime(10000); });
        expect(setItemSpy).toHaveBeenCalledWith(
            STORAGE_KEY,
            expect.stringContaining('"savedAt"')
        );
    });

    it('saves periodically every 10 seconds', () => {
        const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');
        renderHook(() => useAutosave({}, 1));
        act(() => { vi.advanceTimersByTime(30000); });
        expect(setItemSpy).toHaveBeenCalledTimes(3);
    });

    it('does not crash when localStorage is full', () => {
        vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
            throw new Error('QuotaExceededError');
        });
        expect(() => {
            renderHook(() => useAutosave({ data: 'test' }, 1));
            act(() => { vi.advanceTimersByTime(10000); });
        }).not.toThrow();
    });

    it('clears interval on unmount', () => {
        const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');
        const { unmount } = renderHook(() => useAutosave({}, 1));
        unmount();
        act(() => { vi.advanceTimersByTime(10000); });
        expect(setItemSpy).not.toHaveBeenCalled();
    });

    it('restoreDraft returns null when no saved data', () => {
        const { result } = renderHook(() => useAutosave({}, 1));
        expect(result.current.restoreDraft()).toBeNull();
    });

    it('restoreDraft returns parsed saved data', () => {
        const saved = { formData: { title: 'Draft' }, currentStep: 2, savedAt: Date.now() };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
        const { result } = renderHook(() => useAutosave({}, 1));
        expect(result.current.restoreDraft()).toEqual(saved);
    });

    it('restoreDraft returns null when saved data is expired (>24h)', () => {
        const expired = { formData: {}, currentStep: 1, savedAt: Date.now() - 86400001 };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(expired));
        const { result } = renderHook(() => useAutosave({}, 1));
        expect(result.current.restoreDraft()).toBeNull();
        expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
    });

    it('restoreDraft returns null on JSON parse error', () => {
        localStorage.setItem(STORAGE_KEY, 'invalid-json');
        const { result } = renderHook(() => useAutosave({}, 1));
        expect(result.current.restoreDraft()).toBeNull();
    });

    it('clearDraft removes saved data from localStorage', () => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ formData: {}, currentStep: 1, savedAt: Date.now() }));
        const { result } = renderHook(() => useAutosave({}, 1));
        result.current.clearDraft();
        expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
    });
});
