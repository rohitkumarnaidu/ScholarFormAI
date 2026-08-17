// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React, { memo } from 'react';
import { FileText, LayoutTemplate, ListOrdered, ListTree, RefreshCw, Rocket, Scaling, Sliders } from 'lucide-react';

const FormattingOptions = memo(function FormattingOptions({
    addPageNumbers,
    setAddPageNumbers,
    addBorders,
    setAddBorders,
    addCoverPage,
    setAddCoverPage,
    generateTOC,
    setGenerateTOC,
    pageSize,
    setPageSize,
    isProcessing,
    progress,
    file,
    onProcess,
}) {
    return (
        <div className="bg-white rounded-xl border border-slate-200 dark:border-slate-700/70 p-6 shadow-sm hover:shadow-md dark:hover:shadow-none transition-shadow">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-6 flex items-center gap-2">
                <Sliders className="text-primary" />
                2. Formatting Options
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="flex flex-col gap-4">
                    <div className="flex items-center justify-between p-3 rounded-lg border border-slate-100 dark:border-slate-700/70 bg-slate-50 hover:bg-white hover:shadow-sm dark:hover:shadow-none dark:hover:bg-white/10 transition-all">
                        <div className="flex items-center gap-2">
                            <ListOrdered className="text-slate-500" />
                            <span className="text-sm font-bold text-slate-900 dark:text-white">Add Page Numbers</span>
                        </div>
                        <div className="relative inline-block w-10 align-middle select-none transition duration-200 ease-in">
                            <input
                                checked={addPageNumbers}
                                onChange={(e) => setAddPageNumbers(e.target.checked)}
                                disabled={isProcessing || progress === 100}
                                className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 appearance-none cursor-pointer right-5 checked:right-0 transition-all duration-300 disabled:opacity-50"
                                id="page_numbers"
                                name="toggle"
                                style={{ top: 0, right: addPageNumbers ? '0px' : '20px' }}
                                type="checkbox"
                            />
                            <label className={`toggle-label block overflow-hidden h-5 rounded-full cursor-pointer transition-colors duration-300 ${addPageNumbers ? 'bg-primary' : 'bg-slate-300'}`} htmlFor="page_numbers"></label>
                        </div>
                    </div>

                    <div className="flex items-center justify-between p-3 rounded-lg border border-slate-100 dark:border-slate-700/70 bg-slate-50 hover:bg-white hover:shadow-sm dark:hover:shadow-none dark:hover:bg-white/10 transition-all">
                        <div className="flex items-center gap-2">
                            <LayoutTemplate className="text-slate-500" />
                            <span className="text-sm font-bold text-slate-900 dark:text-white">Add Borders</span>
                        </div>
                        <div className="relative inline-block w-10 align-middle select-none transition duration-200 ease-in">
                            <input
                                checked={addBorders}
                                onChange={(e) => setAddBorders(e.target.checked)}
                                disabled={isProcessing || progress === 100}
                                className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 appearance-none cursor-pointer right-5 checked:right-0 transition-all duration-300 disabled:opacity-50"
                                id="borders"
                                name="toggle"
                                style={{ top: 0, right: addBorders ? '0px' : '20px' }}
                                type="checkbox"
                            />
                            <label className={`toggle-label block overflow-hidden h-5 rounded-full cursor-pointer transition-colors duration-300 ${addBorders ? 'bg-primary' : 'bg-slate-300'}`} htmlFor="borders"></label>
                        </div>
                    </div>
                </div>

                <div className="flex flex-col gap-4">
                    <div className="flex items-center justify-between p-3 rounded-lg border border-slate-100 dark:border-slate-700/70 bg-slate-50 hover:bg-white hover:shadow-sm dark:hover:shadow-none dark:hover:bg-white/10 transition-all">
                        <div className="flex items-center gap-2">
                            <FileText className="text-slate-500" />
                            <span className="text-sm font-bold text-slate-900 dark:text-white">Add Cover Page</span>
                        </div>
                        <div className="relative inline-block w-10 align-middle select-none transition duration-200 ease-in">
                            <input
                                checked={addCoverPage}
                                onChange={(e) => setAddCoverPage(e.target.checked)}
                                disabled={isProcessing || progress === 100}
                                className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 appearance-none cursor-pointer right-5 checked:right-0 transition-all duration-300 disabled:opacity-50"
                                id="cover_page"
                                name="toggle"
                                style={{ top: 0, right: addCoverPage ? '0px' : '20px' }}
                                type="checkbox"
                            />
                            <label className={`toggle-label block overflow-hidden h-5 rounded-full cursor-pointer transition-colors duration-300 ${addCoverPage ? 'bg-primary' : 'bg-slate-300'}`} htmlFor="cover_page"></label>
                        </div>
                    </div>

                    <div className="flex items-center justify-between p-3 rounded-lg border border-slate-100 dark:border-slate-700/70 bg-slate-50 hover:bg-white hover:shadow-sm dark:hover:shadow-none dark:hover:bg-white/10 transition-all">
                        <div className="flex flex-col">
                            <div className="flex items-center gap-2">
                                <ListTree className="text-slate-500" />
                                <span className="text-sm font-bold text-slate-900 dark:text-white">Generate TOC</span>
                            </div>
                            <span className="text-[10px] text-slate-400 pl-8">Auto generates from headings</span>
                        </div>
                        <div className="relative inline-block w-10 align-middle select-none transition duration-200 ease-in">
                            <input
                                checked={generateTOC}
                                onChange={(e) => setGenerateTOC(e.target.checked)}
                                disabled={isProcessing || progress === 100}
                                className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 appearance-none cursor-pointer right-5 checked:right-0 transition-all duration-300 disabled:opacity-50"
                                id="toc"
                                name="toggle"
                                style={{ top: 0, right: generateTOC ? '0px' : '20px' }}
                                type="checkbox"
                            />
                            <label className={`toggle-label block overflow-hidden h-5 rounded-full cursor-pointer transition-colors duration-300 ${generateTOC ? 'bg-primary' : 'bg-slate-300'}`} htmlFor="toc"></label>
                        </div>
                    </div>
                </div>

                <div className="col-span-1 md:col-span-2">
                    <div className="flex flex-col gap-2">
                        <label className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            <Scaling className="text-slate-500" />
                            Page Size
                        </label>
                        <select
                            value={pageSize}
                            onChange={(e) => setPageSize(e.target.value)}
                            disabled={isProcessing || progress === 100}
                            className="w-full p-3 rounded-lg border border-slate-200 dark:border-slate-700/70 bg-slate-50 text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all"
                        >
                            <option value="Letter">Letter (US Default)</option>
                            <option value="A4">A4 (International)</option>
                            <option value="Legal">Legal</option>
                        </select>
                        <p className="text-xs text-slate-500">Your selection becomes the default for future documents.</p>
                    </div>
                </div>
            </div>

            <button
                onClick={onProcess}
                disabled={!file || isProcessing}
                className={`w-full mt-8 bg-primary hover:bg-blue-700 text-white font-bold py-4 rounded-xl shadow-lg shadow-primary/25 flex items-center justify-center gap-3 transition-all transform ${(!file || isProcessing) ? 'opacity-50 cursor-not-allowed' : 'hover:-translate-y-0.5'}`}
            >
                {progress === 100 ? 'replay' : isProcessing ? <RefreshCw /> : <Rocket />}
                {isProcessing ? 'Processing Manuscript...' : progress === 100 ? 'Re-process Manuscript' : 'Process Document'}
            </button>
        </div>
    );
});

FormattingOptions.displayName = 'FormattingOptions';

export default FormattingOptions;
