// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

import ExportDialog from '@/src/components/ExportDialog';
import { useDocument } from '@/src/context/DocumentContext';
import { useAuth } from '@/src/context/AuthContext';
import { downloadExport } from '@/src/services/api';
import { isCompleted, isFailed, isProcessing } from '@/src/constants/status';
import useJobFromUrl from '@/src/hooks/useJobFromUrl';

// Feature flag: enable LaTeX export once Agent Alpha ships Module 2 Step 5
const LATEX_EXPORT_ENABLED = process.env.NEXT_PUBLIC_LATEX_EXPORT_ENABLED === 'true';

export default function Download() {
    usePageTitle('Download');
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
    const { isLoggedIn } = useAuth();
    const [isDownloading, setIsDownloading] = useState(false);
    const [downloadError, setDownloadError] = useState(null);
    const [showLoginModal, setShowLoginModal] = useState(false);
    const [showExportDialog, setShowExportDialog] = useState(false);


    const getJobRoute = (suffix, fallback) => (
        job?.id ? `/jobs/${encodeURIComponent(job.id)}/${suffix}` : fallback
    );

    const handleUploadAnother = () => {
        setJob(null);
        sessionStorage.removeItem('scholarform_currentJob');
        navigate('/upload');
    };

    if (isJobLoading && !job) {
        return (
            <div className="min-h-screen flex flex-col bg-background-light dark:bg-background-dark">
                                <main className="flex-1 flex flex-col items-center justify-center">
                    <p className="text-slate-500 dark:text-slate-400 mb-4">Loading document details...</p>
                </main>
            </div>
        );
    }

    if (jobLoadError && !job) {
        return (
            <div className="min-h-screen flex flex-col bg-background-light dark:bg-background-dark">
                                <main className="flex-1 flex flex-col items-center justify-center px-4 text-center">
                    <p className="text-red-600 dark:text-red-400 mb-3">{jobLoadError}</p>
                    <button onClick={() => navigate('/history')} className="text-primary font-bold hover:underline">
                        Return to History
                    </button>
                </main>
            </div>
        );
    }

    if (!job) {
        return (
            <div className="min-h-screen flex flex-col bg-background-light dark:bg-background-dark">
                                <main className="flex-1 flex flex-col items-center justify-center">
                    <p className="text-slate-500 dark:text-slate-400 mb-4">No completed job found.</p>
                    <button onClick={() => navigate('/upload')} className="text-primary font-bold hover:underline">Return to Upload</button>
                </main>
            </div>
        );
    }

    const normalizedJobStatus = job.status?.toUpperCase();
    const processingState = isProcessing(job.status) || ['RUNNING', 'IN_PROGRESS'].includes(normalizedJobStatus);

    // GATING: Processing State
    if (processingState) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-background-light dark:bg-background-dark">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white">Processing Document...</h2>
                    <p className="text-slate-500 dark:text-slate-400">Please wait while we format your manuscript.</p>
                    <button onClick={() => navigate('/upload')} className="text-primary font-bold hover:underline mt-4">View Progress</button>
                </div>
            </div>
        );
    }

    // GATING: Failed State
    if (isFailed(job.status)) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-background-light dark:bg-background-dark">
                <div className="p-8 max-w-md text-center">
                    <div className="w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span className="material-symbols-outlined text-3xl">error</span>
                    </div>
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">Formatting Failed</h2>
                    <p className="text-slate-500 dark:text-slate-400 mb-6">{job.error || "An unexpected error occurred during processing."}</p>
                    <button onClick={handleUploadAnother} className="bg-primary text-white px-6 py-2 rounded-lg font-bold hover:bg-blue-700 transition-colors">Try Again</button>
                </div>
            </div>
        );
    }

    if (!isCompleted(job.status)) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-background-light dark:bg-background-dark">
                <div className="p-8 max-w-md text-center">
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">Document Not Ready</h2>
                    <p className="text-slate-500 dark:text-slate-400 mb-6">
                        This manuscript is still being prepared. Return to Upload to continue.
                    </p>
                    <button onClick={() => navigate('/upload')} className="bg-primary text-white px-6 py-2 rounded-lg font-bold hover:bg-blue-700 transition-colors">
                        Return to Upload
                    </button>
                </div>
            </div>
        );
    }

    const handleDownload = async (format = 'docx') => {
        setIsDownloading(true);
        setDownloadError(null);
        try {
            // Use real backend API with job ID
            const normalizedFormat = String(format || 'docx').toLowerCase();
            const { url, cleanup } = await downloadExport(job.id, normalizedFormat);

            const link = document.createElement('a');
            link.href = url;
            const extensionMap = {
                docx: 'docx',
                pdf: 'pdf',
                tex: 'tex',
            };
            const ext = extensionMap[normalizedFormat] || 'docx';
            const baseName = job.originalFileName
                ? `Formatted_${job.originalFileName.replace(/\.[^/.]+$/, "")}`
                : 'Manuscript_Formatted';
            link.setAttribute('download', `${baseName}.${ext}`);
            document.body.appendChild(link);
            link.click();
            link.parentNode.removeChild(link);
            setTimeout(cleanup, 0);
            setShowExportDialog(false);
        } catch (error) {
            console.error("Download failed:", error);
            setDownloadError(`Download failed. The file may not be ready yet or the server is unavailable. Please try again.`);
        } finally {
            setIsDownloading(false);
        }
    };

    const handleBrowseHistory = () => {
        if (isLoggedIn) {
            navigate('/history');
        } else {
            setShowLoginModal(true);
        }
    };

    const openExportDialog = () => {
        setDownloadError(null);
        setShowExportDialog(true);
    };

    return (
        <div className="min-h-screen flex flex-col bg-background-light dark:bg-background-dark animate-in zoom-in-95 duration-300">
            
            <main className="px-4 sm:px-6 lg:px-10 flex flex-1 justify-center py-8 sm:py-12 min-h-[calc(100vh-200px)] animate-in zoom-in-95 duration-500 relative">
                <div className="layout-content-container flex flex-col max-w-[800px] flex-1">
                    {/* Success Header */}
                    <div className="flex flex-col items-center mb-8">
                        <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 shadow-sm">
                            <span className="material-symbols-outlined text-4xl">check_circle</span>
                        </div>
                        <h1 className="text-[#0d131b] dark:text-slate-50 tracking-light text-[28px] sm:text-[32px] font-bold leading-tight px-4 text-center pb-2">Formatting Complete!</h1>
                        <p className="text-[#4c6c9a] dark:text-slate-400 text-base text-center max-w-[500px]">Your manuscript has been successfully processed and is ready for submission.</p>
                    </div>

                    {/* Main Success Card */}
                    <div className="p-2 sm:p-4 @container">
                        {/* Error Message Banner */}
                        {downloadError && (
                            <div className="mb-6 p-4 rounded-xl border bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-900/30 animate-in fade-in slide-in-from-top duration-300">
                                <div className="flex items-center gap-2">
                                    <span className="material-symbols-outlined text-sm text-red-600 dark:text-red-400">error</span>
                                    <p className="text-sm font-medium text-red-900 dark:text-red-300">{downloadError}</p>
                                </div>
                            </div>
                        )}

                        <div className="flex flex-col items-stretch justify-start rounded-xl @xl:flex-row @xl:items-start shadow-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden">
                            <div className="w-full md:w-1/3 bg-slate-100 dark:bg-slate-800 flex items-center justify-center aspect-[3/4] p-8 group">
                                <div className="w-full h-full max-h-[240px] max-w-[170px] bg-white dark:bg-slate-900 shadow-md border border-slate-200 dark:border-slate-700 rounded-md p-4 flex flex-col gap-3 group-hover:scale-105 transition-transform duration-300">
                                    <div className="w-3/4 h-3 bg-slate-200 dark:bg-slate-700 rounded"></div>
                                    <div className="space-y-1.5 mt-2">
                                        <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-800 rounded"></div>
                                        <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-800 rounded"></div>
                                        <div className="w-5/6 h-1.5 bg-slate-100 dark:bg-slate-800 rounded"></div>
                                    </div>
                                    <div className="space-y-1.5 mt-2">
                                        <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-800 rounded"></div>
                                        <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-800 rounded"></div>
                                        <div className="w-4/6 h-1.5 bg-slate-100 dark:bg-slate-800 rounded"></div>
                                    </div>
                                    <div className="mt-auto self-end w-8 h-8 rounded bg-primary/10 flex items-center justify-center">
                                        <span className="material-symbols-outlined text-[16px] text-primary">auto_awesome</span>
                                    </div>
                                </div>
                            </div>
                            <div className="flex w-full grow flex-col items-stretch justify-center gap-6 py-6 sm:py-8 px-5 sm:px-6 @xl:px-8">
                                <div>
                                    <h3 className="text-[#0d131b] dark:text-slate-50 text-lg sm:text-xl font-bold leading-tight tracking-[-0.015em] mb-2 flex items-center gap-2 break-all">
                                        <span className="material-symbols-outlined text-primary">description</span>
                                        {job.originalFileName}
                                    </h3>
                                    <div className="flex flex-col gap-2">
                                        <div className="flex items-center gap-2 text-[#4c6c9a] dark:text-slate-400">
                                            <span className="material-symbols-outlined text-sm">auto_awesome</span>
                                            <p className="text-sm font-medium">{job.template?.toUpperCase()} Template Applied</p>
                                        </div>
                                        <div className="flex items-center gap-2 text-[#4c6c9a] dark:text-slate-400">
                                            <span className="material-symbols-outlined text-sm">schedule</span>
                                            <p className="text-sm">Processed on {new Date(job.timestamp).toLocaleString()}</p>
                                        </div>
                                    </div>
                                </div>
                                <div className="flex flex-col gap-3">
                                    <button
                                        onClick={openExportDialog}
                                        disabled={isDownloading}
                                        className="flex w-full cursor-pointer items-center justify-center gap-2 overflow-hidden rounded-lg h-12 px-6 bg-primary text-white text-base font-bold leading-normal transition-all hover:bg-blue-700 active:scale-[0.98] shadow-lg shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {isDownloading ? (
                                            <>
                                                <span className="material-symbols-outlined animate-spin">progress_activity</span>
                                                <span className="truncate">Downloading...</span>
                                            </>
                                        ) : (
                                            <>
                                                <span className="material-symbols-outlined">download</span>
                                                <span className="truncate">Choose Export Format</span>
                                            </>
                                        )}
                                    </button>
                                    {/* TODO: Add "tex" option after Module 2 LaTeX export is built */}
                                    {LATEX_EXPORT_ENABLED && (
                                        <button
                                            onClick={() => handleDownload('tex')}
                                            disabled={isDownloading}
                                            className="flex w-full cursor-pointer items-center justify-center gap-2 overflow-hidden rounded-lg h-12 px-6 bg-slate-800 dark:bg-slate-700 text-white text-base font-bold leading-normal transition-all hover:bg-slate-700 dark:hover:bg-slate-600 active:scale-[0.98] shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            {isDownloading ? (
                                                <>
                                                    <span className="material-symbols-outlined animate-spin">progress_activity</span>
                                                    <span className="truncate">Downloading...</span>
                                                </>
                                            ) : (
                                                <>
                                                    <span className="material-symbols-outlined">code</span>
                                                    <span className="truncate">Download as LaTeX (.tex)</span>
                                                </>
                                            )}
                                        </button>
                                    )}
                                    <p className="text-xs text-slate-500 text-center">
                                        Available formats: DOCX, PDF{LATEX_EXPORT_ENABLED ? ', TEX' : ''}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Details and Next Steps */}
                    <div className="mt-8 px-2 sm:px-4">
                        <h4 className="text-sm font-bold uppercase tracking-wider text-[#4c6c9a] dark:text-slate-500 mb-4 px-1">Processing Summary</h4>
                        <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-x-6 border-t border-slate-200 dark:border-slate-800">
                            <div className="md:col-span-2 grid grid-cols-1 md:grid-cols-[220px_1fr] gap-2 md:gap-6 border-b border-slate-200 dark:border-slate-800 py-4 items-center">
                                <p className="text-[#4c6c9a] dark:text-slate-400 text-sm font-semibold uppercase tracking-tight">Output Format</p>
                                <div className="flex items-center gap-2">
                                    <span className="material-symbols-outlined text-blue-500">article</span>
                                    <p className="text-[#0d131b] dark:text-slate-200 text-sm font-medium">DOCX, PDF</p>
                                </div>
                            </div>
                            <div className="md:col-span-2 grid grid-cols-1 md:grid-cols-[220px_1fr] gap-2 md:gap-6 border-b border-slate-200 dark:border-slate-800 py-4 items-center">
                                <p className="text-[#4c6c9a] dark:text-slate-400 text-sm font-semibold uppercase tracking-tight">Style Guide</p>
                                <p className="text-[#0d131b] dark:text-slate-200 text-sm font-medium uppercase">{job.template} Academic Standard</p>
                            </div>
                            <div className="md:col-span-2 grid grid-cols-1 md:grid-cols-[220px_1fr] gap-2 md:gap-6 border-b border-slate-200 dark:border-slate-800 py-4 items-center">
                                <p className="text-[#4c6c9a] dark:text-slate-400 text-sm font-semibold uppercase tracking-tight">AI Enhancement</p>
                                <div className="flex items-center gap-2">
                                    <span className="material-symbols-outlined text-primary text-sm">auto_awesome</span>
                                    <p className="text-[#0d131b] dark:text-slate-200 text-sm">{job.flags?.ai_used ? 'AI Analysis and Correction enabled' : 'Standard formatting only'}</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Secondary Action Button Group */}
                    <div className="mt-10 mb-16 sm:mb-20 flex justify-center">
                        <div className="flex flex-col sm:flex-row gap-4 px-4 py-3 w-full max-w-[800px] justify-center flex-wrap">
                            <button onClick={handleUploadAnother} className="flex w-full sm:w-auto min-w-[160px] cursor-pointer items-center justify-center gap-2 overflow-hidden rounded-lg h-12 px-6 bg-slate-200 dark:bg-slate-800 text-[#0d131b] dark:text-slate-50 text-sm font-bold leading-normal tracking-[0.015em] grow transition-colors hover:bg-slate-300 dark:hover:bg-slate-700">
                                <span className="material-symbols-outlined text-xl">upload_file</span>
                                <span className="truncate">Upload Another</span>
                            </button>
                            <button onClick={handleBrowseHistory} className="flex w-full sm:w-auto min-w-[160px] cursor-pointer items-center justify-center gap-2 overflow-hidden rounded-lg h-12 px-6 bg-white dark:bg-slate-900 border-2 border-slate-200 dark:border-slate-700 text-[#0d131b] dark:text-slate-50 text-sm font-bold leading-normal tracking-[0.015em] grow transition-colors hover:bg-slate-50 dark:hover:bg-slate-800">
                                <span className="material-symbols-outlined text-xl">history</span>
                                <span className="truncate">Browse Documents</span>
                            </button>
                            <button
                                onClick={() => navigate(getJobRoute('results', '/results'))}
                                className="flex w-full sm:w-auto min-w-[160px] cursor-pointer items-center justify-center gap-2 overflow-hidden rounded-lg h-12 px-6 bg-white dark:bg-slate-900 border-2 border-slate-200 dark:border-slate-700 text-[#0d131b] dark:text-slate-50 text-sm font-bold leading-normal tracking-[0.015em] grow transition-colors hover:bg-slate-50 dark:hover:bg-slate-800"
                            >
                                <span className="material-symbols-outlined text-xl">fact_check</span>
                                <span className="truncate">Validation Report</span>
                            </button>
                        </div>
                    </div>
                </div>

                {/* Login Modal */}
                {showLoginModal && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
                        <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl max-w-md w-full p-6 border border-slate-200 dark:border-slate-700 scale-100 animate-in zoom-in-95 duration-200">
                            <div className="flex flex-col items-center text-center gap-4">
                                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                                    <span className="material-symbols-outlined text-2xl">lock</span>
                                </div>
                                <div>
                                    <h3 className="text-xl font-bold text-slate-900 dark:text-white">Login Required</h3>
                                    <p className="text-slate-500 dark:text-slate-400 mt-2">
                                        Please login to view your document history and access saved manuscripts.
                                    </p>
                                </div>
                                <div className="flex gap-3 w-full mt-4">
                                    <button
                                        onClick={() => setShowLoginModal(false)}
                                        className="flex-1 px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-bold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={() => navigate('/login')}
                                        className="flex-1 px-4 py-2.5 rounded-lg bg-primary text-white font-bold hover:bg-blue-600 transition-colors"
                                    >
                                        Login
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                <ExportDialog
                    isOpen={showExportDialog}
                    defaultFormat="docx"
                    isDownloading={isDownloading}
                    error={downloadError}
                    onClose={() => setShowExportDialog(false)}
                    onDownload={handleDownload}
                />
            </main>

        </div>
    );
}



