// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act, cleanup } from '@testing-library/react';
import React from 'react';
import { UserPreferencesProvider, useUserPreferences } from '@/src/context/UserPreferencesContext';

const { mockUseAuth } = vi.hoisted(() => ({
    mockUseAuth: vi.fn(() => ({ user: null, isLoggedIn: false })),
}));

vi.mock('@/src/context/AuthContext', () => ({
    useAuth: () => mockUseAuth(),
}));

const { mockSupabase } = vi.hoisted(() => ({
    mockSupabase: {
        auth: {
            updateUser: vi.fn(),
        },
    },
}));

vi.mock('../lib/supabaseClient', () => ({
    supabase: mockSupabase,
}));

function PrefsProbe() {
    const { preferences, setPreference } = useUserPreferences();
    return (
        <div>
            <div data-testid="fast-mode">{String(preferences.fastMode)}</div>
            <div data-testid="status-updates">{String(preferences.statusUpdates)}</div>
            <div data-testid="newsletter">{String(preferences.newsletter)}</div>
            <button data-testid="toggle-fast" onClick={() => setPreference('fastMode', !preferences.fastMode)}>Toggle Fast</button>
            <button data-testid="toggle-newsletter" onClick={() => setPreference('newsletter', !preferences.newsletter)}>Toggle Newsletter</button>
        </div>
    );
}

