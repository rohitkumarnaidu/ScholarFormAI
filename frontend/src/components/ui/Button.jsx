// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import { forwardRef } from 'react';

const cx = (...classes) => classes.filter(Boolean).join(' ');

const VARIANT_CLASSES = {
    primary: 'bg-primary hover:bg-primary-hover text-white shadow-lg shadow-primary/25 border border-transparent',
    secondary: 'bg-slate-100 dark:bg-white/10 text-slate-800 dark:text-slate-100 border border-slate-200 dark:border-white/15 hover:bg-slate-200 dark:hover:bg-white/20',
    danger: 'bg-red-600 hover:bg-red-700 text-white border border-transparent shadow-lg shadow-red-600/20',
};

const SIZE_CLASSES = {
    sm: 'h-9 px-3 text-sm',
    md: 'h-10 px-4 text-sm',
    lg: 'h-12 px-5 text-base',
};

const Spinner = () => (
    <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" aria-hidden="true" />
);

const Button = forwardRef(function Button(
    {
        className,
        variant = 'primary',
        size = 'md',
        loading = false,
        disabled = false,
        children,
        type = 'button',
        ...props
    },
    ref
) {
    const isDisabled = disabled || loading;

    return (
        <button
            ref={ref}
            type={type}
            disabled={isDisabled}
            className={cx(
                'inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed',
                VARIANT_CLASSES[variant] || VARIANT_CLASSES.primary,
                SIZE_CLASSES[size] || SIZE_CLASSES.md,
                className
            )}
            {...props}
        >
            {loading && <Spinner />}
            <span>{children}</span>
        </button>
    );
});

export default Button;
