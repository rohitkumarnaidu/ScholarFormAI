// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import DynamicIcon from '@/src/components/ui/DynamicIcon';

export default function HealthStatusIndicator({ status, label, details }) {
    const statusConfig = {
        healthy: {
            bg: 'bg-green-100 dark:bg-green-900/30',
            text: 'text-green-700 dark:text-green-400',
            dot: 'bg-green-500',
            icon: 'check_circle',
        },
        degraded: {
            bg: 'bg-amber-100 dark:bg-amber-900/30',
            text: 'text-amber-700 dark:text-amber-400',
            dot: 'bg-amber-500',
            icon: 'warning',
        },
        unavailable: {
            bg: 'bg-red-100 dark:bg-red-900/30',
            text: 'text-red-700 dark:text-red-400',
            dot: 'bg-red-500',
            icon: 'error',
        },
        unknown: {
            bg: 'bg-slate-100 dark:bg-slate-800',
            text: 'text-slate-600 dark:text-slate-400',
            dot: 'bg-slate-400',
            icon: 'help',
        },
    };

    const config = statusConfig[status] || statusConfig.unknown;

    return (
        <div className={`flex items-center gap-3 p-4 rounded-xl ${config.bg} transition-colors`}>
            <div className="relative">
                <DynamicIcon name={config.icon} className={`w-5 h-5 ${config.text}`} />
                <span className={`absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full ${config.dot} ${status === 'healthy' ? 'animate-pulse' : ''}`} />
            </div>
            <div className="flex-1">
                <p className="text-sm font-semibold text-slate-900 dark:text-white">{label}</p>
                {details && (
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{details}</p>
                )}
            </div>
            <span className={`text-xs font-medium px-2 py-1 rounded-full ${config.bg} ${config.text} capitalize`}>
                {status}
            </span>
        </div>
    );
}