describe('UserPreferencesContext', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.useFakeTimers();
        localStorage.clear();
        mockUseAuth.mockReturnValue({ user: null, isLoggedIn: false });
        mockSupabase.auth.updateUser.mockResolvedValue({ data: {} });
    });

    afterEach(() => {
        cleanup();
        vi.useRealTimers();
    });

    it('provides default preferences', () => {
        render(
            <UserPreferencesProvider>
                <PrefsProbe />
            </UserPreferencesProvider>
        );
        expect(screen.getByTestId('fast-mode')).toHaveTextContent('false');
        expect(screen.getByTestId('status-updates')).toHaveTextContent('true');
        expect(screen.getByTestId('newsletter')).toHaveTextContent('false');
    });

    it('toggles fast mode preference', () => {
        render(
            <UserPreferencesProvider>
                <PrefsProbe />
            </UserPreferencesProvider>
        );
        fireEvent.click(screen.getByTestId('toggle-fast'));
        expect(screen.getByTestId('fast-mode')).toHaveTextContent('true');
    });

    it('toggles newsletter preference', () => {
        render(
            <UserPreferencesProvider>
                <PrefsProbe />
            </UserPreferencesProvider>
        );
        fireEvent.click(screen.getByTestId('toggle-newsletter'));
        expect(screen.getByTestId('newsletter')).toHaveTextContent('true');
    });

    it('persists preferences to localStorage', () => {
        render(
            <UserPreferencesProvider>
                <PrefsProbe />
            </UserPreferencesProvider>
        );
        fireEvent.click(screen.getByTestId('toggle-fast'));
        const saved = localStorage.getItem('scholarform_preferences');
        expect(saved).toBeTruthy();
        const parsed = JSON.parse(saved);
        expect(parsed.fastMode).toBe(true);
    });

    it('restores preferences from localStorage on mount when not logged in', () => {
        localStorage.setItem('scholarform_preferences', JSON.stringify({ fastMode: true, statusUpdates: false, newsletter: true }));
        render(
            <UserPreferencesProvider>
                <PrefsProbe />
            </UserPreferencesProvider>
        );
        expect(screen.getByTestId('fast-mode')).toHaveTextContent('true');
        expect(screen.getByTestId('status-updates')).toHaveTextContent('false');
        expect(screen.getByTestId('newsletter')).toHaveTextContent('true');
    });

    it('loads preferences from user metadata when logged in', () => {
        mockUseAuth.mockReturnValue({
            user: { user_metadata: { preferences: { fastMode: true, statusUpdates: false, newsletter: true } } },
            isLoggedIn: true,
        });
        render(
            <UserPreferencesProvider>
                <PrefsProbe />
            </UserPreferencesProvider>
        );
        expect(screen.getByTestId('fast-mode')).toHaveTextContent('true');
        expect(screen.getByTestId('status-updates')).toHaveTextContent('false');
    });

    it('syncs preference changes to supabase after debounce when logged in', () => {
        mockUseAuth.mockReturnValue({
            user: { id: 'user-1', user_metadata: {} },
            isLoggedIn: true,
        });
        render(
            <UserPreferencesProvider>
                <PrefsProbe />
            </UserPreferencesProvider>
        );
        fireEvent.click(screen.getByTestId('toggle-fast'));
        act(() => {
            vi.advanceTimersByTime(1000);
        });
        expect(mockSupabase.auth.updateUser).toHaveBeenCalledWith({
            data: { preferences: { fastMode: true, statusUpdates: true, newsletter: false } },
        });
    });

    it('debounces rapid preference changes and syncs once', () => {
        mockUseAuth.mockReturnValue({
            user: { id: 'user-1', user_metadata: {} },
            isLoggedIn: true,
        });
        render(
            <UserPreferencesProvider>
                <PrefsProbe />
            </UserPreferencesProvider>
        );
        fireEvent.click(screen.getByTestId('toggle-fast'));
        act(() => { vi.advanceTimersByTime(500); });
        fireEvent.click(screen.getByTestId('toggle-newsletter'));
        act(() => { vi.advanceTimersByTime(1000); });
        expect(mockSupabase.auth.updateUser).toHaveBeenCalledTimes(1);
    });

    it('flushes pending changes on unmount when logged in', () => {
        mockUseAuth.mockReturnValue({
            user: { id: 'user-1', user_metadata: {} },
            isLoggedIn: true,
        });
        const { unmount } = render(
            <UserPreferencesProvider>
                <PrefsProbe />
            </UserPreferencesProvider>
        );
        fireEvent.click(screen.getByTestId('toggle-fast'));
        act(() => { vi.advanceTimersByTime(500); });
        unmount();
        expect(mockSupabase.auth.updateUser).toHaveBeenCalled();
    });

    it('handles supabase sync error gracefully', () => {
        mockUseAuth.mockReturnValue({
            user: { id: 'user-1', user_metadata: {} },
            isLoggedIn: true,
        });
        mockSupabase.auth.updateUser.mockRejectedValueOnce(new Error('Network error'));
        render(
            <UserPreferencesProvider>
                <PrefsProbe />
            </UserPreferencesProvider>
        );
        fireEvent.click(screen.getByTestId('toggle-fast'));
        act(() => { vi.advanceTimersByTime(1000); });
        expect(mockSupabase.auth.updateUser).toHaveBeenCalled();
    });

    it('does not sync to supabase when not logged in', () => {
        mockUseAuth.mockReturnValue({ user: null, isLoggedIn: false });
        render(
            <UserPreferencesProvider>
                <PrefsProbe />
            </UserPreferencesProvider>
        );
        fireEvent.click(screen.getByTestId('toggle-fast'));
        act(() => { vi.advanceTimersByTime(1000); });
        expect(mockSupabase.auth.updateUser).not.toHaveBeenCalled();
    });

    it('handles non-logged-in state gracefully', () => {
        mockUseAuth.mockReturnValue({ user: null, isLoggedIn: false });
        render(
            <UserPreferencesProvider>
                <PrefsProbe />
            </UserPreferencesProvider>
        );
        expect(screen.getByTestId('fast-mode')).toHaveTextContent('false');
    });

    it('handles corrupted localStorage gracefully', () => {
        localStorage.setItem('scholarform_preferences', '{invalid}');
        render(
            <UserPreferencesProvider>
                <PrefsProbe />
            </UserPreferencesProvider>
        );
        expect(screen.getByTestId('fast-mode')).toHaveTextContent('false');
    });

    it('overrides with user metadata when logged in, ignoring localStorage', () => {
        localStorage.setItem('scholarform_preferences', JSON.stringify({ fastMode: true, statusUpdates: false, newsletter: true }));
        mockUseAuth.mockReturnValue({
            user: { user_metadata: { preferences: { fastMode: false, statusUpdates: true, newsletter: false } } },
            isLoggedIn: true,
        });
        render(
            <UserPreferencesProvider>
                <PrefsProbe />
            </UserPreferencesProvider>
        );
        expect(screen.getByTestId('fast-mode')).toHaveTextContent('false');
        expect(screen.getByTestId('status-updates')).toHaveTextContent('true');
        expect(screen.getByTestId('newsletter')).toHaveTextContent('false');
    });
});
