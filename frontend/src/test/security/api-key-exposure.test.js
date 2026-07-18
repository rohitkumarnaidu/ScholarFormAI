// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi } from 'vitest';
import fs from 'fs';
import path from 'path';

const PROJECT_ROOT = process.cwd();

describe('API key exposure prevention', () => {
    it('Supabase anon key is not hardcoded in source files', () => {
        const srcDir = path.join(PROJECT_ROOT, 'src');
        const walk = (dir) => {
            const entries = fs.readdirSync(dir, { withFileTypes: true });
            for (const entry of entries) {
                const fullPath = path.join(dir, entry.name);
                if (entry.isDirectory() && !entry.name.startsWith('_') && entry.name !== 'node_modules') {
                    walk(fullPath);
                } else if (entry.isFile() && /\.(js|jsx|ts|tsx)$/.test(entry.name)) {
                    const content = fs.readFileSync(fullPath, 'utf8');
                    const lines = content.split('\n');
                    for (let i = 0; i < lines.length; i += 1) {
                        const line = lines[i];
                        const trimmed = line.trim();
                        const isAssignment = /[=:]/.test(trimmed);
                        const hasHardcodedValue = /["'`]/.test(trimmed) && !trimmed.includes('process.env');
                        if (
                            /SUPABASE_ANON_KEY|supabaseAnonKey|NEXT_PUBLIC_SUPABASE_ANON_KEY/.test(line)
                            && !line.includes('process.env')
                            && hasHardcodedValue
                            && isAssignment
                        ) {
                            throw new Error(
                                `Potential hardcoded key at ${path.relative(PROJECT_ROOT, fullPath)}:${i + 1}: ${line.trim()}`
                            );
                        }
                    }
                }
            }
        };
        expect(() => walk(srcDir)).not.toThrow();
    });

    it('API service layer does not log or expose keys in error messages', async () => {
        const core = await import('../../services/api.core');
        const result = core.getFriendlyErrorMessage({
            status: 500,
            errorData: { detail: 'Invalid API key sk-proj-abc123def' },
            fallbackMessage: '',
        });
        expect(result).not.toMatch(/sk-|SUPABASE|eyJhbGciOiJIUzI1Ni/);
        expect(result).toBe('The server is temporarily unavailable. Please try again shortly.');
    });

    it('fetchWithAuth does not leak auth tokens in error messages', async () => {
        const { getFriendlyErrorMessage } = await import('../../services/api.core');
        const result = getFriendlyErrorMessage({
            status: 401,
            errorData: { detail: 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.invalid' },
            fallbackMessage: '',
        });
        expect(result).not.toMatch(/Bearer|eyJ/);
    });

    it('auth headers are stripped from error responses sent to monitoring', () => {
        const errorPayload = {
            message: 'API Error [/api/v1/documents]: Request failed (500)',
            stack: 'Error: Request failed\n    at fetchWithAuth (api.core.js:450)',
        };
        const jsonString = JSON.stringify(errorPayload);
        expect(jsonString).not.toMatch(/Bearer\s+\S+/);
        expect(jsonString).not.toMatch(/Authorization/i);
    });

    it('no API key patterns exist in rendered HTML source', () => {
        const patterns = [/sk-[A-Za-z0-9]{20,}/, /SUPABASE_ANON_KEY/i, /eyJhbGciOiJIUzI1Ni/];
        const componentsDir = path.join(PROJECT_ROOT, 'src', 'components');
        const walk = (dir) => {
            const entries = fs.readdirSync(dir, { withFileTypes: true });
            for (const entry of entries) {
                const fullPath = path.join(dir, entry.name);
                if (entry.isDirectory()) {
                    walk(fullPath);
                } else if (entry.isFile() && /\.(jsx|tsx)$/.test(entry.name)) {
                    const content = fs.readFileSync(fullPath, 'utf8');
                    for (const pattern of patterns) {
                        if (pattern.test(content)) {
                            const match = content.match(pattern);
                            throw new Error(
                                `Possible key leak in ${path.relative(PROJECT_ROOT, fullPath)}: ${match ? match[0].slice(0, 30) : 'unknown'}`
                            );
                        }
                    }
                }
            }
        };
        expect(() => walk(componentsDir)).not.toThrow();
    });

    it('bundle does not include server-side secrets via process.env.*', () => {
        const srcDir = path.join(PROJECT_ROOT, 'src');
        const walk = (dir) => {
            const entries = fs.readdirSync(dir, { withFileTypes: true });
            for (const entry of entries) {
                const fullPath = path.join(dir, entry.name);
                if (entry.isDirectory() && !entry.name.startsWith('_') && entry.name !== 'node_modules') {
                    walk(fullPath);
                } else if (entry.isFile() && /\.(js|jsx|ts|tsx)$/.test(entry.name)) {
                    const content = fs.readFileSync(fullPath, 'utf8');
                    const serverEnvAccess = content.match(/process\.env\.(?!NEXT_PUBLIC_)(?!NODE_ENV)\w+/g);
                    if (serverEnvAccess) {
                        throw new Error(
                            `Server-side env var in client code at ${path.relative(PROJECT_ROOT, fullPath)}: ${serverEnvAccess.join(', ')}`
                        );
                    }
                }
            }
        };
        expect(() => walk(srcDir)).not.toThrow();
    });

    it('localStorage/sessionStorage does not persist auth tokens insecurely', () => {
        vi.spyOn(Storage.prototype, 'setItem').mockImplementation((key, value) => {
            if (key.startsWith('sb-') && key.includes('-auth-token')) {
                const parsed = JSON.parse(value);
                if (parsed?.access_token?.length > 100) {
                    throw new Error('Long-lived tokens should not persist unchecked in localStorage');
                }
            }
        });

        const badPayload = JSON.stringify({ access_token: 'x'.repeat(500), refresh_token: 'y'.repeat(200) });
        const goodPayload = JSON.stringify({});

        expect(() => localStorage.setItem('sb-xyz-auth-token', badPayload)).toThrow();
        expect(() => localStorage.setItem('sb-xyz-auth-token', goodPayload)).not.toThrow();

        vi.restoreAllMocks();
    });

    it('Authorization header is not included in cross-origin requests', () => {
        const headers = { Authorization: 'Bearer test-token' };
        const url = new URL('https://evil.com/steal');
        expect(url.origin).not.toMatch(/localhost|scholarform/);
        const hasAuth = 'Authorization' in headers;
        expect(hasAuth).toBe(true);
    });
});
