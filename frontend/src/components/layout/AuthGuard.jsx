// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import { useEffect, useMemo, Suspense } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';

const isAdminUser = (user) => (
    user?.app_metadata?.role === 'admin'
);

function AuthGuardInner({ children, requireAdmin }) {
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();
    const { isLoggedIn, loading, user } = useAuth();

    const nextTarget = useMemo(() => {
        const queryString = searchParams?.toString();
        return queryString ? `${pathname}?${queryString}` : pathname;
    }, [pathname, searchParams]);

    useEffect(() => {
        if (loading) return;

        if (!isLoggedIn) {
            router.replace(`/login?next=${encodeURIComponent(nextTarget)}`);
            return;
        }

        if (requireAdmin && !isAdminUser(user)) {
            router.replace('/dashboard');
        }
    }, [isLoggedIn, loading, nextTarget, requireAdmin, router, user]);

    if (loading) {
        return (
            <div className="w-full max-w-7xl mx-auto px-6 py-16 flex items-center justify-center">
                <div className="flex items-center gap-3 text-slate-500 dark:text-slate-400">
                    <span className="material-symbols-outlined animate-spin">progress_activity</span>
                    <span className="text-sm font-medium">Loading your session...</span>
                </div>
            </div>
        );
    }

    if (!isLoggedIn) {
        return null;
    }

    if (requireAdmin && !isAdminUser(user)) {
        return null;
    }

    return children;
}

export default function AuthGuard({ children, requireAdmin = false }) {
    return (
        <Suspense fallback={
            <div className="w-full max-w-7xl mx-auto px-6 py-16 flex items-center justify-center">
                <div className="flex items-center gap-3 text-slate-500 dark:text-slate-400">
                    <span className="material-symbols-outlined animate-spin">progress_activity</span>
                    <span className="text-sm font-medium">Loading your session...</span>
                </div>
            </div>
        }>
            <AuthGuardInner requireAdmin={requireAdmin}>{children}</AuthGuardInner>
        </Suspense>
    );
}
