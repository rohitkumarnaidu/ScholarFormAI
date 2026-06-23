// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import React from 'react';
import { useRouter } from 'next/navigation';
import PreviewView from '@/src/components/Preview';
import ErrorBoundary from '@/src/components/ErrorBoundary';
import useJobFromUrl from '@/src/hooks/useJobFromUrl';
import Footer from '@/src/components/Footer';
import Skeleton from '@/src/components/ui/Skeleton';

export default function Preview() {
    usePageTitle('Preview');
    const router = useRouter();
    const navigate = (href, options = {}) => {
        if (options?.replace) {
            router.replace(href);
            return;
        }
        router.push(href);
    };
    const { job, isLoading: isJobLoading, error: jobLoadError } = useJobFromUrl();

    // Gate: loading job from URL
    if (isJobLoading && !job) {
        return (
            <div className="min-h-screen flex flex-col bg-background-light dark:bg-background-dark animate-in fade-in duration-300">
                <main className="flex-1 flex flex-col p-8 items-center">
                    <div className="max-w-4xl w-full flex-1 bg-white dark:bg-slate-900 shadow-xl border border-slate-200 dark:border-slate-800 p-8 sm:p-12 mb-8 flex flex-col gap-6">
                        <Skeleton className="h-10 w-3/4 mx-auto" />
                        <Skeleton className="h-6 w-1/4 mx-auto" />
                        <div className="h-4" />
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-4 w-5/6" />
                        <Skeleton className="h-4 w-[90%]" />
                        <div className="h-4" />
                        <Skeleton className="h-[200px] w-full" />
                    </div>
                </main>
                <Footer variant="app" />
            </div>
        );
    }

    // Gate: error loading job from URL
    if (jobLoadError && !job) {
        return (
            <div className="min-h-screen flex flex-col bg-background-light dark:bg-background-dark">
                <main className="flex-1 flex flex-col items-center justify-center px-4 text-center">
                    <p className="text-red-600 dark:text-red-400 mb-3">{jobLoadError}</p>
                    <button onClick={() => navigate('/history')} className="text-primary font-bold hover:underline">
                        Return to History
                    </button>
                </main>
                <Footer variant="app" />
            </div>
        );
    }

    // Gate: no job in context or URL
    if (!job) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-background-light dark:bg-background-dark">
                <div className="text-center p-8 bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 max-w-md animate-in fade-in zoom-in duration-300">
                    <span className="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-700 mb-4 block">receipt_long</span>
                    <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">No document to preview</h2>
                    <p className="text-slate-500 dark:text-slate-400 mb-6 text-sm leading-relaxed">
                        Please upload and process a manuscript first to see the final formatted preview.
                    </p>
                    <button
                        onClick={() => navigate('/upload')}
                        className="w-full bg-primary text-white font-bold py-3 px-6 rounded-xl hover:bg-blue-700 transition-all shadow-lg shadow-primary/20 flex items-center justify-center gap-2"
                    >
                        <span className="material-symbols-outlined">upload_file</span>
                        Return to Upload
                    </button>
                </div>
            </div>
        );
    }

    return (
        <ErrorBoundary>
            <PreviewView
                job={job}
                onUpload={() => navigate('/upload')}
                onDownload={() => navigate('/download')}
            />
        </ErrorBoundary>
    );
}

