// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React, { memo } from 'react';
import Link from 'next/link';
import { Plus } from 'lucide-react';
import DynamicIcon from '@/src/components/ui/DynamicIcon';

export const StatsCard = memo(function StatsCard({ 
    title, 
    value, 
    description, 
    icon, 
    iconColor, 
    bgColor, 
    hoverBgColor, 
    href, 
    btnText, 
    isDisabled = false,
    onBtnClick
}) {
    const Content = (
        <>
            <div className={`h-48 w-full ${bgColor} flex items-center justify-center ${hoverBgColor} transition-colors`}>
                <DynamicIcon name={icon} className={`w-12 h-12 ${iconColor}`} />
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
                    <div className="w-full bg-primary text-white py-2.5 px-4 rounded-lg font-bold text-sm hover:bg-blue-700 transition-colors flex items-center justify-center gap-2 text-center">
                        <Plus className="text-sm" />
                        {btnText}
                    </div>
                ) : (
                    <button
                        onClick={onBtnClick}
                        disabled={isDisabled}
                        className="w-full bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white py-2.5 px-4 rounded-lg font-bold text-sm hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {btnText}
                    </button>
                )}
            </div>
        </>
    );

    if (href) {
        return (
            <Link href={href} className="group flex flex-col bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden hover:shadow-xl hover:-translate-y-1 transition-all duration-300 cursor-pointer">
                {Content}
            </Link>
        );
    }

    return (
        <div className="group flex flex-col bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
            {Content}
        </div>
    );
});

StatsCard.displayName = 'StatsCard';

function DashboardStats({ stats, loading }) {
    if (loading) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[...Array(5)].map((_, i) => (
                    <div key={i} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden">
                        <div className="h-48 w-full bg-slate-200 dark:bg-slate-700 animate-pulse" />
                        <div className="p-6 space-y-3">
                            <div className="h-5 w-32 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
                            <div className="h-4 w-48 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
                        </div>
                    </div>
                ))}
            </div>
        );
    }

    const s = stats || {};
    const successRate = typeof s.successRate === 'number' ? Math.round(s.successRate * 100) + '%' : '0%';

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <StatsCard title="Total Documents" value={String(s.totalDocuments ?? 0)} description="All manuscripts processed" icon="description" iconColor="text-blue-600" bgColor="bg-blue-50 dark:bg-blue-950/30" />
                <StatsCard title="Formatted This Month" value={String(s.formattedThisMonth ?? 0)} description="Documents formatted this month" icon="auto_awesome" iconColor="text-green-600" bgColor="bg-green-50 dark:bg-green-950/30" />
                <StatsCard title="Success Rate" value={successRate} description="Percentage of successful formatting jobs" icon="check_circle" iconColor="text-emerald-600" bgColor="bg-emerald-50 dark:bg-emerald-950/30" />
                <StatsCard title="Avg Processing Time" value={s.avgProcessingTime || '0s'} description="Average time to format a document" icon="timer" iconColor="text-purple-600" bgColor="bg-purple-50 dark:bg-purple-950/30" />
                <StatsCard title="Storage Used" value={s.storageUsed || '0 MB'} description="Total storage used for documents" icon="storage" iconColor="text-amber-600" bgColor="bg-amber-50 dark:bg-amber-950/30" />
            </div>
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6">
                <h3 className="text-slate-900 dark:text-white text-lg font-bold mb-4">Activity (Last 7 Days)</h3>
                <div className="flex items-end gap-2 h-32">
                    {[...Array(7)].map((_, i) => (
                        <div key={i} className="flex-1 bg-primary/20 rounded-t-md" style={{ height: `${30 + Math.random() * 70}%` }} />
                    ))}
                </div>
            </div>
        </div>
    );
}

export default DashboardStats;
