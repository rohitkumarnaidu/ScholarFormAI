// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import { useState } from 'react';
import FeedbackForm from '@/src/components/FeedbackForm';
import { getFeedbackSummary } from '@/src/services/api';

export default function FeedbackPage() {
    usePageTitle('Feedback');
    const [summaryData, setSummaryData] = useState(null);
    const [summaryLoading, setSummaryLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('submit');
    const [documentId, setDocumentId] = useState('');

    const loadSummary = async () => {
        if (!documentId.trim()) return;
        setSummaryLoading(true);
        try {
            const data = await getFeedbackSummary(documentId.trim());
            setSummaryData(data);
        } catch (err) {
            console.error('Failed to load feedback summary:', err);
            setSummaryData(null);
        } finally {
            setSummaryLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-background-light dark:bg-background-dark animate-in fade-in duration-500">
            <main className="max-w-4xl mx-auto px-4 py-8">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                        <span className="material-symbols-outlined text-primary text-4xl">feedback</span>
                        Feedback &amp; Corrections
                    </h1>
                    <p className="text-slate-600 dark:text-slate-400 mt-2">
                        Help improve AI formatting accuracy by submitting corrections on processed documents.
                    </p>
                </div>

                {/* Tab Navigation */}
                <div className="flex gap-2 mb-6">
                    {[
                        { id: 'submit', label: 'Submit Feedback', icon: 'edit_note' },
                        { id: 'summary', label: 'View Summary', icon: 'summarize' },
                    ].map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-1.5 min-h-[44px] ${activeTab === tab.id
                                ? 'bg-primary text-white'
                                : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800'
                                }`}
                        >
                            <span className="material-symbols-outlined text-sm">{tab.icon}</span>
                            {tab.label}
                        </button>
                    ))}
                </div>

                {activeTab === 'submit' ? (
                    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
                        <FeedbackForm />
                    </div>
                ) : (
                    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Feedback Summary</h2>
                        <div className="flex gap-3 mb-6">
                            <input
                                type="text"
                                value={documentId}
                                onChange={(e) => setDocumentId(e.target.value)}
                                placeholder="Enter Document Job ID"
                                onKeyDown={(e) => e.key === 'Enter' && loadSummary()}
                                className="flex-1 p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-primary outline-none"
                            />
                            <button
                                onClick={loadSummary}
                                disabled={!documentId.trim() || summaryLoading}
                                className="px-6 py-3 bg-primary hover:bg-primary-hover text-white rounded-lg font-medium transition-colors disabled:opacity-50 shadow-md shadow-primary/20 active:scale-95 min-h-[44px]"
                            >
                                {summaryLoading ? 'Loading...' : 'Load'}
                            </button>
                        </div>

                        {summaryData ? (
                            <div className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                                        <p className="text-sm text-slate-500 dark:text-slate-400">Total Feedback</p>
                                        <p className="text-2xl font-bold text-slate-900 dark:text-white">{summaryData.total_count ?? 0}</p>
                                    </div>
                                    <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                                        <p className="text-sm text-slate-500 dark:text-slate-400">Fields Corrected</p>
                                        <p className="text-2xl font-bold text-slate-900 dark:text-white">{summaryData.fields_corrected ?? 0}</p>
                                    </div>
                                </div>
                                {summaryData.recent_feedback?.length > 0 && (
                                    <div>
                                        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">Recent Corrections</h3>
                                        <div className="space-y-2">
                                            {summaryData.recent_feedback.map((item, idx) => (
                                                <div key={idx} className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700 text-sm">
                                                    <span className="font-medium text-slate-900 dark:text-white">{item.field_name}</span>
                                                    <span className="text-slate-500 mx-2">→</span>
                                                    <span className="text-green-600 dark:text-green-400">{item.corrected_value}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ) : !summaryLoading ? (
                            <p className="text-center text-slate-500 dark:text-slate-400 py-8">
                                Enter a document ID and click Load to view feedback summary.
                            </p>
                        ) : (
                            <div className="flex items-center justify-center py-8">
                                <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
                            </div>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}
