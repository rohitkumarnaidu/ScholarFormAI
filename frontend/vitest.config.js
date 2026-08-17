// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vitest/config';

export default defineConfig({
    resolve: {
        alias: {
            '@/app': fileURLToPath(new URL('./app', import.meta.url)),
            '@/components': fileURLToPath(new URL('./src/components', import.meta.url)),
            '@/context': fileURLToPath(new URL('./src/context', import.meta.url)),
            '@/hooks': fileURLToPath(new URL('./src/hooks', import.meta.url)),
            '@/services': fileURLToPath(new URL('./src/services', import.meta.url)),
            '@/lib': fileURLToPath(new URL('./src/lib', import.meta.url)),
            '@/utils': fileURLToPath(new URL('./src/utils', import.meta.url)),
            '@/constants': fileURLToPath(new URL('./src/constants', import.meta.url)),
            '@/src': fileURLToPath(new URL('./src', import.meta.url)),
            '@': fileURLToPath(new URL('./src', import.meta.url)),
            '@testing-library/react': fileURLToPath(new URL('./node_modules/@testing-library/react', import.meta.url)),
            '@testing-library/user-event': fileURLToPath(new URL('./node_modules/@testing-library/user-event', import.meta.url)),
            'next/navigation': fileURLToPath(new URL('./__mocks__/next/navigation.js', import.meta.url)),
        },
    },
    esbuild: {
        jsx: 'automatic',
    },
    test: {
        pool: 'threads',
        poolOptions: {
            threads: { minThreads: 1, maxThreads: 2 }
        },
        testTimeout: 20000,
        globals: true,
        environment: 'jsdom',
        setupFiles: './src/test/setup.js',
        include: [
            'src/**/*.{test,spec}.{js,jsx,ts,tsx}',
        ],
        exclude: [
            '_legacy_vite_archive/**',
        ],
        coverage: {
            provider: 'v8',
            reporter: ['text', 'lcov', 'json-summary'],
            reportsDirectory: './coverage',
            exclude: [
                'node_modules/**',
                'src/test/**',
                '**/*.{test,spec}.{js,jsx,ts,tsx}',
                'e2e/**',
                'coverage/**',
            ],
            thresholds: {
                statements: 50,
                branches: 50,
                functions: 50,
                lines: 50,
            },
        },
    },
    server: {
        fs: {
            allow: ['..'],
        },
    },
});

