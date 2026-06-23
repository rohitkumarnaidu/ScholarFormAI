// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import React, { useMemo, useRef, useCallback, memo, useEffect } from 'react';
import { useAuth } from '@/src/context/AuthContext';
import { useDocuments } from '@/src/services/api';
import usePageTitle from '@/src/hooks/usePageTitle';
import { useVirtualizer } from '@tanstack/react-virtual';
import Link from 'next/link';

import DashboardRow from '@/src/components/dashboard/DashboardRow';
import { trackPageView } from '@/src/lib/rum';

const StatsCard = memo(({ 
    title, 
    value, 
    description, 
    icon, 
    iconColor, 
    href, 
    btnText, 
    onBtnClick,
    btnClass
}) => {
    const cardContent = (
        <>
            <div className="bg-slate-100/50 dark:bg-slate-800/50 h-48 flex items-center justify-center group-hover:bg-slate-200/50 dark:group-hover:bg-slate-700/50 transition-colors">
                <span className={`material-symbols-outlined ${iconColor} text-5xl`}>{icon}</span>
            </div>
            <div className="p-6">
                <div className="flex justify-between items-start mb-2">
                    <h3 className="text-slate-900 dark:text-white text-lg font-bold">{title}</h3>
                    {value !== undefined && (
                        <span className="bg-primary/20 text-primary text-[10px] font-bold px-2 py-1 rounded-full uppercase tracking-wider">{value}</span>
                    )}
                </div>
                <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed mb-4">{description}</p>
                {href ? (
                    <div className={btnClass}>
                        <span className="material-symbols-outlined text-sm">add</span>
                        {btnText}
                    </div>
                ) : (
                    <button onClick={onBtnClick} className={btnClass}>
                        {btnText}
                    </button>
                )}
            </div>
        </>
    );

    const containerClass = "group flex flex-col bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden hover:shadow-xl hover:-translate-y-1 transition-all duration-300";

    return href ? (
        <Link href={href} className={containerClass}>{cardContent}</Link>
    ) : (
        <div className={containerClass}>{cardContent}</div>
    );
});
StatsCard.displayName = 'StatsCard';

