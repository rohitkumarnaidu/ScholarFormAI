// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import { useState, useRef, useEffect, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';

import { useAuth } from '@/src/context/AuthContext';
import { AlertTriangle, ArrowLeft, MailCheck, User } from 'lucide-react';

function VerifyOTPContent() {
    usePageTitle('Verify OTP');
    const router = useRouter();
    const navigate = useCallback((href, options = {}) => {
        if (options?.replace) {
            router.replace(href);
            return;
        }
        router.push(href);
    }, [router]);
    const searchParams = useSearchParams();
    const { verifyOtp, forgotPassword } = useAuth();
    const email = searchParams.get('email') || '';

    const [otp, setOtp] = useState(['', '', '', '', '', '']);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [resendLoading, setResendLoading] = useState(false);
    const inputRefs = [useRef(), useRef(), useRef(), useRef(), useRef(), useRef()];

    useEffect(() => {
        if (!email) {
            navigate('/forgot-password');
        }
    }, [email, navigate]);

    const handleChange = (index, value) => {
        if (value.length > 1) {
            // Handle paste
            const pasteData = value.slice(0, 6).split('');
            const newOtp = [...otp];
            pasteData.forEach((char, i) => {
                if (index + i < 6) newOtp[index + i] = char;
            });
            setOtp(newOtp);
            // Move focus to last filled or last box
            const lastIndex = Math.min(index + pasteData.length - 1, 5);
            inputRefs[lastIndex].current.focus();
            return;
        }

        const newOtp = [...otp];
        newOtp[index] = value;
        setOtp(newOtp);

        // Move to next field if value is entered
        if (value && index < 5) {
            inputRefs[index + 1].current.focus();
        }
    };

    const handleKeyDown = (index, e) => {
        // Move to previous field on backspace if empty
        if (e.key === 'Backspace' && !otp[index] && index > 0) {
            inputRefs[index - 1].current.focus();
        }
    };

    const handleVerify = async (e) => {
        e.preventDefault();
        setError('');
        const otpString = otp.join('');

        if (otpString.length < 6) {
            setError('Please enter all 6 digits.');
            return;
        }

        setLoading(true);
        const { error: authError } = await verifyOtp(email, otpString);
        if (authError) {
            setError(authError);
            setLoading(false);
        } else {
            navigate(`/reset-password?email=${encodeURIComponent(email)}&otp=${encodeURIComponent(otpString)}`);
            setLoading(false);
        }
    };

    const handleResend = async () => {
        setResendLoading(true);
        setError('');
        const { error: authError } = await forgotPassword(email);
        if (authError) {
            setError(authError);
        } else {
            // Success
        }
        setResendLoading(false);
    };

    return (
        <div className="flex-1 w-full flex flex-col font-display transition-colors duration-300 w-full relative bg-gradient-to-br from-primary-950 via-primary-900 to-primary-800 text-white selection:bg-accent-500/30">

            {/* Page background blob decorations */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
                <div className="absolute top-[-10%] left-[-5%] w-[45%] h-[45%] bg-accent-500/20 rounded-full blur-[120px]"></div>
                <div className="absolute bottom-[-10%] right-[-5%] w-[40%] h-[40%] bg-primary-500/30 rounded-full blur-[100px]"></div>
            </div>

            <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-7xl w-full flex-1 flex flex-col lg:flex-row items-center justify-center lg:justify-between py-12 lg:py-0 relative z-10">
                {/* Left Side: Content floating on gradient background */}
                <div className="hidden lg:flex w-full lg:w-[55%] flex-col justify-center pr-8 xl:pr-20 relative h-full">
                    <div className="relative z-10 max-w-lg animate-in fade-in slide-in-from-left-8 duration-1000">
                        <h2 className="text-4xl xl:text-5xl font-extrabold text-white mb-5 leading-tight">
                            Verify your identity <br />
                            <span className="text-accent-400">to continue securely.</span>
                        </h2>
                        <p className="text-base text-white/60 mb-10 leading-relaxed max-w-md">
                            Enter the 6-digit confirmation code we sent to your email to verify your ownership of this account.
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
                    <div className="w-full max-w-[420px] z-10 animate-in fade-in slide-in-from-right-8 duration-700">
                        <div className="w-full bg-white/5 border border-white/10 backdrop-blur-md rounded-3xl p-8 relative">
                            {/* Inline icon + heading */}
                            <div className="flex items-center gap-3 mb-2">
                                <div className="h-10 w-10 bg-primary/10 rounded-xl flex items-center justify-center text-primary shrink-0">
                                    <MailCheck className="text-primary text-[22px]" />
                                </div>
                                <h1 className="text-2xl font-bold tracking-tight text-white">Verify OTP</h1>
                            </div>
                            <p className="text-white/60 text-sm mb-6">Enter the 6-digit code sent to your email address.</p>

                            {error && (
                                <div className="mb-6 p-4 rounded-xl bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 flex items-start gap-3">
                                    <AlertTriangle className="text-red-500 text-[20px] shrink-0 mt-0.5" />
                                    <p className="text-red-700 dark:text-red-400 text-sm leading-relaxed">{error}</p>
                                </div>
                            )}

                            <form className="flex flex-col gap-6" onSubmit={handleVerify}>
                                <div className="flex justify-center sm:justify-between gap-2 sm:gap-3 py-2 w-full">
                                    {otp.map((digit, i) => (
                                        <input
                                            key={i}
                                            ref={inputRefs[i]}
                                            className="flex h-12 w-10 sm:h-14 sm:w-12 text-center [appearance:textfield] focus:outline-0 focus:ring-2 focus:ring-accent-500/30 focus:border-accent-500 rounded-xl text-xl font-bold leading-normal text-white bg-white/5 border border-white/10 placeholder:text-white/40 transition-all shadow-sm"
                                            maxLength="6" // Note: we allow > 1 in onChange for pasting
                                            type="text"
                                            value={digit}
                                            onChange={(e) => handleChange(i, e.target.value)}
                                            onKeyDown={(e) => handleKeyDown(i, e)}
                                            required
                                        />
                                    ))}
                                </div>

                                <div className="pt-2">
                                    <button
                                        className="flex w-full items-center justify-center rounded-xl h-12 px-5 bg-accent-500 hover:bg-accent-400 shadow-lg shadow-accent-500/25 text-white text-sm font-bold tracking-wide hover:-translate-y-0.5 active:translate-y-0 transition-all disabled:opacity-70 disabled:cursor-not-allowed transform"
                                        type="submit"
                                        disabled={loading}
                                    >
                                        {loading ? (
                                            <div className="flex items-center gap-2">
                                                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                                <span>Verifying...</span>
                                            </div>
                                        ) : 'Verify Code'}
                                    </button>
                                </div>
                            </form>

                            <div className="mt-8 pt-6 border-t border-white/10 text-center sm:text-left">
                                <p className="text-sm text-white/60 mb-4 font-medium">
                                    Didn&apos;t receive the code?
                                    <button
                                        onClick={handleResend}
                                        disabled={resendLoading}
                                        className="text-accent-400 font-bold hover:underline ml-1 bg-transparent border-none p-0 cursor-pointer disabled:opacity-50 transition-all hover:text-accent-300"
                                    >
                                        {resendLoading ? 'Sending...' : 'Resend OTP'}
                                    </button>
                                </p>
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

export default function VerifyOTP() {
    return (
        <Suspense fallback={<div className="min-h-[calc(100vh-72px)] flex items-center justify-center"><div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div></div>}>
            <VerifyOTPContent />
        </Suspense>
    );
}
