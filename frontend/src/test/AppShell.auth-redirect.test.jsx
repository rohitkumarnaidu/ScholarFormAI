// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import AppShell from '@/components/layout/AppShell';
import { useAuth } from '@/context/AuthContext';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

vi.mock('@/context/AuthContext', () => ({
    useAuth: vi.fn(),
}));

vi.mock('@/components/layout/Header', () => ({
    default: () => <div data-testid="header" />,
}));

vi.mock('@/components/layout/Sidebar', () => ({
    default: () => <div data-testid="sidebar" />,
}));

vi.mock('@/components/OnboardingTour', () => ({
    default: () => null,
}));

describe('AppShell landing auth redirect', () => {
    const replaceMock = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        window.matchMedia = vi.fn().mockImplementation(() => ({
            matches: true,
            media: '(min-width: 1024px)',
            onchange: null,
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
            addListener: vi.fn(),
            removeListener: vi.fn(),
            dispatchEvent: vi.fn(),
        }));
        useRouter.mockReturnValue({
            push: vi.fn(),
            replace: replaceMock,
            prefetch: vi.fn(),
            back: vi.fn(),
            forward: vi.fn(),
            refresh: vi.fn(),
        });
    });

    it('redirects authenticated users from landing to dashboard', async () => {
        usePathname.mockReturnValue('/');
        useSearchParams.mockReturnValue(new URLSearchParams());
        useAuth.mockReturnValue({
            user: { id: 'u1' },
            isLoggedIn: true,
            loading: false,
        });

        render(
            <AppShell>
                <div>Landing content</div>
            </AppShell>
        );

        await waitFor(() => {
            expect(replaceMock).toHaveBeenCalledWith('/dashboard');
        });
    });

    it('does not redirect when guest mode is explicitly forced', async () => {
        usePathname.mockReturnValue('/');
        useSearchParams.mockReturnValue(new URLSearchParams('guest=1'));
        
        const originalLocation = window.location;
        delete window.location;
        window.location = { search: '?guest=1', href: 'http://localhost/?guest=1', origin: 'http://localhost' };
        useAuth.mockReturnValue({
            user: { id: 'u1' },
            isLoggedIn: true,
            loading: false,
        });

        render(
            <AppShell>
                <div>Landing content</div>
            </AppShell>
        );

        await waitFor(() => {
            expect(replaceMock).not.toHaveBeenCalled();
        });

        // Cleanup
        window.location = originalLocation;
    });
});
