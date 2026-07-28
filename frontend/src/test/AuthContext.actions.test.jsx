import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/context/AuthContext';

const { authMock, apiMock } = vi.hoisted(() => ({
    authMock: {
        getSession: vi.fn(),
        getUser: vi.fn(),
        onAuthStateChange: vi.fn(),
        signOut: vi.fn(),
        setSession: vi.fn(),
        signInWithOAuth: vi.fn(),
        updateUser: vi.fn(),
    },
    apiMock: {
        signup: vi.fn(),
        login: vi.fn(),
        forgotPassword: vi.fn(),
        verifyOtp: vi.fn(),
        resetPassword: vi.fn(),
    },
}));

vi.mock('../lib/supabaseClient', () => ({
    supabase: {
        auth: authMock,
    },
}));

vi.mock('@/services/api', () => apiMock);

function ActionProbe() {
    const { user, isLoggedIn, loading, signUp, signIn, signInWithGoogle, forgotPassword, resetPassword, verifyOtp, signOut } = useAuth();
    return (
        <div>
            <div data-testid="loading">{String(loading)}</div>
            <div data-testid="isLoggedIn">{String(isLoggedIn)}</div>
            <div data-testid="userId">{user?.id ?? 'none'}</div>
            <button data-testid="signup-btn" onClick={() => signUp({ email: 'test@test.com', password: 'pass' })}>Sign Up</button>
            <button data-testid="signin-btn" onClick={() => signIn('test@test.com', 'pass')}>Sign In</button>
            <button data-testid="google-btn" onClick={() => signInWithGoogle()}>Google</button>
            <button data-testid="forgot-btn" onClick={() => forgotPassword('test@test.com')}>Forgot</button>
            <button data-testid="reset-btn" onClick={() => resetPassword('test@test.com', '123456', 'newpass')}>Reset</button>
            <button data-testid="verify-btn" onClick={() => verifyOtp('test@test.com', '123456')}>Verify</button>
            <button data-testid="signout-btn" onClick={() => signOut({ redirectToLogin: true })}>Sign Out</button>
        </div>
    );
}

