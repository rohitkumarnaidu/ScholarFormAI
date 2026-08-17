// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import { useRef, useEffect, useLayoutEffect } from 'react';
import { FileText } from 'lucide-react';

const ALLOWED_TAGS = new Set([
    'p', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'a', 'img', 'ul', 'ol', 'li', 'table', 'tr', 'td', 'th',
    'thead', 'tbody', 'strong', 'em', 'u', 's', 'br', 'hr',
    'pre', 'code', 'blockquote', 'section', 'article',
]);

const ALLOWED_ATTRS = new Set([
    'href', 'src', 'alt', 'title', 'class', 'id', 'style', 'target', 'rel',
]);

const BAD_URI_SCHEMES = /^javascript\s*:|^data\s*:|^vbscript\s*:/i;

function sanitizeNode(node, doc) {
    // Text node — keep as-is
    if (node.nodeType === 3) return doc.createTextNode(node.nodeValue);

    // Only process element nodes
    if (node.nodeType !== 1) return null;

    const tag = node.tagName.toLowerCase();

    // Strip dangerous elements entirely
    if (/^(script|iframe|object|embed|applet|style|link|meta|base|noscript|frame|frameset|svg|math)$/.test(tag)) {
        return null;
    }

    // For disallowed tags, strip the tag but keep children
    if (!ALLOWED_TAGS.has(tag)) {
        const fragment = doc.createDocumentFragment();
        for (const child of node.childNodes) {
            const sanitized = sanitizeNode(child, doc);
            if (sanitized) fragment.appendChild(sanitized);
        }
        return fragment;
    }

    // Allowed tag — create clean element and filter attributes
    const newEl = doc.createElement(tag);

    for (const attr of node.attributes) {
        const name = attr.name.toLowerCase();

        // Strip event handlers (on*)
        if (/^on\w+$/.test(name) || name === 'on') continue;

        // Only allow whitelisted attributes
        if (!ALLOWED_ATTRS.has(name)) continue;

        // Strip dangerous URI schemes in link-type attributes
        if (/^(href|src|action)$/.test(name) && BAD_URI_SCHEMES.test(attr.value.trim())) continue;

        newEl.setAttribute(name, attr.value);
    }

    // Recurse into children
    for (const child of node.childNodes) {
        const sanitized = sanitizeNode(child, doc);
        if (sanitized) newEl.appendChild(sanitized);
    }

    return newEl;
}

function sanitizeHtml(rawHtml) {
    if (!rawHtml || typeof rawHtml !== 'string') return '';

    // Wrap in a known root so DOMParser always produces a valid tree
    const parser = new DOMParser();
    const doc = parser.parseFromString('<div id="__sf_sanitize_root">' + rawHtml + '</div>', 'text/html');
    const root = doc.getElementById('__sf_sanitize_root');
    if (!root) return '';

    const fragment = doc.createDocumentFragment();
    for (const child of root.childNodes) {
        const sanitized = sanitizeNode(child, doc);
        if (sanitized) fragment.appendChild(sanitized);
    }

    const wrapper = doc.createElement('div');
    wrapper.appendChild(fragment);
    return wrapper.innerHTML;
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
                    <div className="mx-auto max-w-full max-w-[780px] min-h-full bg-white rounded-lg shadow-lg border border-slate-200 p-6 sm:p-10 lg:p-14 transition-opacity duration-200 preview-document">
                        <div
                            className="prose max-w-none prose-slate prose-h1:text-2xl prose-h2:text-xl prose-h3:text-lg font-serif text-[15px] text-slate-900"
                            dangerouslySetInnerHTML={{ __html: sanitized }}
                        />
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center h-full text-center py-20 text-slate-400 dark:text-slate-600 select-none">
                        <FileText className="text-[48px] mb-3 opacity-30" />
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
