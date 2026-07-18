import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

vi.mock('@/src/context/ThemeContext', () => {
    const mockUseTheme = vi.fn(() => ({
        theme: 'light',
        toggleTheme: vi.fn(),
        systemTheme: 'light',
    }));
    return { useTheme: mockUseTheme };
});

describe('ThemeToggle', () => {
    async function getComponent() {
        return (await import('../components/layout/header/ThemeToggle')).default;
    }

    it('renders after mount', async () => {
        const ThemeToggle = await getComponent();
        render(<ThemeToggle />);
        await waitFor(() => {
            expect(screen.getByRole('button')).toBeInTheDocument();
        });
    });

    it('calls toggleTheme on click', async () => {
        const { useTheme } = await import('../context/ThemeContext');
        const toggleTheme = vi.fn();
        useTheme.mockReturnValue({ theme: 'light', toggleTheme, systemTheme: 'light' });

        const ThemeToggle = await getComponent();
        render(<ThemeToggle />);
        await waitFor(() => {
            expect(screen.getByRole('button')).toBeInTheDocument();
        });
        fireEvent.click(screen.getByRole('button'));
        expect(toggleTheme).toHaveBeenCalledTimes(1);
    });

    it('shows dark mode icon when in dark mode', async () => {
        const { useTheme } = await import('../context/ThemeContext');
        useTheme.mockReturnValue({ theme: 'dark', toggleTheme: vi.fn(), systemTheme: 'dark' });

        const ThemeToggle = await getComponent();
        render(<ThemeToggle />);
        await waitFor(() => {
            expect(screen.getByText('light_mode')).toBeInTheDocument();
        });
    });

    it('shows light mode icon when in light mode', async () => {
        const { useTheme } = await import('../context/ThemeContext');
        useTheme.mockReturnValue({ theme: 'light', toggleTheme: vi.fn(), systemTheme: 'light' });

        const ThemeToggle = await getComponent();
        render(<ThemeToggle />);
        await waitFor(() => {
            expect(screen.getByText('dark_mode')).toBeInTheDocument();
        });
    });
});
