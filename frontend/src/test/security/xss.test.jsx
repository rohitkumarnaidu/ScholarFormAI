// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { sanitizeText, sanitizePayload } from '../../services/api.core';
import PreviewPane from '../../components/live-preview/PreviewPane';

describe('sanitizeText XSS prevention', () => {
    it('removes angle brackets from <script> tags', () => {
        const input = '<script>alert("xss")</script>Hello';
        const result = sanitizeText(input);
        expect(result).not.toMatch(/[<>]/);
        expect(result).toContain('Hello');
    });

    it('removes angle brackets from event handlers (onerror=, onload=, onclick=)', () => {
        const inputs = [
            '<img src=x onerror=alert(1)>Hello',
            '<div onload="evil()">Hello</div>',
            '<button onclick=\'steal()\'>Hello</button>',
        ];
        for (const input of inputs) {
            const result = sanitizeText(input);
            expect(result).not.toMatch(/[<>]/);
            expect(result).toContain('Hello');
        }
    });

    it('removes angle brackets from javascript: URLs', () => {
        const inputs = [
            '<a href="javascript:alert(1)">link</a>',
            'javascript:void(0)',
            'JavaScript:document.cookie',
        ];
        for (const input of inputs) {
            const result = sanitizeText(input);
            expect(result).not.toMatch(/[<>]/);
        }
    });

    it('allows safe HTML entities', () => {
        const result = sanitizeText('He said &quot;hello&quot; &amp; waved');
        expect(result).toContain('"hello"');
        expect(result).toContain('&');
        expect(result).not.toMatch(/&quot;/);
        expect(result).not.toMatch(/&amp;/);
    });

    it('handles control characters', () => {
        const input = 'Hello\x00World\x1F\x7FTest';
        expect(sanitizeText(input)).toBe('HelloWorldTest');
    });

    it('handles unicode XSS variants', () => {
        const inputs = [
            '\uFF1Cscript\uFF1Ealert(1)\uFF1C/script\uFF1E',
            '\u003Cscript\u003E',
            '<scr\u0069pt>',
        ];
        for (const input of inputs) {
            const result = sanitizeText(input);
            expect(result).not.toMatch(/[<>]/);
        }
    });

    it('handles long malicious strings without throwing', () => {
        const longPayload = '<script>' + 'A'.repeat(10000) + '</script>B';
        const result = sanitizeText(longPayload);
        expect(result).not.toMatch(/[<>]/);
        expect(result.length).toBeLessThan(longPayload.length);
    });
});

describe('sanitizeHtml XSS prevention (PreviewPane)', () => {
    it('prevents XSS via <img src=x onerror=alert(1)>', () => {
        render(
            <PreviewPane
                html='<img src=x onerror=alert(1)><p>Safe</p>'
                isLoading={false}
            />
        );
        expect(screen.getByText('Safe')).toBeInTheDocument();
        expect(screen.queryByText(/alert/i)).not.toBeInTheDocument();
    });

    it('prevents XSS via <svg onload=alert(1)>', () => {
        render(
            <PreviewPane
                html='<svg onload=alert(1)><p>Safe</p></svg>'
                isLoading={false}
            />
        );
        expect(screen.getByText('Safe')).toBeInTheDocument();
    });

    it('prevents DOM clobbering via <form name=body>', () => {
        render(
            <PreviewPane
                html='<form name="body"><input name="innerHTML"></form><p>Safe</p>'
                isLoading={false}
            />
        );
        expect(screen.getByText('Safe')).toBeInTheDocument();
    });

    it('prevents template injection {{constructor}}', () => {
        render(
            <PreviewPane
                html='<p>{{constructor.constructor("alert(1)")()}}</p><p>Safe</p>'
                isLoading={false}
            />
        );
        expect(screen.getByText('Safe')).toBeInTheDocument();
    });
});

describe('sanitizePayload deep sanitization', () => {
    it('recursively removes angle brackets in nested objects', () => {
        const payload = {
            title: '<script>evil()</script>Hello',
            meta: {
                description: '<img src=x onerror=steal()>desc',
                tags: ['<script>a</script>tag1', 'safe'],
            },
        };
        const result = sanitizePayload(payload);
        expect(result.title).not.toMatch(/[<>]/);
        expect(result.title).toContain('Hello');
        expect(result.meta.description).not.toMatch(/[<>]/);
        expect(result.meta.description).toContain('desc');
        expect(result.meta.tags[0]).not.toMatch(/[<>]/);
        expect(result.meta.tags[0]).toContain('tag1');
        expect(result.meta.tags[1]).toBe('safe');
    });

    it('removes angle brackets in arrays', () => {
        const input = ['<script>a</script>', '<p onclick=x>text</p>', 'valid'];
        const result = sanitizePayload(input);
        for (const item of result) {
            expect(item).not.toMatch(/[<>]/);
        }
        expect(result[2]).toBe('valid');
    });

    it('handles null and undefined gracefully', () => {
        expect(sanitizePayload(null)).toBeNull();
        expect(sanitizePayload(undefined)).toBeUndefined();
    });

    it('combined XSS + CSRF-like payload in template name', () => {
        const payload = {
            template_name: '<script>fetch("/api/keys",{credentials:"include"})</script>',
            document_title: '"><img src=x onerror="fetch(\'/admin\')">',
        };
        const result = sanitizePayload(payload);
        expect(result.template_name).not.toMatch(/[<>]/);
        expect(result.document_title).not.toMatch(/[<>]/);
    });
});
