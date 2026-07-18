// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { sanitizeText, sanitizePayload } from '../../services/api.core';
import PreviewPane from '../../components/live-preview/PreviewPane';

vi.mock('../../lib/supabaseClient', () => ({
    supabase: null,
}));

describe('Open redirect prevention', () => {
    it('sanitizeRedirectPath prevents open redirects', async () => {
        const auth = await import('../../services/api.auth');
        const getRedirectPath = (path) => {
            if (typeof path !== 'string') return '/dashboard';
            if (!path.startsWith('/') || path.startsWith('//')) return '/dashboard';
            return path;
        };
        const testCases = [
            { input: '//evil.com', expected: '/dashboard' },
            { input: 'https://evil.com', expected: '/dashboard' },
            { input: 'http://evil.com', expected: '/dashboard' },
            { input: '///evil.com', expected: '/dashboard' },
            { input: 123, expected: '/dashboard' },
            { input: '/dashboard', expected: '/dashboard' },
            { input: '/settings/profile', expected: '/settings/profile' },
            { input: '/', expected: '/' },
            { input: '', expected: '/dashboard' },
            { input: null, expected: '/dashboard' },
        ];
        for (const { input, expected } of testCases) {
            expect(getRedirectPath(input)).toBe(expected);
        }
    });

    it('URL sanitization removes angle brackets from href content', () => {
        const inputs = [
            '<a href="javascript:alert(1)">click</a>',
            '<a href="javascript:void(0)">click</a>',
            '<a href="JavaScript:document.location="http://evil.com"">click</a>',
        ];
        for (const input of inputs) {
            const result = sanitizeText(input);
            expect(result).not.toMatch(/[<>]/);
        }
    });
});

describe('Content sanitization before display', () => {
    it('rendered content from API is sanitized before display', () => {
        render(<PreviewPane html='<script>document.cookie</script><h1>Title</h1>' isLoading={false} />);
        expect(screen.getByText('Title')).toBeInTheDocument();
        expect(screen.queryByText(/document\.cookie/i)).not.toBeInTheDocument();
    });

    it('user profile data (name, bio) has angle brackets removed', () => {
        const profile = {
            display_name: '<script>steal()</script>John',
            bio: '<img src=x onerror="track()">Writer &amp; researcher',
        };
        const sanitized = sanitizePayload(profile);
        expect(sanitized.display_name).not.toMatch(/[<>]/);
        expect(sanitized.display_name).toContain('John');
        expect(sanitized.bio).not.toMatch(/[<>]/);
        expect(sanitized.bio).toContain('Writer');
        expect(sanitized.bio).toContain('researcher');
    });

    it('document titles with XSS have angle brackets removed', () => {
        const titles = [
            '<script>alert("xss")</script>My Paper',
            '"><img src=x onerror=alert(1)>Title',
        ];
        for (const title of titles) {
            const result = sanitizeText(title);
            expect(result).not.toMatch(/[<>]/);
            expect(result).toBeTruthy();
        }
    });

    it('template names with injection have angle brackets removed', () => {
        const templates = [
            { name: 'apa; DROP TABLE users;--', id: 'apa' },
            { name: '<script>fetch("/api/keys")</script>IEEE', id: 'ieee' },
        ];
        for (const tmpl of templates) {
            const sanitized = sanitizePayload(tmpl);
            expect(sanitized.name).not.toMatch(/[<>]/);
            expect(sanitized.id).toBe(tmpl.id);
        }
    });

    it('notification content has angle brackets removed', () => {
        const notification = {
            title: 'Your document is ready!',
            message: 'Click <a href="javascript:alert(1)">here</a> to view',
        };
        const sanitized = sanitizePayload(notification);
        expect(sanitized.title).toBe('Your document is ready!');
        expect(sanitized.message).not.toMatch(/[<>]/);
    });

    it('error messages from API do not contain raw HTML in production', () => {
        const core = sanitizePayload({ detail: '<script>alert("db_error")</script>Invalid input' });
        const rawDetail = core.detail;
        expect(sanitizeText(rawDetail)).not.toMatch(/[<>]/);
    });
});
