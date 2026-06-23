// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import React, { memo, useMemo } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/src/context/AuthContext';
import ThemeToggle from '@/src/components/layout/header/ThemeToggle';
import NotificationBell from '@/src/components/NotificationBell';

const HEADER_STYLE = {
    backgroundColor: 'rgba(255, 255, 255, 0.4)',
    backdropFilter: 'blur(16px) saturate(160%)',
    WebkitBackdropFilter: 'blur(16px) saturate(160%)',
    borderBottom: '1px solid rgba(0, 0, 0, 0.08)',
};

const Logo = memo(({ href }) => (
    <Link 
        href={href} 
        aria-label="ScholarForm AI Home"
        className="flex items-center gap-2 group active:scale-95 focus:ring-2 focus:ring-primary focus:outline-none rounded-lg transition-all text-decoration-none"
    >
        <div className="flex items-center justify-center pointer-events-none">
            <span className="material-symbols-outlined text-[30px] sm:text-[34px] text-blue-700 dark:text-blue-400">auto_stories</span>
        </div>
        <span className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white leading-none tracking-tight">
            ScholarForm <span className="text-blue-600 dark:text-blue-400">AI</span>
        </span>
    </Link>
));
Logo.displayName = 'Logo';

const Header = memo(function Header({ section = 'shared', isSidebarLayout = false, onOpenMobileSidebar }) {
    const pathname = usePathname();
    const { user, loading, isLoggedIn } = useAuth();
    
    const uiUser = loading ? null : (isLoggedIn ? user : null);

    const dashboardHref = useMemo(() => {
        if (!uiUser) return '/';
        return pathname.includes('generator') || section === 'generator' ? '/generate' : '/dashboard';
    }, [uiUser, pathname, section]);

    return (
        <header 
            style={HEADER_STYLE}
            className={`app-header sticky top-0 z-50 w-full transition-all duration-300 dark:!bg-slate-900/30 dark:border-white/5 ${isSidebarLayout ? 'h-12' : 'h-[64px]'}`}
        >
            <div className="h-full mx-auto px-4 sm:px-6 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                    {isSidebarLayout && (
                        <button
                            onClick={onOpenMobileSidebar}
                            className="p-1.5 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-white/10 rounded-lg transition-colors"
                            aria-label="Toggle Sidebar"
                        >
                            <span className="material-symbols-outlined text-[24px]">menu</span>
                        </button>
                    )}
                    <Logo href={dashboardHref} />
                </div>

                <div className="flex items-center gap-1.5 sm:gap-2">
                    <div className="hidden sm:flex items-center gap-1.5 sm:gap-2">
                        <ThemeToggle />
                        <NotificationBell />
                        <button aria-label="Settings" className="p-1.5 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-white/10 rounded-lg transition-colors">
                            <span className="material-symbols-outlined text-[20px]">settings</span>
                        </button>
                    </div>

                    {loading ? null : uiUser ? (
                        <div className="flex items-center gap-2 pl-2 sm:pl-3 border-l border-slate-200 dark:border-white/10">
                            <div className="hidden md:flex flex-col items-end">
                                <span className="text-[13px] font-bold text-slate-900 dark:text-white leading-none">
                                    {uiUser.user_metadata?.full_name || uiUser.email?.split('@')[0] || 'Researcher'}
                                </span>
                                <span className="text-[9px] font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider mt-0.5">
                                    {uiUser.app_metadata?.role || 'Free Plan'}
                                </span>
                            </div>
                            <button aria-label="User Profile" className="size-8 sm:size-9 flex items-center justify-center text-slate-600 dark:text-slate-300 hover:text-primary dark:hover:text-primary-light transition-all rounded-lg hover:bg-slate-100 dark:hover:bg-white/10">
                                <span className="material-symbols-outlined text-[22px] sm:text-[26px]">person</span>
                            </button>
                        </div>
                    ) : (
                        <div className="flex items-center gap-2">
                            <Link 
                                href="/login"
                                className="hidden sm:flex px-3 py-1.5 text-sm font-bold text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors"
                            >
                                Login
                            </Link>
                            <Link 
                                href="/signup"
                                className="px-3 sm:px-4 py-1.5 sm:py-2 bg-primary hover:bg-primary-hover text-white text-xs sm:text-sm font-bold rounded-lg transition-all shadow-md shadow-primary/20 hover:-translate-y-0.5 active:translate-y-0"
                            >
                                Get Started
                            </Link>
                        </div>
                    )}
                </div>
            </div>
        </header>
    );
});

export default Header;
