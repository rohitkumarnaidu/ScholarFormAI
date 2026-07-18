import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import Sidebar from '../components/layout/Sidebar';

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
    usePathname: vi.fn(() => '/dashboard'),
    useRouter: vi.fn(() => ({ push: mockPush })),
    useSearchParams: vi.fn(() => new URLSearchParams()),
}));

vi.mock('../context/AuthContext', () => ({
    useAuth: vi.fn(() => ({
        user: { email: 'user@test.com' },
        signOut: vi.fn(() => Promise.resolve()),
        loading: false,
    })),
}));

describe('Sidebar', () => {
    it('renders navigation items for authenticated user', () => {
        render(<Sidebar />);
        expect(screen.getByText('Dashboard')).toBeInTheDocument();
        expect(screen.getByText('Upload')).toBeInTheDocument();
        expect(screen.getByText('History')).toBeInTheDocument();
    });

    it('shows guest links when guest param is set', async () => {
        const { useSearchParams } = await import('next/navigation');
        useSearchParams.mockReturnValue(new URLSearchParams('guest=1'));

        render(<Sidebar />);
        expect(screen.getByText('Get Started')).toBeInTheDocument();
        expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();

        useSearchParams.mockReturnValue(new URLSearchParams());
    });

    it('navigates on link click', () => {
        render(<Sidebar />);
        fireEvent.click(screen.getByText('Upload'));
        expect(mockPush).toHaveBeenCalledWith('/upload');
    });

    it('renders mode switcher', () => {
        render(<Sidebar />);
        expect(screen.getByText('formatter')).toBeInTheDocument();
        expect(screen.getByText('generator')).toBeInTheDocument();
    });

    it('shows settings and sign out for authenticated', () => {
        render(<Sidebar />);
        expect(screen.getByText('Settings')).toBeInTheDocument();
        expect(screen.getByText('Sign Out')).toBeInTheDocument();
    });

    it('calls onClose when navigating', () => {
        const onClose = vi.fn();
        render(<Sidebar onClose={onClose} />);
        fireEvent.click(screen.getByText('History'));
        expect(onClose).toHaveBeenCalled();
    });

    it('renders close button when onClose provided', () => {
        render(<Sidebar onClose={() => {}} />);
        expect(screen.getByLabelText('Close Sidebar')).toBeInTheDocument();
    });
});
