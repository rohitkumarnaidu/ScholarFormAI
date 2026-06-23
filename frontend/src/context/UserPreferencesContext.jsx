// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { supabase } from '../lib/supabaseClient';

const UserPreferencesContext = createContext();
const DEBOUNCE_MS = 1000;

export const UserPreferencesProvider = ({ children }) => {
    const { user, isLoggedIn } = useAuth();
    const [preferences, setPreferencesState] = useState({
        fastMode: false,
        statusUpdates: true,
        newsletter: false,
    });
    const pendingChangesRef = useRef(null);
    const debounceTimerRef = useRef(null);

    useEffect(() => {
        if (isLoggedIn && user?.user_metadata?.preferences) {
            setPreferencesState((prev) => ({
                ...prev,
                ...user.user_metadata.preferences,
            }));
        } else if (!isLoggedIn) {
            const saved = localStorage.getItem('scholarform_preferences');
            if (saved) {
                try {
                    setPreferencesState(JSON.parse(saved));
                } catch (e) {
                    console.error("Failed to parse preferences from localStorage", e);
                }
            }
        }
    }, [isLoggedIn, user]);

    useEffect(() => {
        localStorage.setItem('scholarform_preferences', JSON.stringify(preferences));
    }, [preferences]);

    const syncToSupabase = useCallback((prefs) => {
        if (isLoggedIn && supabase) {
            supabase.auth.updateUser({
                data: { preferences: prefs }
            }).catch(err => console.error("Failed to sync preferences to Supabase:", err));
        }
    }, [isLoggedIn]);

    const flushPendingChanges = useCallback(() => {
        if (pendingChangesRef.current) {
            syncToSupabase(pendingChangesRef.current);
            pendingChangesRef.current = null;
        }
    }, [syncToSupabase]);

    useEffect(() => {
        return () => {
            if (debounceTimerRef.current) {
                clearTimeout(debounceTimerRef.current);
                flushPendingChanges();
            }
        };
    }, [flushPendingChanges]);

    const setPreference = (key, value) => {
        setPreferencesState((prev) => {
            const next = { ...prev, [key]: value };

            if (isLoggedIn && supabase) {
                pendingChangesRef.current = next;

                if (debounceTimerRef.current) {
                    clearTimeout(debounceTimerRef.current);
                }

                debounceTimerRef.current = setTimeout(() => {
                    flushPendingChanges();
                    debounceTimerRef.current = null;
                }, DEBOUNCE_MS);
            }

            return next;
        });
    };

    return (
        <UserPreferencesContext.Provider value={{ preferences, setPreference }}>
            {children}
        </UserPreferencesContext.Provider>
    );
};

export const useUserPreferences = () => useContext(UserPreferencesContext);
