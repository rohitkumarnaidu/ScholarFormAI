// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React, { memo, useState, useEffect } from 'react';
import Link from 'next/link';
import { fetchTemplates } from '../../services/api.templates';
import { ArrowRight, ChevronDown } from 'lucide-react';

const FALLBACK_OPTIONS = [
    { value: 'none', label: 'None (No formatting)' },
    { value: 'ieee', label: 'IEEE' },
    { value: 'apa', label: 'APA (7th Edition)' },
    { value: 'acm', label: 'ACM' },
    { value: 'springer', label: 'Springer' },
    { value: 'elsevier', label: 'Elsevier' },
    { value: 'nature', label: 'Nature' },
    { value: 'harvard', label: 'Harvard' },
    { value: 'chicago', label: 'Chicago (17th)' },
    { value: 'mla', label: 'MLA (9th)' },
    { value: 'vancouver', label: 'Vancouver' },
    { value: 'numeric', label: 'Numeric' },
    { value: 'modern_blue', label: 'Modern Blue' },
    { value: 'modern_gold', label: 'Modern Gold' },
    { value: 'modern_red', label: 'Modern Red' },
];

const TemplateSelector = memo(function TemplateSelector({
    category,
    template,
    isProcessing,
    file,
    formatFileSize,
    onCategoryChange,
    onTemplateSelect,
}) {
    const [templateOptions, setTemplateOptions] = useState(FALLBACK_OPTIONS);

    useEffect(() => {
        let cancelled = false;
        fetchTemplates().then((templates) => {
            if (cancelled) return;
            const mapped = templates.map((t) => ({
                value: t.id,
                label: t.name,
            }));
            setTemplateOptions(mapped);
        });
        return () => { cancelled = true; };
    }, []);
    const fileMetaText = file ? `${file.name} (${formatFileSize(file.size)})` : 'No file selected';

    return (
        <div>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 w-full sm:w-auto">
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white whitespace-nowrap">Select Template</h2>

                    <div className="relative w-full sm:w-64 group">
                        <select
                            value={category}
                            onChange={(e) => onCategoryChange(e.target.value)}
                            disabled={isProcessing}
                            className="template-selector-trigger w-full h-10 rounded-lg border border-slate-200 dark:border-slate-700/70 bg-white dark:bg-slate-900 pl-3 pr-8 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none appearance-none disabled:opacity-50 transition-all font-medium cursor-pointer"
                        >
                            {templateOptions.map((option) => (
                                <option key={option.value} value={option.value}>
                                    {option.label}
                                </option>
                            ))}
                        </select>
                        <div className="pointer-events-none absolute inset-y-0 right-3 flex items-center">
                            <ChevronDown className="text-[18px] text-slate-500 dark:text-slate-400" />
                        </div>
                    </div>
                </div>

                <Link className="text-sm font-medium text-primary hover:underline flex items-center gap-1 shrink-0" href="/templates">
                    Browse Library <ArrowRight className="text-[16px]" />
                </Link>
            </div>

            {/* Template preview cards intentionally commented out for now.
                Keeping only the dropdown selector and browse action. */}
            <div className="sr-only" aria-hidden="true">
                <span>{fileMetaText}</span>
                <span>{template}</span>
                <span>{typeof onTemplateSelect === 'function' ? 'template-select-enabled' : 'template-select-disabled'}</span>
            </div>
        </div>
    );
});

TemplateSelector.displayName = 'TemplateSelector';

export default TemplateSelector;
