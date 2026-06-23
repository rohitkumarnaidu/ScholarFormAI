// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

export default function ToggleSwitch({ id, label, sublabel, checked, onChange }) {
    return (
        <div className="flex items-center justify-between p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800">
            <div className="flex flex-col">
                <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">{label}</span>
                <span className="text-xs text-slate-500">{sublabel}</span>
            </div>
            <div className="relative inline-block w-12 align-middle select-none transition duration-200 ease-in">
                <input
                    type="checkbox"
                    name="toggle"
                    id={id}
                    checked={checked}
                    onChange={onChange}
                    className="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white border-4 appearance-none cursor-pointer right-6 checked:right-0 transition-all duration-300"
                    style={{ top: 0 }}
                />
                <label
                    htmlFor={id}
                    className="toggle-label block overflow-hidden h-6 rounded-full bg-slate-300 cursor-pointer transition-colors duration-300"
                ></label>
            </div>
        </div>
    );
}
