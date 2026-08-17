// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import { forwardRef } from 'react';

const cx = (...classes) => classes.filter(Boolean).join(' ');

const STATUS_STYLES = {
    completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    processing: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    pending: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
};

const Badge = forwardRef(function Badge(
    { className, status = 'pending', children, ...props },
    ref
) {
    const normalizedStatus = String(status || 'pending').toLowerCase();
    const style = STATUS_STYLES[normalizedStatus] || STATUS_STYLES.pending;

    return (
        <span
            ref={ref}
            className={cn('inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold', style, className)}
            {...props}
        >
            {children || normalizedStatus}
        </span>
    );
});

export default Badge;
