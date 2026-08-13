// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import { useState, useEffect, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';

import { useAuth } from '@/src/context/AuthContext';

function ResetPasswordContent() {
    usePageTitle('Reset Password');
    const router = useRouter();
    const navigate = useCallback((href, options = {}) => {
        if (options?.replace) {
            router.replace(href);
            return;
        }
        router.push(href);
    }, [router]);
    const searchParams = useSearchParams();
    const { resetPassword } = useAuth();

    const email = searchParams.get('email') || '';
    const otp = searchParams.get('otp') || '';

    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!email || !otp) {
            navigate('/forgot-password');
        }
    }, [email, otp, navigate]);

    const handleReset = async (e) => {
        e.preventDefault();
        setError('');
        setMessage('');

        if (password !== confirmPassword) {
            setError("Passwords do not match.");
            return;
        }

        if (password.length < 8) {
            setError("Password must be at least 8 characters.");
            return;
        }

        setLoading(true);
        const { error: authError } = await resetPassword(email, otp, password);

        if (authError) {
            setError(authError);
            setLoading(false);
        } else {
            setMessage("Password updated successfully! Redirecting to login...");
            setTimeout(() => {
                navigate('/login');
            }, 2000);
            setLoading(false);
        }
    };

    return (
        <div className="flex-1 w-full flex flex-col font-display transition-colors duration-300 w-full relative bg-gradient-to-br from-primary-950 via-primary-900 to-primary-800 text-white selection:bg-accent-500/30">

            {/* Page background blob decorations */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
                <div className="absolute top-[-10%] left-[-5%] w-[45%] h-[45%] bg-accent-500/20 rounded-full blur-[120px]"></div>
                <div className="absolute bottom-[-10%] right-[-5%] w-[40%] h-[40%] bg-primary-500/30 rounded-full blur-[100px]"></div>
            </div>

            <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-7xl w-full flex-1 flex flex-col lg:flex-row items-center justify-center lg:justify-between py-12 lg:py-0 relative z-10">
                {/* Left Side: Content floating on gradient background - NO symbols */}
                <div className="hidden lg:flex w-full lg:w-[55%] flex-col justify-center pr-8 xl:pr-20 relative h-full">
                    <div className="relative z-10 max-w-lg animate-in fade-in slide-in-from-left-8 duration-1000">
                        <h2 className="text-4xl xl:text-5xl font-extrabold text-white mb-5 leading-tight">
                            Secure your account <br />
                            <span className="text-accent-400">and resume your work.</span>
                        </h2>
                        <p className="text-base text-white/60 mb-10 leading-relaxed max-w-md">
                            Choose a strong, unique password to protect your formatted manuscripts and research data.
                        </p>

                        <div className="flex items-center gap-4">
                            <div className="flex -space-x-3">
                                {[1, 2, 3, 4].map((i) => (
                                    <div key={i} className="w-10 h-10 rounded-full border-2 border-white dark:border-background-dark bg-gradient-to-br from-violet-200 to-indigo-300 dark:from-slate-700 dark:to-slate-800 flex items-center justify-center shadow-md">
                                        <span className="material-symbols-outlined text-[16px] text-white/40">person</span>
                                    </div>
                                ))}
                            </div>
                            <div className="text-sm font-semibold text-white/60">
                                Trusted by <span className="text-white font-black">25k+</span> researchers
                            </div>
                        </div>
                    </div>
                </div>

                {/* Right Side: Glassmorphic Form Card */}
                <div className="w-full lg:w-[45%] flex items-center justify-center lg:h-full">
                    <div className="w-full max-w-[420px] z-10 animate-in fade-in slide-in-from-right-8 duration-700">
                        <div className="w-full bg-white/5 border border-white/10 backdrop-blur-md rounded-3xl p-8 relative">

                            <div className="mb-6">
                                <h1 className="text-2xl font-bold text-white mb-1.5 tracking-tight">Reset password</h1>
                                <p className="text-white/60 text-sm">Create a new password for your account.</p>
                            </div>

                            {error && (
                                <div className="mb-6 p-4 rounded-xl bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 flex items-start gap-3">
                                    <span className="material-symbols-outlined text-red-500 text-[20px] shrink-0 mt-0.5">error</span>
                                    <p className="text-red-700 dark:text-red-400 text-sm leading-relaxed">{error}</p>
                                </div>
                            )}

                            {message && (
                                <div className="mb-6 p-4 rounded-xl bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/20 flex items-start gap-3">
                                    <span className="material-symbols-outlined text-green-500 text-[20px] shrink-0 mt-0.5">check_circle</span>
                                    <p className="text-green-700 dark:text-green-400 text-sm leading-relaxed font-medium">{message}</p>
                                </div>
                            )}

                            <form className="flex flex-col gap-5" onSubmit={handleReset}>
                                {/* New Password */}
                                <div className="flex flex-col gap-2">
                                    <label className="text-sm font-semibold text-white/90" htmlFor="password">New Password</label>
                                    <div className="relative flex items-center">
                                        <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-white/40 text-[20px] pointer-events-none">lock</span>
                                        <input
                                            id="password"
                                            className="form-input flex w-full rounded-xl text-white bg-white/5 border border-white/10 placeholder:text-white/40 focus:outline-0 focus:ring-2 focus:ring-accent-500/30 focus:border-accent-500 h-12 pl-12 pr-12 text-sm font-medium transition-all shadow-sm"
                                            placeholder="Enter your new password"
                                            type={showPassword ? "text" : "password"}
                                            required
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                        />
                                        <button
                                            type="button"
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-accent-400 transition-colors flex items-center justify-center p-1"
                                            onClick={() => setShowPassword(!showPassword)}
                                            title={showPassword ? "Hide password" : "Show password"}
                                        >
                                            <span className="material-symbols-outlined text-[20px]">
                                                {showPassword ? 'visibility_off' : 'visibility'}
                                            </span>
                                        </button>
                                    </div>
                                    <p className="text-xs text-white/60 mt-1 pl-1">At least 8 characters with a number</p>
                                </div>

                                {/* Confirm Password */}
                                <div className="flex flex-col gap-2">
                                    <label className="text-sm font-semibold text-white/90" htmlFor="confirmPassword">Confirm Password</label>
                                    <div className="relative flex items-center">
                                        <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-white/40 text-[20px] pointer-events-none">lock_reset</span>
                                        <input
                                            id="confirmPassword"
                                            className="form-input flex w-full rounded-xl text-white bg-white/5 border border-white/10 placeholder:text-white/40 focus:outline-0 focus:ring-2 focus:ring-accent-500/30 focus:border-accent-500 h-12 pl-12 pr-12 text-sm font-medium transition-all shadow-sm"
                                            placeholder="Enter your new password again"
                                            type={showConfirmPassword ? "text" : "password"}
                                            required
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                        />
                                        <button
                                            type="button"
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-accent-400 transition-colors flex items-center justify-center p-1"
                                            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                            title={showConfirmPassword ? "Hide password" : "Show password"}
                                        >
                                            <span className="material-symbols-outlined text-[20px]">
                                                {showConfirmPassword ? 'visibility_off' : 'visibility'}
                                            </span>
                                        </button>
                                    </div>
                                </div>

                                {/* Submit Button */}
                                <div className="pt-4">
                                    <button
                                        className="flex w-full items-center justify-center rounded-xl h-12 px-5 bg-accent-500 hover:bg-accent-400 shadow-lg shadow-accent-500/25 text-white text-sm font-bold tracking-wide hover:-translate-y-0.5 active:translate-y-0 transition-all disabled:opacity-70 disabled:cursor-not-allowed transform"
                                        type="submit"
                                        disabled={loading}
                                    >
                                        {loading ? (
                                            <div className="flex items-center gap-2">
                                                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                                <span>Updating Password...</span>
                                            </div>
                                        ) : 'Reset Password'}
                                    </button>
                                </div>
                            </form>

                            <div className="mt-8 text-center sm:text-left border-white/10 pt-6 border-t font-medium">
                                <Link href="/login" className="inline-flex items-center gap-2 text-accent-400 hover:text-accent-300 transition-colors text-sm font-semibold">
                                    <span className="material-symbols-outlined text-[18px]">keyboard_backspace</span>
                                    Back to Sign in
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function ResetPassword() {
    return (
        <Suspense fallback={<div className="min-h-[calc(100vh-72px)] flex items-center justify-center"><div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div></div>}>
            <ResetPasswordContent />
        </Suspense>
    );
}
