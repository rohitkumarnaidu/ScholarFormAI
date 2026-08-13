// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import { usePathname } from 'next/navigation';

// Routes that use AppShell (have their own Header + Sidebar)
const appShellPrefixes = [
    '/upload', '/preview', '/processing', '/results', '/edit', '/compare',
    '/download', '/templates', '/live', '/jobs', '/dashboard', '/history',
    '/batch-upload', '/template-editor',
    '/generate', '/agent', '/multi-upload', '/synthesis',
    '/settings', '/profile', '/api-keys', '/providers', '/contributing',
    '/feedback', '/notifications', '/admin-dashboard',
];

// Routes that have their own custom nav/footer
const customNavRoutes = ['/login', '/signup', '/forgot-password', '/reset-password', '/verify-otp', '/auth/callback'];

function shouldHideGlobalNav(pathname) {
    if (pathname === '/') return true; // Landing page has its own nav
    if (customNavRoutes.some(r => pathname.startsWith(r))) return true;
    if (appShellPrefixes.some(r => pathname.startsWith(r))) return true;
    return false;
}

function shouldHideGlobalFooter(pathname) {
    // AppShell routes don't need the global footer
    if (appShellPrefixes.some(r => pathname.startsWith(r))) return true;
    // Auth pages don't need global footer
    if (customNavRoutes.some(r => pathname.startsWith(r))) return true;
    if (pathname === '/') return true; // Landing page has its own footer
    return false;
}

export function ConditionalNavbar({ children }) {
    const pathname = usePathname();
    if (shouldHideGlobalNav(pathname)) return null;
    return children;
}

export function ConditionalFooter({ children }) {
    const pathname = usePathname();
    if (shouldHideGlobalFooter(pathname)) return null;
    return children;
}
