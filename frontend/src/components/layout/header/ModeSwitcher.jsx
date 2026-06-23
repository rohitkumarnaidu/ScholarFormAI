// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

export default function ModeSwitcher({ activeMode, onChange, compact = false }) {
    // A clean, pill-shaped wrapper matching Perplexity's aesthetic
    const baseWrapper = 'relative flex items-center rounded-full bg-slate-100/80 dark:bg-white/5 surface-ladder-06 p-1 border border-slate-200/50 dark:border-white/10 surface-ladder-border-10 shadow-inner transition-colors';

    // Base option styles with precise text color for inactive states
    const baseOption = `relative z-10 font-bold transition-all duration-300 flex items-center justify-center gap-2 cursor-pointer
        text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200
        peer-checked:text-slate-900 dark:peer-checked:text-white 
        rounded-full ${compact ? 'py-1.5 px-4 text-xs' : 'py-2 px-5 text-sm min-w-[124px]'}`;

    return (
        <div className={baseWrapper}>
            {/* Sliding highlighted background indicator */}
            <div
                className={`absolute top-1 bottom-1 w-[calc(50%-4px)] bg-white dark:bg-white/10 surface-ladder-14 rounded-full shadow-[0_2px_8px_rgba(0,0,0,0.08)] dark:shadow-[0_2px_8px_rgba(0,0,0,0.3)] transition-transform duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)] ${activeMode === 'formatter' ? 'translate-x-0' : 'translate-x-[calc(100%+8px)]'
                    }`}
            />

            <label className="flex-1 relative cursor-pointer">
                <input
                    type="radio"
                    name={compact ? 'mode-mobile' : 'mode'}
                    className="peer sr-only"
                    checked={activeMode === 'formatter'}
                    onChange={() => onChange('formatter')}
                    aria-label="Formatter Mode"
                />
                <div className={baseOption}>
                    <span className={`material-symbols-outlined ${compact ? 'text-[16px]' : 'text-[18px]'}`}>format_align_left</span>
                    Formatter
                </div>
            </label>
            <label className="flex-1 relative cursor-pointer">
                <input
                    type="radio"
                    name={compact ? 'mode-mobile' : 'mode'}
                    className="peer sr-only"
                    checked={activeMode === 'generator'}
                    onChange={() => onChange('generator')}
                    aria-label="Generator Mode"
                />
                <div className={baseOption}>
                    <span className={`material-symbols-outlined animate-pulse-slow ${compact ? 'text-[16px]' : 'text-[18px]'}`}>auto_awesome</span>
                    Generator
                </div>
            </label>
        </div>
    );
}
