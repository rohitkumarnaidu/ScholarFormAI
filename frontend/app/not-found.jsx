// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import { useRouter } from 'next/navigation';

export default function NotFound() {
    const router = useRouter();

    return (
        <div className="min-h-[80vh] flex flex-col items-center justify-center p-6 text-center animate-in stagger-fade">
            <h1 className="text-8xl font-bold bg-gradient-to-r from-red-500 to-rose-600 bg-clip-text text-transparent mb-6">404</h1>
            <h2 className="text-2xl font-semibold mb-4 text-slate-800 dark:text-slate-100">Page Not Found</h2>
            <p className="text-slate-600 dark:text-slate-400 max-w-md mb-8">
                The page you are looking for doesn&apos;t exist or has been moved.
            </p>
            <div className="flex gap-4">
                <button
                    onClick={() => router.back()}
                    className="px-6 py-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-lg font-medium hover:bg-slate-50 dark:hover:bg-slate-700 transition"
                >
                    Go Back
                </button>
                <button
                    onClick={() => router.push('/')}
                    className="px-6 py-2 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition"
                >
                    Return Home
                </button>
            </div>
        </div>
    );
}
