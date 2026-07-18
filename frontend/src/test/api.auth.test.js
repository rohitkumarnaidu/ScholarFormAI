import { describe, it, expect, vi } from 'vitest';
import { signup, login, forgotPassword, verifyOtp, resetPassword, googleAuth } from '../services/api.auth';

vi.mock('../services/api.core', () => ({
    fetchWithAuth: vi.fn(() => Promise.resolve({ ok: true })),
    sanitizePayload: vi.fn((x) => x),
}));

vi.mock('../lib/supabaseClient', () => ({
    supabase: {
        auth: {
            signInWithOAuth: vi.fn(() => Promise.resolve({ data: {}, error: null })),
        },
    },
}));

describe('api.auth', () => {
    it('signup posts to /api/v1/auth/signup', async () => {
        await signup({ email: 'test@test.com', password: 'test123' });
        const { fetchWithAuth } = await import('../services/api.core');
        expect(fetchWithAuth).toHaveBeenCalledWith('/api/v1/auth/signup', expect.any(Object));
    });

    it('login posts to /api/v1/auth/login', async () => {
        const { fetchWithAuth } = await import('../services/api.core');
        await login({ email: 'test@test.com', password: 'test123' });
        expect(fetchWithAuth).toHaveBeenCalledWith('/api/v1/auth/login', expect.any(Object));
    });

    it('forgotPassword posts to /api/v1/auth/forgot-password', async () => {
        const { fetchWithAuth } = await import('../services/api.core');
        await forgotPassword({ email: 'test@test.com' });
        expect(fetchWithAuth).toHaveBeenCalledWith('/api/v1/auth/forgot-password', expect.any(Object));
    });

    it('verifyOtp posts to /api/v1/auth/verify-otp', async () => {
        const { fetchWithAuth } = await import('../services/api.core');
        await verifyOtp({ email: 'test@test.com', token: '123456' });
        expect(fetchWithAuth).toHaveBeenCalledWith('/api/v1/auth/verify-otp', expect.any(Object));
    });

    it('resetPassword posts to /api/v1/auth/reset-password', async () => {
        const { fetchWithAuth } = await import('../services/api.core');
        await resetPassword({ password: 'newpass' });
        expect(fetchWithAuth).toHaveBeenCalledWith('/api/v1/auth/reset-password', expect.any(Object));
    });

    it('googleAuth calls supabase OAuth', async () => {
        const { supabase } = await import('../lib/supabaseClient');
        await googleAuth('/dashboard');
        expect(supabase.auth.signInWithOAuth).toHaveBeenCalledWith({
            provider: 'google',
            options: expect.objectContaining({
                redirectTo: expect.stringContaining('/auth/callback'),
            }),
        });
    });

    it('googleAuth sanitizes invalid redirect path (number)', async () => {
        const { supabase } = await import('../lib/supabaseClient');
        await googleAuth(123);
        expect(supabase.auth.signInWithOAuth).toHaveBeenCalledWith({
            provider: 'google',
            options: expect.objectContaining({
                redirectTo: expect.stringContaining(encodeURIComponent('/dashboard')),
            }),
        });
    });

    it('googleAuth sanitizes double-slash redirect path', async () => {
        const { supabase } = await import('../lib/supabaseClient');
        await googleAuth('//evil.com');
        expect(supabase.auth.signInWithOAuth).toHaveBeenCalledWith({
            provider: 'google',
            options: expect.objectContaining({
                redirectTo: expect.stringContaining(encodeURIComponent('/dashboard')),
            }),
        });
    });

    it('googleAuth uses default redirect for undefined path', async () => {
        const { supabase } = await import('../lib/supabaseClient');
        await googleAuth();
        expect(supabase.auth.signInWithOAuth).toHaveBeenCalledWith({
            provider: 'google',
            options: expect.objectContaining({
                redirectTo: expect.stringContaining(encodeURIComponent('/dashboard')),
            }),
        });
    });
});
