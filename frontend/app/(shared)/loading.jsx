// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

export default function SharedLoading() {
    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex items-center justify-center">
            <div className="flex flex-col items-center gap-4">
                <div className="w-12 h-12 border-4 border-primary/30 border-t-primary rounded-full animate-spin" />
                <p className="text-sm text-slate-500 dark:text-slate-400 animate-pulse">Loading...</p>
            </div>
        </div>
    );
}
