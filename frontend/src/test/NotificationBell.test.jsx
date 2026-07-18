import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import NotificationBell from '../components/NotificationBell';

vi.mock('@/src/utils/notifications', () => ({
    loadNotifications: vi.fn(() => []),
    saveNotifications: vi.fn(),
    STORAGE_KEY: 'scholarform_notifications',
}));

vi.mock('@/src/lib/supabaseClient', () => ({
    supabase: null,
}));

vi.mock('@/src/context/AuthContext', () => ({
    useAuth: vi.fn(() => ({ user: null })),
}));

vi.mock('next/navigation', () => ({
    useRouter: vi.fn(() => ({
        push: vi.fn(),
    })),
}));

describe('NotificationBell', () => {
    it('renders notification button', () => {
        render(<NotificationBell />);
        expect(screen.getByLabelText('Notifications')).toBeInTheDocument();
    });

    it('shows no notifications state when dropdown opened', () => {
        render(<NotificationBell />);
        fireEvent.click(screen.getByLabelText('Notifications'));
        expect(screen.getByText('No notifications')).toBeInTheDocument();
    });

    it('shows dropdown when clicked', () => {
        render(<NotificationBell />);
        fireEvent.click(screen.getByLabelText('Notifications'));
        expect(screen.getByRole('menu')).toBeInTheDocument();
    });

    it('shows view all button in dropdown', () => {
        render(<NotificationBell />);
        fireEvent.click(screen.getByLabelText('Notifications'));
        expect(screen.getByText('View all notifications')).toBeInTheDocument();
    });

    it('closes dropdown on outside click', () => {
        render(<NotificationBell />);
        fireEvent.click(screen.getByLabelText('Notifications'));
        expect(screen.getByRole('menu')).toBeInTheDocument();

        fireEvent.mouseDown(document.body);
        expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    });
});
