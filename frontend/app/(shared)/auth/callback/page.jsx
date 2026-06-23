// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

import { supabase } from '@/src/lib/supabaseClient';
import { useAuth } from '@/src/context/AuthContext';

export default function AuthCallback() {
    usePageTitle('Authenticating');
    const router = useRouter();
    const { refreshSession } = useAuth();
    const [error, setError] = useState('');

    useEffect(() => {
        let isMounted = true;

        const completeOAuthSignIn = async () => {
            try {
                if (!supabase) {
                    throw new Error('Supabase is not configured. Check NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.');
                }

                const queryParams = new URLSearchParams(window.location.search);
                const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''));
                const nextPath = queryParams.get('next');
                const redirectTarget = (typeof nextPath === 'string' && nextPath.startsWith('/') && !nextPath.startsWith('//'))
                    ? nextPath
                    : '/dashboard';

                const callbackError =
                    queryParams.get('error_description') ||
                    queryParams.get('error') ||
                    hashParams.get('error_description') ||
                    hashParams.get('error');

                if (callbackError) {
                    throw new Error(decodeURIComponent(callbackError.replace(/\+/g, ' ')));
                }

                const code = queryParams.get('code');
                if (code) {
                    const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);
                    if (exchangeError) {
                        throw exchangeError;
                    }
                }

                const accessToken = hashParams.get('access_token');
                const refreshToken = hashParams.get('refresh_token');
                if (accessToken && refreshToken) {
                    const { error: setSessionError } = await supabase.auth.setSession({
                        access_token: accessToken,
                        refresh_token: refreshToken,
                    });
                    if (setSessionError) {
                        throw setSessionError;
                    }
                }

                const {
                    data: { session },
                    error: sessionError,
                } = await supabase.auth.getSession();

                if (sessionError) {
                    throw sessionError;
                }

                if (!session?.access_token) {
                    throw new Error('No active session was returned from OAuth.');
                }

                await refreshSession();
                if (isMounted) {
                    router.replace(redirectTarget);
                }
            } catch (oauthError) {
                if (isMounted) {
                    setError(
                        typeof oauthError?.message === 'string'
                            ? oauthError.message
                            : 'Unable to complete Google sign in. Please try again.'
                    );
                }
            }
        };

        completeOAuthSignIn();
        return () => {
            isMounted = false;
        };
    }, [refreshSession, router]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-background-light dark:bg-background-dark px-4">
            <div className="w-full max-w-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-8 text-center shadow-sm">
                <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-3">Completing sign in...</h1>
                {error ? (
                    <>
                        <p className="text-sm text-red-600 dark:text-red-400 mb-6">{error}</p>
                        <Link
                            href="/login"
                            className="inline-flex items-center justify-center rounded-lg h-11 px-5 bg-primary text-white text-sm font-semibold hover:bg-primary/90 transition-colors"
                        >
                            Back to login
                        </Link>
                    </>
                ) : (
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                        Please wait while we finish your authentication.
                    </p>
                )}
            </div>
        </div>
    );
}


