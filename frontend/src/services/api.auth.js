// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { supabase } from '../lib/supabaseClient';
import { fetchWithAuth, sanitizePayload } from './api.core';

const postJson = (endpoint, payload) => (
    fetchWithAuth(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sanitizePayload(payload)),
    })
);

const sanitizeRedirectPath = (path) => {
    if (typeof path !== 'string') return '/dashboard';
    if (!path.startsWith('/') || path.startsWith('//')) return '/dashboard';
    return path;
};

export const signup = async (data) => postJson('/api/v1/auth/signup', data);

export const login = async (data) => postJson('/api/v1/auth/login', data);

export const forgotPassword = async (data) => postJson('/api/v1/auth/forgot-password', data);

export const verifyOtp = async (data) => postJson('/api/v1/auth/verify-otp', data);

export const resetPassword = async (data) => postJson('/api/v1/auth/reset-password', data);

export const googleAuth = async (redirectPath = '/dashboard') => {
    if (!supabase) throw new Error('Supabase client is not initialized');

    const safeRedirectPath = sanitizeRedirectPath(redirectPath);
    return supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
            redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(safeRedirectPath)}`,
        },
    });
};
