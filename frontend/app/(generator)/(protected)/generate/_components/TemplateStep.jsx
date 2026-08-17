// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import { useMemo, useState } from 'react';
import { CheckCircle } from 'lucide-react';

export default function TemplateStep({ selected, onSelect, templates }) {
    const [filter, setFilter] = useState('');
    const [activeCategory, setActiveCategory] = useState('All');

    const categories = useMemo(
        () => ['All', ...new Set(templates.map((entry) => entry.category))],
        [templates]
    );

    const visibleTemplates = useMemo(() => {
        return templates.filter((entry) => {
            const matchesCategory = activeCategory === 'All' || entry.category === activeCategory;
            const query = filter.toLowerCase();
            return matchesCategory && (
                entry.name.toLowerCase().includes(query) ||
                entry.category.toLowerCase().includes(query)
            );
        });
    }, [activeCategory, filter, templates]);

    return (
        <div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">Choose a Template</h2>
            <p className="text-slate-500 dark:text-slate-400 mb-6">Pick the journal or style template for your document.</p>
            <div className="flex flex-col sm:flex-row gap-3 mb-6">
                <input
                    id="template-search"
                    type="text"
                    placeholder="Search templates..."
                    value={filter}
                    onChange={(event) => setFilter(event.target.value)}
                    className="flex-1 bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-2.5 text-slate-900 dark:text-slate-100 placeholder-slate-500 dark:placeholder-slate-500 text-sm focus:outline-none focus:border-primary transition"
                />
                <div className="flex gap-2 flex-wrap">
                    {categories.map((category) => (
                        <button
                            key={category}
                            onClick={() => setActiveCategory(category)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition min-h-[36px] ${activeCategory === category
                                ? 'bg-blue-600 text-white'
                                : 'bg-slate-100 dark:bg-white/5 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-white/10 hover:text-slate-900 dark:hover:text-white'
                                }`}
                        >
                            {category}
                        </button>
                    ))}
                </div>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                {visibleTemplates.map((entry) => (
                    <button
                        key={entry.id}
                        id={`template-${entry.id}`}
                        onClick={() => onSelect(entry.id)}
                        className={`flex flex-col items-start gap-1 p-4 rounded-xl border-2 text-left transition-all duration-150 min-h-[72px] ${selected === entry.id
                            ? 'border-primary bg-primary/10'
                            : 'border-glass-border bg-white/5 hover:border-glass-border/50 hover:bg-white/8'
                            }`}
                    >
                        <span className={`text-xs font-bold uppercase tracking-wider ${selected === entry.id ? 'text-primary-light' : 'text-slate-500'}`}>
                            {entry.category}
                        </span>
                        <span className="text-slate-900 dark:text-slate-100 font-semibold text-sm">{entry.name}</span>
                        {selected === entry.id && (
                            <CheckCircle className="text-primary-light text-sm mt-1" />
                        )}
                    </button>
                ))}
            </div>
        </div>
    );
}
