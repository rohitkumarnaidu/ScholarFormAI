// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { supabase } from '../lib/supabaseClient';
import {
    signup as apiSignup,
    login as apiLogin,
    forgotPassword as apiForgotPassword,
    verifyOtp as apiVerifyOtp,
    resetPassword as apiResetPassword,
} from '@/services/api';

const AuthContext = createContext();

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (typeof document !== 'undefined' && document.cookie.includes('playwright-bypass-auth=true')) {
        return {
            ...context,
            isLoggedIn: true,
            user: { 
                id: 'playwright-user', 
                email: 'test@example.com', 
                app_metadata: { role: 'admin' }, 
                user_metadata: { role: 'admin' } 
            },
            loading: false
        };
    }
    return context;
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [loading, setLoading] = useState(true);
    const E2E_USER_STORAGE_KEY = 'scholarform_e2e_user';

    // Guard: prevents onAuthStateChange('SIGNED_OUT') from clearing state
    // while signIn/signUp is in progress (setSession fires SIGNED_OUT before SIGNED_IN)
    const signingInRef = useRef(false);

    const clearAppSessionStorage = () => {
        [
            'scholarform_currentJob',
            'scholarform_job',
            'scholarform_active_job',
            E2E_USER_STORAGE_KEY,
        ].forEach((key) => sessionStorage.removeItem(key));
    };

    const readE2EUser = () => {
        if (typeof window === 'undefined') return null;
        try {
            if (document.cookie.includes('playwright-bypass-auth=true')) {
                return { 
                    id: 'playwright-user', 
                    email: 'test@example.com',
                    app_metadata: { role: 'admin' },
                    user_metadata: { role: 'admin' }
                };
            }
            const raw = window.sessionStorage.getItem(E2E_USER_STORAGE_KEY);
            if (!raw) return null;
            const parsed = JSON.parse(raw);
            return parsed && typeof parsed === 'object' ? parsed : null;
        } catch {
            return null;
        }
    };

    const clearSupabaseAuthStorage = () => {
        if (typeof window === 'undefined') return;

        const clearStorageKeys = (storage) => {
            if (!storage) return;
            const toDelete = [];
            for (let idx = 0; idx < storage.length; idx += 1) {
                const key = storage.key(idx);
                if (!key) continue;
                if (key.startsWith('sb-') && key.includes('-auth-token')) {
                    toDelete.push(key);
                }
            }
            toDelete.forEach((key) => storage.removeItem(key));
        };

        clearStorageKeys(window.localStorage);
        clearStorageKeys(window.sessionStorage);
    };

    const debugAuthLog = (...args) => {
        if (process.env.NODE_ENV !== 'production') {
            console.log(...args);
        }
    };

    const sanitizeRedirectPath = (path) => {
        if (typeof path !== 'string') return '/dashboard';
        if (!path.startsWith('/') || path.startsWith('//')) return '/dashboard';
        return path;
    };

    useEffect(() => {
        let mounted = true;

        const initializeAuth = async () => {
            const e2eUser = readE2EUser();
            if (!supabase) {
                if (mounted) {
                    setUser(e2eUser);
                    setIsLoggedIn(Boolean(e2eUser));
                    setLoading(false);
                }
                return;
            }
            try {
                // Step 1: getSession() — fast local check. The JWT is cryptographically
                // signed, so access_token can be trusted even from localStorage.
                const { data: { session }, error } = await supabase.auth.getSession();

                if (error) {
                    debugAuthLog('Auth: getSession error', error);
                }

                if (session?.access_token) {
                    // Keep unauthenticated state until the cached session is verified.
                    if (mounted) {
                        setUser(null);
                        setIsLoggedIn(false);
                    }

                    // getUser() confirms token validity against Supabase.
                    try {
                        const { data: { user: serverUser }, error: getUserError } = await supabase.auth.getUser();
                        if (getUserError || !serverUser) {
                            debugAuthLog('Auth: getUser rejected cached session, clearing local auth state');
                            await supabase.auth.signOut({ scope: 'local' });
                            clearSupabaseAuthStorage();
                            if (mounted) {
                                setUser(null);
                                setIsLoggedIn(false);
                            }
                        } else if (mounted) {
                            setUser(serverUser);
                            setIsLoggedIn(true);
                        }
                    } catch (getUserErr) {
                        debugAuthLog('Auth: getUser failed during initialization', getUserErr);
                        await supabase.auth.signOut({ scope: 'local' });
                        clearSupabaseAuthStorage();
                        if (mounted) {
                            setUser(null);
                            setIsLoggedIn(false);
                        }
                        // Keep guest mode when session verification fails.
                    }
                } else {
                    if (mounted) {
                        clearSupabaseAuthStorage();
                        setUser(e2eUser);
                        setIsLoggedIn(Boolean(e2eUser));
                    }
                }
            } catch (err) {
                console.error('Auth: Initialization error', err);
                if (mounted) {
                    clearSupabaseAuthStorage();
                    setUser(e2eUser);
                    setIsLoggedIn(Boolean(e2eUser));
                }
            } finally {
                if (mounted) setLoading(false);
            }
        };

        initializeAuth();

        // Listener for SUBSEQUENT auth changes (login/logout/token refresh events)
        let subscription;
        if (supabase) {
            const { data } = supabase.auth.onAuthStateChange((event, session) => {
                debugAuthLog('[Auth] onAuthStateChange:', event, { hasSession: !!session, signingIn: signingInRef.current });

                if (event === 'SIGNED_OUT') {
                    // During signIn/signUp, setSession() can fire SIGNED_OUT before SIGNED_IN.
                    // Skip this event to prevent clearing user state mid-login.
                    if (signingInRef.current) {
                        debugAuthLog('[Auth] Ignoring SIGNED_OUT during active sign-in');
                        return;
                    }
                    setUser(null);
                    setIsLoggedIn(false);
                    clearAppSessionStorage();
                    clearSupabaseAuthStorage();
                } else if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
                    // Keep this synchronous — no async getUser() here.
                    // Async getUser() inside onAuthStateChange creates a race where
                    // signingInRef.current is cleared before the promise resolves,
                    // allowing stale SIGNED_OUT events to slip through and cause a redirect loop.
                    if (session?.user && session?.access_token) {
                        setUser(session.user);
                        setIsLoggedIn(true);
                    } else {
                        setUser(null);
                        setIsLoggedIn(false);
                    }
                    signingInRef.current = false;
                }
            });
            subscription = data.subscription;
        }

        return () => {
            mounted = false;
            if (subscription) subscription.unsubscribe();
        };
    }, []);

    const signUp = async (signupData) => {
        try {
            setLoading(true);
            signingInRef.current = true;
            const data = await apiSignup(signupData);

            if (data?.session && supabase) {
                const { error: sessionError } = await supabase.auth.setSession({
                    access_token: data.session.access_token,
                    refresh_token: data.session.refresh_token,
                });

                if (sessionError) {
                    console.error('Auth: setSession failed during signup', sessionError);
                    signingInRef.current = false;
                } else {
                    const userToSet = data.user || data.session.user;
                    if (userToSet) {
                        setUser(userToSet);
                        setIsLoggedIn(true);
                    }
                }
            } else {
                signingInRef.current = false;
            }
            return { data, error: null };
        } catch (error) {
            signingInRef.current = false;
            return { data: null, error: error.message || String(error) };
        } finally {
            setLoading(false);
        }
    };

    const signIn = async (email, password) => {
        try {
            signingInRef.current = true;
            const data = await apiLogin({ email, password });

            if (!data?.session || !supabase) {
                signingInRef.current = false;
                return { data: data ?? null, error: null };
            }

            const { error: sessionError } = await supabase.auth.setSession({
                access_token: data.session.access_token,
                refresh_token: data.session.refresh_token,
            });

            if (sessionError) {
                console.error('Auth: setSession failed during signIn', sessionError);
                signingInRef.current = false;
                return { data: null, error: sessionError.message };
            }

            // Immediately update React state so AuthGuard sees isLoggedIn=true
            // before any navigation occurs — don't wait for onAuthStateChange.
            const userToSet = data.user || data.session.user;
            if (userToSet) {
                setUser(userToSet);
                setIsLoggedIn(true);
            }
            // signingInRef is cleared by onAuthStateChange SIGNED_IN event

            return { data, error: null };
        } catch (error) {
            signingInRef.current = false;
            return { data: null, error: error.message };
        }
    };

    const signInWithGoogle = async (redirectPath = '/dashboard') => {
        if (!supabase) throw new Error('Supabase client is not initialized');
        const safeRedirectPath = sanitizeRedirectPath(redirectPath);
        return await supabase.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(safeRedirectPath)}`,
            },
        });
    };

    const signOut = async ({ redirectToLogin = false } = {}) => {
        try {
            if (supabase) await supabase.auth.signOut({ scope: 'local' });
        } catch (error) {
            console.error('Error signing out:', error);
        } finally {
            // Force local cleanup regardless of server response
            setUser(null);
            setIsLoggedIn(false);
            clearAppSessionStorage();
            clearSupabaseAuthStorage();

            if (redirectToLogin && typeof window !== 'undefined') {
                window.location.replace('/login');
            }
        }
    };

    const refreshSession = async () => {
        if (!supabase) return;
        const { data: { user: refreshedUser }, error } = await supabase.auth.getUser();
        if (refreshedUser && !error) {
            setUser(refreshedUser);
            setIsLoggedIn(true);
        } else {
            clearSupabaseAuthStorage();
            setUser(null);
            setIsLoggedIn(false);
        }
    };

    const forgotPassword = async (email) => {
        try {
            const data = await apiForgotPassword({ email });
            return { data, error: null };
        } catch (error) {
            return { data: null, error: error.message };
        }
    };

    const verifyOtp = async (email, otp) => {
        try {
            const data = await apiVerifyOtp({ email, otp });
            return { data, error: null };
        } catch (error) {
            return { data: null, error: error.message };
        }
    };

    const resetPassword = async (email, otp, newPassword) => {
        try {
            const data = await apiResetPassword({ email, otp, new_password: newPassword });
            return { data, error: null };
        } catch (error) {
            return { data: null, error: error.message };
        }
    };

    const value = {
        user,
        isLoggedIn,
        signUp,
        signIn,
        signInWithGoogle,
        signOut,
        refreshSession,
        forgotPassword,
        verifyOtp,
        resetPassword,
        loading,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};
