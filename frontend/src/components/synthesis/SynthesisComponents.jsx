// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React, { memo } from 'react';
import { Download } from 'lucide-react';

export const SynthesisDownloadSection = memo(function SynthesisDownloadSection({ apiUrl, documentUrl, pdfUrl }) {
    return (
        <div className="mt-8 flex flex-wrap gap-4">
            <a
                href={`${apiUrl}${documentUrl}`}
                className="flex-1 sm:flex-none inline-flex justify-center items-center px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl shadow-sm transition active:scale-95"
                download
            >
                <Download className="w-5 h-5 mr-2" />
                Download DOCX
            </a>
            <a
                href={`${apiUrl}${pdfUrl}`}
                className="flex-1 sm:flex-none inline-flex justify-center items-center px-6 py-3 bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/40 border border-red-200 dark:border-red-900 font-medium rounded-xl transition active:scale-95"
                download
            >
                <Download className="w-5 h-5 mr-2" />
                Download PDF
            </a>
        </div>
    );
});

SynthesisDownloadSection.displayName = 'SynthesisDownloadSection';

export const SynthesisQualityPanel = memo(function SynthesisQualityPanel({ score = 92, metrics = [] }) {
    return (
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 flex flex-col items-center">
            <h4 className="font-semibold text-slate-700 dark:text-slate-300 mb-6 self-start">Confidence Score</h4>

            <div className="relative w-32 h-32 flex items-center justify-center">
                <svg className="w-full h-full transform -rotate-90">
                    <circle cx="64" cy="64" r="56" fill="none" className="stroke-slate-100 dark:stroke-slate-700" strokeWidth="12" />
                    <circle
                        cx="64" cy="64" r="56" fill="none"
                        className="stroke-green-500 transition-all duration-1000 ease-out"
                        strokeWidth="12"
                        strokeDasharray="351.8"
                        strokeDashoffset={`${351.8 - (351.8 * score) / 100}`}
                        strokeLinecap="round"
                    />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center flex-col">
                    <span className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">{score}</span>
                    <span className="text-[10px] font-bold uppercase text-slate-500 leading-none">/ 100</span>
                </div>
            </div>

            <div className="mt-6 w-full space-y-3 pt-6 border-t border-slate-100 dark:border-slate-700">
                {metrics.map((m, idx) => (
                    <div key={idx} className="flex justify-between items-center text-sm">
                        <span className="text-slate-500 dark:text-slate-400">{m.label}</span>
                        <span className="font-medium text-green-600 dark:text-green-400">{m.value}%</span>
                    </div>
                ))}
            </div>
        </div>
    );
});

SynthesisQualityPanel.displayName = 'SynthesisQualityPanel';
