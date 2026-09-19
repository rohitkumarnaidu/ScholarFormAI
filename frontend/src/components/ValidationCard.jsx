// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React, { memo } from 'react';
import { Map, AlertCircle, ImageOff, Brain } from 'lucide-react';
import Button from '@/src/components/ui/Button';

function ValidationCard({ type = "error", title, description, badge, onAction, onIgnore }) {
    // Styles based on type
    const styles = {
        error: {
            borderClass: "border-red-500",
            iconBg: "bg-red-100 dark:bg-red-950/40",
            iconText: "text-red-600 dark:text-red-400",
            icon: AlertCircle,
            badgeBg: "bg-red-100 dark:bg-red-900/30",
            badgeText: "text-red-600 dark:text-red-400"
        },
        warning: {
            borderClass: "border-amber-400",
            iconBg: "bg-amber-100 dark:bg-amber-950/40",
            iconText: "text-amber-600 dark:text-amber-400",
            icon: ImageOff,
            badgeBg: "bg-amber-100 dark:bg-amber-900/30",
            badgeText: "text-amber-600 dark:text-amber-400"
        },
        advisory: {
            borderClass: "border-primary/20",
            iconBg: "bg-primary",
            iconText: "text-white",
            icon: Brain,
            badgeBg: "bg-primary/20",
            badgeText: "text-primary"
        }
    };

    const s = styles[type] || styles.error;

    return (
        <div className={`bg-white dark:bg-slate-900 border-l-4 ${s.borderClass} rounded-lg p-5 shadow-sm hover:shadow-md transition-shadow group`}>
            <div className="flex gap-4">
                <div className={`${s.iconBg} ${s.iconText} h-10 w-10 rounded-lg flex items-center justify-center shrink-0`}>
                    <s.icon className="w-5 h-5" />
                </div>
                <div className="flex-1">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-1">
                        <h3 className="font-bold text-slate-900 dark:text-white">{title}</h3>
                        <span className={`${s.badgeBg} ${s.badgeText} text-[10px] font-black uppercase px-2 py-0.5 rounded w-fit`}>{badge}</span>
                    </div>
                    <p className="text-slate-600 dark:text-slate-400 text-sm leading-relaxed">{description}</p>
                    <div className="mt-4 flex flex-wrap items-center gap-3 sm:gap-4">
                        <Button variant="link" className="p-0 h-auto text-primary text-xs font-bold flex items-center gap-1" onClick={onAction}>
                            <Map className="text-xs" />
                            Locate in doc
                        </Button>
                        <Button
                            variant="link"
                            className="p-0 h-auto text-slate-500 text-xs font-bold hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
                            onClick={() => onIgnore?.({ type, title, description, badge })}
                        >
                            Ignore
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default memo(ValidationCard);
