// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import { forwardRef, useRef, useEffect } from 'react';
import Button from './Button';

import { cn } from '@/src/lib/utils';

const ConfirmDialog = forwardRef(function ConfirmDialog(
    {
        className,
        open = false,
        title = 'Are you sure?',
        description,
        confirmLabel = 'Confirm',
        cancelLabel = 'Cancel',
        onConfirm,
        onCancel,
        isLoading = false,
        danger = true,
        ...props
    },
    ref
) {
    const localRef = useRef(null);

    useEffect(() => {
        if (!open) return;
        const dialogNode = localRef.current;
        if (!dialogNode) return;

        const handleKeydown = (e) => {
            if (e.key === 'Escape') {
                onCancel?.();
                return;
            }
            if (e.key !== 'Tab') return;

            const focusableElements = dialogNode.querySelectorAll(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            if (focusableElements.length === 0) return;

            const firstElement = focusableElements[0];
            const lastElement = focusableElements[focusableElements.length - 1];

            if (e.shiftKey) {
                if (document.activeElement === firstElement || !dialogNode.contains(document.activeElement)) {
                    lastElement.focus();
                    e.preventDefault();
                }
            } else {
                if (document.activeElement === lastElement || !dialogNode.contains(document.activeElement)) {
                    firstElement.focus();
                    e.preventDefault();
                }
            }
        };

        document.addEventListener('keydown', handleKeydown);

        const focusableElements = dialogNode.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        setTimeout(() => focusableElements[0]?.focus(), 50);

        return () => {
            document.removeEventListener('keydown', handleKeydown);
        };
    }, [open, onCancel]);

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-slate-950/50 backdrop-blur-sm" onClick={onCancel} />
            <div
                ref={(node) => {
                    localRef.current = node;
                    if (typeof ref === 'function') ref(node);
                    else if (ref) ref.current = node;
                }}
                role="dialog"
                aria-modal="true"
                className={cn('relative w-full max-w-md rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-2xl', className)}
                {...props}
            >
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
                {description ? (
                    <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{description}</p>
                ) : null}
                <div className="mt-5 flex justify-end gap-2">
                    <Button variant="secondary" onClick={onCancel} disabled={isLoading}>{cancelLabel}</Button>
                    <Button variant={danger ? 'danger' : 'primary'} onClick={onConfirm} loading={isLoading}>{confirmLabel}</Button>
                </div>
            </div>
        </div>
    );
});

export default ConfirmDialog;
