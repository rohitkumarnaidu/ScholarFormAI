// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import AuthGuard from '@/components/layout/AuthGuard';
import { useAuth } from '@/context/AuthContext';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

vi.mock('@/context/AuthContext', () => ({
    useAuth: vi.fn(),
}));

describe('AuthGuard', () => {
    const replaceMock = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        useRouter.mockReturnValue({
            push: vi.fn(),
            replace: replaceMock,
            prefetch: vi.fn(),
            back: vi.fn(),
            forward: vi.fn(),
            refresh: vi.fn(),
        });
        usePathname.mockReturnValue('/dashboard');
        useSearchParams.mockReturnValue(new URLSearchParams('tab=recent'));
    });

    it('redirects to login when unauthenticated', async () => {
        useAuth.mockReturnValue({ isLoggedIn: false, loading: false, user: null });

        render(
            <AuthGuard>
                <div>Protected Content</div>
            </AuthGuard>
        );

        await waitFor(() => {
            expect(replaceMock).toHaveBeenCalledWith('/login?next=%2Fdashboard%3Ftab%3Drecent');
        });
        expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });

    it('renders children when authenticated', () => {
        useAuth.mockReturnValue({ isLoggedIn: true, loading: false, user: { id: 'u1' } });

        render(
            <AuthGuard>
                <div>Protected Content</div>
            </AuthGuard>
        );

        expect(screen.getByText('Protected Content')).toBeInTheDocument();
        expect(replaceMock).not.toHaveBeenCalled();
    });

    it('redirects non-admin user from admin-only route', async () => {
        useAuth.mockReturnValue({
            isLoggedIn: true,
            loading: false,
            user: { id: 'u1', app_metadata: { role: 'user' } },
        });

        render(
            <AuthGuard requireAdmin>
                <div>Admin Panel</div>
            </AuthGuard>
        );

        await waitFor(() => {
            expect(replaceMock).toHaveBeenCalledWith('/dashboard');
        });
        expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument();
    });
});
