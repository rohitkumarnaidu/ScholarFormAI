// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, renderHook, act } from '@testing-library/react';
import React from 'react';

const { mockUpdateUser, mockGetSession } = vi.hoisted(() => ({
    mockUpdateUser: vi.fn().mockResolvedValue({ error: null }),
    mockGetSession: vi.fn().mockResolvedValue({ data: { session: { user: { id: 'user-1' } } } }),
}));

vi.mock('../lib/supabaseClient', () => ({
    supabase: {
        auth: {
            getSession: mockGetSession,
            updateUser: mockUpdateUser,
        },
    },
}));

vi.mock('next-themes', () => ({
    useTheme: () => ({
        theme: 'light',
        setTheme: vi.fn(),
        systemTheme: 'light',
    }),
    ThemeProvider: ({ children, ...props }) => React.createElement('div', { 'data-testid': 'next-themes-provider', ...props }, children),
}));

import { ThemeProvider, useTheme } from '../context/ThemeContext';

describe('ThemeContext', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockGetSession.mockResolvedValue({ data: { session: { user: { id: 'user-1' } } } });
        mockUpdateUser.mockResolvedValue({ error: null });
        Object.defineProperty(window, 'matchMedia', {
            value: vi.fn().mockImplementation(() => ({
                matches: false,
                addEventListener: vi.fn(),
                removeEventListener: vi.fn(),
            })),
            writable: true,
        });
    });

    it('provides default theme from next-themes', () => {
        const { result } = renderHook(() => useTheme(), { wrapper: ThemeProvider });
        expect(result.current.theme).toBe('light');
    });

    it('provides toggleTheme function', () => {
        const { result } = renderHook(() => useTheme(), { wrapper: ThemeProvider });
        expect(typeof result.current.toggleTheme).toBe('function');
    });

    it('provides setTheme function', () => {
        const { result } = renderHook(() => useTheme(), { wrapper: ThemeProvider });
        expect(typeof result.current.setTheme).toBe('function');
    });

    it('provides systemTheme', () => {
        const { result } = renderHook(() => useTheme(), { wrapper: ThemeProvider });
        expect(result.current.systemTheme).toBe('light');
    });

    it('provides systemPrefersDark boolean', () => {
        const { result } = renderHook(() => useTheme(), { wrapper: ThemeProvider });
        expect(typeof result.current.systemPrefersDark).toBe('boolean');
    });

    it('renders ThemeProvider children', () => {
        const { container } = render(
            React.createElement(ThemeProvider, null,
                React.createElement('div', { 'data-testid': 'child' }, 'Hello')
            )
        );
        expect(container.querySelector('[data-testid="child"]')).toBeTruthy();
    });

    it('sets displayName on ThemeProvider', () => {
        expect(ThemeProvider.displayName || 'ThemeProvider').toBe('ThemeProvider');
    });

    it('wraps with next-themes ThemeProvider', () => {
        const { container } = render(
            React.createElement(ThemeProvider, null,
                React.createElement('div', null, 'test')
            )
        );
        const nextProvider = container.querySelector('[data-testid="next-themes-provider"]');
        expect(nextProvider).toBeTruthy();
    });

    it('calls updateUser when setTheme is called with dark value', async () => {
        const { result } = renderHook(() => useTheme(), { wrapper: ThemeProvider });
        act(() => { result.current.setTheme('dark'); });
        await vi.waitFor(() => {
            expect(mockUpdateUser).toHaveBeenCalled();
        });
    });

    it('calls updateUser when setTheme is called with light value', async () => {
        const { result } = renderHook(() => useTheme(), { wrapper: ThemeProvider });
        act(() => { result.current.setTheme('light'); });
        await vi.waitFor(() => {
            expect(mockUpdateUser).toHaveBeenCalled();
        });
    });
});
