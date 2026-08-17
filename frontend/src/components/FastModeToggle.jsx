import { Zap } from 'lucide-react';
// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

export default function FastModeToggle({ fastMode, setFastMode, disabled }) {
    return (
        <div className="flex items-center justify-between p-3 rounded-lg border border-amber-200 dark:border-amber-800/50 bg-amber-50 dark:bg-amber-900/20 hover:bg-amber-100 dark:hover:bg-amber-900/30 transition-colors">
            <div className="flex flex-col">
                <div className="flex items-center gap-2">
                    <Zap className="text-amber-600 dark:text-amber-400" />
                    <span className="text-sm font-bold text-slate-900 dark:text-white">Fast Mode</span>
                </div>
                <span className="text-[10px] text-slate-500 dark:text-slate-400 pl-8">
                    Skips AI reasoning &amp; semantic parsing for faster processing
                </span>
            </div>
            <div className="relative inline-block w-10 align-middle select-none transition duration-200 ease-in">
                <input
                    checked={fastMode}
                    onChange={(e) => setFastMode(e.target.checked)}
                    disabled={disabled}
                    className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 appearance-none cursor-pointer right-5 checked:right-0 transition-all duration-300 disabled:opacity-50"
                    id="fast_mode"
                    name="toggle"
                    style={{ top: 0, right: fastMode ? '0px' : '20px' }}
                    type="checkbox"
                />
                <label
                    className={`toggle-label block overflow-hidden h-5 rounded-full cursor-pointer transition-colors duration-300 ${fastMode ? 'bg-amber-500' : 'bg-slate-300'}`}
                    htmlFor="fast_mode"
                />
            </div>
        </div>
    );
}
