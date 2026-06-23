// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import { useRef, useEffect, useLayoutEffect } from 'react';

// Basic HTML sanitization — strips <script> tags and event handlers
function sanitizeHtml(rawHtml) {
    if (!rawHtml || typeof rawHtml !== 'string') return '';
    return rawHtml
        .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
        .replace(/\son\w+\s*=\s*["'][^"']*["']/gi, '')
        .replace(/\son\w+\s*=\s*[^\s>]+/gi, '');
}

/**
 * PreviewPane – renders backend-supplied HTML in a sandboxed document-style container.
 *
 * Props:
 *  html      {string}  – Raw HTML from backend
 *  isLoading {boolean} – Show "Analyzing…" overlay
 */
export default function PreviewPane({ html, isLoading }) {
    const containerRef = useRef(null);
    const scrollTopRef = useRef(0);

    // Save scroll position before html update
    useEffect(() => {
        const el = containerRef.current;
        if (el) scrollTopRef.current = el.scrollTop;
    }, [html]);

    // Restore scroll position after DOM update
    useLayoutEffect(() => {
        const el = containerRef.current;
        if (el) el.scrollTop = scrollTopRef.current;
    }, [html]);

    const sanitized = sanitizeHtml(html);

    return (
        <div className="relative h-full flex flex-col bg-slate-100 dark:bg-slate-950 overflow-hidden">
            {/* Scroll container */}
            <div
                ref={containerRef}
                className="flex-1 overflow-y-auto overflow-x-hidden p-4 sm:p-6 scroll-smooth"
                aria-label="Document preview"
            >
                {sanitized ? (
                    <div className="mx-auto max-w-[780px] min-h-full bg-white rounded-lg shadow-lg border border-slate-200 p-6 sm:p-10 lg:p-14 transition-opacity duration-200 preview-document">
                        <div
                            className="prose max-w-none prose-slate prose-h1:text-2xl prose-h2:text-xl prose-h3:text-lg font-serif text-[15px] text-slate-900"
                            dangerouslySetInnerHTML={{ __html: sanitized }}
                        />
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center h-full text-center py-20 text-slate-400 dark:text-slate-600 select-none">
                        <span className="material-symbols-outlined text-[48px] mb-3 opacity-30">article</span>
                        <p className="text-sm font-medium">Preview will appear here as you type</p>
                    </div>
                )}
            </div>

            {/* Analyzing overlay */}
            {isLoading && (
                <div className="absolute inset-0 flex items-center justify-center bg-white/60 dark:bg-slate-900/60 backdrop-blur-sm z-10 transition-opacity duration-200">
                    <div className="flex items-center gap-3 px-5 py-3 rounded-xl bg-white dark:bg-slate-800 shadow-lg border border-slate-200 dark:border-slate-700">
                        <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                        <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">Analyzing…</span>
                    </div>
                </div>
            )}
        </div>
    );
}
