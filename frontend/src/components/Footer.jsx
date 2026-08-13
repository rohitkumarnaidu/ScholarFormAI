// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { useMetricsHealth } from '@/services/api.hooks';
import { subscribeNewsletter } from '@/services/api.core';

export default function Footer({ variant = 'app' }) {
    const { data: health } = useMetricsHealth({ staleTime: 60000, retry: false });
    const [email, setEmail] = useState('');
    const [status, setStatus] = useState('idle'); // idle, loading, success, error

    const handleSubscribe = async (e) => {
        e.preventDefault();
        if (!email || !email.includes('@')) return;

        setStatus('loading');
        try {
            await subscribeNewsletter(email);
            setStatus('success');
            setEmail('');
            setTimeout(() => setStatus('idle'), 3000);
        } catch {
            setStatus('error');
        }
    };


    const preventPlaceholderNav = (event) => {
        event.preventDefault();
    };

    if (variant === 'landing') {
        return (
            <footer className="app-footer pt-20 pb-10 relative overflow-hidden">
                <div className="max-w-[1240px] mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
                    <div className="grid grid-cols-1 md:grid-cols-12 gap-12 mb-16">
                        <div className="md:col-span-4">
                            <div className="flex items-center gap-2 sm:gap-3 mb-6">
                                <div className="size-10 sm:size-12 flex items-center justify-center">
                                    <span className="material-symbols-outlined text-[32px] sm:text-[38px] text-blue-700 dark:text-blue-400">auto_stories</span>
                                </div>
                                <span className="text-[22px] font-black tracking-tight text-slate-900 dark:text-white">ScholarForm AI</span>
                            </div>
                            <p className="text-[15px] text-slate-500 dark:text-slate-400 leading-[1.7] mb-8 pr-4">
                                Providing specialized technical writing and formatting for academic researchers worldwide.
                            </p>
                            <div className="flex items-center gap-4">
                                <a href="https://twitter.com" target="_blank" rel="noopener noreferrer" className="size-10 rounded-full bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-400 hover:text-primary hover:border-primary/30 hover:bg-primary/5 transition-all">
                                    <span className="material-symbols-outlined text-lg">share</span>
                                </a>
                                <a href="mailto:contact@scholarform.ai" className="size-10 rounded-full bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-400 hover:text-primary hover:border-primary/30 hover:bg-primary/5 transition-all">
                                    <span className="material-symbols-outlined text-lg">mail</span>
                                </a>
                            </div>
                        </div>
                        <div className="md:col-span-8 grid grid-cols-2 md:grid-cols-3 gap-8">
                            <div>
                                <h5 className="text-slate-900 dark:text-white font-bold text-sm mb-6 uppercase tracking-wider">Product</h5>
                                <ul className="flex flex-col gap-4">
                                    <li><Link href="/templates" className="text-[15px] text-slate-500 dark:text-slate-400 hover:text-primary hover:translate-x-1 transition-all inline-block">Templates</Link></li>
                                    <li><Link href="/#pricing" className="text-[15px] text-slate-500 dark:text-slate-400 hover:text-primary hover:translate-x-1 transition-all inline-block">Pricing</Link></li>
                                    <li><Link href="/upload" className="text-[15px] text-slate-500 dark:text-slate-400 hover:text-primary hover:translate-x-1 transition-all inline-block">Formatter</Link></li>
                                    <li><Link href="/#features" className="text-[15px] text-slate-500 dark:text-slate-400 hover:text-primary hover:translate-x-1 transition-all inline-block">Features</Link></li>
                                </ul>
                            </div>
                            <div>
                                <h5 className="text-slate-900 dark:text-white font-bold text-sm mb-6 uppercase tracking-wider">Resources</h5>
                                <ul className="flex flex-col gap-4">
                                    <li><Link href="/#about" className="text-[15px] text-slate-500 dark:text-slate-400 hover:text-primary hover:translate-x-1 transition-all inline-block">About Us</Link></li>
                                    <li>
                                        <div className="flex items-center">
                                            <Link href="#" onClick={preventPlaceholderNav} className="text-[15px] text-slate-500 dark:text-slate-400 hover:text-primary hover:translate-x-1 transition-all inline-block">Documentation</Link>
                                            <span className="ml-2 text-[10px] px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 font-semibold border border-blue-200 dark:border-blue-500/30">Soon</span>
                                        </div>
                                    </li>
                                    <li>
                                        <div className="flex items-center">
                                            <Link href="#" onClick={preventPlaceholderNav} className="text-[15px] text-slate-500 dark:text-slate-400 hover:text-primary hover:translate-x-1 transition-all inline-block">Video Tutorials</Link>
                                            <span className="ml-2 text-[10px] px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 font-semibold border border-blue-200 dark:border-blue-500/30">Soon</span>
                                        </div>
                                    </li>
                                    <li>
                                        <div className="flex items-center gap-2">
                                            <div className={`size-2 rounded-full ${health ? (health?.status === 'healthy' || health?.status === 'ok' ? 'bg-green-500' : 'bg-amber-500') : 'bg-slate-300'} animate-pulse`} />
                                            <Link href="#" onClick={preventPlaceholderNav} className="text-[15px] text-slate-500 dark:text-slate-400 hover:text-primary hover:translate-x-1 transition-all inline-block">
                                                {health ? (health?.status === 'healthy' || health?.status === 'ok' ? 'All Systems Operational' : 'Degraded Performance') : 'Checking System Status...'}
                                            </Link>
                                        </div>
                                    </li>
                                </ul>
                            </div>
                            <div className="col-span-2 md:col-span-1 pt-8 md:pt-0">
                                <h5 className="text-slate-900 dark:text-white font-bold text-sm mb-4 uppercase tracking-wider">Stay Updated</h5>
                                <p className="text-sm text-slate-500 dark:text-slate-400 mb-4 leading-relaxed">Join our newsletter to get updates on new academic templates and formatting features.</p>
                                <form onSubmit={handleSubscribe} className="flex gap-2 relative">
                                    <input 
                                        type="email" 
                                        value={email}
                                        onChange={(e) => {
                                            setEmail(e.target.value);
                                            if (status === 'error') setStatus('idle');
                                        }}
                                        disabled={status === 'loading' || status === 'success'}
                                        placeholder={status === 'success' ? '✔ Subscribed!' : 'Email address'}
                                        className={`w-full bg-slate-50 dark:bg-slate-800/50 border ${status === 'error' ? 'border-red-400 focus:ring-red-400' : status === 'success' ? 'border-green-400 text-green-600' : 'border-slate-200 dark:border-slate-700/50 focus:ring-primary/50'} rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 text-slate-900 dark:text-white transition-all shadow-sm disabled:opacity-70`}
                                        suppressHydrationWarning
                                    />
                                    <button 
                                        type="submit" 
                                        disabled={status === 'loading' || status === 'success' || !email}
                                        className="bg-primary hover:bg-primary-hover text-white px-5 rounded-xl transition-all shadow-md shadow-primary/20 flex items-center justify-center hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:hover:translate-y-0 disabled:cursor-not-allowed"
                                        suppressHydrationWarning
                                    >
                                        {status === 'loading' ? (
                                            <span className="material-symbols-outlined text-[20px] animate-spin">refresh</span>
                                        ) : status === 'success' ? (
                                            <span className="material-symbols-outlined text-[20px]">check</span>
                                        ) : (
                                            <span className="material-symbols-outlined text-[20px]">send</span>
                                        )}
                                    </button>
                                </form>
                                {status === 'error' && (
                                    <p className="text-xs text-red-500 mt-2 absolute">Something went wrong. Please try again.</p>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="pt-8 flex flex-col md:flex-row justify-between items-center gap-6">
                        <div className="flex flex-wrap items-center justify-center md:justify-start gap-x-6 gap-y-2">
                            <span className="text-[13px] text-slate-400" suppressHydrationWarning>&copy; {new Date().getFullYear()} ScholarForm AI. All rights reserved.</span>
                            <div className="hidden sm:block h-3 w-px bg-slate-200 dark:bg-slate-700" />
                            <Link href="/privacy" className="text-[13px] text-slate-500 hover:text-primary transition-colors">Privacy Policy</Link>
                            <Link href="/terms" className="text-[13px] text-slate-500 hover:text-primary transition-colors">Terms of Service</Link>
                        </div>
                        <div className="flex items-center justify-center gap-6">
                            <div className="flex items-center gap-1.5 text-slate-400 dark:text-slate-500 group" title={health?.version ? `Backend Ver: ${health.version}` : 'GDPR Compliant'}>
                                <span className={`material-symbols-outlined text-[16px] transition-colors ${health?.status ? 'text-green-500' : 'group-hover:text-green-500'}`}>shield</span>
                                <span className="text-[11px] font-bold tracking-widest uppercase">GDPR Ready</span>
                            </div>
                            <div className="flex items-center gap-1.5 text-slate-400 dark:text-slate-500 group">
                                <span className={`material-symbols-outlined text-[16px] transition-colors ${health?.status ? 'text-blue-500' : 'group-hover:text-blue-500'}`}>verified</span>
                                <span className="text-[11px] font-bold tracking-widest uppercase">Publisher Partner</span>
                            </div>
                        </div>
                    </div>
                </div>
            </footer>
        );
    }

    return (
        <footer className="app-footer max-w-[1280px] mx-auto px-4 sm:px-6 py-8 sm:py-10 mt-10 sm:mt-12">
            <div className="flex flex-col md:flex-row justify-between items-center gap-4 sm:gap-6">
                <div className="flex items-center gap-2 text-slate-400" suppressHydrationWarning>
                    <span className="material-symbols-outlined text-xl">auto_stories</span>
                    <span className="text-sm font-medium text-center md:text-left">&copy; {new Date().getFullYear()} ScholarForm AI. Built for academics.</span>
                </div>
                <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
                    <Link href="/terms" className="text-sm text-slate-500 dark:text-slate-400 hover:text-primary transition-colors">Terms of Service</Link>
                    <Link href="/privacy" className="text-sm text-slate-500 dark:text-slate-400 hover:text-primary transition-colors">Privacy Policy</Link>
                    <a href="mailto:support@scholarform.ai" className="text-sm text-slate-500 dark:text-slate-400 hover:text-primary transition-colors">Support</a>
                </div>
            </div>
        </footer>
    );
}
