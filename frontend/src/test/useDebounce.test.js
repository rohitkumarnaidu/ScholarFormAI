import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDebounce } from '../hooks/useDebounce';

describe('useDebounce', () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('returns initial value immediately', () => {
        const { result } = renderHook(() => useDebounce('hello', 300));
        expect(result.current).toBe('hello');
    });

    it('updates debounced value after delay', () => {
        const { result, rerender } = renderHook(
            ({ value, delay }) => useDebounce(value, delay),
            { initialProps: { value: 'hello', delay: 300 } }
        );

        rerender({ value: 'world', delay: 300 });

        expect(result.current).toBe('hello');

        act(() => { vi.advanceTimersByTime(300); });

        expect(result.current).toBe('world');
    });

    it('uses default delay of 300ms', () => {
        const { result } = renderHook(() => useDebounce('test'));
        expect(result.current).toBe('test');
    });

    it('cancels previous timer on rapid updates', () => {
        const { result, rerender } = renderHook(
            ({ value }) => useDebounce(value, 300),
            { initialProps: { value: 'a' } }
        );

        rerender({ value: 'b' });
        act(() => { vi.advanceTimersByTime(100); });

        rerender({ value: 'c' });
        act(() => { vi.advanceTimersByTime(300); });

        expect(result.current).toBe('c');
    });
});
