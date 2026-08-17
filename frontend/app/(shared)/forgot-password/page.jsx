// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

import { useAuth } from '@/src/context/AuthContext';
import { AlertTriangle, ArrowLeft, CheckCircle, KeyRound, Mail, User } from 'lucide-react';

export default function ForgotPassword() {
    usePageTitle('Forgot Password');
    const { forgotPassword } = useAuth();
    const router = useRouter();
    const navigate = (href, options = {}) => {
        if (options?.replace) {
            router.replace(href);
            return;
        }
        router.push(href);
    };
    const [email, setEmail] = useState('');
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [countdown, setCountdown] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setMessage('');
        setError('');
        setLoading(true);

        const { error: authError } = await forgotPassword(email);

        if (authError) {
            setError(authError);
            setLoading(false);
        } else {
            setMessage('OTP has been sent to your email.');
            setCountdown(5);
            let timeLeft = 5;
            const timer = setInterval(() => {
                timeLeft -= 1;
                setCountdown(timeLeft);
                if (timeLeft <= 0) {
                    clearInterval(timer);
                    navigate(`/verify-otp?email=${encodeURIComponent(email)}`);
                }
            }, 1000);
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
                {/* Left Side: Content only — NO floating symbols */}
                <div className="hidden lg:flex w-full lg:w-[55%] flex-col justify-center pr-8 xl:pr-20 relative h-full">
                    <div className="relative z-10 max-w-lg animate-in fade-in slide-in-from-left-8 duration-1000">
                        <h2 className="text-4xl xl:text-5xl font-extrabold text-white mb-5 leading-tight">
                            Recover your access <br />
                            <span className="text-accent-400">securely and easily.</span>
                        </h2>
                        <p className="text-base text-white/60 mb-10 leading-relaxed max-w-md">
                            Ensure you never lose access to your formatted manuscripts or ongoing research projects. We will send a secure OTP to your email.
                        </p>

                        <div className="flex items-center gap-4">
                            <div className="flex -space-x-3">
                                {[1, 2, 3, 4].map((i) => (
                                    <div key={i} className="w-10 h-10 rounded-full border-2 border-white dark:border-background-dark bg-gradient-to-br from-violet-200 to-indigo-300 dark:from-slate-700 dark:to-slate-800 flex items-center justify-center shadow-md">
                                        <User className="text-[16px] text-white/40" />
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
                    <div className="w-full max-w-full max-w-[420px] z-10 animate-in fade-in slide-in-from-right-8 duration-700">
                        <div className="w-full bg-white/5 border border-white/10 backdrop-blur-md rounded-3xl p-8 relative">
                            {/* Inline icon + heading */}
                            <div className="flex items-center gap-3 mb-2">
                                <div className="h-10 w-10 bg-primary/10 rounded-xl flex items-center justify-center shrink-0">
                                    <KeyRound className="text-primary text-[22px]" />
                                </div>
                                <h1 className="text-2xl font-bold tracking-tight text-white">Forgot password?</h1>
                            </div>
                            <p className="text-white/60 text-sm mb-6">Enter your registered email address to receive a secure 6-digit OTP.</p>

                            {message && (
                                <div className="mb-6 p-4 rounded-xl bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/20 flex flex-col items-start gap-3">
                                    <div className="flex items-center gap-3 w-full">
                                        <CheckCircle className="text-green-500 text-[20px] shrink-0" />
                                        <p className="text-green-700 dark:text-green-400 text-sm leading-relaxed font-medium">{message}</p>
                                    </div>
                                    {countdown !== null && (
                                        <div className="w-full flex justify-center text-green-600 dark:text-green-500 text-xs font-bold bg-green-100 dark:bg-green-900/30 rounded-lg py-1.5 px-3">
                                            Redirecting in {countdown}s...
                                        </div>
                                    )}
                                </div>
                            )}

                            {error && (
                                <div className="mb-6 p-4 rounded-xl bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 flex items-start gap-3">
                                    <AlertTriangle className="text-red-500 text-[20px] shrink-0 mt-0.5" />
                                    <p className="text-red-700 dark:text-red-400 text-sm leading-relaxed">{error}</p>
                                </div>
                            )}

                            <form className="flex flex-col gap-6" onSubmit={handleSubmit}>
                                {/* Email Field */}
                                <div className="flex flex-col gap-2 text-left">
                                    <label className="text-sm font-semibold text-white/90" htmlFor="email">Email Address</label>
                                    <div className="relative">
                                        <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-white/40 text-[20px]" />
                                        <input
                                            id="email"
                                            className="form-input flex w-full rounded-xl text-white bg-white/5 border border-white/10 placeholder:text-white/40 focus:outline-0 focus:ring-2 focus:ring-accent-500/30 focus:border-accent-500 h-12 pl-12 pr-4 text-sm font-medium transition-all shadow-sm"
                                            placeholder="Enter your registered email address"
                                            required
                                            type="email"
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                        />
                                    </div>
                                </div>

                                {/* Submit Button */}
                                <div className="pt-2">
                                    <button
                                        className="flex w-full items-center justify-center rounded-xl h-12 px-5 bg-accent-500 hover:bg-accent-400 shadow-lg shadow-accent-500/25 text-white text-sm font-bold tracking-wide hover:-translate-y-0.5 active:translate-y-0 transition-all disabled:opacity-70 disabled:cursor-not-allowed transform"
                                        type="submit"
                                        disabled={loading || countdown !== null}
                                    >
                                        {loading ? (
                                            <div className="flex items-center gap-2">
                                                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                                <span>Sending...</span>
                                            </div>
                                        ) : 'Send OTP'}
                                    </button>
                                </div>
                            </form>

                            <div className="mt-10 text-center sm:text-left border-white/10 pt-6 border-t font-medium">
                                <Link href="/login" className="inline-flex items-center gap-2 text-accent-400 hover:text-accent-300 transition-colors text-sm font-semibold">
                                    <ArrowLeft className="text-[18px]" />
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
