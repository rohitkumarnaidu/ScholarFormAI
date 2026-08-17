// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import React, { useState, useMemo, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

import * as Diff from 'diff';
import { getComparison } from '@/src/services/api';
import useJobFromUrl from '@/src/hooks/useJobFromUrl';
import { BadgeCheck, ChevronRight, FileDown, FileEdit, FileText, History, Info, Network, Pause, Play, RefreshCw, Wand2 } from 'lucide-react';

const toLineText = (value) => {
    if (typeof value === 'string') {
        return value;
    }
    if (value && typeof value === 'object' && typeof value.text === 'string') {
        return value.text;
    }
    if (value == null) {
        return '';
    }
    return String(value);
};

const getFormattedTextFromStructuredData = (structuredData) => {
    if (!structuredData || typeof structuredData !== 'object') {
        return '';
    }

    if (Array.isArray(structuredData.blocks)) {
        return structuredData.blocks
            .map((block) => toLineText(block))
            .filter((line) => line.trim() !== '')
            .join('\n\n');
    }

    if (structuredData.sections && typeof structuredData.sections === 'object') {
        return Object.values(structuredData.sections)
            .map((section) => {
                if (Array.isArray(section)) {
                    return section
                        .map((line) => toLineText(line))
                        .filter((line) => line.trim() !== '')
                        .join('\n');
                }
                return toLineText(section).trim();
            })
            .filter((sectionText) => sectionText.trim() !== '')
            .join('\n\n');
    }

    return '';
};

const buildHtmlDiffDocument = (htmlDiff, highlightsEnabled) => {
    if (typeof htmlDiff !== 'string' || htmlDiff.trim() === '') {
        return '';
    }

    const script = `
<script>
    document.addEventListener('keydown', function(e) {
        if (e.key === 'n' || e.key === 'N' || e.key === 'p' || e.key === 'P') {
            window.parent.postMessage({ type: 'diff_nav', key: e.key }, '*');
        }
    });
</script>
`;

    if (highlightsEnabled) {
        return htmlDiff.includes('</body>') ? htmlDiff.replace('</body>', `${script}</body>`) : htmlDiff + script;
    }

    const overrideStyles = `
<style>
body {
    word-wrap: break-word;
    overflow-wrap: break-word;
}
.diff_add, .diff_sub, .diff_chg {
    background: transparent !important;
}
</style>`;

    const styledHtml = htmlDiff.includes('</head>')
        ? htmlDiff.replace('</head>', `${overrideStyles}</head>`)
        : `${overrideStyles}${htmlDiff}`;

    return styledHtml.includes('</body>') ? styledHtml.replace('</body>', `${script}</body>`) : styledHtml + script;
};

