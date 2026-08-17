// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import React, { memo } from 'react';
import Link from 'next/link';
import { Download, FileText } from 'lucide-react';

// Constants for status (inlined to avoid missing imports in this context)
const isCompleted = (status) => status === 'completed' || status === 'success' || status === 'ready';
const isProcessing = (status) => status === 'processing' || status === 'uploading' || status === 'queued';

const DashboardRow = memo(function DashboardRow({ item, style }) {
    if (!item) return null;

    const completed = isCompleted(item.status);
    const processing = isProcessing(item.status);
    const timestamp = item.timestamp || item.created_at || new Date().toISOString();

    return (
        <tr 
            style={style} 
            className="group hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors border-b border-slate-100 dark:border-white/5"
        >
            <td className="px-4 md:px-6 py-4 min-w-[200px] md:min-w-full max-w-[300px]">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400 group-hover:bg-primary/10 group-hover:text-primary transition-colors">
                        <FileText className="text-[20px]" />
                    </div>
                    <div className="flex flex-col min-w-0">
                        <span className="text-slate-900 dark:text-white font-bold truncate max-w-[240px]">
                            {item.originalFileName || item.filename || 'Untitled Manuscript'}
                        </span>
                        <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider">
                            ID: {item.id?.substring(0, 8) || '...'}
                        </span>
                    </div>
                </div>
            </td>
            <td className="px-6 py-4">
                <div className="flex items-center">
                    <span 
                        role="status"
                        aria-label={`Status: ${item.status || 'Pending'}`}
                        className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider ${
                        completed 
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' 
                        : processing 
                        ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' 
                        : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                    }`}>
                        <span className={`w-1.5 h-1.5 rounded-full mr-2 ${completed ? 'bg-green-500' : processing ? 'bg-blue-500 animate-pulse' : 'bg-slate-400'}`}></span>
                        {item.status || 'Pending'}
                    </span>
                </div>
            </td>
            <td className="px-6 py-4">
                <span className="text-sm font-medium text-slate-500 dark:text-slate-400">
                    {new Date(timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                </span>
            </td>
            <td className="px-6 py-4 text-right">
                <div className="flex items-center justify-end gap-2">
                    {completed ? (
                        <button 
                            onClick={() => window.open(`/api/v1/formatter/documents/${item.id}/download`)}
                            aria-label={`Download manuscript: ${item.originalFileName || item.filename}`}
                            className="h-9 px-4 rounded-lg bg-primary/10 text-primary hover:bg-primary hover:text-white focus:ring-2 focus:ring-primary focus:outline-none font-bold text-xs transition-all flex items-center gap-2"
                        >
                            <Download className="text-[18px]" />
                            Download
                        </button>
                    ) : (
                        <Link 
                            href="/upload"
                            aria-label={`Resume upload for manuscript: ${item.originalFileName || item.filename}`}
                            className="h-9 px-4 rounded-lg border border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 focus:ring-2 focus:ring-primary focus:outline-none font-bold text-xs transition-all flex items-center justify-center"
                        >
                            Resume
                        </Link>
                    )}
                </div>
            </td>
        </tr>
    );
});

DashboardRow.displayName = 'DashboardRow';

export default DashboardRow;
