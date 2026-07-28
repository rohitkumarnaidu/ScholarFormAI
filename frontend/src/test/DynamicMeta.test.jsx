import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import React from 'react';

const mockUseTheme = vi.fn(() => ({ theme: 'dark' }));

vi.mock('../context/ThemeContext', () => ({
    useTheme: mockUseTheme,
}));

describe('DynamicMeta', () => {
    it('renders null', async () => {
        const DynamicMeta = (await import('../components/layout/DynamicMeta')).default;
        const { container } = render(<DynamicMeta />);
        expect(container.innerHTML).toBe('');
    });

    it('sets theme-color meta for dark mode', async () => {
        const meta = document.createElement('meta');
        meta.name = 'theme-color';
        document.head.appendChild(meta);

        const DynamicMeta = (await import('../components/layout/DynamicMeta')).default;
        render(<DynamicMeta />);
        expect(meta.content).toBe('#09090b');

        document.head.removeChild(meta);
    });

    it('sets theme-color meta for light mode', async () => {
        const { useTheme } = await import('@/context/ThemeContext');
        useTheme.mockReturnValue({ theme: 'light' });

        const meta = document.createElement('meta');
        meta.name = 'theme-color';
        document.head.appendChild(meta);

        const DynamicMeta = (await import('../components/layout/DynamicMeta')).default;
        render(<DynamicMeta />);
        expect(meta.content).toBe('#f6f6f8');

        document.head.removeChild(meta);
    });
});