export default function Compare() {
    usePageTitle('Compare Documents');
    const router = useRouter();
    const navigate = (href, options = {}) => {
        if (options?.replace) {
            router.replace(href);
            return;
        }
        router.push(href);
    };
    const { job, isLoading: isJobLoading, error: jobLoadError } = useJobFromUrl();
    const [viewMode, setViewMode] = useState('text');
    const [scrollSync, setScrollSync] = useState(true);
    const [highlights, setHighlights] = useState(true);
    const [isPaused, setIsPaused] = useState(false);
    const [diffData, setDiffData] = useState({ left: [], right: [] });
    const [structuredData, setStructuredData] = useState(null);
    const [htmlDiff, setHtmlDiff] = useState('');
    const [comparisonError, setComparisonError] = useState('');
    const [isComparisonLoading, setIsComparisonLoading] = useState(false);

    const diffRefs = React.useRef([]);
    const currentDiffIndex = React.useRef(-1);

    useEffect(() => {
        const handleNavKey = (key) => {
            if (key === 'n' || key === 'N') {
                const prev = currentDiffIndex.current;
                const iframe = document.querySelector('iframe');
                if (iframe && iframe.contentWindow) {
                    try {
                        const diffs = Array.from(iframe.contentWindow.document.querySelectorAll('.diff_add, .diff_sub, .diff_chg'));
                        if (diffs.length > 0) {
                            const next = Math.min(prev + 1, diffs.length - 1);
                            diffs[next].scrollIntoView({ behavior: 'smooth', block: 'center' });
                            currentDiffIndex.current = next;
                            return;
                        }
                    } catch (e) {
                        // ignore cors errors if any
                    }
                }
                const next = Math.min(prev + 1, diffRefs.current.length - 1);
                if (diffRefs.current[next]) {
                    diffRefs.current[next].scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                currentDiffIndex.current = next;
            } else if (key === 'p' || key === 'P') {
                const prev = currentDiffIndex.current;
                const iframe = document.querySelector('iframe');
                if (iframe && iframe.contentWindow) {
                    try {
                        const diffs = Array.from(iframe.contentWindow.document.querySelectorAll('.diff_add, .diff_sub, .diff_chg'));
                        if (diffs.length > 0) {
                            const next = Math.max(prev - 1, 0);
                            diffs[next].scrollIntoView({ behavior: 'smooth', block: 'center' });
                            currentDiffIndex.current = next;
                            return;
                        }
                    } catch (e) {
                        // ignore cors errors if any
                    }
                }
                const next = Math.max(prev - 1, 0);
                if (diffRefs.current[next]) {
                    diffRefs.current[next].scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                currentDiffIndex.current = next;
            }
        };

        const handleKeyDown = (e) => {
            if (e.target?.tagName === 'INPUT' || e.target?.tagName === 'TEXTAREA') return;
            handleNavKey(e.key);
        };
        const handleMessage = (e) => {
            if (e.data?.type === 'diff_nav') {
                handleNavKey(e.data.key);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        window.addEventListener('message', handleMessage);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('message', handleMessage);
        };
    }, []);

    const effectiveHighlights = highlights && !isPaused;

    useEffect(() => {
        if (!job?.id) {
            setDiffData({ left: [], right: [] });
            setStructuredData(null);
            setHtmlDiff('');
            setComparisonError('');
            setIsComparisonLoading(false);
            return;
        }

        let isCancelled = false;
        setIsComparisonLoading(true);
        setComparisonError('');

        getComparison(job.id)
            .then((data) => {
                if (isCancelled) {
                    return;
                }

                const nextStructuredData = data?.formatted?.structured_data || null;
                setStructuredData(nextStructuredData);

                const backendHtmlDiff = typeof data?.html_diff === 'string'
                    ? data.html_diff
                    : '';
                setHtmlDiff(backendHtmlDiff);

                if (backendHtmlDiff) {
                    setDiffData({ left: [], right: [] });
                    return;
                }

                const originalText = data?.original?.raw_text || '';
                const formattedText = getFormattedTextFromStructuredData(nextStructuredData);
                const changes = Diff.diffLines(originalText, formattedText);
                const left = [];
                const right = [];

                changes.forEach((part) => {
                    const lines = part.value.replace(/\n$/, '').split('\n');
                    if (part.added) {
                        lines.forEach((line) => {
                            right.push({ text: line, type: 'added' });
                            left.push({ text: '', type: 'empty' });
                        });
                    } else if (part.removed) {
                        lines.forEach((line) => {
                            left.push({ text: line, type: 'removed' });
                            right.push({ text: '', type: 'empty' });
                        });
                    } else {
                        lines.forEach((line) => {
                            left.push({ text: line, type: 'unchanged' });
                            right.push({ text: line, type: 'unchanged' });
                        });
                    }
                });

                setDiffData({ left, right });
            })
            .catch((error) => {
                if (isCancelled) {
                    return;
                }
                console.error('Comparison load failed:', error);
                setComparisonError(
                    typeof error?.message === 'string'
                        ? error.message
                        : 'Unable to load comparison data.'
                );
                setDiffData({ left: [], right: [] });
                setStructuredData(null);
                setHtmlDiff('');
            })
            .finally(() => {
                if (!isCancelled) {
                    setIsComparisonLoading(false);
                }
            });

        return () => {
            isCancelled = true;
        };
    }, [job?.id]);

    const diffs = useMemo(() => diffData, [diffData]);
    const htmlDiffDocument = useMemo(
        () => buildHtmlDiffDocument(htmlDiff, effectiveHighlights),
        [effectiveHighlights, htmlDiff]
    );

    const getJobRoute = (suffix, fallback) => (
        job?.id ? `/jobs/${encodeURIComponent(job.id)}/${suffix}` : fallback
    );

    if (isJobLoading && !job) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-background-light dark:bg-background-dark">
                <p className="text-slate-500 dark:text-slate-400 mb-4">Loading document details...</p>
            </div>
        );
    }

    if (jobLoadError && !job) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-background-light dark:bg-background-dark px-4 text-center">
                <p className="text-red-600 dark:text-red-400 mb-3">{jobLoadError}</p>
                <button onClick={() => navigate('/history')} className="text-primary font-bold hover:underline">
                    Return to History
                </button>
            </div>
        );
    }

    if (!job) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-background-light dark:bg-background-dark">
                <p className="text-slate-500 dark:text-slate-400 mb-4">No active document to compare.</p>
                <button onClick={() => navigate('/upload')} className="text-primary font-bold hover:underline">Return to Upload</button>
            </div>
        );
    }

    diffRefs.current = [];

    return (
        <div className="bg-background-light dark:bg-background-dark font-display text-slate-900 dark:text-slate-50 min-h-screen flex flex-col animate-in zoom-in-95 duration-300">

            <main className="flex-1 flex flex-col max-w-full max-w-[1600px] mx-auto w-full px-4 sm:px-6 lg:px-10 py-6 animate-in fade-in duration-500">
                {/* Section Header */}
                <div className="flex flex-col md:flex-row md:items-end justify-between mb-2">
                    <div>
                        <nav className="flex text-xs text-slate-500 mb-1 gap-2 items-center">
                            <Link className="hover:underline" href="/history">Documents</Link>
                            <ChevronRight className="text-[14px]" />
                            <span className="font-medium break-all">{job.originalFileName}</span>
                        </nav>
                        <div className="flex items-center gap-3">
                            <h1 className="text-slate-900 dark:text-white text-2xl font-bold leading-tight tracking-[-0.015em]">Document Comparison</h1>
                            <span className="hidden sm:inline-flex px-2 py-0.5 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                                Keyboard: N (Next) • P (Prev)
                            </span>
                        </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 mt-4 md:mt-0">
                        <button
                            onClick={() => setIsPaused(!isPaused)}
                            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-bold transition-all ${isPaused ? 'bg-amber-50 border-amber-200 text-amber-600' : 'bg-primary/5 border-primary/20 text-primary hover:bg-primary/10'}`}
                        >
                            {isPaused ? <Play className="text-[18px]" /> : <Pause className="text-[18px]" />}
                            {isPaused ? 'Resume Highlights' : 'Pause Highlights'}
                        </button>
                        <span className="text-xs font-medium text-slate-500 px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded uppercase">{job.template} Template Applied</span>
                    </div>
                </div>

                {/* Toolbar & Control Bar */}
                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm mb-6 flex flex-col gap-3 p-2">
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
                        <div className="flex flex-col sm:flex-row sm:items-center gap-2 w-full">
                            <div className="flex p-1 bg-slate-100 dark:bg-slate-800 rounded-lg sm:mr-2 overflow-x-auto">
                                <button
                                    onClick={() => setViewMode('text')}
                                    className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-bold transition-all ${viewMode === 'text' ? 'bg-white dark:bg-slate-700 shadow-sm text-primary' : 'text-slate-500 dark:text-slate-400 hover:text-primary'}`}
                                >
                                    <FileText className="text-[20px]" />
                                    Text View
                                </button>
                                {/* Only show Structured view if data exists */}
                                {structuredData && (
                                    <button
                                        onClick={() => setViewMode('structured')}
                                        className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-all ${viewMode === 'structured' ? 'bg-white dark:bg-slate-700 shadow-sm text-primary' : 'text-slate-500 dark:text-slate-400 hover:text-primary'}`}
                                    >
                                        <Network className="text-[20px]" />
                                        Structured
                                    </button>
                                )}
                            </div>
                            <div className="flex h-10 items-center justify-center rounded-lg bg-slate-100 dark:bg-slate-800 p-1">
                                <label onClick={() => setScrollSync(!scrollSync)} className={`cursor-pointer flex h-full items-center justify-center rounded-md px-3 text-xs transition-all ${scrollSync ? 'bg-white dark:bg-slate-700 shadow-sm text-primary font-bold' : 'text-slate-500 dark:text-slate-400 font-medium hover:text-primary'}`}>
                                    <RefreshCw className="text-[18px] mr-1" />
                                    <span className="truncate">Sync: {scrollSync ? 'ON' : 'OFF'}</span>
                                </label>
                                <label onClick={() => setHighlights(!highlights)} className={`cursor-pointer flex h-full items-center justify-center rounded-md px-3 text-xs transition-all ${highlights ? 'bg-white dark:bg-slate-700 shadow-sm text-primary font-bold' : 'text-slate-500 dark:text-slate-400 font-medium hover:text-primary'}`}>
                                    <Wand2 className="text-[18px] mr-1" />
                                    <span className="truncate">Highlights: {highlights ? 'ON' : 'OFF'}</span>
                                </label>
                            </div>
                        </div>

                        <div className="flex items-center gap-2 self-end sm:self-auto">
                            <button onClick={() => navigate(getJobRoute('download', '/download'))} className="p-2 text-slate-500 hover:text-primary transition-colors" title="Download">
                                <FileDown />
                            </button>
                            <button
                                onClick={() => navigate(getJobRoute('edit', '/edit'))}
                                className="flex items-center justify-center rounded-lg h-10 bg-primary text-white gap-2 px-4 sm:px-6 text-sm font-bold shadow-md hover:bg-blue-600 transition-all"
                            >
                                <FileEdit />
                                <span className="truncate">Edit Version</span>
                            </button>
                        </div>
                    </div>
                </div>

                {comparisonError && (
                    <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300">
                        {comparisonError}
                    </div>
                )}

                {isComparisonLoading && (
                    <div className="mb-4 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
                        Loading comparison data...
                    </div>
                )}

                {/* Side-by-Side Split View OR Structured Data View */}
                {viewMode === 'text' ? (
                    htmlDiffDocument ? (
                        <div className="flex-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
                            <iframe
                                title="Authoritative backend diff"
                                srcDoc={htmlDiffDocument}
                                sandbox="allow-scripts"
                                className="w-full min-h-[420px] sm:min-h-[620px] h-full border-0 bg-white dark:bg-slate-900"
                            />
                        </div>
                    ) : (
                        <div className="flex-1 flex flex-col lg:flex-row gap-4 min-h-[420px] sm:min-h-[520px] lg:min-h-[600px]">
                            {/* Left Panel: Original */}
                            <div className="flex-1 flex flex-col bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
                                <div className="px-6 py-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50 flex justify-between items-center">
                                    <h3 className="font-bold text-sm text-slate-700 dark:text-slate-200 uppercase tracking-wider flex items-center gap-2">
                                        <History className="text-[18px] text-slate-400" />
                                        Original
                                    </h3>
                                    <span className="text-[10px] text-slate-400">Source: {job.originalFileName}</span>
                                </div>
                                <div className={`flex-1 p-4 sm:p-8 overflow-y-auto custom-scrollbar leading-relaxed text-slate-800 dark:text-slate-300 font-serif text-[15px] ${scrollSync ? 'scroll-sync-left' : ''}`}>
                                    <div className="max-w-2xl mx-auto space-y-1">
                                        {diffs.left.map((line, i) => (
                                            <div key={i} className={`min-h-[24px] ${effectiveHighlights && line.type === 'removed'
                                                ? 'bg-red-100 dark:bg-red-900/30 border-l-2 border-red-500 pl-2'
                                                : line.type === 'empty' ? 'bg-slate-50/50 dark:bg-slate-800/30' : ''
                                                }`}>
                                                <p className="break-words">{line.text}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <div className="hidden lg:flex flex-col items-center justify-center px-0 text-slate-300 dark:text-slate-700">
                                <Link />
                            </div>

                            {/* Right Panel: Processed */}
                            <div className="flex-1 flex flex-col bg-white dark:bg-slate-900 border-2 border-primary rounded-xl overflow-hidden shadow-lg relative transition-all duration-300">
                                {isPaused && (
                                    <div className="absolute inset-0 bg-white/20 dark:bg-slate-900/20 backdrop-blur-[1px] z-10 flex items-center justify-center pointer-events-none">
                                        <div className="bg-white/90 dark:bg-slate-800/90 p-4 rounded-full shadow-2xl border border-amber-200 animate-in fade-in zoom-in duration-300">
                                            <Wand2 className="text-amber-500 text-6xl" />
                                        </div>
                                    </div>
                                )}
                                <div className="px-6 py-3 border-b border-slate-200 dark:border-slate-800 bg-primary/5 flex justify-between items-center">
                                    <h3 className="font-bold text-sm text-primary uppercase tracking-wider flex items-center gap-2">
                                        <BadgeCheck className="text-[18px]" />
                                        Processed ({job.template})
                                    </h3>
                                    <div className="flex gap-2">
                                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded transition-colors ${isPaused ? 'bg-amber-100 text-amber-600' : 'bg-green-100 text-green-600 dark:text-green-400'}`}>
                                            {isPaused ? 'HIGHLIGHTS PAUSED' : 'VALIDATED'}
                                        </span>
                                    </div>
                                </div>
                                <div className={`flex-1 p-4 sm:p-8 overflow-y-auto custom-scrollbar bg-white dark:bg-slate-900 ${scrollSync ? 'scroll-sync-right' : ''}`}>
                                    <div className="max-w-2xl mx-auto space-y-1">
                                        {diffs.right.map((line, i) => (
                                            <div key={i}
                                                ref={(el) => { if (el && line.type === 'added') diffRefs.current.push(el); }}
                                                className={`min-h-[24px] relative ${effectiveHighlights && line.type === 'added'
                                                    ? 'bg-green-100 dark:bg-green-900/30 border-l-2 border-green-500 pl-2'
                                                    : line.type === 'empty' ? 'bg-slate-50/50 dark:bg-slate-800/30' : ''
                                                    }`}>
                                                <p className="break-words">{line.text}</p>
                                                {effectiveHighlights && line.text.trim() !== '' && line.type !== 'empty' && (
                                                    <span className="inline-block ml-1 text-primary/30 font-serif translate-y-[2px]" title="Formatting Symbol">|</span>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )
                ) : (
                    <div className="flex-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm p-6 overflow-auto">
                        <div className="bg-slate-50 dark:bg-slate-950 p-4 rounded-lg border border-slate-100 dark:border-slate-800">
                            <h3 className="font-bold text-sm text-slate-700 dark:text-slate-200 uppercase tracking-wider mb-4 border-b border-slate-200 dark:border-slate-800 pb-2">
                                Structured Data View
                            </h3>
                            <pre className="font-mono text-xs text-slate-600 dark:text-slate-400 overflow-auto whitespace-pre-wrap break-words">
                                {JSON.stringify(structuredData, null, 2)}
                            </pre>
                        </div>
                    </div>
                )}

                {/* Diff Summary Footer */}
                <div className="mt-4 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-3 px-4 py-2 bg-slate-100 dark:bg-slate-800 rounded-lg text-xs">
                    <div className="flex flex-wrap items-center gap-4 sm:gap-6">
                        <div className="flex items-center gap-2">
                            <span className="w-3 h-3 rounded-full bg-diff-add border border-green-300"></span>
                            <span className="font-medium">Insertions</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="w-3 h-3 rounded-full bg-diff-mod border border-yellow-300"></span>
                            <span className="font-medium">Formatting Changes</span>
                        </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-3 sm:gap-4 text-slate-500">
                        <span className="flex items-center gap-1">
                            <Info className="text-[16px]" />
                            {htmlDiffDocument ? 'Backend HTML diff active' : 'Client-side diff active'}
                        </span>
                        <span className="sm:border-l border-slate-300 dark:border-slate-600 sm:pl-4 break-all">Job ID: {job.id}</span>
                    </div>
                </div>
            </main>
        </div>
    );
}