export default function DashboardPage() {
    usePageTitle('Dashboard');
    useEffect(() => { trackPageView('/dashboard'); }, []);
    const { user } = useAuth();
    const {
        data: documentsPayload,
        isLoading: loading,
        refetch,
    } = useDocuments({ limit: 100 });
    const history = useMemo(() => (
        Array.isArray(documentsPayload?.documents)
            ? documentsPayload.documents
            : Array.isArray(documentsPayload?.history)
                ? documentsPayload.history
                : []
    ), [documentsPayload]);

    const parentRef = useRef(null);

    const rowVirtualizer = useVirtualizer({
        count: history.length,
        getScrollElement: () => parentRef.current,
        estimateSize: () => 72,
        overscan: 5,
    });
    const virtualRows = rowVirtualizer.getVirtualItems();

    const displayName = useMemo(() => user?.user_metadata?.full_name || 'Researcher', [user]);
    const readyCount = useMemo(
        () => history.filter((document) => document.status === 'completed').length,
        [history]
    );

    const handleDownloadLatest = useCallback(() => {
        if (history[0]?.id) {
            window.open(`/api/v1/formatter/documents/${history[0].id}/download`);
        }
    }, [history]);

    const handleRefresh = useCallback(() => {
        refetch();
    }, [refetch]);

    return (
        <div className="min-h-screen bg-background-light dark:bg-background-dark py-8">
            <div className="mx-auto max-w-[1240px] px-4 sm:px-6">
                <header className="mb-10">
                    <h1 className="text-3xl sm:text-4xl font-black text-slate-900 dark:text-white tracking-tight">
                        Welcome back, {displayName}
                    </h1>
                    <p className="text-slate-500 dark:text-slate-400 mt-2 text-lg">
                        Manage your manuscripts and track validation status in real-time.
                    </p>
                </header>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 mt-2">
                    <StatsCard 
                        title="Upload New Manuscript"
                        description="Start a new submission and formatting check. Supports .docx and LaTeX files."
                        icon="cloud_upload"
                        iconColor="text-indigo-600 dark:text-indigo-400"
                        href="/upload"
                        btnText="New Submission"
                        btnClass="w-full bg-primary text-white py-2.5 px-4 rounded-lg font-bold text-sm hover:bg-blue-700 transition-colors flex items-center justify-center gap-2 text-center"
                    />
                    <StatsCard 
                        title="My Manuscripts"
                        description="Track progress of ongoing projects."
                        icon="description"
                        iconColor="text-slate-600 dark:text-slate-400"
                        value={`${history.length} Active`}
                        href="/history"
                        btnText="View All Projects"
                        btnClass="w-full bg-blue-600 text-white py-2.5 px-4 rounded-lg font-bold text-sm hover:bg-blue-700 transition-colors flex items-center justify-center gap-2 text-center"
                    />
                    <StatsCard 
                        title="Validation Results"
                        description="Detailed compliance reports and export-ready files."
                        icon="fact_check"
                        iconColor="text-green-600 dark:text-green-400"
                        value={`${readyCount} Ready`}
                        btnText="Download Results"
                        onBtnClick={handleDownloadLatest}
                        btnClass="w-full bg-slate-100 dark:bg-white/10 text-slate-900 dark:text-white py-2.5 px-4 rounded-lg font-bold text-sm hover:bg-slate-200 dark:hover:bg-white/20 transition-colors"
                    />
                </div>

                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden shadow-sm">
                    <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                        <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            Recent Activity
                        </h2>
                        <div className="flex items-center gap-4">
                            <button onClick={handleRefresh} className="text-sm font-semibold text-primary hover:text-blue-700 transition-colors flex items-center gap-1.5">
                                <span className={`material-symbols-outlined text-lg ${loading ? 'animate-spin' : ''}`}>refresh</span> Refresh
                            </button>
                            <Link href="/history" className="text-sm font-semibold text-primary hover:text-blue-700 transition-colors flex items-center gap-1">
                                View full history <span className="material-symbols-outlined text-lg">arrow_forward</span>
                            </Link>
                        </div>
                    </div>

                    <div ref={parentRef} className="overflow-x-auto max-h-[600px] overflow-y-auto custom-scrollbar">
                        <table className="w-full border-collapse min-w-[500px] md:min-w-[800px]">
                            <thead className="sticky top-0 bg-slate-50 dark:bg-slate-800/50 backdrop-blur-md z-10">
                                <tr>
                                    <th className="text-left text-[11px] font-bold text-slate-400 uppercase tracking-widest px-6 py-4 border-b border-slate-100 dark:border-white/5">Manuscript Title</th>
                                    <th className="text-left text-[11px] font-bold text-slate-400 uppercase tracking-widest px-6 py-4 border-b border-slate-100 dark:border-white/5">Status</th>
                                    <th className="text-left text-[11px] font-bold text-slate-400 uppercase tracking-widest px-6 py-4 border-b border-slate-100 dark:border-white/5">Last Modified</th>
                                    <th className="text-right text-[11px] font-bold text-slate-400 uppercase tracking-widest px-6 py-4 border-b border-slate-100 dark:border-white/5">Actions</th>
                                </tr>
                            </thead>
                            <tbody style={{ height: `${rowVirtualizer.getTotalSize()}px`, position: 'relative' }}>
                                {virtualRows.map((virtualRow) => (
                                    <DashboardRow
                                        key={virtualRow.key}
                                        item={history[virtualRow.index]}
                                        index={virtualRow.index}
                                        style={{
                                            position: 'absolute',
                                            top: 0,
                                            left: 0,
                                            width: '100%',
                                            height: `${virtualRow.size}px`,
                                            transform: `translateY(${virtualRow.start}px)`,
                                        }}
                                    />
                                ))}
                                {(!history || history.length === 0) && !loading && (
                                    <tr>
                                        <td colSpan="4" className="px-6 py-12 text-center">
                                            <div className="flex flex-col items-center gap-3">
                                                <span className="material-symbols-outlined text-4xl text-slate-300">folder_open</span>
                                                <p className="text-slate-500 font-medium">No activity found. Start by uploading a manuscript.</p>
                                                <Link href="/upload" className="mt-2 text-primary font-bold hover:underline">New Upload</Link>
                                            </div>
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}
