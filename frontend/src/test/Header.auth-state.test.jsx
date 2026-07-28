// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import Header from '@/components/layout/Header';
import { useAuth } from '@/context/AuthContext';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

vi.mock('@/context/AuthContext', () => ({
    useAuth: vi.fn(),
}));

vi.mock('@/components/layout/header/ThemeToggle', () => ({
    default: () => <div data-testid="theme-toggle" />,
}));

vi.mock('@/components/NotificationBell', () => ({
    default: () => <div data-testid="notification-bell" />,
}));

describe('Header auth rendering', () => {
    beforeEach(() => {
        vi.clearAllMocks();

        useRouter.mockReturnValue({
            push: vi.fn(),
            replace: vi.fn(),
            prefetch: vi.fn(),
            back: vi.fn(),
            forward: vi.fn(),
            refresh: vi.fn(),
        });
        usePathname.mockReturnValue('/');
        useSearchParams.mockReturnValue(new URLSearchParams());
    });

    it('shows guest actions when user object exists but session is not logged in', () => {
        useAuth.mockReturnValue({
            user: { id: 'stale-user' },
            isLoggedIn: false,
            loading: false,
        });

        render(<Header />);

        expect(screen.getByText('Login')).toBeInTheDocument();
        expect(screen.queryByText('Researcher')).not.toBeInTheDocument();
    });

    it('shows dashboard action only when isLoggedIn is true', () => {
        useAuth.mockReturnValue({
            user: { id: 'real-user' },
            isLoggedIn: true,
            loading: false,
        });

        render(<Header />);

        expect(screen.getByText('Researcher')).toBeInTheDocument();
        expect(screen.queryByText('Login')).not.toBeInTheDocument();
    });

    it('hides guest actions while auth is loading on app routes', () => {
        usePathname.mockReturnValue('/dashboard');
        useAuth.mockReturnValue({
            user: null,
            isLoggedIn: false,
            loading: true,
        });

        render(<Header isSidebarLayout onOpenMobileSidebar={vi.fn()} />);

        expect(screen.queryByText('Login')).not.toBeInTheDocument();
        expect(screen.queryByText('Sign Up')).not.toBeInTheDocument();
    });
});
