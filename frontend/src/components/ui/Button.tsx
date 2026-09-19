// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import { forwardRef } from 'react';
import { cn } from '@/lib/utils';



const VARIANT_CLASSES: Record<string, string> = {
    primary: 'bg-primary hover:bg-primary-hover text-white shadow-lg shadow-primary/25 border border-transparent',
    secondary: 'bg-slate-100 dark:bg-white/10 text-slate-800 dark:text-slate-100 border border-slate-200 dark:border-white/15 hover:bg-slate-200 dark:hover:bg-white/20',
    danger: 'bg-red-600 hover:bg-red-700 text-white border border-transparent shadow-lg shadow-red-600/20',
    success: 'bg-emerald-600 hover:bg-emerald-700 text-white border border-transparent shadow-lg shadow-emerald-600/20',
    outline: 'bg-transparent border-2 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800',
    ghost: 'bg-transparent border border-transparent text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white',
    magic: 'bg-gradient-to-r from-violet-600 to-indigo-600 text-white border border-transparent hover:from-violet-700 hover:to-indigo-700 shadow-md shadow-violet-500/20',
};

const SIZE_CLASSES: Record<string, string> = {
    sm: 'h-9 px-3 text-sm',
    md: 'h-10 px-4 text-sm',
    lg: 'h-12 px-5 text-base',
    icon: 'size-10 p-0',
};

const Spinner = () => (
    <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" aria-hidden="true" />
);

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'danger' | 'success' | 'outline' | 'ghost' | 'magic';
    size?: 'sm' | 'md' | 'lg' | 'icon';
    loading?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>((
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
) => {
    const isDisabled = disabled || loading;

    return (
        <button
            ref={ref}
            type={type}
            disabled={isDisabled}
            className={cn(
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
