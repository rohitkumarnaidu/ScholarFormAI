// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import SessionHistory from '../components/generator/SessionHistory';

const { mockGetUser, mockGetSessions, mockDeleteSession } = vi.hoisted(() => ({
    mockGetUser: vi.fn(),
    mockGetSessions: vi.fn(),
    mockDeleteSession: vi.fn(),
}));

vi.mock('@/src/lib/supabaseClient', () => ({
    supabase: {
        auth: { getUser: mockGetUser },
    },
}));

vi.mock('@/src/services/api.v1', () => ({
    getGeneratorSessions: mockGetSessions,
    deleteGeneratorSession: mockDeleteSession,
}));

describe('SessionHistory', () => {
    const defaultProps = {
        activeSessionId: null,
        onSelectSession: vi.fn(),
    };

    beforeEach(() => {
        vi.clearAllMocks();
        mockGetUser.mockResolvedValue({ data: { user: { id: 'user-1' } } });
        mockGetSessions.mockResolvedValue({ sessions: [] });
    });

    it('renders sign-in prompt when no user', async () => {
        mockGetUser.mockResolvedValue({ data: { user: null } });
        render(<SessionHistory {...defaultProps} />);
        await waitFor(() => {
            expect(screen.getByText('Sign in required')).toBeInTheDocument();
        });
    });

    it('renders Recent Sessions heading', async () => {
        render(<SessionHistory {...defaultProps} />);
        await waitFor(() => {
            expect(screen.getByText('Recent Sessions')).toBeInTheDocument();
        });
    });

    it('shows empty state when no sessions', async () => {
        mockGetSessions.mockResolvedValue({ sessions: [] });
        render(<SessionHistory {...defaultProps} />);
        await waitFor(() => {
            expect(screen.getByText('No recent sessions.')).toBeInTheDocument();
        });
    });

    it('renders session list items', async () => {
        mockGetSessions.mockResolvedValue({
            sessions: [
                { id: 'sess-1', title: 'Test Session', date: new Date().toISOString(), status: 'completed' },
            ],
        });
        render(<SessionHistory {...defaultProps} />);
        await waitFor(() => {
            expect(screen.getByText('Test Session')).toBeInTheDocument();
        });
    });

    it('calls onSelectSession when session is clicked', async () => {
        const onSelectSession = vi.fn();
        mockGetSessions.mockResolvedValue({
            sessions: [
                { id: 'sess-1', title: 'Test Session', date: new Date().toISOString(), status: 'completed' },
            ],
        });
        render(<SessionHistory {...defaultProps} onSelectSession={onSelectSession} />);
        await waitFor(() => {
            expect(screen.getByText('Test Session')).toBeInTheDocument();
        });
        fireEvent.click(screen.getByText('Test Session'));
        expect(onSelectSession).toHaveBeenCalledWith('sess-1');
    });

    it('highlights active session', async () => {
        mockGetSessions.mockResolvedValue({
            sessions: [
                { id: 'sess-1', title: 'Active Session', date: new Date().toISOString(), status: 'completed' },
            ],
        });
        render(<SessionHistory {...defaultProps} activeSessionId="sess-1" />);
        await waitFor(() => {
            expect(screen.getByText('Active Session')).toBeInTheDocument();
        });
    });

    it('falls back to mock data on API error', async () => {
        mockGetSessions.mockRejectedValue(new Error('API error'));
        const consoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {});
        render(<SessionHistory {...defaultProps} />);
        await waitFor(() => {
            expect(screen.getByText('IEEE Paper on AI Education')).toBeInTheDocument();
        });
        consoleWarn.mockRestore();
    });

    it('calls deleteGeneratorSession on delete', async () => {
        mockGetSessions.mockResolvedValue({
            sessions: [
                { id: 'sess-1', title: 'Test Session', date: new Date().toISOString(), status: 'completed' },
            ],
        });
        const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
        render(<SessionHistory {...defaultProps} />);
        await waitFor(() => {
            expect(screen.getByText('Test Session')).toBeInTheDocument();
        });
        confirmSpy.mockRestore();
    });

    it('does not delete on cancel confirm', async () => {
        mockGetSessions.mockResolvedValue({
            sessions: [
                { id: 'sess-1', title: 'Test Session', date: new Date().toISOString(), status: 'completed' },
            ],
        });
        const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);
        render(<SessionHistory {...defaultProps} />);
        await waitFor(() => {
            expect(screen.getByText('Test Session')).toBeInTheDocument();
        });
        confirmSpy.mockRestore();
    });

    it('shows session template when available', async () => {
        mockGetSessions.mockResolvedValue({
            sessions: [
                { id: 'sess-1', title: 'Test', date: new Date().toISOString(), template: 'IEEE' },
            ],
        });
        render(<SessionHistory {...defaultProps} />);
        await waitFor(() => {
            expect(screen.getByText('IEEE')).toBeInTheDocument();
        });
    });

    it('displays Today at for current date', async () => {
        mockGetSessions.mockResolvedValue({
            sessions: [
                { id: 'sess-1', title: 'Test', date: new Date().toISOString(), status: 'completed' },
            ],
        });
        render(<SessionHistory {...defaultProps} />);
        await waitFor(() => {
            expect(screen.getByText(/Today at/)).toBeInTheDocument();
        });
    });
});
