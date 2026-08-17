// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

export default function GenerateStep({ status, progress, stage, message, error, outline, onDownload, onReset }) {
    const stages = [
        { key: 'generating', label: 'Generating content', icon: 'auto_awesome' },
        { key: 'structuring', label: 'Structuring blocks', icon: 'schema' },
        { key: 'formatting', label: 'Applying template', icon: 'format_paint' },
        { key: 'exporting', label: 'Exporting document', icon: 'file_download' },
        { key: 'done', label: 'Document ready', icon: 'check_circle' },
    ];

    const activeIndex = stages.findIndex((entry) => entry.key === stage);

    return (
        <div className="space-y-8">
            <div>
                <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-1">
                    {status === 'done' ? 'Document Ready!' : status === 'failed' ? 'Generation Failed' : 'Generating Your Document...'}
                </h2>
                <p className="text-slate-500 dark:text-slate-400 text-sm">{message || 'AI is working on your document...'}</p>
            </div>

            {status !== 'failed' && (
                <div>
                    <div className="flex justify-between text-xs text-slate-500 mb-2">
                        <span>{stage ? stage.charAt(0).toUpperCase() + stage.slice(1) : 'Queued'}</span>
                        <span>{progress}%</span>
                    </div>
                    <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-blue-500 to-violet-500 rounded-full transition-all duration-500" style={{ width: `${progress}%` }} />
                    </div>
                </div>
            )}

            <div className="space-y-3">
                {stages.map((entry, index) => {
                    const isDone = index < activeIndex || status === 'done';
                    const isActive = entry.key === stage && status !== 'done';

                    return (
                        <div key={entry.key} className={`flex items-center gap-3 p-3 rounded-xl transition ${isDone ? 'bg-green-500/10' : isActive ? 'bg-primary/10' : 'bg-white/3'}`}>
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${isDone ? 'bg-green-500' : isActive ? 'bg-primary' : 'bg-white/10'}`}>
                                <span className="material-symbols-outlined text-white text-sm">{isDone ? 'check' : entry.icon}</span>
                            </div>
                            <span className={`text-sm ${isDone ? 'text-green-300' : isActive ? 'text-blue-300' : 'text-slate-600'}`}>{entry.label}</span>
                            {isActive && <span className="ml-auto text-xs text-primary-light animate-pulse">In progress...</span>}
                        </div>
                    );
                })}
            </div>

            {outline?.length > 0 && (
                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-3">Generated Structure Preview</h3>
                    <ul className="space-y-1.5 text-sm text-slate-300 max-h-56 overflow-y-auto pr-2">
                        {outline.map((item, index) => (
                            <li key={`${item}-${index}`} className="flex gap-2">
                                <span className="text-primary-light">{index + 1}.</span>
                                <span>{item}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {status === 'failed' && error && (
                <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-sm">
                    <p className="font-semibold mb-1">Error</p>
                    <p className="font-mono text-xs">{error}</p>
                </div>
            )}

            {status === 'done' && (
                <div className="flex gap-3 flex-wrap">
                    <button
                        id="btn-download-docx"
                        onClick={() => onDownload('docx')}
                        className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-primary to-primary-hover shadow-lg shadow-primary/30 hover:shadow-primary/50 text-white rounded-xl font-semibold text-sm hover:scale-[1.02] transition active:scale-95"
                    >
                        <span className="material-symbols-outlined text-base">file_download</span>
                        Download DOCX
                    </button>
                    <button
                        id="btn-download-pdf"
                        onClick={() => onDownload('pdf')}
                        className="flex items-center gap-2 px-6 py-3 bg-slate-100 dark:bg-white/10 text-slate-800 dark:text-white rounded-xl font-semibold text-sm hover:bg-slate-200 dark:hover:bg-white/20 transition active:scale-95"
                    >
                        <span className="material-symbols-outlined text-base">picture_as_pdf</span>
                        Download PDF
                    </button>
                    <button
                        id="btn-generate-another"
                        onClick={onReset}
                        className="flex items-center gap-2 px-6 py-3 bg-slate-100 dark:bg-white/10 text-slate-800 dark:text-white rounded-xl font-semibold text-sm hover:bg-slate-200 dark:hover:bg-white/20 transition active:scale-95"
                    >
                        <span className="material-symbols-outlined text-base">add</span>
                        Generate Another
                    </button>
                </div>
            )}

            {status === 'failed' && (
                <button
                    id="btn-try-again"
                    onClick={onReset}
                    className="flex items-center gap-2 px-6 py-3 bg-slate-100 dark:bg-white/10 text-slate-800 dark:text-white rounded-xl font-semibold text-sm hover:bg-slate-200 dark:hover:bg-white/20 transition active:scale-95"
                >
                    <span className="material-symbols-outlined text-base">refresh</span>
                    Try Again
                </button>
            )}
        </div>
    );
}
