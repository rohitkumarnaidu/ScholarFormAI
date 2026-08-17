// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import { forwardRef } from 'react';

const Input = forwardRef(function Input(
    {
        className,
        label,
        error,
        helperText,
        id,
        ...props
    },
    ref
) {
    const inputId = id || props.name || undefined;
    const errorId = inputId ? `${inputId}-error` : undefined;
    const helperId = inputId ? `${inputId}-helper` : undefined;

    return (
        <div className="w-full">
            {label ? (
                <label htmlFor={inputId} className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    {label}
                </label>
            ) : null}
            <input
                ref={ref}
                id={inputId}
                aria-invalid={error ? 'true' : undefined}
                aria-describedby={error ? errorId : helperText ? helperId : undefined}
                className={cn(
                    'w-full rounded-xl border px-4 py-2.5 text-sm outline-none transition-colors',
                    'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100',
                    error
                        ? 'border-red-500/60 focus:border-red-500'
                        : 'border-slate-300 dark:border-slate-700 focus:border-primary',
                    className
                )}
                {...props}
            />
            {error ? (
                <p id={errorId} className="mt-1 text-xs text-red-600 dark:text-red-400">{error}</p>
            ) : helperText ? (
                <p id={helperId} className="mt-1 text-xs text-slate-500 dark:text-slate-400">{helperText}</p>
            ) : null}
        </div>
    );
});

export default Input;
