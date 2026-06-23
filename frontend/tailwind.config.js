// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import forms from '@tailwindcss/forms';
import containerQueries from '@tailwindcss/container-queries';

/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
        "./app/**/*.{js,ts,jsx,tsx}",
        "./components/**/*.{js,ts,jsx,tsx}",
    ],
    darkMode: "class",
    theme: {
        extend: {
            fontFamily: {
                "display": ['var(--font-manrope)', '"Manrope"', "sans-serif"]
            },
            borderRadius: {
                "DEFAULT": "0.5rem",
                "lg": "1rem",
                "xl": "1.5rem",
                "2xl": "2rem",
            },
            transitionTimingFunction: {
                'spring': 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
            },
            colors: {
                "background-dark": "#09090b",
                "background-light": "#f6f6f8",
                "primary": "#136dec",
                "primary-hover": "#0f5bbd",
                "primary-light": "#4d94f8",
                "primary-dark": "#0d4faa",
                "glass-surface": "var(--glass-surface)",
                "glass-border": "var(--glass-border)",
                "diff-add": "#dcfce7",
                "diff-remove": "#fee2e2",
                "diff-mod": "#fef9c3",
                "diff-text-add": "#166534",
                "diff-text-remove": "#991b1b",
                "diff-text-mod": "#854d0e",
                "success": "#10b981",
                "warning": "#f59e0b",
                "error": "#ef4444",
                "info": "#3b82f6",
                "secondary": "#6b7280",
            },
        },
    },
    plugins: [
        forms,
        containerQueries,
    ],
}
