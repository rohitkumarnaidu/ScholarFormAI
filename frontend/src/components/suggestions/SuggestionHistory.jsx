// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import React, { memo, useState, useMemo, useCallback } from 'react';
import EmptyState from '@/src/components/ui/EmptyState';

const cx = (...classes) => classes.filter(Boolean).join(' ');

const STATUS_TABS = [
    { key: 'all', label: 'All' },
    { key: 'accepted', label: 'Accepted' },
    { key: 'rejected', label: 'Rejected' },
    { key: 'dismissed', label: 'Dismissed' },
];

const STATUS_COLORS = {
    accepted: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    rejected: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    dismissed: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
};

const TYPE_COLORS = {
    style: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    grammar: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    structure: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
    citation: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
    clarity: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
};

function formatDate(ts) {
    if (!ts) return '';
    return new Date(ts).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

const SuggestionHistory = memo(function SuggestionHistory({
    history = [],
}) {
    const [activeFilter, setActiveFilter] = useState('all');

    const filtered = useMemo(() => {
        if (activeFilter === 'all') return history;
        return history.filter(item => item.status === activeFilter);
    }, [history, activeFilter]);

    const handleFilterChange = useCallback((key) => {
        setActiveFilter(key);
    }, []);

    return (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-200 dark:border-slate-800">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-3 flex items-center gap-2">
                    <span className="material-symbols-outlined text-primary text-lg">history</span>
                    Suggestion History
                </h3>
                <div className="flex gap-1">
                    {STATUS_TABS.map(tab => (
                        <button
                            key={tab.key}
                            onClick={() => handleFilterChange(tab.key)}
                            className={cx(
                                'px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors',
                                activeFilter === tab.key
                                    ? 'bg-primary text-white'
                                    : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                            )}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            <div className="divide-y divide-slate-100 dark:divide-slate-800/50 max-h-96 overflow-y-auto">
                {filtered.length === 0 ? (
                    <div className="py-8">
                        <EmptyState
                            icon="history"
                            title={activeFilter === 'all' ? 'No suggestion history' : `No ${activeFilter} suggestions`}
                            description="Past suggestions will appear here after you review them."
                        />
                    </div>
                ) : (
                    filtered.map((item) => (
                        <div key={item.id} className="p-4 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                            <div className="flex items-start justify-between mb-2">
                                <div className="flex gap-2 items-center">
                                    <span className={cx(
                                        'inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider',
                                        TYPE_COLORS[item.type] || 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                                    )}>
                                        {item.type || 'Unknown'}
                                    </span>
                                    <span className={cx(
                                        'inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold',
                                        STATUS_COLORS[item.status] || 'bg-slate-100 text-slate-600'
                                    )}>
                                        {item.status}
                                    </span>
                                </div>
                                {item.actionedAt && (
                                    <span className="text-[10px] text-slate-400 shrink-0">{formatDate(item.actionedAt)}</span>
                                )}
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <p className="text-[10px] font-semibold text-slate-400 mb-0.5 uppercase">Original</p>
                                    <p className="text-xs text-slate-600 dark:text-slate-300 line-clamp-2">{item.originalText}</p>
                                </div>
                                <div>
                                    <p className="text-[10px] font-semibold text-slate-400 mb-0.5 uppercase">Result</p>
                                    <p className="text-xs text-slate-900 dark:text-white line-clamp-2">{item.suggestedText || item.acceptedText || item.result}</p>
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
});

SuggestionHistory.displayName = 'SuggestionHistory';

export default SuggestionHistory;
