// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import DOMPurify from 'dompurify';

let hookAdded = false;

/**
 * Securely sanitizes HTML strings for safe rendering using DOMPurify.
 * - Enforces the HTML profile (stripping MathML and SVG unless explicitly allowed).
 * - Forbids execution vectors (script, iframe, object, form, etc.).
 * - Strips unsafe inline event handlers (onerror, onload, etc.).
 * - Ensures any target="_blank" links automatically get rel="noopener noreferrer".
 */
export function sanitizeHtml(html: string): string {
    if (typeof window === 'undefined') {
        return '';
    }
    
    if (!hookAdded) {
        DOMPurify.addHook('afterSanitizeAttributes', function(node) {
            if ('target' in node && node.getAttribute('target') === '_blank') {
                node.setAttribute('rel', 'noopener noreferrer');
            }
        });
        hookAdded = true;
    }

    return DOMPurify.sanitize(html || '', {
        USE_PROFILES: { html: true },
        FORBID_TAGS: ['script', 'style', 'iframe', 'frame', 'object', 'embed', 'form', 'base', 'applet', 'meta', 'link'],
        FORBID_ATTR: [
            'onerror', 'onload', 'onclick', 'onmouseover', 'onmouseout', 'onfocus', 'onblur', 'onchange', 'onsubmit', 'onkeydown', 'onkeypress', 'onkeyup'
        ],
        ADD_ATTR: ['target'],
    });
}
