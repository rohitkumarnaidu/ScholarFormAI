// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import React, { memo } from 'react';
import Link from 'next/link';
import Skeleton from '@/components/ui/Skeleton';

import { cn } from '@/src/lib/utils';

const ACTIVITY_ICONS = {
    upload: '↑',
    format: '⚙',
    download: '↓',
    edit: '✏',
    export: '📄',
};

const defaultIcon = '•';

function formatTimestamp(ts) {
    if (!ts) return '';
    const date = new Date(ts);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function ActivityIcon({ type }) {
    const icon = ACTIVITY_ICONS[type] || defaultIcon;
    const colorMap = {
        upload: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
        format: 'bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400',
        download: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
        edit: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400',
        export: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
    };
    return (
        <div className={cn('w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold shrink-0', colorMap[type] || 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400')}>
            {icon}
        </div>
    );
}

const RecentActivity = memo(function RecentActivity({ activities, loading = false }) {
    if (loading) {
        return (
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
                <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                    <Skeleton className="h-5 w-32" />
                    <Skeleton className="h-4 w-16" />
                </div>
                <div className="divide-y divide-slate-100 dark:divide-slate-800/50">
                    {Array.from({ length: 5 }).map((_, i) => (
                        <div key={`act-skel-${i}`} className="flex items-center gap-3 p-4">
                            <Skeleton className="h-9 w-9 rounded-lg shrink-0" />
                            <div className="flex-1 min-w-0">
                                <Skeleton className="h-4 w-3/4 mb-1" />
                                <Skeleton className="h-3 w-1/2" />
                            </div>
                            <Skeleton className="h-3 w-12 shrink-0" />
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    if (!activities || activities.length === 0) {
        return (
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
                <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                        <span className="material-symbols-outlined text-primary text-lg">history</span>
                        Recent Activity
                    </h3>
                    <Link href="/history" className="text-xs font-semibold text-primary hover:underline">View all</Link>
                </div>
                <div className="flex flex-col items-center justify-center py-10 px-4 text-center">
                    <span className="material-symbols-outlined text-3xl text-slate-300 dark:text-slate-600 mb-2">history</span>
                    <p className="text-sm text-slate-500 dark:text-slate-400">No recent activity</p>
                    <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">Upload a manuscript to get started</p>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <span className="material-symbols-outlined text-primary text-lg">history</span>
                    Recent Activity
                </h3>
                <Link href="/history" className="text-xs font-semibold text-primary hover:underline">View all</Link>
            </div>
            <div className="divide-y divide-slate-100 dark:divide-slate-800/50">
                {activities.slice(0, 10).map((activity) => (
                    <div key={activity.id} className="flex items-center gap-3 p-4 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                        <ActivityIcon type={activity.type} />
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold text-slate-900 dark:text-white truncate">
                                {activity.description}
                            </p>
                            {activity.documentName && (
                                <p className="text-xs text-slate-400 dark:text-slate-500 truncate">
                                    {activity.documentName}
                                </p>
                            )}
                        </div>
                        <span className="text-xs text-slate-400 dark:text-slate-500 shrink-0">
                            {formatTimestamp(activity.timestamp)}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
});

RecentActivity.displayName = 'RecentActivity';

export default RecentActivity;
export { ActivityIcon, formatTimestamp };
