// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

import Footer from '@/src/components/Footer';
import ValidationCard from '@/src/components/ValidationCard';
import { useDocument } from '@/src/context/DocumentContext';
import { getPreview, getJobSummary } from '@/src/services/api.documents';
import useJobFromUrl from '@/src/hooks/useJobFromUrl';
import Skeleton from '@/src/components/ui/Skeleton';

function ValidationResults() {
    const router = useRouter();
    const navigate = (href, options = {}) => {
        if (options?.replace) {
            router.replace(href);
            return;
        }
        router.push(href);
    };
    const { setJob } = useDocument();
    const { job, isLoading: isJobLoading, error: jobLoadError } = useJobFromUrl();
    const [activeTab, setActiveTab] = useState('all');
    const [resolvedResult, setResolvedResult] = useState(job?.result || null);
    const [isLoadingResult, setIsLoadingResult] = useState(false);
    const [resultLoadError, setResultLoadError] = useState('');
    const [ignoredIssues, setIgnoredIssues] = useState(new Set());
    
    const [jobSummary, setJobSummary] = useState(null);
    const [isLoadingSummary, setIsLoadingSummary] = useState(false);

    const handleIgnore = useCallback((issue) => {
        const key = `${issue.type}:${issue.title}:${issue.description}`;
        setIgnoredIssues(prev => {
            const next = new Set(prev);
            next.add(key);
            return next;
        });
    }, []);

    useEffect(() => {
        if (!job?.id) {
            setResolvedResult(null);
            setResultLoadError('');
            setIsLoadingResult(false);
            return;
        }

        let isCancelled = false;
        
        if (!job.result) {
            setIsLoadingResult(true);
            setResultLoadError('');
            getPreview(job.id, { debounceMs: 0 })
                .then((data) => {
                    if (isCancelled) return;
                    const validation = data?.validation_results || null;
                    setResolvedResult(validation);
                    if (validation) {
                        setJob((previousJob) => ({ ...(previousJob || {}), result: validation }));
                    }
                })
                .catch((error) => {
                    if (isCancelled) return;
                    console.error('Failed to load validation results:', error);
                    setResultLoadError(error?.message || 'Unable to load validation results.');
                })
                .finally(() => {
                    if (!isCancelled) setIsLoadingResult(false);
                });
        }
        
        setIsLoadingSummary(true);
        getJobSummary(job.id)
            .then(data => {
                if (isCancelled) return;
                setJobSummary(data);
            })
            .catch(error => console.error('Failed to load job summary:', error))
            .finally(() => {
                if (!isCancelled) setIsLoadingSummary(false);
            });

        return () => { isCancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [job?.id]);

    // Gate: loading job from URL
    if (isJobLoading && !job) {
        return (
            <div className="min-h-screen flex flex-col bg-background-light dark:bg-background-dark">
                <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 sm:py-12 animate-in fade-in duration-300">
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 mb-8">
                        <div className="space-y-3">
                            <Skeleton className="h-10 w-64 md:w-80" />
                            <Skeleton className="h-5 w-48 md:w-96" />
                        </div>
                        <Skeleton className="h-10 w-32" />
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                        <Skeleton className="h-[120px] w-full" />
                        <Skeleton className="h-[120px] w-full" />
                        <Skeleton className="h-[120px] w-full" />
                        <Skeleton className="h-[120px] w-full" />
                    </div>
                    <Skeleton className="h-[400px] w-full" />
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
            <div className="min-h-screen flex flex-col bg-background-light dark:bg-background-dark">
                <main className="flex-1 flex flex-col items-center justify-center p-6 text-center">
                    <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center mb-4">
                        <span className="material-symbols-outlined text-slate-400 text-3xl">find_in_page</span>
                    </div>
                    <p className="text-slate-500 dark:text-slate-400 mb-4">No validation results found. Your document may not have been processed yet.</p>
                    <button onClick={() => navigate('/upload')} className="text-primary font-bold hover:underline">Return to Upload</button>
                </main>
                <Footer variant="app" />
            </div>
        );
    }

    if (isLoadingResult && !resolvedResult) {
        return (
            <div className="min-h-screen flex flex-col bg-background-light dark:bg-background-dark">
                <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 sm:py-12 animate-in fade-in duration-300">
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 mb-8">
                        <div>
                            <h1 className="text-3xl sm:text-4xl font-black text-slate-900 dark:text-white mb-2 tracking-tight">
                                Validation Results
                            </h1>
                            <p className="text-slate-500 dark:text-slate-400 text-lg break-all">
                                Review your formatting score and applied fixes for {job.originalFileName || 'your document'}
                            </p>
                        </div>
                        <Skeleton className="h-10 w-32" />
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                        <Skeleton className="h-[120px] w-full" />
                        <Skeleton className="h-[120px] w-full" />
                        <Skeleton className="h-[120px] w-full" />
                        <Skeleton className="h-[120px] w-full" />
                    </div>
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8">
                        <div className="lg:col-span-1 flex flex-col gap-6">
                            <Skeleton className="h-[300px] w-full" />
                            <Skeleton className="h-[200px] w-full" />
                        </div>
                        <div className="lg:col-span-2 space-y-6">
                            <Skeleton className="h-[400px] w-full" />
                        </div>
                    </div>
                </main>
                <Footer variant="app" />
            </div>
        );
    }

    if (!resolvedResult) {
        return (
            <div className="min-h-screen flex flex-col bg-background-light dark:bg-background-dark">
                <main className="flex-1 flex flex-col items-center justify-center p-6 text-center">
                    <div className="w-16 h-16 bg-red-50 dark:bg-red-900/20 text-red-500 rounded-full flex items-center justify-center mb-4">
                        <span className="material-symbols-outlined text-3xl">error</span>
                    </div>
                    <p className="text-slate-500 dark:text-slate-400 mb-2">Failed to load validation results.</p>
                    {resultLoadError ? <p className="text-red-500 text-sm mb-4">{resultLoadError}</p> : null}
                    <button onClick={() => navigate('/upload')} className="text-primary font-bold hover:underline">Return to Upload</button>
                </main>
                <Footer variant="app" />
            </div>
        );
    }

    const { errors = [], warnings = [], advisories = [] } = resolvedResult || {};
    const totalIssues = errors.length + warnings.length + advisories.length;

    const parseIssue = (issue, type) => {
        if (typeof issue === 'object') {
            return { ...issue, type };
        }

        let title = 'Formatting Issue';
        const description = issue;
        const lower = issue.toLowerCase();

        if (lower.includes('missing required section') || lower.includes('order')) {
            title = 'Structure Violation';
        } else if (lower.includes('figure') || lower.includes('caption')) {
            title = 'Figure/Table Issue';
        } else if (lower.includes('reference') || lower.includes('citation')) {
            title = 'Citation Issue';
        } else if (lower.includes('font') || lower.includes('spacing') || lower.includes('margin')) {
            title = 'Style & Layout';
        }

        return {
            type,
            title,
            description,
            severity: type === 'error' ? 'Critical' : type === 'warning' ? 'Minor' : 'Info',
        };
    };

    const filteredIssues = () => {
        let issues = [];

        if (activeTab === 'all' || activeTab === 'errors') {
            issues = [...issues, ...errors.map((e) => parseIssue(e, 'error'))];
        }
        if (activeTab === 'all' || activeTab === 'warnings') {
            issues = [...issues, ...warnings.map((w) => parseIssue(w, 'warning'))];
        }
        if (activeTab === 'all' || activeTab === 'advisories') {
            issues = [...issues, ...advisories.map((a) => parseIssue(a, 'advisory'))];
        }
        return issues.filter(issue => {
            const key = `${issue.type}:${issue.title}:${issue.description}`;
            return !ignoredIssues.has(key);
        });
    };

    return (
        <>

            <main className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <nav className="flex flex-wrap items-center gap-2 text-sm font-medium text-slate-500 dark:text-slate-400">
                    <Link href="/history" className="hover:text-primary transition-colors">My Files</Link>
                    <span className="material-symbols-outlined text-xs">chevron_right</span>
                    <span className="text-slate-900 dark:text-slate-100">Validation Results</span>
                </nav>

                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div className="space-y-2">
                        <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-slate-900 dark:text-white">Validation Results Analysis</h1>
                        <p className="text-slate-500 dark:text-slate-400 text-base sm:text-lg break-words">
                            Diagnostic report for <span className="font-mono text-slate-700 dark:text-slate-200 break-all">{job.originalFileName}</span>
                        </p>
                    </div>
                    <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
                        <button onClick={() => navigate('/upload')} className="flex w-full sm:w-auto items-center justify-center rounded-lg h-11 px-6 bg-slate-200 dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm font-bold hover:bg-slate-300 dark:hover:bg-slate-700 transition-colors">
                            <span className="material-symbols-outlined mr-2 text-lg">upload_file</span>
                            Re-upload
                        </button>
                        <button onClick={() => navigate('/download')} className="flex w-full sm:w-auto items-center justify-center rounded-lg h-11 px-6 bg-primary text-white text-sm font-bold shadow-lg shadow-primary/20 hover:bg-primary/90 transition-all">
                            <span className="material-symbols-outlined mr-2 text-lg">download</span>
                            Verify & Download
                        </button>
                    </div>
                </div>

                <div className="bg-white dark:bg-slate-900 rounded-xl p-6 shadow-sm border border-slate-200 dark:border-slate-800 flex flex-col lg:flex-row gap-6 items-start lg:items-center">
                    <div className="flex-1 space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div className="space-y-1">
                                <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Filename</p>
                                <p className="text-slate-900 dark:text-slate-100 font-semibold break-all">{job.originalFileName}</p>
                            </div>
                            <div className="space-y-1">
                                <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Formatting Template</p>
                                <p className="text-slate-900 dark:text-slate-100 font-semibold uppercase">{job.template}</p>
                            </div>
                            <div className="space-y-1">
                                <p className="text-xs font-bold uppercase tracking-wider text-slate-400">AI Enhancement</p>
                                <div className="flex items-center gap-2 flex-wrap">
                                    <p className="text-slate-900 dark:text-slate-100 font-semibold">{job.flags?.ai_used ? 'Enabled' : 'Disabled'}</p>
                                    {/* LLM Provider Badge */}
                                    {job.llm_provider && (() => {
                                        const providerMap = {
                                            groq: { label: 'Groq', cls: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300 ring-green-200 dark:ring-green-800' },
                                            nvidia: { label: 'NVIDIA', cls: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 ring-blue-200 dark:ring-blue-800' },
                                            ollama: { label: 'Ollama', cls: 'bg-slate-100 text-slate-700 dark:bg-slate-700/60 dark:text-slate-300 ring-slate-200 dark:ring-slate-600' },
                                        };
                                        const key = job.llm_provider.toLowerCase();
                                        const provider = providerMap[key] || { label: job.llm_provider, cls: 'bg-slate-100 text-slate-700 dark:bg-slate-700/60 dark:text-slate-300 ring-slate-200 dark:ring-slate-600' };
                                        return (
                                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold ring-1 ${provider.cls}`}>
                                                <span className="material-symbols-outlined text-[11px]">smart_toy</span>
                                                {provider.label}
                                            </span>
                                        );
                                    })()}
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="w-full lg:w-48 h-28 bg-slate-100 dark:bg-slate-800 rounded-lg flex flex-col items-center justify-center text-slate-400 border border-dashed border-slate-300 dark:border-slate-700 overflow-hidden relative group">
                        <span className="material-symbols-outlined text-3xl group-hover:scale-110 transition-transform">description</span>
                        <span className="text-[10px] mt-2 font-mono">DOCUMENT PREVIEW</span>
                        <div className="absolute inset-0 bg-primary/10 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                            <button onClick={() => navigate('/compare')} className="text-[10px] font-bold bg-white text-primary px-3 py-1 rounded shadow-sm">VIEW DIFF</button>
                        </div>
                    </div>
                </div>

                {/* ── Quality Score Panel ── */}
                {isLoadingSummary ? (
                    <div className="bg-white dark:bg-slate-900 rounded-xl p-6 shadow-sm border border-slate-200 dark:border-slate-800 flex items-center justify-center min-h-[160px]">
                        <div className="flex flex-col items-center">
                            <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mb-3"></div>
                            <p className="text-sm text-slate-500 dark:text-slate-400">Loading quality analysis...</p>
                        </div>
                    </div>
                ) : jobSummary ? (
                    (() => {
                        const overall = jobSummary.overall_score ?? null;
                        const overallColor =
                            overall === null ? 'text-slate-500'
                            : overall >= 80 ? 'text-green-600 dark:text-green-400'
                            : overall >= 50 ? 'text-amber-600 dark:text-amber-400'
                            : 'text-red-600 dark:text-red-400';
                        const overallBg =
                            overall === null ? 'text-slate-200 dark:text-slate-700'
                            : overall >= 80 ? 'text-green-500'
                            : overall >= 50 ? 'text-amber-500'
                            : 'text-red-500';
                        return (
                            <div className="bg-white dark:bg-slate-900 rounded-xl p-6 shadow-sm border border-slate-200 dark:border-slate-800 space-y-5">
                                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
                                    <h2 className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                        <span className="material-symbols-outlined text-primary">analytics</span>
                                        Document Quality Analysis
                                    </h2>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-start">
                                    {/* Overall Score Ring */}
                                    <div className="flex flex-col items-center justify-center p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-100 dark:border-slate-700/50">
                                        <div className="relative w-24 h-24 mb-2">
                                            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                                                <path className="text-slate-200 dark:text-slate-700" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3" />
                                                <path className={overallBg} strokeDasharray={`${overall !== null ? overall : 0}, 100`} d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                                            </svg>
                                            <div className="absolute inset-0 flex flex-col items-center justify-center">
                                                <span className={`text-2xl font-black ${overallColor} leading-none`}>{overall !== null ? overall : '-'}</span>
                                                <span className="text-[10px] font-bold text-slate-400 mt-1 uppercase tracking-widest">Score</span>
                                            </div>
                                        </div>
                                        <span className={`text-xs font-bold uppercase tracking-wider ${overallColor}`}>
                                            {overall === null ? 'Unknown' : overall >= 80 ? 'Excellent' : overall >= 50 ? 'Fair' : 'Needs Work'}
                                        </span>
                                    </div>
                                    
                                    <div className="col-span-1 md:col-span-3 grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        {/* Template Compliance */}
                                        {(() => {
                                            const tc = jobSummary.template_compliance ?? null;
                                            const tcColor = tc === null ? 'bg-slate-400' : tc >= 80 ? 'bg-green-500' : tc >= 50 ? 'bg-amber-500' : 'bg-red-500';
                                            const tcText = tc === null ? 'text-slate-500' : tc >= 80 ? 'text-green-600 dark:text-green-400' : tc >= 50 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400';
                                            return (
                                                <div className="space-y-2 bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-100 dark:border-slate-700/50">
                                                    <div className="flex justify-between text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                                        <span>Template Compliance</span>
                                                        <span className={tcText}>{tc !== null ? `${tc}%` : '—'}</span>
                                                    </div>
                                                    <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                                                        <div className={`h-full rounded-full ${tcColor} transition-all duration-700`} style={{ width: `${tc ?? 0}%` }} />
                                                    </div>
                                                </div>
                                            );
                                        })()}
                                        
                                        {/* Content Quality */}
                                        {(() => {
                                            const cc = jobSummary.content_quality ?? jobSummary.content_completeness ?? null;
                                            const ccColor = cc === null ? 'bg-slate-400' : cc >= 80 ? 'bg-green-500' : cc >= 50 ? 'bg-amber-500' : 'bg-red-500';
                                            const ccText = cc === null ? 'text-slate-500' : cc >= 80 ? 'text-green-600 dark:text-green-400' : cc >= 50 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400';
                                            return (
                                                <div className="space-y-2 bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-100 dark:border-slate-700/50">
                                                    <div className="flex justify-between text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                                        <span>Content Quality</span>
                                                        <span className={ccText}>{cc !== null ? `${cc}%` : '—'}</span>
                                                    </div>
                                                    <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                                                        <div className={`h-full rounded-full ${ccColor} transition-all duration-700`} style={{ width: `${cc ?? 0}%` }} />
                                                    </div>
                                                </div>
                                            );
                                        })()}
                                        
                                        {/* Citation Count Badge */}
                                        <div className="flex items-center gap-3 bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-100 dark:border-slate-700/50">
                                            <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 flex items-center justify-center">
                                                <span className="material-symbols-outlined text-[18px]">format_quote</span>
                                            </div>
                                            <div>
                                                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Citations Detected</p>
                                                <p className="text-xl font-black text-slate-900 dark:text-white leading-none mt-1">{jobSummary.citation_count ?? '—'}</p>
                                            </div>
                                        </div>
                                        
                                        {/* Missing Sections */}
                                        <div className="flex flex-col justify-center bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-100 dark:border-slate-700/50">
                                            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">Missing Required Sections</p>
                                            {jobSummary.missing_sections && jobSummary.missing_sections.length > 0 ? (
                                                <div className="flex flex-wrap gap-1.5">
                                                    {jobSummary.missing_sections.map((sec, idx) => (
                                                        <span key={idx} className="px-2 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-[10px] font-bold rounded">
                                                            {sec}
                                                        </span>
                                                    ))}
                                                </div>
                                            ) : (
                                                <div className="flex items-center gap-1 text-green-600 dark:text-green-400 text-xs font-bold">
                                                    <span className="material-symbols-outlined text-[14px]">check_circle</span>
                                                    None detected
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        );
                    })()
                ) : (
                    <div className="bg-slate-50 dark:bg-slate-800/50 border border-dashed border-slate-300 dark:border-slate-700 rounded-xl p-6 flex items-center gap-4">
                        <span className="material-symbols-outlined text-slate-400 text-3xl">analytics</span>
                        <div>
                            <p className="font-semibold text-slate-700 dark:text-slate-300">Quality analysis not available</p>
                            <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">Quality scores (template compliance, content quality &amp; citations) will appear here when the backend provides them.</p>
                        </div>
                    </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="bg-red-50 dark:bg-red-950/20 border border-red-100 dark:border-red-900/30 rounded-xl p-6 flex flex-col">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-red-700 dark:text-red-400 font-bold text-sm">Errors</span>
                            <span className="material-symbols-outlined text-red-600 dark:text-red-400">error</span>
                        </div>
                        <p className="text-3xl sm:text-4xl font-black text-red-700 dark:text-red-400">{errors.length}</p>
                        <p className="text-xs text-red-600/70 dark:text-red-400/50 mt-1 font-medium italic">{errors.length > 0 ? 'Require immediate attention' : 'No critical issues'}</p>
                    </div>
                    <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-100 dark:border-amber-900/30 rounded-xl p-6 flex flex-col">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-amber-700 dark:text-amber-400 font-bold text-sm">Warnings</span>
                            <span className="material-symbols-outlined text-amber-600 dark:text-amber-400">warning</span>
                        </div>
                        <p className="text-3xl sm:text-4xl font-black text-amber-700 dark:text-amber-400">{warnings.length}</p>
                        <p className="text-xs text-amber-600/70 dark:text-amber-400/50 mt-1 font-medium italic">Formatting improvements</p>
                    </div>
                    <div className="bg-primary/5 dark:bg-primary/10 border border-primary/10 dark:border-primary/20 rounded-xl p-6 flex flex-col">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-primary font-bold text-sm">AI Advisory</span>
                            <span className="material-symbols-outlined text-primary">auto_awesome</span>
                        </div>
                        <p className="text-3xl sm:text-4xl font-black text-primary">{advisories.length}</p>
                        <p className="text-xs text-primary/70 mt-1 font-medium italic">Insights and optimizations</p>
                    </div>
                </div>

                <div className="space-y-6">
                    <div className="flex items-center border-b border-slate-200 dark:border-slate-800 overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0">
                        <button
                            onClick={() => setActiveTab('all')}
                            className={`px-6 py-3 font-bold text-sm transition-colors border-b-2 whitespace-nowrap ${activeTab === 'all'
                                ? 'border-primary text-primary'
                                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'}`}
                        >
                            All Issues ({totalIssues})
                        </button>
                        <button
                            onClick={() => setActiveTab('errors')}
                            className={`px-6 py-3 font-bold text-sm transition-colors border-b-2 whitespace-nowrap ${activeTab === 'errors'
                                ? 'border-red-600 text-red-600 dark:text-red-400'
                                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'}`}
                        >
                            Errors ({errors.length})
                        </button>
                        <button
                            onClick={() => setActiveTab('warnings')}
                            className={`px-6 py-3 font-bold text-sm transition-colors border-b-2 whitespace-nowrap ${activeTab === 'warnings'
                                ? 'border-amber-600 text-amber-600 dark:text-amber-400'
                                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'}`}
                        >
                            Warnings ({warnings.length})
                        </button>
                        <button
                            onClick={() => setActiveTab('advisories')}
                            className={`px-6 py-3 font-bold text-sm transition-colors border-b-2 whitespace-nowrap ${activeTab === 'advisories'
                                ? 'border-primary text-primary'
                                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'}`}
                        >
                            Advisories ({advisories.length})
                        </button>
                    </div>

                    <div className="space-y-4 min-h-[200px]">
                        {filteredIssues().length > 0 ? filteredIssues().map((issue, idx) => (
                            <ValidationCard
                                key={idx}
                                type={issue.type || (activeTab === 'errors' ? 'error' : activeTab === 'warnings' ? 'warning' : 'info')}
                                title={issue.title || issue.issue || 'Formatting Issue'}
                                description={issue.description || issue.message || issue}
                                badge={issue.severity || (activeTab === 'errors' ? 'Critical' : 'Notice')}
                                onIgnore={handleIgnore}
                            />
                        )) : (
                            <div className="flex flex-col items-center justify-center py-16 px-4">
                                <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400">
                                    <span className="material-symbols-outlined text-5xl">check_circle</span>
                                </div>
                                <h3 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">No validation issues found</h3>
                                <p className="text-slate-500 dark:text-slate-400 text-center max-w-md">
                                    {activeTab === 'all'
                                        ? 'Your manuscript meets all formatting requirements and is ready for submission.'
                                        : `No ${activeTab} detected in your manuscript.`}
                                </p>
                            </div>
                        )}
                    </div>
                </div>

                <div className="flex flex-col sm:flex-row gap-4 pt-8">
                    <button onClick={() => navigate('/compare')} className="flex-1 flex items-center justify-center gap-2 py-4 bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 rounded-xl font-bold text-slate-700 dark:text-slate-200 hover:border-primary transition-all shadow-sm">
                        <span className="material-symbols-outlined">compare_arrows</span>
                        Compare with Original
                    </button>
                    <button onClick={() => navigate('/edit')} className="flex-1 flex items-center justify-center gap-2 py-4 bg-primary text-white rounded-xl font-bold hover:bg-blue-700 transition-all shadow-lg shadow-primary/20">
                        <span className="material-symbols-outlined">edit_note</span>
                        Edit Processed Version
                    </button>
                </div>

                <Footer variant="app" />
            </main>
        </>
    );
}

export default ValidationResults;

