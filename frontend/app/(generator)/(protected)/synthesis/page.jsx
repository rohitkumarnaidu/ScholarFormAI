// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import React, { useEffect, useState, Suspense, useMemo } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { FileText, ArrowLeft, MessageSquare, AlertCircle } from 'lucide-react';
import { getSynthesisSession } from '@/src/services/api.synthesis';

import { 
    SynthesisDownloadSection, 
    SynthesisQualityPanel 
} from '@/src/components/synthesis/SynthesisComponents';

const QUALITY_METRICS = [
    { label: 'Citation Alignment', value: 95 },
    { label: 'Section Continuity', value: 88 },
    { label: 'Formatting Match', value: 93 },
];

function SynthesisResultContent() {
    const searchParams = useSearchParams();
    const sessionId = searchParams.get('session');
    const router = useRouter();

    const [sessionData, setSessionData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!sessionId) {
            setError('No session ID provided.');
            setLoading(false);
            return;
        }

        getSynthesisSession(sessionId)
            .then(res => {
                setSessionData(res);
                setLoading(false);
            })
            .catch(() => {
                setError('Failed to load session results.');
                setLoading(false);
            });
    }, [sessionId]);

    const urls = useMemo(() => {
        if (!sessionData?.file_id) return { docx: null, pdf: null };
        return {
            docx: `/api/v1/generator/sessions/${sessionId}/export/docx`,
            pdf: `/api/v1/generator/sessions/${sessionId}/export/pdf`
        };
    }, [sessionData, sessionId]);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    if (loading) return <LoadingSpinner />;

    if (error || !sessionData) {
        return (
            <div className="max-w-3xl mx-auto my-12 p-6 bg-red-50 text-red-600 dark:bg-red-900/20 rounded-xl flex items-center">
                <AlertCircle className="w-6 h-6 mr-3" />
                <h2 className="text-xl font-medium">{error || "Could not fetch session."}</h2>
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto px-4 py-12 animate-in fade-in duration-500">
            <button
                onClick={() => router.back()}
                className="flex items-center text-slate-500 hover:text-indigo-600 dark:hover:text-indigo-400 font-medium mb-8 transition group"
            >
                <ArrowLeft className="w-4 h-4 mr-2 group-hover:-translate-x-1 transition-transform" /> Back
            </button>

            <div className="grid grid-cols-1 lg:grid-cols-1 md:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-6">
                    <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-8">
                        <div className="flex items-start justify-between">
                            <div>
                                <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white mb-2">Synthesized Manuscript</h1>
                                <p className="text-slate-500 dark:text-slate-400">Template: <strong>{sessionData.target_template || 'Default'}</strong></p>
                            </div>
                            <div className="h-16 w-16 bg-indigo-50 dark:bg-indigo-900/30 rounded-2xl flex items-center justify-center text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-800">
                                <FileText className="w-8 h-8" />
                            </div>
                        </div>

                        <SynthesisDownloadSection 
                            apiUrl={apiUrl} 
                            documentUrl={urls.docx} 
                            pdfUrl={urls.pdf} 
                        />
                    </div>

                    <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-8 flex items-center justify-between">
                        <div className="flex items-center">
                            <div className="p-3 bg-indigo-100 text-indigo-600 dark:bg-indigo-900/40 rounded-full mr-4">
                                <MessageSquare className="w-6 h-6" />
                            </div>
                            <div>
                                <h3 className="font-semibold text-slate-900 dark:text-white text-lg">Follow-up Questions?</h3>
                                <p className="text-slate-500 dark:text-slate-400 text-sm">Review your cross-document Q&A session.</p>
                            </div>
                        </div>
                        <button
                            onClick={() => router.push('/multi-upload')}
                            className="px-5 py-2 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-600 hover:bg-slate-50 rounded-lg text-sm font-medium transition active:scale-95"
                        >
                            New Synthesis
                        </button>
                    </div>
                </div>

                <div className="lg:col-span-1">
                    <SynthesisQualityPanel score={92} metrics={QUALITY_METRICS} />
                </div>
            </div>
        </div>
    );
}

function LoadingSpinner() {
    return (
        <div className="flex justify-center items-center h-[60vh]">
            <div className="relative">
                <div className="w-12 h-12 border-4 border-slate-200 dark:border-slate-800 rounded-full"></div>
                <div className="absolute top-0 left-0 w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
            </div>
        </div>
    );
}

export default function SynthesisResultPage() {
    return (
        <Suspense fallback={<LoadingSpinner />}>
            <SynthesisResultContent />
        </Suspense>
    );
}
