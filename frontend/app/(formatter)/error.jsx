// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import { useEffect } from 'react';

export default function FormatterError({ error, reset }) {
    useEffect(() => {
        console.error('Route error in (formatter):', error);
    }, [error]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 px-4">
            <div className="max-w-lg w-full rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-xl">
                <div className="flex items-start gap-3">
                    <span className="material-symbols-outlined text-red-600">error</span>
                    <div>
                        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Formatter Error</h2>
                        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                            The formatter encountered an issue. Your manuscript data is safe.
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