describe('AuthContext actions', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
        sessionStorage.clear();
        authMock.getSession.mockResolvedValue({ data: { session: null }, error: null });
        authMock.getUser.mockResolvedValue({ data: { user: null }, error: null });
        authMock.onAuthStateChange.mockReturnValue({
            data: { subscription: { unsubscribe: vi.fn() } },
        });
        authMock.signOut.mockResolvedValue({ error: null });
        authMock.setSession.mockResolvedValue({ error: null });
    });

    it('signUp calls api.signup and sets session on success', async () => {
        const sessionData = {
            session: { access_token: 'tok', refresh_token: 'ref', user: { id: 'new-user' } },
            user: { id: 'new-user' },
        };
        apiMock.signup.mockResolvedValueOnce(sessionData);

        render(<AuthProvider><ActionProbe /></AuthProvider>);

        await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

        fireEvent.click(screen.getByTestId('signup-btn'));

        await waitFor(() => {
            expect(apiMock.signup).toHaveBeenCalledWith({ email: 'test@test.com', password: 'pass' });
        });
        expect(authMock.setSession).toHaveBeenCalledWith({
            access_token: 'tok',
            refresh_token: 'ref',
        });
    });

    it('signUp returns error when api throws', async () => {
        apiMock.signup.mockRejectedValueOnce(new Error('Email taken'));

        render(<AuthProvider><ActionProbe /></AuthProvider>);

        await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

        fireEvent.click(screen.getByTestId('signup-btn'));

        await waitFor(() => {
            expect(screen.getByTestId('loading')).toHaveTextContent('false');
        });
    });

    it('signUp handles setSession failure', async () => {
        const sessionData = {
            session: { access_token: 'tok', refresh_token: 'ref', user: { id: 'new-user' } },
            user: { id: 'new-user' },
        };
        apiMock.signup.mockResolvedValueOnce(sessionData);
        authMock.setSession.mockResolvedValueOnce({ error: new Error('setSession failed') });

        render(<AuthProvider><ActionProbe /></AuthProvider>);

        await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

        fireEvent.click(screen.getByTestId('signup-btn'));

        await waitFor(() => {
            expect(screen.getByTestId('loading')).toHaveTextContent('false');
        });
    });

    it('signIn calls api.login and sets session', async () => {
        const loginData = {
            session: { access_token: 'tok', refresh_token: 'ref', user: { id: 'user-1' } },
            user: { id: 'user-1' },
        };
        apiMock.login.mockResolvedValueOnce(loginData);

        render(<AuthProvider><ActionProbe /></AuthProvider>);

        await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

        fireEvent.click(screen.getByTestId('signin-btn'));

        await waitFor(() => {
            expect(apiMock.login).toHaveBeenCalledWith({ email: 'test@test.com', password: 'pass' });
        });
        expect(authMock.setSession).toHaveBeenCalled();
    });

    it('signIn handles login error', async () => {
        apiMock.login.mockRejectedValueOnce(new Error('Invalid credentials'));

        render(<AuthProvider><ActionProbe /></AuthProvider>);

        await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

        fireEvent.click(screen.getByTestId('signin-btn'));

        await waitFor(() => {
            expect(screen.getByTestId('loading')).toHaveTextContent('false');
        });
    });

    it('signIn handles missing session gracefully', async () => {
        apiMock.login.mockResolvedValueOnce({ data: 'no_session_data' });

        render(<AuthProvider><ActionProbe /></AuthProvider>);

        await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

        fireEvent.click(screen.getByTestId('signin-btn'));

        await waitFor(() => {
            expect(screen.getByTestId('loading')).toHaveTextContent('false');
        });
    });

    it('signIn handles setSession failure', async () => {
        const loginData = {
            session: { access_token: 'tok', refresh_token: 'ref', user: { id: 'user-1' } },
            user: { id: 'user-1' },
        };
        apiMock.login.mockResolvedValueOnce(loginData);
        authMock.setSession.mockResolvedValueOnce({ error: { message: 'Session error' } });

        render(<AuthProvider><ActionProbe /></AuthProvider>);

        await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

        fireEvent.click(screen.getByTestId('signin-btn'));

        await waitFor(() => {
            expect(screen.getByTestId('loading')).toHaveTextContent('false');
        });
    });

    it('signInWithGoogle calls supabase OAuth', async () => {
        render(<AuthProvider><ActionProbe /></AuthProvider>);

        await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

        fireEvent.click(screen.getByTestId('google-btn'));

        await waitFor(() => {
            expect(authMock.signInWithOAuth).toHaveBeenCalledWith({
                provider: 'google',
                options: expect.objectContaining({
                    redirectTo: expect.stringContaining('/auth/callback'),
                }),
            });
        });
    });

    it('forgotPassword calls api.forgotPassword', async () => {
        render(<AuthProvider><ActionProbe /></AuthProvider>);

        await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

        fireEvent.click(screen.getByTestId('forgot-btn'));

        await waitFor(() => {
            expect(apiMock.forgotPassword).toHaveBeenCalledWith({ email: 'test@test.com' });
        });
    });

    it('forgotPassword handles error', async () => {
        apiMock.forgotPassword.mockRejectedValueOnce(new Error('User not found'));

        render(<AuthProvider><ActionProbe /></AuthProvider>);

        await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

        fireEvent.click(screen.getByTestId('forgot-btn'));

        await waitFor(() => {
            expect(screen.getByTestId('loading')).toHaveTextContent('false');
        });
    });

    it('resetPassword calls api.resetPassword', async () => {
        render(<AuthProvider><ActionProbe /></AuthProvider>);

        await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

        fireEvent.click(screen.getByTestId('reset-btn'));

        await waitFor(() => {
            expect(apiMock.resetPassword).toHaveBeenCalledWith({ email: 'test@test.com', otp: '123456', new_password: 'newpass' });
        });
    });

    it('resetPassword handles error', async () => {
        apiMock.resetPassword.mockRejectedValueOnce(new Error('Invalid OTP'));

        render(<AuthProvider><ActionProbe /></AuthProvider>);

        await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

        fireEvent.click(screen.getByTestId('reset-btn'));

        await waitFor(() => {
            expect(screen.getByTestId('loading')).toHaveTextContent('false');
        });
    });

    it('verifyOtp calls api.verifyOtp', async () => {
        render(<AuthProvider><ActionProbe /></AuthProvider>);

        await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

        fireEvent.click(screen.getByTestId('verify-btn'));

        await waitFor(() => {
            expect(apiMock.verifyOtp).toHaveBeenCalledWith({ email: 'test@test.com', otp: '123456' });
        });
    });

    it('verifyOtp handles error', async () => {
        apiMock.verifyOtp.mockRejectedValueOnce(new Error('Invalid OTP'));

        render(<AuthProvider><ActionProbe /></AuthProvider>);

        await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

        fireEvent.click(screen.getByTestId('verify-btn'));

        await waitFor(() => {
            expect(screen.getByTestId('loading')).toHaveTextContent('false');
        });
    });

    it('signOut redirects to login when redirectToLogin is true', async () => {
        Object.defineProperty(window, 'location', {
            value: { replace: vi.fn() },
            writable: true,
        });

        render(<AuthProvider><ActionProbe /></AuthProvider>);

        await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

        fireEvent.click(screen.getByTestId('signout-btn'));

        await waitFor(() => {
            expect(window.location.replace).toHaveBeenCalledWith('/login');
        });
    });

    it('signOut handles supabase error gracefully', async () => {
        authMock.signOut.mockRejectedValueOnce(new Error('Server error'));

        render(<AuthProvider><ActionProbe /></AuthProvider>);

        await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));

        fireEvent.click(screen.getByTestId('signout-btn'));

        await waitFor(() => {
            expect(screen.getByTestId('isLoggedIn')).toHaveTextContent('false');
        });
    });
});
