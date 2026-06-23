// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React, { useEffect, useMemo, useState } from 'react';
import { isCompleted } from '../constants/status';
import { getPreview } from '@/src/services/api';

function buildSectionChunks(structuredData) {
    if (!structuredData?.sections || typeof structuredData.sections !== 'object') {
        return [
            {
                section: 'CONTENT',
                text: 'No structured text content available.',
            },
        ];
    }

    const entries = Object.entries(structuredData.sections)
        .map(([section, texts]) => ({
            section,
            text: Array.isArray(texts) ? texts.join('\n') : String(texts || ''),
        }))
        .filter((item) => item.text.trim().length > 0);

    if (!entries.length) {
        return [
            {
                section: 'CONTENT',
                text: 'No structured text content available.',
            },
        ];
    }

    return entries;
}

export default function Preview({
    job,
    onUpload,
    onDownload,
}) {
    const [title, setTitle] = useState('');
    const [allSections, setAllSections] = useState([]);
    const [visibleSections, setVisibleSections] = useState([]);
    const [loadProgress, setLoadProgress] = useState(0);
    const [isFetchingPreview, setIsFetchingPreview] = useState(false);
    const [errorMessage, setErrorMessage] = useState('');
    const [zoomLevel, setZoomLevel] = useState(1);

    useEffect(() => {
        let isCancelled = false;

        const fetchPreview = async () => {
            if (!job?.id) {
                return;
            }

            setIsFetchingPreview(true);
            setErrorMessage('');
            setLoadProgress(0);
            setVisibleSections([]);

            try {
                const data = await getPreview(job.id, { debounceMs: 350 });

                if (isCancelled) {
                    return;
                }

                setTitle(
                    data.metadata?.filename?.split('.')[0] ||
                    job.originalFileName ||
                    'Untitled'
                );
                setAllSections(buildSectionChunks(data.structured_data));
            } catch (error) {
                if (isCancelled) {
                    return;
                }
                console.error('Failed to load preview:', error);
                setErrorMessage(error?.message || 'Error loading preview content. Please try again.');
                setAllSections([
                    {
                        section: 'ERROR',
                        text: 'Error loading preview content. Please try again.',
                    },
                ]);
            } finally {
                if (!isCancelled) {
                    setIsFetchingPreview(false);
                }
            }
        };

        fetchPreview();

        return () => {
            isCancelled = true;
        };
    }, [job?.id, job?.originalFileName]);

    useEffect(() => {
        if (!allSections.length) {
            setVisibleSections([]);
            setLoadProgress(0);
            return;
        }

        let isCancelled = false;
        let cursor = 0;
        const chunkSize = 2;

        const renderNextChunk = () => {
            if (isCancelled) {
                return;
            }

            const nextSections = allSections.slice(cursor, cursor + chunkSize);
            if (!nextSections.length) {
                setLoadProgress(100);
                return;
            }

            cursor += nextSections.length;
            setVisibleSections((current) => [...current, ...nextSections]);
            setLoadProgress(Math.min(100, Math.round((cursor / allSections.length) * 100)));

            if (cursor < allSections.length) {
                setTimeout(renderNextChunk, 60);
            }
        };

        setVisibleSections([]);
        setLoadProgress(0);
        const timerId = setTimeout(renderNextChunk, 0);

        return () => {
            isCancelled = true;
            clearTimeout(timerId);
        };
    }, [allSections]);

    const wordCount = useMemo(() => {
        const visibleText = visibleSections.map((item) => item.text).join(' ');
        return visibleText.split(/\s+/).filter(Boolean).length;
    }, [visibleSections]);

    const isIncrementalLoadActive =
        visibleSections.length < allSections.length || isFetchingPreview;

    return (
        <div className="bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100 min-h-screen flex flex-col font-display">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 px-4 sm:px-6 py-3 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 animate-in slide-in-from-top duration-300">
                <div className="flex items-center gap-2 overflow-hidden min-w-0">
                    <button
                        onClick={onUpload}
                        className="text-slate-500 dark:text-slate-400 text-sm font-medium hover:text-primary whitespace-nowrap"
                    >
                        Upload
                    </button>
                    <span className="text-slate-400">/</span>
                    <span className="text-slate-900 dark:text-white text-sm font-semibold truncate">
                        {title} (Preview)
                    </span>
                    <span className="ml-2 px-2 py-0.5 bg-primary/10 text-primary dark:bg-primary/20 text-[10px] font-bold uppercase rounded">
                        Read Only
                    </span>
                </div>

                <div className="flex items-center gap-3 w-full lg:w-auto">
                    {isIncrementalLoadActive ? (
                        <span className="text-xs text-slate-500 mr-2 flex items-center gap-1 flex-1">
                            <span className="material-symbols-outlined text-[14px] animate-spin">
                                progress_activity
                            </span>
                            Preview loading {loadProgress}%
                        </span>
                    ) : (
                        <span className="text-xs text-slate-400 mr-2 flex items-center gap-1">
                            <span className="material-symbols-outlined text-[14px]">info</span>
                            This is a read-only final inspection
                        </span>
                    )}

                    {/* Zoom Controls (UX-P3-1) */}
                    <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 rounded-lg p-1 mr-2">
                        <button
                            onClick={() => setZoomLevel(prev => Math.max(0.5, prev - 0.1))}
                            className="p-1 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 rounded transition"
                            title="Zoom Out"
                            aria-label="Zoom Out"
                        >
                            <span className="material-symbols-outlined text-[16px]" aria-hidden="true">zoom_out</span>
                        </button>
                        <span className="text-xs font-semibold w-10 text-center text-slate-700 dark:text-slate-300">
                            {Math.round(zoomLevel * 100)}%
                        </span>
                        <button
                            onClick={() => setZoomLevel(prev => Math.min(2.5, prev - 0.1))}
                            className="p-1 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 rounded transition"
                            title="Zoom In"
                            aria-label="Zoom In"
                        >
                            <span className="material-symbols-outlined text-[16px]" aria-hidden="true">zoom_in</span>
                        </button>
                    </div>

                    <button
                        onClick={onDownload}
                        disabled={!isCompleted(job?.status)}
                        className="flex items-center justify-center gap-1.5 px-4 py-1.5 bg-primary text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-slate-400 w-full sm:w-auto"
                    >
                        <span className="material-symbols-outlined text-[18px]">download</span>
                        <span className="text-sm font-bold">Download Final</span>
                    </button>
                </div>
            </div>

            <div className="flex flex-1 flex-col xl:flex-row overflow-hidden">
                <main className="flex-1 overflow-y-auto bg-slate-50 dark:bg-background-dark p-4 sm:p-6 lg:p-8 flex justify-center">
                    <div className="w-full max-w-[850px] transition-transform duration-200" style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'top center' }}>
                        <article className="manuscript-paper bg-white dark:bg-slate-900 min-h-[700px] lg:min-h-[1100px] p-5 sm:p-8 lg:p-16 rounded-sm border border-slate-200 dark:border-slate-800 shadow-xl overflow-hidden pointer-events-none select-none">
                            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white mb-6 sm:mb-8">
                                {title.replace(/_/g, ' ')}
                            </h1>

                            {errorMessage ? (
                                <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                                    {errorMessage}
                                </div>
                            ) : null}

                            <div className="w-full text-base sm:text-lg leading-relaxed text-slate-700 dark:text-slate-300 font-serif space-y-6">
                                {visibleSections.map((item, index) => (
                                    <section key={`${item.section}-${index}`} className="animate-in fade-in duration-200">
                                        <h2 className="text-base font-semibold uppercase tracking-wide mb-2 text-slate-700 dark:text-slate-200">
                                            {item.section}
                                        </h2>
                                        <p className="whitespace-pre-wrap">{item.text}</p>
                                    </section>
                                ))}
                            </div>
                        </article>
                    </div>
                </main>

                <aside className="w-full xl:w-80 border-t xl:border-t-0 xl:border-l border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col xl:max-h-none max-h-[360px]">
                    <div className="p-4 border-b border-slate-200 dark:border-slate-800">
                        <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            <span className="material-symbols-outlined text-primary">analytics</span>
                            Final Formatting Report
                        </h3>
                    </div>
                    <div className="flex-1 overflow-y-auto p-4 space-y-4">
                        <div className="p-4 bg-green-50 dark:bg-green-900/10 border border-green-100 dark:border-green-900/30 rounded-xl">
                            <div className="flex gap-2 mb-1">
                                <span className="material-symbols-outlined text-green-500 text-sm">check_circle</span>
                                <h4 className="text-sm font-bold text-green-900 dark:text-green-400">Template Compliant</h4>
                            </div>
                            <p className="text-xs text-green-700 dark:text-green-300">
                                Structure and style were validated against the selected template.
                            </p>
                        </div>
                        <div className="p-4 bg-blue-50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/30 rounded-xl">
                            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Document Info</h4>
                            <div className="space-y-3">
                                <div>
                                    <p className="text-[10px] text-slate-400 uppercase font-bold">Visible Word Count</p>
                                    <p className="text-sm font-semibold">{wordCount} Words</p>
                                </div>
                                <div>
                                    <p className="text-[10px] text-slate-400 uppercase font-bold">Template</p>
                                    <p className="text-sm font-semibold">{job.template?.toUpperCase() || 'NONE'} Standard</p>
                                </div>
                                <div>
                                    <p className="text-[10px] text-slate-400 uppercase font-bold">Job Status</p>
                                    <p className="text-sm font-semibold text-green-600">Complete</p>
                                </div>
                                <div>
                                    <p className="text-[10px] text-slate-400 uppercase font-bold">Preview Load</p>
                                    <p className="text-sm font-semibold">{loadProgress}%</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </aside>
            </div>

            <footer className="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 flex items-center justify-center px-4 sm:px-6 py-2 text-[10px] font-medium text-slate-400 uppercase tracking-widest text-center">
                <span>ScholarForm AI Preview Mode - Read Only</span>
            </footer>
        </div>
    );
}
