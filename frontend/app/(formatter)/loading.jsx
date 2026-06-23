// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

export default function FormatterLoading() {
    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-6">
            <div className="max-w-4xl mx-auto space-y-6">
                <div className="h-8 w-48 bg-slate-200 dark:bg-slate-800 rounded-lg animate-pulse" />
                <div className="h-64 bg-slate-200 dark:bg-slate-800 rounded-xl animate-pulse" />
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="h-32 bg-slate-200 dark:bg-slate-800 rounded-xl animate-pulse" />
                    <div className="h-32 bg-slate-200 dark:bg-slate-800 rounded-xl animate-pulse" />
                </div>
            </div>
        </div>
    );
}
