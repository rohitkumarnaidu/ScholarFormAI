// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import { forwardRef } from 'react';

const cx = (...classes) => classes.filter(Boolean).join(' ');

const Card = forwardRef(function Card({ className, glass = false, children, ...props }, ref) {
    return (
        <div
            ref={ref}
            className={cx(
                'rounded-2xl border p-4 sm:p-5',
                glass
                    ? 'bg-glass-surface backdrop-blur-xl border-glass-border'
                    : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800',
                className
            )}
            {...props}
        >
            {children}
        </div>
    );
});

export default Card;
