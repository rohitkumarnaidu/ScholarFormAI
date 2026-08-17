// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';

import usePageTitle from '@/src/hooks/usePageTitle';
import { useAuth } from '@/src/context/AuthContext';

const DEFAULT_PROCESSING_MESSAGE = "Unsupported file type or corrupted metadata detected. We couldn't parse your manuscript for formatting. Please check your file format and try again.";
const DEFAULT_NOT_FOUND_MESSAGE = 'The page you requested could not be found. It may have been moved or deleted.';

function normalizeError(errorValue) {
    if (!errorValue) return null;
    if (typeof errorValue === 'string') {
        return {
            title: 'Processing Error',
            message: errorValue,
        };
    }

    const title = errorValue.title || errorValue.name || 'Processing Error';
    const message = errorValue.message || DEFAULT_PROCESSING_MESSAGE;
    return { title, message };
}

import { Suspense } from 'react';
import { AlertTriangle, FileUp, Headset } from 'lucide-react';

function ErrorContent() {
    usePageTitle('Error');
    const searchParams = useSearchParams();
    const { isLoggedIn } = useAuth();
    const queryMessage = searchParams.get('message');
    const queryTitle = searchParams.get('title');
    const resolvedError = normalizeError(queryMessage ? { title: queryTitle, message: queryMessage } : null);
    const isNotFound = !resolvedError;

    const title = isNotFound ? 'Page not found' : resolvedError.title;
    const message = isNotFound ? DEFAULT_NOT_FOUND_MESSAGE : resolvedError.message;
    const checklistItems = isNotFound
        ? [
            'Check the URL for typos',
            'Use navigation links to return to a valid page',
            'Go back to Upload or Dashboard to continue your workflow',
        ]
        : [
            'Check if your file is in .docx, .pdf, .tex, .txt, .html, or .md format',
            'Ensure the file is not password protected or encrypted',
            'Rename the file to remove special characters and retry',
        ];

    const primaryLink = isNotFound ? (isLoggedIn ? '/dashboard' : '/') : '/upload';
    const primaryLabel = isNotFound ? (isLoggedIn ? 'Go to Dashboard' : 'Go to Home') : 'Return to Upload';

    return (
        <main className="flex-1 flex flex-col items-center justify-center px-4 py-12">
            <div className="max-w-[640px] w-full bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-[#e7ecf3] dark:border-slate-800 overflow-hidden">
                <div className="flex flex-col items-center gap-6 px-4 sm:px-8 pt-10 pb-6">
                    <div className="flex items-center justify-center w-24 h-24 rounded-full bg-red-50 dark:bg-red-900/20 text-red-500">
                        <AlertTriangle className="text-6xl" />
                    </div>
                    <div className="flex flex-col items-center gap-3 text-center">
                        <h1 className="text-[#0d131b] dark:text-white text-3xl font-bold leading-tight tracking-tight">{title}</h1>
                        <p className="text-slate-600 dark:text-slate-400 text-base leading-relaxed max-w-[480px]">
                            {message}
                        </p>
                    </div>
                </div>

                <div className="px-4 sm:px-8">
                    <div className="h-px bg-[#e7ecf3] dark:bg-slate-800 w-full" />
                </div>

                <div className="px-4 sm:px-8 py-6">
                    <h3 className="text-[#0d131b] dark:text-white text-lg font-bold leading-tight mb-4">Recommended Next Steps</h3>
                    <div className="space-y-1">
                        {checklistItems.map((item) => (
                            <label key={item} className="flex gap-x-4 py-3 px-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer group">
                                <div className="relative flex items-center">
                                    <input className="h-5 w-5 rounded border-[#cfd9e7] dark:border-slate-700 border-2 bg-transparent text-primary checked:bg-primary checked:border-primary focus:ring-0 focus:ring-offset-0 transition-all" type="checkbox" />
                                </div>
                                <p className="text-slate-700 dark:text-slate-300 text-base font-normal leading-normal">{item}</p>
                            </label>
                        ))}
                    </div>
                </div>

                <div className="bg-slate-50 dark:bg-slate-800/30 px-4 sm:px-8 py-6 flex flex-col sm:flex-row gap-3 justify-center">
                    <Link href={primaryLink} className="flex-1 flex min-w-[160px] cursor-pointer items-center justify-center rounded-lg h-12 px-6 bg-primary text-white text-sm font-bold leading-normal tracking-wide transition-opacity hover:opacity-90 active:scale-95 duration-150">
                        <FileUp className="mr-2" />
                        <span className="truncate">{primaryLabel}</span>
                    </Link>
                    {isNotFound ? (
                        <Link href="/upload" className="flex-1 flex min-w-[160px] cursor-pointer items-center justify-center rounded-lg h-12 px-6 bg-white dark:bg-slate-800 border border-[#cfd9e7] dark:border-slate-700 text-[#0d131b] dark:text-white text-sm font-bold leading-normal tracking-wide transition-all hover:bg-slate-50 dark:hover:bg-slate-700 active:scale-95 duration-150">
                            <FileUp className="mr-2" />
                            <span className="truncate">Open Upload</span>
                        </Link>
                    ) : (
                        <button
                            onClick={() => window.open('mailto:support@scholarform.ai', '_self')}
                            className="flex-1 flex min-w-[160px] cursor-pointer items-center justify-center rounded-lg h-12 px-6 bg-white dark:bg-slate-800 border border-[#cfd9e7] dark:border-slate-700 text-[#0d131b] dark:text-white text-sm font-bold leading-normal tracking-wide transition-all hover:bg-slate-50 dark:hover:bg-slate-700 active:scale-95 duration-150"
                        >
                            <Headset className="mr-2" />
                            <span className="truncate">Contact Support</span>
                        </button>
                    )}
                </div>
            </div>

            <div className="mt-8 flex items-center gap-2 text-slate-500 dark:text-slate-400 text-sm">
                <span className="flex h-2 w-2 rounded-full bg-green-500" />
                <p>All other systems are operational. <Link href="/admin-dashboard" className="text-primary hover:underline underline-offset-4 ml-1">View status page</Link></p>
            </div>

            <footer className="w-full py-8 px-4 sm:px-10 text-center border-t border-[#e7ecf3] dark:border-slate-800 text-slate-400 text-xs mt-8">
                <p suppressHydrationWarning>(c) {new Date().getFullYear()} ManuscriptFormatter. Professional Academic Tools for Researchers.</p>
            </footer>
        </main>
    );
}

export default function ErrorPage() {
    return (
        <Suspense fallback={<main className="flex-1 flex flex-col items-center justify-center px-4 py-12"><div className="text-slate-500">Loading error details...</div></main>}>
            <ErrorContent />
        </Suspense>
    );
}
