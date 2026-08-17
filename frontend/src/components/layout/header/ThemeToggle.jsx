// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import { useTheme } from '@/context/ThemeContext';
import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';

export default function ThemeToggle() {
    const { theme, toggleTheme, systemTheme } = useTheme();
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    if (!mounted) {
        return <div className="h-10 w-10" aria-hidden="true" />;
    }

    const currentTheme = theme === 'system' ? systemTheme : theme;
    const isDark = currentTheme === 'dark';

    return (
        <button
            onClick={toggleTheme}
            className="flex h-10 w-10 items-center justify-center text-slate-600 dark:text-slate-300 hover:text-primary dark:hover:text-primary-hover transition-colors active:scale-95 focus:outline-none"
            aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
            {isDark ? <Sun className="text-[20px]" /> : <Moon className="text-[20px]" />}
        </button>
    );
}
