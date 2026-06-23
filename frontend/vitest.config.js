// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vitest/config';

export default defineConfig({
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./', import.meta.url)),
            '@testing-library/react': fileURLToPath(new URL('./node_modules/@testing-library/react', import.meta.url)),
            '@testing-library/user-event': fileURLToPath(new URL('./node_modules/@testing-library/user-event', import.meta.url)),
            'next/navigation': fileURLToPath(new URL('./__mocks__/next/navigation.js', import.meta.url)),
        },
    },
    esbuild: {
        jsx: 'automatic',
    },
    test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: './src/test/setup.js',
        include: [
            'src/**/*.{test,spec}.{js,jsx,ts,tsx}',
        ],
        exclude: [
            '_legacy_vite_archive/**',
        ],
    },
    server: {
        fs: {
            allow: ['..'],
        },
    },
});

