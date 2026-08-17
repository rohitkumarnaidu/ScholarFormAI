// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import { useState, useCallback, useEffect } from 'react';
import { useAuth } from '@/src/context/AuthContext';
import { canAccess } from '@/src/lib/planTier';
import UpgradeModal from '@/src/components/UpgradeModal';

import BatchUploadPanel from '@/src/components/BatchUploadPanel';
import { uploadDocumentWithProgress } from '@/src/services/api';
import { Download, FileUp, Palette, Rocket } from 'lucide-react';

export default function BatchUpload() {
    usePageTitle('Batch Upload');
    const [files, setFiles] = useState([]);
    const [template, setTemplate] = useState('IEEE');
    const [processing, setProcessing] = useState(false);
    
    const { user } = useAuth();
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);

    useEffect(() => {
        if (user && !canAccess(user, 'batch_upload')) {
            setShowUpgradeModal(true);
        }
    }, [user]);

    const handleFilesSelected = useCallback((selectedFiles) => {
        const newFiles = selectedFiles.map((f) => ({
            file: f,
            id: `${f.name}-${Date.now()}-${Math.random().toString(36).slice(2)}`,
            status: 'pending',
            progress: 0,
            jobId: null,
            error: null,
        }));
        setFiles((prev) => [...prev, ...newFiles]);
    }, []);

    const removeFile = useCallback((id) => {
        setFiles((prev) => prev.filter((f) => f.id !== id));
    }, []);

    const updateFile = useCallback((id, updates) => {
        setFiles((prev) => prev.map((f) => (f.id === id ? { ...f, ...updates } : f)));
    }, []);

    const retryFile = useCallback((id) => {
        updateFile(id, { status: 'pending', error: null, progress: 0 });
    }, [updateFile]);

    const processAll = async () => {
        const pending = files.filter((f) => f.status === 'pending');
        if (pending.length === 0) return;

        setProcessing(true);

        // Run all uploads concurrently — failure in one doesn't affect others
        await Promise.allSettled(
            pending.map(async (entry) => {
                updateFile(entry.id, { status: 'uploading', progress: 0 });
                try {
                    const result = await uploadDocumentWithProgress(
                        entry.file,
                        template,
                        {},
                        {
                            onProgress: (percent) => updateFile(entry.id, { progress: percent }),
                        }
                    );
                    updateFile(entry.id, {
                        status: 'done',
                        progress: 100,
                        jobId: result?.job_id || null,
                    });
                } catch (err) {
                    updateFile(entry.id, {
                        status: 'error',
                        error: err.message || 'Upload failed',
                    });
                }
            })
        );

        setProcessing(false);
    };

    const completedCount = files.filter((f) => f.status === 'done').length;
    const errorCount = files.filter((f) => f.status === 'error').length;

    return (
        <div className="min-h-screen bg-background-light dark:bg-background-dark flex flex-col">
            <UpgradeModal 
                isOpen={showUpgradeModal} 
                onClose={() => setShowUpgradeModal(false)} 
                title="Upgrade to Pro for Batch Upload" 
            />
            
            {!canAccess(user, 'batch_upload') ? (
                <main className="flex-1 max-w-4xl mx-auto px-4 py-8 w-full flex flex-col items-center justify-center">
                    <div className="text-center">
                        <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-200 mb-4">Batch Upload is a Pro Feature</h2>
                        <p className="text-slate-600 dark:text-slate-400 mb-6">Upgrade to our Pro plan to process multiple documents simultaneously and save time.</p>
                        <button onClick={() => setShowUpgradeModal(true)} className="px-6 py-3 bg-primary text-white font-medium rounded-xl">
                            View Plans
                        </button>
                    </div>
                </main>
            ) : (
                <main className="flex-1 max-w-4xl mx-auto px-4 py-8 w-full">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                        <FileUp className="text-primary text-4xl" />
                        Batch Upload
                    </h1>
                    <p className="text-slate-600 dark:text-slate-400 mt-2">
                        Upload and process multiple documents at once with the same template settings.
                    </p>
                </div>

                {/* Template Selection */}
                <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm mb-6">
                    <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                        <Palette className="text-primary" />
                        Template
                    </h2>
                    <select
                        value={template}
                        onChange={(e) => setTemplate(e.target.value)}
                        disabled={processing}
                        className="w-full md:w-auto p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-primary outline-none"
                    >
                        <option value="IEEE">IEEE</option>
                        <option value="Springer">Springer</option>
                        <option value="APA">APA</option>
                        <option value="Nature">Nature</option>
                        <option value="Vancouver">Vancouver</option>
                        <option value="none">None (Auto-detect)</option>
                    </select>
                </div>

                {/* Upload Panel */}
                <BatchUploadPanel
                    files={files}
                    onFilesSelected={handleFilesSelected}
                    onRemove={removeFile}
                    onRetry={retryFile}
                    disabled={processing}
                />

                {/* Action Bar */}
                {files.length > 0 && (
                    <div className="mt-6 flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 shadow-sm">
                        <div className="text-sm text-slate-600 dark:text-slate-400">
                            {files.length} file{files.length !== 1 ? 's' : ''}
                            {completedCount > 0 && (
                                <span className="text-green-600 dark:text-green-400 ml-2">• {completedCount} done</span>
                            )}
                            {errorCount > 0 && (
                                <span className="text-red-600 dark:text-red-400 ml-2">• {errorCount} failed</span>
                            )}
                        </div>
                        <div className="flex items-center gap-3">
                            {/* Download All — shows when at least one file completed */}
                            {completedCount > 0 && !processing && (
                                <button
                                    onClick={() => {
                                        files
                                            .filter((f) => f.status === 'done' && f.jobId)
                                            .forEach((f) => {
                                                const url = `/jobs/${encodeURIComponent(f.jobId)}/download`;
                                                window.open(url, '_blank', 'noopener,noreferrer');
                                            });
                                    }}
                                    className="px-5 py-2.5 bg-green-600 hover:bg-green-700 text-white font-bold rounded-xl shadow-lg shadow-green-600/25 transition-all flex items-center gap-2"
                                >
                                    <Download />
                                    Download All ({completedCount})
                                </button>
                            )}
                            <button
                                onClick={processAll}
                                disabled={processing || files.filter((f) => f.status === 'pending').length === 0}
                                className="px-6 py-3 bg-primary hover:bg-blue-700 text-white font-bold rounded-xl shadow-lg shadow-primary/25 transition-all disabled:opacity-50 flex items-center gap-2"
                            >
                                {processing ? (
                                    <>
                                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                        Processing...
                                    </>
                                ) : (
                                    <>
                                        <Rocket />
                                        Process All ({files.filter((f) => f.status === 'pending').length})
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                )}
            </main>
            )}
        </div>
    );
}
