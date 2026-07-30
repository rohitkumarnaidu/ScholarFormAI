// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const supabaseAdmin = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL || '',
    process.env.SUPABASE_SERVICE_ROLE_KEY || '',
    { auth: { persistSession: false, autoRefreshToken: false } }
);

const decodeJwtPayload = (token) => {
    try {
        const base64Url = token.split('.')[1];
        if (!base64Url) return null;
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = atob(base64);
        return JSON.parse(jsonPayload);
    } catch {
        return null;
    }
};

const getAdminRole = (userOrPayload) => {
    if (!userOrPayload) return false;
    const appRole = userOrPayload?.app_metadata?.role;
    return appRole === 'admin';
};

const verifyJwtWithSupabase = async (token) => {
    try {
        const { data, error } = await supabaseAdmin.auth.getUser(token);
        if (error || !data?.user) return null;
        return data.user;
    } catch {
        return null;
    }
};

/**
 * Try to find an access token across Supabase cookie naming conventions.
 * Supabase JS v2 splits large session cookies into parts:
 *   sb-<ref>-auth-token.0, sb-<ref>-auth-token.1, …
 * It also sometimes stores the whole JSON under "supabase-auth-token".
 */
const extractAccessToken = (request) => {
    const cookieHeader = request.headers.get('cookie') || '';
    const cookies = {};
    cookieHeader.split(';').forEach((pair) => {
        const eqIdx = pair.indexOf('=');
        if (eqIdx === -1) return;
        const key = pair.slice(0, eqIdx).trim();
        const val = pair.slice(eqIdx + 1).trim();
        cookies[key] = val;
    });

    // 1. Try to find any cookie that looks like an sb-*-auth-token (may be JSON or raw JWT)
    const authCookieKey = Object.keys(cookies).find(
        (k) => k.startsWith('sb-') && k.endsWith('-auth-token')
    );

    if (authCookieKey) {
        const raw = cookies[authCookieKey];
        try {
            // Supabase stores the whole session object as JSON
            const parsed = JSON.parse(decodeURIComponent(raw));
            return parsed?.access_token || parsed?.[0]?.access_token || null;
        } catch {
            // Maybe it's a raw JWT (older storage)
            if (raw.split('.').length === 3) return raw;
        }
    }

    // 2. Chunked cookies: sb-<ref>-auth-token.0, .1, …  — concatenate and parse
    const chunkKeys = Object.keys(cookies)
        .filter((k) => /^sb-.+-auth-token\.\d+$/.test(k))
        .sort();

    if (chunkKeys.length > 0) {
        try {
            const combined = chunkKeys.map((k) => cookies[k]).join('');
            const parsed = JSON.parse(decodeURIComponent(combined));
            return parsed?.access_token || null;
        } catch {
            return null;
        }
    }

    return null;
};

export default async function middleware(request) {
    const { pathname } = request.nextUrl;

    const token = extractAccessToken(request);
    if (!token) {
        const url = request.nextUrl.clone();
        url.pathname = '/login';
        url.searchParams.set('reason', 'unauthorized');
        url.searchParams.set('next', pathname);
        return NextResponse.redirect(url);
    }

    const verifiedUser = await verifyJwtWithSupabase(token);
    if (!verifiedUser) {
        const payload = decodeJwtPayload(token);
        if (payload?.exp && payload.exp < Math.floor(Date.now() / 1000)) {
            const url = request.nextUrl.clone();
            url.pathname = '/login';
            url.searchParams.set('reason', 'session_expired');
            url.searchParams.set('next', pathname);
            return NextResponse.redirect(url);
        }
        const url = request.nextUrl.clone();
        url.pathname = '/login';
        url.searchParams.set('reason', 'invalid_token');
        return NextResponse.redirect(url);
    }

    const isAdminRoute = pathname.startsWith('/admin-dashboard') || pathname.startsWith('/admin');
    if (isAdminRoute && !getAdminRole(verifiedUser)) {
        if (pathname.startsWith('/api/')) {
            return new NextResponse(
                JSON.stringify({ success: false, message: 'Forbidden: Admin access required' }),
                { status: 403, headers: { 'content-type': 'application/json' } }
            );
        }
        const url = request.nextUrl.clone();
        url.pathname = '/dashboard';
        url.searchParams.set('reason', 'forbidden');
        return NextResponse.redirect(url);
    }

    return NextResponse.next();
}

export const config = {
    matcher: [
        '/admin-dashboard/:path*',
        '/dashboard/:path*',
        '/upload/:path*',
        '/batch-upload/:path*',
        '/history/:path*',
        '/results/:path*',
        '/preview/:path*',
        '/compare/:path*',
        '/settings/:path*',
        '/profile/:path*',
        '/api-keys/:path*',
        '/generate/:path*',
        '/synthesis/:path*',
        '/agent/:path*',
        '/template-editor/:path*',
    ],
};
