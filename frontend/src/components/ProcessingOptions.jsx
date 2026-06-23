// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

const EXPORT_FORMAT_OPTIONS = [
    { value: 'docx', label: 'DOCX (.docx)' },
    { value: 'pdf', label: 'PDF (.pdf)' },
    { value: 'tex', label: 'LaTeX (.tex)' },
];

export default function ProcessingOptions({
    selectedFormat = 'docx',
    onFormatChange,
    disabled = false,
    label = 'Export format',
}) {
    return (
        <div className="flex flex-col gap-2">
            <label
                htmlFor="export-format"
                className="text-sm font-semibold text-slate-900 dark:text-slate-100"
            >
                {label}
            </label>

            <select
                id="export-format"
                name="export-format"
                value={selectedFormat}
                disabled={disabled}
                onChange={(event) => onFormatChange?.(event.target.value)}
                data-testid="export-format-select"
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 disabled:opacity-60 disabled:cursor-not-allowed"
            >
                {EXPORT_FORMAT_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                        {option.label}
                    </option>
                ))}
            </select>
        </div>
    );
}
