// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React, { memo } from 'react';

const STATUS_META = {
    PROCESSING: {
        label: 'Processing',
        className: 'bg-primary/10 text-primary',
    },
    COMPLETED: {
        label: 'Completed',
        className: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    },
    COMPLETED_WITH_WARNINGS: {
        label: 'Completed With Warnings',
        className: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    },
    FAILED: {
        label: 'Failed',
        className: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    },
    CANCELLED: {
        label: 'Cancelled',
        className: 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200',
    },
    PENDING: {
        label: 'Pending',
        className: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
    },
    STANDBY: {
        label: 'Standby',
        className: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
    },
};

const normalizeStatus = (status) => String(status || 'STANDBY').trim().toUpperCase();

function StatusBadge({ status = 'STANDBY' }) {
    const normalized = normalizeStatus(status);
    const config = STATUS_META[normalized] || STATUS_META.STANDBY;

    return (
        <span className={`text-xs font-bold uppercase tracking-widest px-2 py-1 rounded ${config.className}`}>
            {config.label}
        </span>
    );
}

export default memo(StatusBadge);
