// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import { usePathname, useRouter } from 'next/navigation';
import React, { useEffect, useState, Suspense, useMemo, useCallback } from 'react';
import OnboardingTour from '@/components/OnboardingTour';
import { useAuth } from '@/context/AuthContext';

const AUTH_ROUTES = ['/login', '/signup', '/forgot-password', '/verify-otp', '/reset-password', '/auth/callback'];

export default function AppShell({ children, section = 'shared' }) {
    const pathname = usePathname();
    const router = useRouter();
    const { isLoggedIn, loading } = useAuth();

    const [isDesktopSidebarOpen, setIsDesktopSidebarOpen] = useState(false);
    const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
    const [isDesktop, setIsDesktop] = useState(false);

    const isAuthRoute = useMemo(
        () => AUTH_ROUTES.some((route) => pathname.startsWith(route)),
        [pathname]
    );
    const isLandingRoute = useMemo(
        () => pathname === '/' || pathname === '/terms' || pathname === '/privacy',
        [pathname]
    );

    const showSidebarLayout = useMemo(
        () => !isLandingRoute && !isAuthRoute,
        [isLandingRoute, isAuthRoute]
    );

    useEffect(() => {
        if (typeof window === 'undefined') return;
        const params = new URLSearchParams(window.location.search || '');
        const isGuest = params.get('guest') === '1';
        // isGuest is only used for the redirect guard below

        if (loading) return;
        if (pathname === '/' && isLoggedIn && !isGuest) {
            router.replace('/dashboard');
        }
    }, [pathname, isLoggedIn, loading, router]);

    useEffect(() => {
        if (typeof window === 'undefined') {
            return undefined;
        }

        const mediaQuery = window.matchMedia('(min-width: 1024px)');
        const handleChange = (event) => {
            setIsDesktop(event.matches);
            if (!event.matches) {
                setIsDesktopSidebarOpen(false);
            }
        };

        setIsDesktop(mediaQuery.matches);

        if (typeof mediaQuery.addEventListener === 'function') {
            mediaQuery.addEventListener('change', handleChange);
            return () => mediaQuery.removeEventListener('change', handleChange);
        }

        mediaQuery.addListener(handleChange);
        return () => mediaQuery.removeListener(handleChange);
    }, []);

    const toggleSidebar = useCallback(() => {
        if (isDesktop) {
            setIsDesktopSidebarOpen((prev) => !prev);
        } else {
            setIsMobileSidebarOpen(true);
        }
    }, [isDesktop]);

    // Header height 48px (h-12)
    const appHeaderHeightPx = 48;
    const sidebarW = isDesktopSidebarOpen ? 240 : 72;

    // Unified glassmorphism configuration
    const glassClasses = "backdrop-blur-xl saturate-[160%] bg-white/40 dark:bg-slate-950/40";

    if (!showSidebarLayout) {
        return (
            <div className="relative z-10 flex flex-col min-h-screen">
                <Suspense fallback={<div className={`h-12 w-full border-b border-black/5 dark:border-white/5 ${glassClasses}`} />}>
                    <Header section={section} />
                </Suspense>
                <main id="main-content" tabIndex="-1" className="flex-grow flex flex-col items-center w-full relative z-10 focus:outline-none">
                    {children}
                </main>
                <OnboardingTour />
            </div>
        );
    }

    return (
        <>
            {/* Theme-Adaptive Background layer */}
            <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
                <div className="absolute inset-0 bg-[#f6f6f8] dark:bg-[#09090b]" />
                <div className="absolute top-[20%] left-[10%] w-[40vw] h-[40vw] rounded-full bg-blue-600/5 dark:bg-blue-600/10 blur-[120px]" />
                <div className="absolute bottom-[10%] right-[15%] w-[30vw] h-[30vw] rounded-full bg-indigo-600/5 dark:bg-indigo-600/10 blur-[100px]" />
            </div>

            {/* Sticky Header */}
            <div className="fixed top-0 left-0 right-0 z-50">
                <Suspense fallback={<div className={`h-12 w-full border-b border-black/5 dark:border-white/5 ${glassClasses}`} />}>
                    <Header
                        section={section}
                        isSidebarLayout={true}
                        onOpenMobileSidebar={toggleSidebar}
                    />
                </Suspense>
            </div>

            {/* Mobile Sidebar Back-drop */}
            {isMobileSidebarOpen && (
                <div className="lg:hidden fixed inset-0 z-[60] flex">
                    <div className="fixed inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-sm" onClick={() => setIsMobileSidebarOpen(false)} aria-hidden="true" />
                    <div className={`sidebar-mobile relative flex flex-col w-[260px] h-full shadow-2xl animate-in slide-in-from-left duration-300 border-r border-black/5 dark:border-white/10 ${glassClasses}`}>
                        <Suspense fallback={<div className="w-full h-full bg-white/20 dark:bg-slate-950/20" />}>
                            <Sidebar section={section} onClose={() => setIsMobileSidebarOpen(false)} isCollapsed={false} />
                        </Suspense>
                    </div>
                </div>
            )}

            {/* Desktop Sidebar (Theme and Color perfectly unified with Header) */}
            <div
                className={`fixed left-0 hidden lg:flex flex-col justify-start z-40 transition-all duration-300 ease-in-out sidebar-desktop border-r border-black/5 dark:border-white/10 ${glassClasses} ${isDesktopSidebarOpen ? 'w-[240px]' : 'w-[72px] items-center'}`}
                style={{ top: `${appHeaderHeightPx}px`, bottom: 0 }}
            >
                <div className="w-full h-full flex flex-col">
                    <Suspense fallback={<div className="w-full h-full bg-white/20 dark:bg-slate-950/20" />}>
                        <Sidebar section={section} isCollapsed={!isDesktopSidebarOpen} />
                    </Suspense>
                </div>
            </div>

            {/* Main Content Area */}
            <main
                id="main-content"
                tabIndex="-1"
                className="appshell-main relative z-10 min-h-screen custom-scrollbar focus:outline-none"
                style={{
                    paddingTop: `${appHeaderHeightPx}px`,
                    paddingLeft: isDesktop ? `${sidebarW}px` : '0px',
                }}
            >
                {children}
            </main>
            <OnboardingTour />
        </>
    );
}
