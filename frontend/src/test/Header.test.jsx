import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

vi.mock('next/navigation', () => ({
    usePathname: vi.fn(() => '/dashboard'),
}));

vi.mock('../context/AuthContext', () => ({
    useAuth: vi.fn(() => ({ user: { email: 'test@test.com' }, loading: false, isLoggedIn: true })),
}));

vi.mock('../components/layout/header/ThemeToggle', () => ({
    default: () => <div data-testid="theme-toggle">Theme</div>,
}));

vi.mock('../components/NotificationBell', () => ({
    default: () => <div data-testid="notification-bell">Bell</div>,
}));

describe('Header', () => {
    it('renders the logo', async () => {
        const Header = (await import('../components/layout/Header')).default;
        render(<Header />);
        expect(screen.getByText('ScholarForm')).toBeInTheDocument();
        expect(screen.getByText('AI')).toBeInTheDocument();
    });

    it('shows login button for unauthenticated users', async () => {
        const { useAuth } = await import('../context/AuthContext');
        useAuth.mockReturnValue({ user: null, loading: false, isLoggedIn: false });

        const Header = (await import('../components/layout/Header')).default;
        render(<Header />);
        expect(screen.getByText('Login')).toBeInTheDocument();
        expect(screen.getByText('Get Started')).toBeInTheDocument();
    });

    it('shows sidebar toggle when isSidebarLayout', async () => {
        const Header = (await import('../components/layout/Header')).default;
        render(<Header isSidebarLayout onOpenMobileSidebar={() => {}} />);
        expect(screen.getByLabelText('Toggle Sidebar')).toBeInTheDocument();
    });

    it('renders theme toggle and notification bell', async () => {
        const Header = (await import('../components/layout/Header')).default;
        render(<Header />);
        expect(screen.getByTestId('theme-toggle')).toBeInTheDocument();
        expect(screen.getByTestId('notification-bell')).toBeInTheDocument();
    });

    it('renders user name when logged in', async () => {
        const { useAuth } = await import('../context/AuthContext');
        useAuth.mockReturnValue({
            user: { email: 'researcher@test.com', user_metadata: {}, app_metadata: {} },
            loading: false,
            isLoggedIn: true,
        });

        const Header = (await import('../components/layout/Header')).default;
        render(<Header />);
        expect(screen.getByText('researcher')).toBeInTheDocument();
    });
});
