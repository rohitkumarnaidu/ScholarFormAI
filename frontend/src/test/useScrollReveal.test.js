// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import useScrollReveal from '@/src/hooks/useScrollReveal';

describe('useScrollReveal', () => {
    let observeFn;
    let disconnectFn;
    let observerCallback;

    beforeEach(() => {
        observeFn = vi.fn();
        disconnectFn = vi.fn();
        observerCallback = null;
        function MockIntersectionObserver(cb) {
            observerCallback = cb;
            this.observe = observeFn;
            this.disconnect = disconnectFn;
        }
        vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);
        window.matchMedia = vi.fn().mockReturnValue({ matches: false });
        Object.defineProperty(window, 'innerHeight', { value: 900, configurable: true });
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('returns a ref object', () => {
        const { result } = renderHook(() => useScrollReveal());
        expect(result.current).toHaveProperty('current');
    });

    it('adds revealed class when reduced motion is preferred', () => {
        window.matchMedia = vi.fn().mockReturnValue({ matches: true });
        const { result, rerender } = renderHook(({ threshold }) => useScrollReveal({ threshold }), {
            initialProps: { threshold: 0.15 },
        });
        const el = document.createElement('div');
        result.current.current = el;
        rerender({ threshold: 0.16 });
        expect(el.classList.contains('revealed')).toBe(true);
    });

    it('does not create IntersectionObserver when element is null', () => {
        renderHook(() => useScrollReveal());
        expect(observeFn).not.toHaveBeenCalled();
    });

    it('creates IntersectionObserver and observes element', () => {
        const { result, rerender } = renderHook(({ threshold }) => useScrollReveal({ threshold }), {
            initialProps: { threshold: 0.3 },
        });
        const el = document.createElement('div');
        Object.defineProperty(el, 'getBoundingClientRect', { value: () => ({ top: 1000 }) });
        result.current.current = el;
        rerender({ threshold: 0.31 });
        expect(observeFn).toHaveBeenCalledWith(el);
    });

    it('adds revealed when element is already in viewport', () => {
        const { result, rerender } = renderHook(({ threshold }) => useScrollReveal({ threshold }), {
            initialProps: { threshold: 0.15 },
        });
        const el = document.createElement('div');
        Object.defineProperty(el, 'getBoundingClientRect', { value: () => ({ top: 100 }) });
        result.current.current = el;
        rerender({ threshold: 0.16 });
        expect(el.classList.contains('revealed')).toBe(true);
        expect(observeFn).not.toHaveBeenCalled();
    });

    it('observes element when not in viewport', () => {
        const { result, rerender } = renderHook(({ threshold }) => useScrollReveal({ threshold }), {
            initialProps: { threshold: 0.15 },
        });
        const el = document.createElement('div');
        Object.defineProperty(el, 'getBoundingClientRect', { value: () => ({ top: 1000 }) });
        result.current.current = el;
        rerender({ threshold: 0.16 });
        expect(observeFn).toHaveBeenCalledWith(el);
    });

    it('disconnects observer on unmount', () => {
        const { result, rerender, unmount } = renderHook(
            ({ threshold }) => useScrollReveal({ threshold }),
            { initialProps: { threshold: 0.15 } }
        );
        const el = document.createElement('div');
        Object.defineProperty(el, 'getBoundingClientRect', { value: () => ({ top: 1000 }) });
        result.current.current = el;
        rerender({ threshold: 0.16 });
        unmount();
        expect(disconnectFn).toHaveBeenCalled();
    });

    it('triggers revealed when intersection observer callback fires', () => {
        const { result, rerender } = renderHook(({ threshold }) => useScrollReveal({ threshold }), {
            initialProps: { threshold: 0.15 },
        });
        const el = document.createElement('div');
        Object.defineProperty(el, 'getBoundingClientRect', { value: () => ({ top: 1000 }) });
        result.current.current = el;
        rerender({ threshold: 0.16 });
        expect(observerCallback).toBeDefined();
        observerCallback([{ isIntersecting: true }]);
        expect(el.classList.contains('revealed')).toBe(true);
    });
});
