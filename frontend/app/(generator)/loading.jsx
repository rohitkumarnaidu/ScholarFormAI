// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

export default function GeneratorLoading() {
    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-6">
            <div className="max-w-4xl mx-auto space-y-6">
                <div className="h-8 w-56 bg-slate-200 dark:bg-slate-800 rounded-lg animate-pulse" />
                <div className="h-48 bg-slate-200 dark:bg-slate-800 rounded-xl animate-pulse" />
                <div className="space-y-3">
                    <div className="h-4 w-full bg-slate-200 dark:bg-slate-800 rounded animate-pulse" />
                    <div className="h-4 w-3/4 bg-slate-200 dark:bg-slate-800 rounded animate-pulse" />
                    <div className="h-4 w-5/6 bg-slate-200 dark:bg-slate-800 rounded animate-pulse" />
                </div>
            </div>
        </div>
    );
}
