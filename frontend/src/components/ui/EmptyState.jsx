// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import { forwardRef } from 'react';
import Button from './Button';

const cx = (...classes) => classes.filter(Boolean).join(' ');

const EmptyState = forwardRef(function EmptyState(
    {
        className,
        icon = 'inbox',
        title = 'No data yet',
        description = 'There is nothing to show right now.',
        actionLabel,
        onAction,
        action,
        ...props
    },
    ref
) {
    return (
        <div
            ref={ref}
            className={cx(
                'w-full rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-8 text-center',
                className
            )}
            {...props}
        >
            <div className="mx-auto mb-3 w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-500 dark:text-slate-400">
                <span className="material-symbols-outlined">{icon}</span>
            </div>
            <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>
            {action || (actionLabel && onAction) ? (
                <div className="mt-4 flex justify-center">
                    {action || (
                        <Button variant="secondary" onClick={onAction}>{actionLabel}</Button>
                    )}
                </div>
            ) : null}
        </div>
    );
});

export default EmptyState;
