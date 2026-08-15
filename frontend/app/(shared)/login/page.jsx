// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import { useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { LoginSchema } from '@/src/lib/schemas';
import { z } from 'zod';
import { User, AlertCircle, Mail, Lock, Eye, EyeOff } from 'lucide-react';

import { useAuth } from '@/src/context/AuthContext';

function LoginContent() {
    usePageTitle('Sign In');
    const { signIn, signInWithGoogle } = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState('');
    const [fieldErrors, setFieldErrors] = useState({});
    const [localLoading, setLocalLoading] = useState(false);
    const nextPath = searchParams.get('next');
    const redirectPath = nextPath?.startsWith('/') && !nextPath.startsWith('//')
        ? nextPath
        : '/dashboard';

    const handleEmailLogin = async (e) => {
        e.preventDefault();
        setError('');
        setFieldErrors({});

        // Frontend validation with Zod
        try {
            LoginSchema.parse({ email, password });
        } catch (err) {
            if (err instanceof z.ZodError) {
                const errors = {};
                err.errors.forEach(e => {
                    errors[e.path[0]] = e.message;
                });
                setFieldErrors(errors);
                return;
            }
        }

        setLocalLoading(true);
        const { data, error: signInError } = await signIn(email, password);

        if (signInError) {
            console.error(signInError);
            setError(signInError);
            setLocalLoading(false);
        } else {
            // Check if user is an admin
            const userObj = data?.user || data?.session?.user;
            const isAdmin = userObj?.app_metadata?.role === 'admin' || userObj?.user_metadata?.role === 'admin';

            // Route admins to admin dashboard if no specific next path was requested
            const finalRedirectPath = (isAdmin && redirectPath === '/dashboard')
                ? '/admin-dashboard'
                : redirectPath;

            router.push(finalRedirectPath);
        }
    };

    const handleGoogleLogin = async () => {
        setError('');
        const { error: googleError } = await signInWithGoogle(redirectPath);
        if (googleError) {
            console.error(googleError);
            setError(googleError.message || googleError);
        }
    };

    return (
        <div className="min-h-[calc(100vh-72px)] flex font-display transition-colors duration-300 w-full relative overflow-hidden flex-col lg:flex-row bg-gradient-to-br from-primary-950 via-primary-900 to-primary-800 text-white selection:bg-accent-500/30">

            {/* Page background blob decorations */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
                <div className="absolute top-[-10%] left-[-5%] w-[45%] h-[45%] bg-accent-500/20 rounded-full blur-[120px]"></div>
                <div className="absolute bottom-[-10%] right-[-5%] w-[40%] h-[40%] bg-primary-500/30 rounded-full blur-[100px]"></div>
                <div className="absolute top-[40%] right-[20%] w-[25%] h-[25%] bg-accent-400/15 rounded-full blur-[80px]"></div>
            </div>

            <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-7xl flex flex-col lg:flex-row items-center justify-between lg:py-0 relative z-10 min-h-[calc(100vh-72px)] overflow-y-auto">
                {/* Left Side: Content floating on gradient background */}
                <div className="hidden lg:flex w-full lg:w-[55%] flex-col justify-center pr-8 xl:pr-20 relative h-full">
                    <div className="relative z-10 max-w-lg animate-in fade-in slide-in-from-left-8 duration-1000">
                        <h2 className="text-4xl xl:text-5xl font-extrabold text-white mb-5 leading-tight">
                            Focus on your research. <br />
                            <span className="bg-gradient-to-r from-accent-300 to-accent-500 bg-clip-text text-transparent pb-2">We handle the formatting.</span>
                        </h2>
                        <p className="text-base text-white/70 mb-10 leading-relaxed max-w-md">
                            Join thousands of researchers worldwide who use ScholarForm AI to perfectly format their academic manuscripts for top-tier journals in seconds.
                        </p>

                        <div className="flex items-center gap-4">
                            <div className="flex -space-x-2">
                                <div className="w-9 h-9 rounded-full border-2 border-white dark:border-slate-900 flex items-center justify-center shadow-md" style={{ background: 'linear-gradient(135deg, #a78bfa, #7c3aed)' }}>
                                    <User className="h-4 w-4 text-white" />
                                </div>
                                <div className="w-9 h-9 rounded-full border-2 border-white dark:border-slate-900 flex items-center justify-center shadow-md" style={{ background: 'linear-gradient(135deg, #60a5fa, #4338ca)' }}>
                                    <User className="h-4 w-4 text-white" />
                                </div>
                                <div className="w-9 h-9 rounded-full border-2 border-white dark:border-slate-900 flex items-center justify-center shadow-md" style={{ background: 'linear-gradient(135deg, #34d399, #0f766e)' }}>
                                    <User className="h-4 w-4 text-white" />
                                </div>
                                <div className="w-9 h-9 rounded-full border-2 border-white dark:border-slate-900 flex items-center justify-center shadow-md" style={{ background: 'linear-gradient(135deg, #fb7185, #be185d)' }}>
                                    <User className="h-4 w-4 text-white" />
                                </div>
                            </div>
                            <div className="text-sm font-semibold text-white/70">
                                Trusted by <span className="text-white font-black">25k+</span> researchers
                            </div>
                        </div>
                    </div>
                </div>

                {/* Right Side: Glassmorphic Form Card */}
                <div className="w-full lg:w-[45%] flex items-center justify-center py-10 lg:py-0 lg:h-full">
                    <div className="w-full max-w-[420px] z-10 animate-in fade-in slide-in-from-right-8 duration-700">
                        <div className="w-full bg-white/5 border border-white/10 backdrop-blur-md rounded-3xl p-8 relative">

                            <div className="mb-6">
                                <h1 className="text-2xl font-bold text-white mb-1.5 tracking-tight">Welcome back</h1>
                                <p className="text-white/60 text-sm">Please enter your details to sign in.</p>
                            </div>

                            {error && (
                                <div className="mb-6 p-4 rounded-2xl bg-red-50/80 dark:bg-red-500/10 backdrop-blur-sm border border-red-200/50 dark:border-red-500/20 flex items-start gap-3 shadow-sm">
                                    <AlertCircle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
                                    <p className="text-red-700 dark:text-red-400 text-sm leading-relaxed">{error}</p>
                                </div>
                            )}

                            <form className="flex flex-col gap-4" onSubmit={handleEmailLogin}>
                                {/* Email Field */}
                                <div className="flex flex-col gap-2">
                                    <label className="text-sm font-semibold text-white/90" htmlFor="email">Email Address</label>
                                    <div className="relative w-full">
                                        <Mail className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-white/40 group-focus-within:text-accent-400 transition-colors pointer-events-none" />
                                        <input
                                            id="email"
                                            className={`w-full rounded-2xl text-white focus:outline-none focus:ring-2 focus:ring-accent-500/30 border bg-white/5 hover:border-white/20 focus:border-accent-500 h-12 pl-12 pr-4 text-sm font-medium transition-all placeholder:text-white/40 shadow-sm ${fieldErrors.email ? 'border-red-500' : 'border-white/10'}`}
                                            placeholder="your@email.com"
                                            type="email"
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                        />
                                        {fieldErrors.email && <p className="text-[10px] text-red-500 mt-1 px-1 font-medium">{fieldErrors.email}</p>}
                                    </div>
                                </div>

                                {/* Password Field */}
                                <div className="flex flex-col gap-2">
                                    <label className="text-sm font-semibold text-white/90" htmlFor="password">Password</label>
                                    <div className="relative w-full">
                                        <Lock className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-white/40 group-focus-within:text-accent-400 transition-colors pointer-events-none" />
                                        <input
                                            id="password"
                                            className={`w-full rounded-2xl text-white focus:outline-none focus:ring-2 focus:ring-accent-500/30 border bg-white/5 hover:border-white/20 focus:border-accent-500 h-12 pl-12 pr-11 text-sm font-medium transition-all placeholder:text-white/40 shadow-sm ${fieldErrors.password ? 'border-red-500' : 'border-white/10'}`}
                                            placeholder="Enter your password"
                                            type={showPassword ? 'text' : 'password'}
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                        />
                                        {fieldErrors.password && <p className="text-[10px] text-red-500 mt-1 px-1 font-medium">{fieldErrors.password}</p>}
                                        <button
                                            type="button"
                                            onClick={() => setShowPassword(!showPassword)}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/80 transition-colors p-0.5"
                                        >
                                            {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                                        </button>
                                    <div className="flex justify-end mt-1">
                                        <Link href="/forgot-password" className="text-accent-400 text-xs font-semibold hover:text-accent-300 transition-colors">Forgot password?</Link>
                                    </div>
                                </div>
                                </div>

                                {/* Login Button */}
                                <div className="pt-2">
                                    <button
                                        className="flex w-full items-center justify-center rounded-xl h-12 px-5 bg-accent-500 text-white text-sm font-bold tracking-wide hover:bg-accent-400 hover:-translate-y-0.5 active:translate-y-0 shadow-lg shadow-accent-500/25 transition-all disabled:opacity-70 disabled:cursor-not-allowed transform"
                                        type="submit"
                                        disabled={localLoading}
                                    >
                                        {localLoading ? (
                                            <div className="flex items-center gap-2">
                                                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                                <span>Signing in...</span>
                                            </div>
                                        ) : 'Sign In'}
                                    </button>
                                </div>
                            </form>

                            <div className="relative flex items-center py-8">
                                <div className="flex-grow border-t border-white/10"></div>
                                <span className="flex-shrink mx-4 text-[13px] text-white/40 font-medium">Or continue with</span>
                                <div className="flex-grow border-t border-white/10"></div>
                            </div>

                            {/* Social Login */}
                            <button
                                type="button"
                                onClick={handleGoogleLogin}
                                className="w-full flex items-center justify-center gap-3 bg-white/5 border border-white/10 text-white h-12 rounded-xl text-sm font-semibold hover:bg-white/10 hover:-translate-y-0.5 active:translate-y-0 transition-all shadow-sm mb-2"
                            >
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                                </svg>
                                Google
                            </button>

                            <div className="mt-6 text-center text-sm font-medium text-white/60">
                                Don&apos;t have an account?{' '}
                                <Link href={`/signup${nextPath ? `?next=${encodeURIComponent(nextPath)}` : ''}`} className="text-accent-400 hover:text-accent-300 font-bold transition-colors">
                                    Sign up
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function Login() {
    return (
        <Suspense fallback={<div className="min-h-[calc(100vh-72px)] flex items-center justify-center"><div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div></div>}>
            <LoginContent />
        </Suspense>
    );
}
