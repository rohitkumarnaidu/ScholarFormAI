import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import usePageTitle from '../hooks/usePageTitle';

describe('usePageTitle', () => {
    beforeEach(() => {
        document.title = 'ScholarForm AI';
    });

    it('sets document title with suffix', () => {
        renderHook(() => usePageTitle('Upload Document'));
        expect(document.title).toBe('Upload Document — ScholarForm AI');
    });

    it('sets fallback title when empty', () => {
        renderHook(() => usePageTitle(''));
        expect(document.title).toBe('ScholarForm AI');
    });

    it('restores previous title on unmount', () => {
        document.title = 'Original Page';
        const { unmount } = renderHook(() => usePageTitle('New Page'));
        expect(document.title).toBe('New Page — ScholarForm AI');

        unmount();
        expect(document.title).toBe('Original Page');
    });

    it('renders title with suffix for whitespace-only title', () => {
        renderHook(() => usePageTitle('   '));
        expect(document.title).toBe('— ScholarForm AI');
    });
});
