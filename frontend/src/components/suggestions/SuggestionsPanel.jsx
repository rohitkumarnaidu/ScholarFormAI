// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import React, { memo, useCallback, useEffect } from 'react';
import Skeleton from '@/components/ui/Skeleton';
import SuggestionCard from './SuggestionCard';

const SuggestionsPanel = memo(function SuggestionsPanel({
    suggestions = [],
    onAccept,
    onReject,
    onDismiss,
    isOpen = false,
    onClose,
    loading = false,
}) {
    const handleKeyDown = useCallback((e) => {
        if (e.key === 'Escape') onClose?.();
    }, [onClose]);

    useEffect(() => {
        if (isOpen) {
            document.addEventListener('keydown', handleKeyDown);
            return () => document.removeEventListener('keydown', handleKeyDown);
        }
    }, [isOpen, handleKeyDown]);

    if (!isOpen) return null;

    return (
        <>
            <div
                className="fixed inset-0 bg-black/20 z-40 animate-in fade-in duration-200"
                onClick={onClose}
            />
            <div className="fixed top-0 right-0 h-full w-full sm:w-96 bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-2xl z-50 flex flex-col">
                <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-800">
                    <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-primary">auto_awesome</span>
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white">AI Suggestions</h2>
                        {!loading && (
                            <span className="text-xs font-semibold bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded text-slate-500">
                                {suggestions.length}
                            </span>
                        )}
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                        aria-label="Close suggestions panel"
                    >
                        <span className="material-symbols-outlined">close</span>
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {loading ? (
                        <>
                            {Array.from({ length: 3 }).map((_, i) => (
                                <div key={`sp-sk-${i}`} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4">
                                    <div className="flex justify-between mb-3">
                                        <Skeleton className="h-5 w-16 rounded" />
                                        <Skeleton className="h-4 w-10" />
                                    </div>
                                    <Skeleton className="h-1.5 w-full rounded-full mb-3" />
                                    <Skeleton className="h-3 w-12 mb-1" />
                                    <Skeleton className="h-4 w-full mb-1" />
                                    <Skeleton className="h-4 w-3/4 mb-3" />
                                    <Skeleton className="h-3 w-12 mb-1" />
                                    <Skeleton className="h-4 w-full mb-1" />
                                    <Skeleton className="h-4 w-2/3 mb-4" />
                                    <div className="flex gap-2">
                                        <Skeleton className="h-7 flex-1 rounded-lg" />
                                        <Skeleton className="h-7 flex-1 rounded-lg" />
                                        <Skeleton className="h-7 w-7 rounded-lg" />
                                    </div>
                                </div>
                            ))}
                        </>
                    ) : suggestions.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                            <span className="material-symbols-outlined text-4xl text-slate-300 dark:text-slate-600 mb-3">auto_awesome</span>
                            <h3 className="text-base font-semibold text-slate-900 dark:text-white mb-1">No suggestions yet</h3>
                            <p className="text-sm text-slate-500 dark:text-slate-400">AI suggestions will appear here as you edit your document.</p>
                        </div>
                    ) : (
                        suggestions.map((suggestion) => (
                            <SuggestionCard
                                key={suggestion.id}
                                suggestion={suggestion}
                                onAccept={onAccept}
                                onReject={onReject}
                                onDismiss={onDismiss}
                            />
                        ))
                    )}
                </div>

                {!loading && suggestions.length > 0 && (
                    <div className="p-4 border-t border-slate-200 dark:border-slate-800">
                        <p className="text-xs text-center text-slate-400 dark:text-slate-500">
                            Press <kbd className="px-1 py-0.5 bg-slate-100 dark:bg-slate-800 rounded text-xs font-mono">Esc</kbd> to close
                        </p>
                    </div>
                )}
            </div>
        </>
    );
});

SuggestionsPanel.displayName = 'SuggestionsPanel';

export default SuggestionsPanel;
