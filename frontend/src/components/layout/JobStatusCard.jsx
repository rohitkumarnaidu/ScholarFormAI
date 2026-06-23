// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import React, { memo } from 'react';

function JobStatusCard({ job }) {
    // Default mock data if job is undefined
    const data = job || {
        filename: 'Thesis_Final_Draft_v2.docx',
        status: 'completed', // completed, processing, failed
        template: 'APA 7th Edition',
        timeAgo: '2 mins ago',
        size: '2.4 MB',
        description: 'Successfully formatted with citations checked against Zotero database. All margins and headers compliant with university guidelines.',
    };

    const isProcessing = data.status === 'processing';
    const isFailed = data.status === 'failed';
    const isCompleted = data.status === 'completed';

    return (
        <div className={`glass-panel group p-6 rounded-2xl transition-all duration-300 
            ${isCompleted ? 'hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5' : ''}
            ${isProcessing ? 'border-l-4 border-l-primary hover:border-t hover:border-r hover:border-b hover:border-t-primary/30 hover:border-r-primary/30 hover:border-b-primary/30' : ''}
            ${isFailed ? 'hover:border-red-500/30' : ''}
        `}>
            <div className="flex flex-col md:flex-row gap-6">

                {/* Thumbnail / Status Icon Box */}
                <div className={`relative shrink-0 w-full md:w-48 aspect-video md:aspect-[4/3] rounded-xl overflow-hidden bg-slate-800 border border-slate-700 transition-colors 
                    ${isCompleted ? 'group-hover:border-primary/40' : ''}
                    ${isFailed ? 'group-hover:border-red-500/30' : ''}
                `}>
                    <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-slate-800 to-slate-900">
                        {isCompleted && <span className="material-symbols-outlined text-4xl text-primary opacity-80 group-hover:scale-110 transition-transform duration-500">description</span>}
                        {isProcessing && <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>}
                        {isFailed && <span className="material-symbols-outlined text-4xl text-red-500 opacity-50 grayscale group-hover:grayscale-0 transition-all font-light">error</span>}
                    </div>

                    {/* Status Badge */}
                    {isCompleted && (
                        <div className="absolute top-3 left-3 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 backdrop-blur-md flex items-center gap-1.5">
                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">Ready</span>
                        </div>
                    )}
                    {isProcessing && (
                        <div className="absolute top-3 left-3 px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 backdrop-blur-md flex items-center gap-1.5">
                            <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></div>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-blue-400">Processing</span>
                        </div>
                    )}
                    {isFailed && (
                        <div className="absolute top-3 left-3 px-2.5 py-1 rounded-full bg-red-500/10 border border-red-500/20 backdrop-blur-md flex items-center gap-1.5">
                            <div className="w-1.5 h-1.5 rounded-full bg-red-500"></div>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-red-400">Failed</span>
                        </div>
                    )}
                </div>

                {/* Content */}
                <div className="flex flex-col flex-1 justify-between gap-4">
                    <div>
                        <div className="flex justify-between items-start mb-2">
                            <h3 className={`text-lg font-bold text-white transition-colors
                                ${isCompleted ? 'group-hover:text-primary' : ''}
                                ${isFailed ? 'group-hover:text-red-400' : ''}
                            `}>
                                {data.filename}
                            </h3>
                            <button className="text-slate-500 hover:text-white transition-colors p-1" aria-label="More options">
                                <span className="material-symbols-outlined">more_vert</span>
                            </button>
                        </div>

                        {/* Metadata Tags */}
                        {isCompleted || isFailed ? (
                            <div className="flex flex-wrap gap-3 text-sm text-slate-400 mb-4 tracking-tight">
                                {data.template && (
                                    <span className="flex items-center gap-1 bg-slate-800/50 px-2 py-0.5 rounded text-xs border border-slate-700/50">
                                        <span className="material-symbols-outlined text-[14px]">style</span> {data.template}
                                    </span>
                                )}
                                <span className="flex items-center gap-1 bg-slate-800/50 px-2 py-0.5 rounded text-xs border border-slate-700/50">
                                    <span className="material-symbols-outlined text-[14px]">schedule</span> {data.timeAgo}
                                </span>
                                {data.size && (
                                    <span className="flex items-center gap-1 bg-slate-800/50 px-2 py-0.5 rounded text-xs border border-slate-700/50">
                                        <span className="material-symbols-outlined text-[14px]">folder_open</span> {data.size}
                                    </span>
                                )}
                            </div>
                        ) : (
                            <div className="w-full bg-slate-800 rounded-full h-1.5 mb-4 overflow-hidden">
                                <div className="bg-gradient-to-r from-blue-500 to-primary h-1.5 rounded-full transition-all duration-300" style={{ width: '45%' }}></div>
                            </div>
                        )}

                        {/* Description / Progress Logic */}
                        <p className={`text-sm ${isFailed ? 'text-red-400 bg-red-500/10 p-2 rounded border border-red-500/20 inline-block' : 'text-slate-400 line-clamp-2'}`}>
                            {data.description}
                        </p>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-3 pt-2">
                        {isCompleted && (
                            <>
                                <button className="flex items-center gap-2 bg-slate-100 hover:bg-white text-slate-900 px-4 py-2 rounded-lg text-sm font-bold transition-transform active:scale-95 shadow-sm">
                                    <span className="material-symbols-outlined text-[18px]">download</span>
                                    Download
                                </button>
                                <button className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white px-4 py-2 rounded-lg text-sm font-medium transition-transform active:scale-95 border border-slate-700 focus:ring-2 focus:ring-primary focus:outline-none">
                                    <span className="material-symbols-outlined text-[18px]">visibility</span>
                                    Preview
                                </button>
                            </>
                        )}
                        {isProcessing && (
                            <button className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white px-4 py-2 rounded-lg text-sm font-medium transition-transform active:scale-95 border border-slate-700">
                                <span className="material-symbols-outlined text-[18px]">cancel</span>
                                Cancel
                            </button>
                        )}
                        {isFailed && (
                            <>
                                <button className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white px-4 py-2 rounded-lg text-sm font-medium transition-transform active:scale-95 border border-slate-700 focus:ring-2 focus:ring-red-500">
                                    <span className="material-symbols-outlined text-[18px]">refresh</span>
                                    Retry
                                </button>
                                <button className="flex items-center gap-2 text-slate-500 hover:text-slate-300 px-2 py-2 rounded-lg text-sm font-medium transition-colors">
                                    View Logs
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default memo(JobStatusCard);
