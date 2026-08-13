// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';

import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';

import { useAuth } from '@/src/context/AuthContext';
import { SignupSchema } from '@/src/lib/schemas';
import { z } from 'zod';

function SignupContent() {
    usePageTitle('Create Account');
    const { signUp, signInWithGoogle } = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();
    const navigate = (href, options = {}) => {
        if (options?.replace) {
            router.replace(href);
            return;
        }
        router.push(href);
    };
    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');
    const [institution, setInstitution] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);
    const [error, setError] = useState('');
    const [fieldErrors, setFieldErrors] = useState({});
    const [localLoading, setLocalLoading] = useState(false);
    const [successMessage, setSuccessMessage] = useState('');
    const [termsAccepted, setTermsAccepted] = useState(false);
    const isPasswordValid = password.length >= 8 && /\d/.test(password);
    const nextPath = searchParams.get('next');
    const redirectPath = nextPath?.startsWith('/') && !nextPath.startsWith('//')
        ? nextPath
        : '/dashboard';

    const getPasswordStrength = (pass) => {
        if (!pass) return { score: 0, label: '', color: 'bg-slate-200', textColor: 'text-slate-500' };
        let score = 0;
        if (pass.length >= 8) score += 1;
        if (/[A-Z]/.test(pass) && /[a-z]/.test(pass)) score += 1;
        if (/\d/.test(pass)) score += 1;
        if (/[^a-zA-Z\d]/.test(pass)) score += 1;

        if (score <= 1) return { score: 1, label: 'Weak', color: 'bg-red-500', textColor: 'text-red-500' };
        if (score === 2) return { score: 2, label: 'Fair', color: 'bg-amber-500', textColor: 'text-amber-500' };
        if (score === 3) return { score: 3, label: 'Good', color: 'bg-blue-500', textColor: 'text-blue-500' };
        return { score: 4, label: 'Strong', color: 'bg-green-500', textColor: 'text-green-500' };
    };

    const strength = getPasswordStrength(password);

    const handleSignup = async (e) => {
        e.preventDefault();
        setError('');
        setFieldErrors({});
        setSuccessMessage('');

        if (password !== confirmPassword) {
            setError("Passwords do not match.");
            return;
        }

        // Frontend validation with Zod
        try {
            SignupSchema.parse({
                full_name: fullName,
                email: email,
                institution: institution,
                password: password,
                terms_accepted: termsAccepted
            });
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
        const { data, error: signupError } = await signUp({
            full_name: fullName,
            email: email,
            institution: institution,
            password: password,
            terms_accepted: termsAccepted
        });

        if (signupError) {
            setError(typeof signupError === 'string' ? signupError : signupError.message || String(signupError));
            setLocalLoading(false);
        } else {
            setLocalLoading(false);
            if (data?.user && !data?.session) {
                setSuccessMessage("Account created! Please check your email to verify your account.");
            } else {
                setSuccessMessage("Account created! Redirecting...");
                setTimeout(() => {
                    navigate(redirectPath, { replace: true });
                }, 1000);
            }
        }
    };

    const handleGoogleSignup = async () => {
        setError('');
        const { error: googleError } = await signInWithGoogle(redirectPath);
        if (googleError) {
            setError(googleError.message || googleError);
        }
    };

    return (
        <div className="min-h-[calc(100vh-72px)] flex font-display transition-colors duration-300 w-full bg-slate-50">
            <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-7xl flex flex-col lg:flex-row items-center justify-between min-h-full">
                
                {/* Left Side: Professional Branding */}
                <div className="hidden lg:flex w-full lg:w-[50%] flex-col justify-center pr-8 xl:pr-16 relative h-full">
                    <div className="max-w-lg animate-in fade-in slide-in-from-left-8 duration-1000">
                        <div className="mb-8 inline-flex items-center gap-2 rounded-lg bg-primary/10 px-4 py-2 text-primary font-bold">
                            <span className="material-symbols-outlined text-[20px]">description</span>
                            <span>ScholarForm AI</span>
                        </div>
                        <h2 className="text-4xl xl:text-5xl font-extrabold text-slate-900 mb-6 leading-tight tracking-tight">
                            Your research deserves <br />
                            <span className="text-primary">perfect formatting.</span>
                        </h2>
                        <p className="text-lg text-slate-600 mb-10 leading-relaxed max-w-md font-medium">
                            Join thousands of researchers worldwide who use ScholarForm AI to automatically format their academic manuscripts for top-tier journals in seconds.
                        </p>

                        <div className="flex items-center gap-4">
                            <div className="flex -space-x-3">
                                <div className="w-10 h-10 rounded-full border-2 border-slate-50 flex items-center justify-center bg-slate-200 text-slate-500 shadow-sm">
                                    <span className="material-symbols-outlined text-[18px]">person</span>
                                </div>
                                <div className="w-10 h-10 rounded-full border-2 border-slate-50 flex items-center justify-center bg-slate-300 text-slate-600 shadow-sm">
                                    <span className="material-symbols-outlined text-[18px]">person</span>
                                </div>
                                <div className="w-10 h-10 rounded-full border-2 border-slate-50 flex items-center justify-center bg-slate-400 text-white shadow-sm">
                                    <span className="material-symbols-outlined text-[18px]">person</span>
                                </div>
                                <div className="w-10 h-10 rounded-full border-2 border-slate-50 flex items-center justify-center bg-primary text-white shadow-sm">
                                    <span className="material-symbols-outlined text-[18px]">person</span>
                                </div>
                            </div>
                            <div className="text-sm font-semibold text-slate-600">
                                Trusted by <span className="text-slate-900 font-black">25k+</span> researchers
                            </div>
                        </div>
                    </div>
                </div>

                {/* Right Side: Clean Form Card */}
                <div className="w-full lg:w-[50%] flex items-center justify-center py-12 lg:py-0">
                    <div className="w-full max-w-[460px] animate-in fade-in slide-in-from-right-8 duration-700">
                        <div className="w-full bg-white border border-slate-200 shadow-lg rounded-2xl p-8">
                            
                            <div className="mb-6">
                                <h1 className="text-2xl font-bold text-slate-900 mb-2 tracking-tight">Create an account</h1>
                                <p className="text-slate-500 text-sm font-medium">Set up your free account to get started.</p>
                            </div>

                            {error && (
                                <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3">
                                    <span className="material-symbols-outlined text-red-500 shrink-0 mt-0.5">error</span>
                                    <p className="text-red-700 text-sm font-medium">{error}</p>
                                </div>
                            )}

                            {successMessage && (
                                <div className="mb-6 p-4 rounded-xl bg-green-50 border border-green-200 flex items-start gap-3">
                                    <span className="material-symbols-outlined text-green-500 shrink-0 mt-0.5">check_circle</span>
                                    <p className="text-green-700 text-sm font-medium">{successMessage}</p>
                                </div>
                            )}

                            <form className="flex flex-col gap-4" onSubmit={handleSignup}>
                                {/* Full Name */}
                                <div className="flex flex-col gap-2">
                                    <label className="text-sm font-bold text-slate-700" htmlFor="fullName">Full Name</label>
                                    <div className="relative w-full">
                                        <span className="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">person</span>
                                        <input
                                            id="fullName"
                                            className={`w-full rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary/20 border bg-white focus:border-primary h-11 pl-11 pr-4 text-sm font-medium transition-all placeholder:text-slate-400 ${fieldErrors.full_name ? 'border-red-500' : 'border-slate-300'}`}
                                            placeholder="e.g. Jane Doe"
                                            type="text"
                                            value={fullName}
                                            onChange={(e) => setFullName(e.target.value)}
                                        />
                                        {fieldErrors.full_name && <p className="text-[11px] text-red-500 mt-1 font-bold">{fieldErrors.full_name}</p>}
                                    </div>
                                </div>

                                {/* Email */}
                                <div className="flex flex-col gap-2">
                                    <label className="text-sm font-bold text-slate-700" htmlFor="email">Institutional Email</label>
                                    <div className="relative w-full">
                                        <span className="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">mail</span>
                                        <input
                                            id="email"
                                            className={`w-full rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary/20 border bg-white focus:border-primary h-11 pl-11 pr-4 text-sm font-medium transition-all placeholder:text-slate-400 ${fieldErrors.email ? 'border-red-500' : 'border-slate-300'}`}
                                            placeholder="name@university.edu"
                                            type="email"
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                        />
                                        {fieldErrors.email && <p className="text-[11px] text-red-500 mt-1 font-bold">{fieldErrors.email}</p>}
                                    </div>
                                </div>

                                {/* Institution */}
                                <div className="flex flex-col gap-2">
                                    <label className="text-sm font-bold text-slate-700" htmlFor="institution">
                                        Institution <span className="text-xs text-slate-400 font-normal ml-1">(Optional)</span>
                                    </label>
                                    <div className="relative w-full">
                                        <span className="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">school</span>
                                        <input
                                            id="institution"
                                            className={`w-full rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary/20 border bg-white focus:border-primary h-11 pl-11 pr-4 text-sm font-medium transition-all placeholder:text-slate-400 ${fieldErrors.institution ? 'border-red-500' : 'border-slate-300'}`}
                                            placeholder="University Name"
                                            type="text"
                                            value={institution}
                                            onChange={(e) => setInstitution(e.target.value)}
                                        />
                                        {fieldErrors.institution && <p className="text-[11px] text-red-500 mt-1 font-bold">{fieldErrors.institution}</p>}
                                    </div>
                                </div>

                                {/* Passwords */}
                                <div className="grid grid-cols-1 gap-4">
                                    <div className="flex flex-col gap-2">
                                        <label className="text-sm font-bold text-slate-700" htmlFor="password">Password</label>
                                        <div className="relative w-full">
                                            <span className="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">lock</span>
                                            <input
                                                id="password"
                                                className={`w-full rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary/20 border bg-white focus:border-primary h-11 pl-11 pr-12 text-sm font-medium transition-all placeholder:text-slate-400 ${fieldErrors.password ? 'border-red-500' : 'border-slate-300'}`}
                                                placeholder="Create a password"
                                                type={showPassword ? 'text' : 'password'}
                                                value={password}
                                                onChange={(e) => setPassword(e.target.value)}
                                            />
                                            {fieldErrors.password && <p className="text-[11px] text-red-500 mt-1 font-bold">{fieldErrors.password}</p>}
                                            <button
                                                type="button"
                                                onClick={() => setShowPassword(!showPassword)}
                                                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                                            >
                                                <span className="material-symbols-outlined text-[20px]">{showPassword ? 'visibility_off' : 'visibility'}</span>
                                            </button>
                                        </div>
                                        {password && (
                                            <div className="flex items-center gap-3 mt-1 px-1">
                                                <div className="flex-1 flex gap-1 h-1.5">
                                                    {[1, 2, 3, 4].map(level => (
                                                        <div
                                                            key={level}
                                                            className={`h-full flex-1 rounded-full transition-colors duration-300 ${level <= strength.score ? strength.color : 'bg-slate-200'}`}
                                                        />
                                                    ))}
                                                </div>
                                                <span className={`text-[10px] font-bold uppercase tracking-wider w-12 text-right ${strength.textColor}`}>
                                                    {strength.label}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                    <div className="flex flex-col gap-2">
                                        <label className="text-sm font-bold text-slate-700" htmlFor="confirmPassword">Confirm Password</label>
                                        <div className="relative w-full">
                                            <span className="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">lock</span>
                                            <input
                                                id="confirmPassword"
                                                className={`w-full rounded-lg text-slate-900 focus:outline-none focus:ring-2 h-11 pl-11 pr-12 text-sm font-medium transition-all placeholder:text-slate-400 border bg-white ${confirmPassword && confirmPassword !== password
                                                    ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20'
                                                    : 'border-slate-300 focus:border-primary focus:ring-primary/20'
                                                    }`}
                                                placeholder="Repeat your password"
                                                type={showConfirm ? 'text' : 'password'}
                                                required
                                                value={confirmPassword}
                                                onChange={(e) => setConfirmPassword(e.target.value)}
                                            />
                                            <button
                                                type="button"
                                                onClick={() => setShowConfirm(!showConfirm)}
                                                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                                            >
                                                <span className="material-symbols-outlined text-[20px]">{showConfirm ? 'visibility_off' : 'visibility'}</span>
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                {/* Requirements hint */}
                                <div className="flex items-center gap-2 mt-2">
                                    <span className={`material-symbols-outlined text-[16px] transition-colors ${isPasswordValid ? 'text-green-500' : 'text-slate-400'}`}>
                                        {isPasswordValid ? 'check_circle' : 'info'}
                                    </span>
                                    <span className="text-slate-500 text-xs font-medium">Requires 8+ characters and a number.</span>
                                </div>

                                {/* Terms */}
                                <div className="flex items-start gap-3 mt-2">
                                    <input
                                        className="mt-1 flex-shrink-0 h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary transition-colors cursor-pointer"
                                        id="terms"
                                        required
                                        type="checkbox"
                                        checked={termsAccepted}
                                        onChange={(e) => setTermsAccepted(e.target.checked)}
                                    />
                                    <div>
                                        <label className="text-sm text-slate-600 font-medium cursor-pointer" htmlFor="terms">
                                            I agree to the <Link className="text-primary font-bold hover:underline transition-colors" href="/terms">Terms of Service</Link> and <Link className="text-primary font-bold hover:underline transition-colors" href="/privacy">Privacy Policy</Link>.
                                        </label>
                                        {fieldErrors.terms_accepted && <p className="text-[11px] text-red-500 mt-1 font-bold">{fieldErrors.terms_accepted}</p>}
                                    </div>
                                </div>

                                {/* Submit Button */}
                                <div className="pt-4">
                                    <button
                                        className="flex w-full items-center justify-center rounded-lg h-11 px-5 bg-primary text-white text-sm font-bold hover:bg-blue-700 active:scale-[0.98] shadow-md shadow-primary/20 transition-all disabled:opacity-70 disabled:cursor-not-allowed"
                                        type="submit"
                                        disabled={localLoading}
                                    >
                                        {localLoading ? (
                                            <div className="flex items-center gap-2">
                                                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                                <span>Creating Account...</span>
                                            </div>
                                        ) : 'Create Account'}
                                    </button>
                                </div>
                            </form>

                            <div className="relative flex items-center py-6">
                                <div className="flex-grow border-t border-slate-200"></div>
                                <span className="flex-shrink mx-4 text-xs font-bold uppercase tracking-wider text-slate-400">Or continue with</span>
                                <div className="flex-grow border-t border-slate-200"></div>
                            </div>

                            {/* Social Signup */}
                            <button
                                type="button"
                                onClick={handleGoogleSignup}
                                className="w-full flex items-center justify-center gap-3 bg-white border border-slate-200 text-slate-700 h-11 rounded-lg text-sm font-bold hover:bg-slate-50 active:scale-[0.98] transition-all shadow-sm"
                            >
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                                </svg>
                                Google
                            </button>

                            <p className="text-center text-sm text-slate-600 mt-6 font-medium">
                                Already have an account? <Link href="/login" className="text-primary font-bold hover:underline transition-colors ml-1">Sign in</Link>
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function Signup() {
    return (
        <Suspense fallback={<div className="min-h-[calc(100vh-72px)] flex items-center justify-center"><div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div></div>}>
            <SignupContent />
        </Suspense>
    );
}
