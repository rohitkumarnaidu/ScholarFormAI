// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { useEffect, useRef } from 'react';

export default function DeleteConfirmDialog({ isOpen, onConfirm, onCancel, documentName, isDeleting }) {
    const dialogRef = useRef(null);

    useEffect(() => {
        if (isOpen) {
            dialogRef.current?.focus();
        }
    }, [isOpen]);

    useEffect(() => {
        if (!isOpen) return;
        const dialogNode = dialogRef.current;
        if (!dialogNode) return;

        const handleKeydown = (e) => {
            if (e.key === 'Escape' && !isDeleting) {
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
    }, [isOpen, isDeleting, onCancel]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div
                ref={dialogRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby="delete-dialog-title"
                tabIndex={-1}
                className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 p-6 max-w-md w-full mx-4 animate-in fade-in zoom-in"
            >
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                        <span className="material-symbols-outlined text-red-600 dark:text-red-400">warning</span>
                    </div>
                    <h3 id="delete-dialog-title" className="text-lg font-bold text-slate-900 dark:text-white">
                        Delete Document
                    </h3>
                </div>

                <p className="text-slate-600 dark:text-slate-400 mb-6">
                    Are you sure you want to delete{' '}
                    <span className="font-semibold text-slate-900 dark:text-white">
                        {documentName || 'this document'}
                    </span>
                    ? This action cannot be undone.
                </p>

                <div className="flex gap-3 justify-end">
                    <button
                        onClick={onCancel}
                        disabled={isDeleting}
                        className="px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors disabled:opacity-50"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onConfirm}
                        disabled={isDeleting}
                        className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
                    >
                        {isDeleting ? (
                            <>
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                Deleting...
                            </>
                        ) : (
                            <>
                                <span className="material-symbols-outlined text-sm">delete</span>
                                Delete
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
