// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React, { memo } from 'react';
import Link from 'next/link';

export const StatsCard = memo(function StatsCard({ 
    title, 
    value, 
    description, 
    icon, 
    iconColor, 
    bgColor, 
    hoverBgColor, 
    href, 
    btnText, 
    isDisabled = false,
    onBtnClick
}) {
    const Content = (
        <>
            <div className={`h-48 w-full ${bgColor} flex items-center justify-center ${hoverBgColor} transition-colors`}>
                <span className={`material-symbols-outlined ${iconColor} text-5xl`}>{icon}</span>
            </div>
            <div className="p-6">
                <div className="flex justify-between items-start mb-2">
                    <h3 className="text-slate-900 dark:text-white text-lg font-bold">{title}</h3>
                    {value !== undefined && (
                        <span className="bg-primary/20 text-primary text-[10px] font-bold px-2 py-1 rounded-full uppercase tracking-wider">{value}</span>
                    )}
                </div>
                <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed mb-4">{description}</p>
                {href ? (
                    <div className="w-full bg-primary text-white py-2.5 px-4 rounded-lg font-bold text-sm hover:bg-blue-700 transition-colors flex items-center justify-center gap-2 text-center">
                        <span className="material-symbols-outlined text-sm">add</span>
                        {btnText}
                    </div>
                ) : (
                    <button
                        onClick={onBtnClick}
                        disabled={isDisabled}
                        className="w-full bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white py-2.5 px-4 rounded-lg font-bold text-sm hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {btnText}
                    </button>
                )}
            </div>
        </>
    );

    if (href) {
        return (
            <Link href={href} className="group flex flex-col bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden hover:shadow-xl hover:-translate-y-1 transition-all duration-300 cursor-pointer">
                {Content}
            </Link>
        );
    }

    return (
        <div className="group flex flex-col bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
            {Content}
        </div>
    );
});

StatsCard.displayName = 'StatsCard';
