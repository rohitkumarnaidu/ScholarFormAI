// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import React, { memo, useMemo } from 'react';
import Skeleton from '@/components/ui/Skeleton';

import { cn } from '@/src/lib/utils';
import { BarChart } from 'lucide-react';

const COLOR_MAP = {
    'current-month': 'bg-primary hover:bg-blue-600',
    default: 'bg-slate-300 dark:bg-slate-600 hover:bg-slate-400 dark:hover:bg-slate-500',
};

const UsageChart = memo(function UsageChart({ data, days = 7, height = 180, loading = false }) {
    const chartData = useMemo(() => {
        if (!data || data.length === 0) return [];
        const sliced = data.slice(-days);
        const maxVal = Math.max(...sliced.map(d => d.value), 1);
        return { items: sliced, maxVal };
    }, [data, days]);

    const yLabels = useMemo(() => {
        if (!chartData.items || chartData.items.length === 0) return [];
        const max = chartData.maxVal;
        const steps = 4;
        return Array.from({ length: steps + 1 }, (_, i) => Math.round((max / steps) * i));
    }, [chartData]);

    if (loading) {
        return (
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
                <Skeleton className="h-5 w-40 mb-4" />
                <div className="flex gap-2 items-end" style={{ height: `${height}px` }}>
                    {Array.from({ length: days }).map((_, i) => (
                        <Skeleton key={`chart-sk-${i}`} className="flex-1" style={{ height: `${20 + Math.random() * (height - 30)}px` }} />
                    ))}
                </div>
            </div>
        );
    }

    if (!data || data.length === 0) {
        return (
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                    <BarChart className="text-primary text-lg" />
                    Formatting Activity
                </h3>
                <div className="flex flex-col items-center justify-center py-8 text-center">
                    <BarChart className="text-3xl text-slate-300 dark:text-slate-600 mb-2" />
                    <p className="text-sm text-slate-500 dark:text-slate-400">No activity data available</p>
                </div>
            </div>
        );
    }

    const { items, maxVal } = chartData;
    const barHeight = height - 24;
    const now = new Date();
    const currentMonth = now.getMonth();

    return (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                <BarChart className="text-primary text-lg" />
                Formatting Activity ({days}-day view)
            </h3>
            <div className="flex gap-1">
                <div className="flex flex-col justify-between pr-2 text-right shrink-0" style={{ height: `${barHeight}px` }}>
                    {yLabels.slice().reverse().map((val, i) => (
                        <span key={i} className="text-[10px] text-slate-400 font-medium leading-none">{val}</span>
                    ))}
                </div>
                <div className="flex items-end gap-1.5 flex-1" style={{ height: `${barHeight}px` }}>
                    {items.map((point, i) => {
                        const barH = maxVal > 0 ? Math.max(3, (point.value / maxVal) * barHeight) : 0;
                        const d = point.date ? new Date(point.date) : null;
                        const isCurrentMonth = d && d.getMonth() === currentMonth;
                        return (
                            <div
                                key={i}
                                className="flex-1 flex flex-col items-center justify-end h-full"
                            >
                                <div
                                    title={`${point.label || ''}: ${point.value}`}
                                    className={cn(
                                        'w-full max-w-[32px] rounded-t-sm transition-all duration-300',
                                        isCurrentMonth ? COLOR_MAP['current-month'] : COLOR_MAP.default
                                    )}
                                    style={{ height: `${barH}px`, minHeight: barH > 0 ? '3px' : '0' }}
                                />
                            </div>
                        );
                    })}
                </div>
            </div>
            <div className="flex gap-1.5 mt-2">
                <div className="pr-7 shrink-0" />
                {items.map((point, i) => (
                    <div key={i} className="flex-1 text-center">
                        <span className="text-[10px] text-slate-400 font-medium truncate block">{point.label || ''}</span>
                    </div>
                ))}
            </div>
        </div>
    );
});

UsageChart.displayName = 'UsageChart';

export default UsageChart;
