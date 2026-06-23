// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React, { memo } from 'react';

const CategoryTabs = memo(function CategoryTabs() {
    return (
        <div className="flex flex-col items-center gap-4">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white text-center">Select Category</h2>
            <div className="w-full flex justify-center">
                <div className="w-full max-w-[920px] overflow-x-auto pb-1">
                    <div className="flex min-w-max justify-center gap-2 bg-slate-100 surface-ladder-10 border border-slate-200 dark:border-slate-700/70 surface-ladder-border-10 p-1.5 rounded-xl shadow-inner mx-auto">
                        <button className="w-[200px] sm:w-[220px] py-2.5 rounded-lg bg-primary text-white text-sm font-bold shadow-sm transition-all whitespace-nowrap">
                            Documents
                        </button>
                        <button
                            disabled
                            aria-disabled="true"
                            className="w-[200px] sm:w-[220px] py-2.5 rounded-lg text-slate-500 dark:text-slate-400 text-sm font-medium bg-slate-200/50 dark:bg-white/5 surface-ladder-06 cursor-not-allowed opacity-80 inline-flex items-center justify-center gap-2 whitespace-nowrap"
                        >
                            <span>Resume</span>
                            <span className="text-xs bg-gray-200 dark:bg-white/10 px-2 py-0.5 rounded">
                                Coming Soon
                            </span>
                        </button>
                        <button
                            disabled
                            aria-disabled="true"
                            className="w-[200px] sm:w-[220px] py-2.5 rounded-lg text-slate-500 dark:text-slate-400 text-sm font-medium bg-slate-200/50 dark:bg-white/5 surface-ladder-06 cursor-not-allowed opacity-80 inline-flex items-center justify-center gap-2 whitespace-nowrap"
                        >
                            <span>Portfolio</span>
                            <span className="text-xs bg-gray-200 dark:bg-white/10 px-2 py-0.5 rounded">
                                Coming Soon
                            </span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
});

CategoryTabs.displayName = 'CategoryTabs';

export default CategoryTabs;
