// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { createContext, useContext, useEffect } from 'react';
import { ThemeProvider as NextThemeProvider, useTheme as useNextTheme } from 'next-themes';
import { supabase } from '../lib/supabaseClient';

const ThemeContext = createContext();

function ThemeSyncWrapper({ children }) {
    const { theme, setTheme: setNextTheme, systemTheme } = useNextTheme();

    useEffect(() => {
        const fetchRemoteTheme = async () => {
            if (!supabase) return;
            const { data: { session } } = await supabase.auth.getSession();
            if (session?.user?.user_metadata?.theme) {
                const remoteTheme = session.user.user_metadata.theme;
                if (remoteTheme !== theme) {
                    setNextTheme(remoteTheme);
                }
            }
        };
        fetchRemoteTheme();
    }, [setNextTheme, theme]);

    const syncThemeToSupabase = async (newTheme) => {
        if (!supabase) return;
        try {
            const { data: { session } } = await supabase.auth.getSession();
            if (session?.user) {
                await supabase.auth.updateUser({
                    data: { theme: newTheme }
                });
            }
        } catch (err) {
            console.error('Failed to sync theme to Supabase', err);
        }
    };

    const toggleTheme = () => {
        const next = theme === 'dark' ? 'light' : 'dark';
        setNextTheme(next);
        syncThemeToSupabase(next);
    };

    const setTheme = (nextTheme) => {
        const parsed = nextTheme === 'dark' ? 'dark' : 'light';
        setNextTheme(parsed);
        syncThemeToSupabase(parsed);
    };

    return (
        <ThemeContext.Provider value={{ theme, systemTheme, toggleTheme, setTheme }}>
            {children}
        </ThemeContext.Provider>
    );
}

export function ThemeProvider({ children }) {
    return (
        <NextThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
            <ThemeSyncWrapper>
                {children}
            </ThemeSyncWrapper>
        </NextThemeProvider>
    );
}

export function useTheme() {
    return useContext(ThemeContext);
}
