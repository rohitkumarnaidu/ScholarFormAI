// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React, { memo } from 'react';

function MetricsCard({ title, value, icon, subtitle, color = 'primary', trend, isLoading = false }) {
    const colorMap = {
        primary: 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800',
        green: 'bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 border-green-200 dark:border-green-800',
        amber: 'bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-800',
        red: 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border-red-200 dark:border-red-800',
        purple: 'bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 border-purple-200 dark:border-purple-800',
    };

    const iconColorMap = {
        primary: 'bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400',
        green: 'bg-green-100 dark:bg-green-900/40 text-green-600 dark:text-green-400',
        amber: 'bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400',
        red: 'bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400',
        purple: 'bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-400',
    };

    return (
        <div className={`rounded-xl border p-5 ${colorMap[color] || colorMap.primary} transition-all hover:shadow-md`}>
            <div className="flex items-start justify-between">
                <div className="flex-1">
                    <p className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">{title}</p>
                    {isLoading ? (
                        <div className="h-9 w-24 bg-slate-200 dark:bg-slate-700/50 rounded animate-pulse my-1"></div>
                    ) : (
                        <p className="text-3xl font-bold text-slate-900 dark:text-white">{value ?? '—'}</p>
                    )}
                    {isLoading && subtitle ? (
                        <div className="h-4 w-32 bg-slate-200 dark:bg-slate-700/50 rounded animate-pulse mt-2"></div>
                    ) : (
                        subtitle && <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{subtitle}</p>
                    )}
                    {trend !== undefined && (
                        <div className={`flex items-center gap-1 mt-2 text-xs font-medium ${trend >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                            <span className="material-symbols-outlined text-sm">
                                {trend >= 0 ? 'trending_up' : 'trending_down'}
                            </span>
                            {Math.abs(trend)}%
                        </div>
                    )}
                </div>
                {icon && (
                    <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${iconColorMap[color] || iconColorMap.primary}`}>
                        <span className="material-symbols-outlined">{icon}</span>
                    </div>
                )}
            </div>
        </div>
    );
}

export default memo(MetricsCard);
