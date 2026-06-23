// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import { useEffect } from 'react';

export default function AdminError({ error, reset }) {
    useEffect(() => {
        console.error('Route error in (admin):', error);
    }, [error]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 px-4">
            <div className="max-w-lg w-full rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-xl">
                <div className="flex items-start gap-3">
                    <span className="material-symbols-outlined text-red-600">admin_panel_settings</span>
                    <div>
                        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Admin Dashboard Error</h2>
                        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                            The admin dashboard encountered an issue. Please try again.
                        </p>
                    </div>
                </div>
                <div className="mt-6">
                    <button
                        type="button"
                        onClick={() => reset()}
                        className="w-full rounded-lg bg-primary text-white px-4 py-2.5 text-sm font-bold hover:bg-blue-700 transition-colors"
                    >
                        Try Again
                    </button>
                </div>
                {process.env.NODE_ENV !== 'production' ? (
                    <p className="mt-4 text-xs text-slate-500 break-words">
                        {error?.message || String(error)}
                    </p>
                ) : null}
            </div>
        </div>
    );
}
