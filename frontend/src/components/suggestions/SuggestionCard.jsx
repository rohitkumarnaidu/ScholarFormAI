// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import React, { memo, useState, useCallback } from 'react';

import { cn } from '@/src/lib/utils';

const TYPE_COLORS = {
    style: { badge: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400', label: 'Style' },
    grammar: { badge: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400', label: 'Grammar' },
    structure: { badge: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400', label: 'Structure' },
    citation: { badge: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400', label: 'Citation' },
    clarity: { badge: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400', label: 'Clarity' },
};

const SCORE_COLORS = [
    { max: 50, bar: 'bg-red-500', text: 'text-red-600 dark:text-red-400' },
    { max: 70, bar: 'bg-yellow-500', text: 'text-yellow-600 dark:text-yellow-400' },
    { max: 100, bar: 'bg-green-500', text: 'text-green-600 dark:text-green-400' },
];

function getScoreColor(score) {
    if (typeof score !== 'number') return SCORE_COLORS[2];
    return SCORE_COLORS.find(s => score <= s.max) || SCORE_COLORS[2];
}

const EXPAND_THRESHOLD = 120;

const SuggestionCard = memo(function SuggestionCard({ suggestion, onAccept, onReject, onDismiss }) {
    const [expanded, setExpanded] = useState(false);
    const [animatingOut, setAnimatingOut] = useState(false);

    const typeInfo = TYPE_COLORS[suggestion.type] || { badge: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400', label: suggestion.type || 'Unknown' };
    const scoreInfo = getScoreColor(suggestion.score);
    const scoreWidth = typeof suggestion.score === 'number' ? Math.min(Math.max(suggestion.score, 0), 100) : 0;

    const originalLong = suggestion.originalText && suggestion.originalText.length > EXPAND_THRESHOLD;
    const showExpand = originalLong;

    const handleAccept = useCallback(() => {
        setAnimatingOut(true);
        onAccept?.(suggestion.id);
    }, [onAccept, suggestion.id]);

    const handleReject = useCallback(() => {
        setAnimatingOut(true);
        onReject?.(suggestion.id);
    }, [onReject, suggestion.id]);

    const handleDismiss = useCallback(() => {
        setAnimatingOut(true);
        onDismiss?.(suggestion.id);
    }, [onDismiss, suggestion.id]);

    return (
        <div className={cn(
            'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm transition-all duration-200',
            animatingOut ? 'opacity-0 scale-95' : 'opacity-100 animate-in fade-in slide-in-from-right duration-300'
        )}>
            <div className="flex items-start justify-between mb-3">
                <span className={cn('inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider', typeInfo.badge)}>
                    {typeInfo.label}
                </span>
                <span className={cn('text-xs font-bold', scoreInfo.text)}>
                    {typeof suggestion.score === 'number' ? `${Math.round(suggestion.score)}%` : 'N/A'}
                </span>
            </div>

            <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full mb-3">
                <div
                    className={cn('h-full rounded-full transition-all', scoreInfo.bar)}
                    style={{ width: `${scoreWidth}%` }}
                />
            </div>

            {suggestion.originalText && (
                <div className="mb-2">
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-0.5">Original</p>
                    <p className={cn(
                        'text-sm text-slate-600 dark:text-slate-300 line-through',
                        !expanded && showExpand ? 'line-clamp-2' : ''
                    )}>
                        {suggestion.originalText}
                    </p>
                    {showExpand && (
                        <button
                            onClick={() => setExpanded(!expanded)}
                            className="text-xs text-primary hover:underline mt-0.5"
                        >
                            {expanded ? 'Show less' : 'Show more'}
                        </button>
                    )}
                </div>
            )}

            {suggestion.suggestedText && (
                <div className="mb-4">
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-0.5">Suggested</p>
                    <p className="text-sm text-slate-900 dark:text-white bg-green-50 dark:bg-green-900/10 rounded-lg p-2 border border-green-100 dark:border-green-900/30">
                        {suggestion.suggestedText}
                    </p>
                </div>
            )}

            <div className="flex gap-2">
                <button
                    onClick={handleAccept}
                    className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg bg-green-600 hover:bg-green-700 text-white font-semibold text-xs transition-colors"
                >
                    <span className="material-symbols-outlined text-[14px]">check</span>
                    Accept
                </button>
                <button
                    onClick={handleReject}
                    className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 font-semibold text-xs transition-colors"
                >
                    <span className="material-symbols-outlined text-[14px]">close</span>
                    Reject
                </button>
                <button
                    onClick={handleDismiss}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                    title="Dismiss"
                >
                    <span className="material-symbols-outlined text-[16px]">more_horiz</span>
                </button>
            </div>
        </div>
    );
});

SuggestionCard.displayName = 'SuggestionCard';

export default SuggestionCard;
export { TYPE_COLORS, SCORE_COLORS };
