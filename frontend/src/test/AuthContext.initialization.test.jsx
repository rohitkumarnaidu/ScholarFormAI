// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/context/AuthContext';

const { authMock } = vi.hoisted(() => ({
    authMock: {
        getSession: vi.fn(),
        getUser: vi.fn(),
        onAuthStateChange: vi.fn(),
        signOut: vi.fn(),
        setSession: vi.fn(),
        signInWithOAuth: vi.fn(),
    },
}));

vi.mock('../lib/supabaseClient', () => ({
    supabase: {
        auth: authMock,
    },
}));

vi.mock('@/services/api', () => ({
    signup: vi.fn(),
    login: vi.fn(),
    forgotPassword: vi.fn(),
    verifyOtp: vi.fn(),
    resetPassword: vi.fn(),
}));

function AuthStateProbe() {
    const { user, isLoggedIn, loading } = useAuth();

    return (
        <div>
            <div data-testid="loading">{String(loading)}</div>
            <div data-testid="isLoggedIn">{String(isLoggedIn)}</div>
            <div data-testid="userId">{user?.id ?? 'none'}</div>
        </div>
    );
}

function SignOutProbe() {
    const { signOut } = useAuth();

    return (
        <button
            data-testid="signOutBtn"
            onClick={() => signOut()}
        >
            Sign Out
        </button>
    );
}

describe('AuthContext initialization', () => {
    const sbKey = 'sb-testproject-auth-token';

    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
        sessionStorage.clear();
        authMock.onAuthStateChange.mockReturnValue({
            data: {
                subscription: { unsubscribe: vi.fn() },
            },
        });
        authMock.signOut.mockResolvedValue({ error: null });
    });

    it('clears auth state when cached session cannot be verified', async () => {
        localStorage.setItem(sbKey, JSON.stringify({ access_token: 'stale-token' }));
        authMock.getSession.mockResolvedValue({
            data: {
                session: {
                    access_token: 'cached-token',
                    user: { id: 'cached-user' },
                },
            },
            error: null,
        });
        authMock.getUser.mockResolvedValue({
            data: { user: null },
            error: { message: 'invalid token' },
        });

        render(
            <AuthProvider>
                <AuthStateProbe />
            </AuthProvider>
        );

        await waitFor(() => {
            expect(screen.getByTestId('loading')).toHaveTextContent('false');
        });

        expect(screen.getByTestId('isLoggedIn')).toHaveTextContent('false');
        expect(screen.getByTestId('userId')).toHaveTextContent('none');
        expect(authMock.signOut).toHaveBeenCalledWith({ scope: 'local' });
        expect(localStorage.getItem(sbKey)).toBeNull();
    });

    it('marks user as logged in when server verification succeeds', async () => {
        authMock.getSession.mockResolvedValue({
            data: {
                session: {
                    access_token: 'valid-token',
                    user: { id: 'cached-user' },
                },
            },
            error: null,
        });
        authMock.getUser.mockResolvedValue({
            data: { user: { id: 'verified-user' } },
            error: null,
        });

        render(
            <AuthProvider>
                <AuthStateProbe />
            </AuthProvider>
        );

        await waitFor(() => {
            expect(screen.getByTestId('loading')).toHaveTextContent('false');
        });

        expect(screen.getByTestId('isLoggedIn')).toHaveTextContent('true');
        expect(screen.getByTestId('userId')).toHaveTextContent('verified-user');
        expect(authMock.signOut).not.toHaveBeenCalled();
    });

    it('clears local supabase token key when signOut is called', async () => {
        localStorage.setItem(sbKey, JSON.stringify({ access_token: 'stale-token' }));
        authMock.getSession.mockResolvedValue({
            data: { session: null },
            error: null,
        });
        authMock.getUser.mockResolvedValue({
            data: { user: null },
            error: null,
        });

        render(
            <AuthProvider>
                <SignOutProbe />
            </AuthProvider>
        );

        await waitFor(() => {
            expect(screen.getByTestId('signOutBtn')).toBeInTheDocument();
        });
        fireEvent.click(screen.getByTestId('signOutBtn'));

        await waitFor(() => {
            expect(authMock.signOut).toHaveBeenCalledWith({ scope: 'local' });
        });
        expect(localStorage.getItem(sbKey)).toBeNull();
    });
});
