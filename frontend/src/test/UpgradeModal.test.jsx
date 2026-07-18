import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import UpgradeModal from '../components/UpgradeModal';

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
    useRouter: vi.fn(() => ({ push: mockPush })),
}));

describe('UpgradeModal', () => {
    it('returns null when not open', () => {
        const { container } = render(<UpgradeModal isOpen={false} />);
        expect(container.innerHTML).toBe('');
    });

    it('renders when open', () => {
        render(<UpgradeModal isOpen={true} />);
        expect(screen.getByText('Upgrade to Pro')).toBeInTheDocument();
        expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('renders custom title', () => {
        render(<UpgradeModal isOpen={true} title="Get Pro" />);
        expect(screen.getByText('Get Pro')).toBeInTheDocument();
    });

    it('shows feature list', () => {
        render(<UpgradeModal isOpen={true} />);
        expect(screen.getByText('Unlimited document uploads')).toBeInTheDocument();
        expect(screen.getByText('AI Agent chat assistance')).toBeInTheDocument();
    });

    it('navigates to billing on upgrade', () => {
        const onClose = vi.fn();
        render(<UpgradeModal isOpen={true} onClose={onClose} />);
        fireEvent.click(screen.getByText('Upgrade Now'));
        expect(mockPush).toHaveBeenCalledWith('/settings?tab=billing');
        expect(onClose).toHaveBeenCalled();
    });

    it('calls onClose on backdrop click', () => {
        const onClose = vi.fn();
        render(<UpgradeModal isOpen={true} onClose={onClose} />);
        const backdrop = document.querySelector('[class*="bg-black"]');
        fireEvent.click(backdrop);
        expect(onClose).toHaveBeenCalled();
    });

    it('calls onClose when maybe later clicked', () => {
        const onClose = vi.fn();
        render(<UpgradeModal isOpen={true} onClose={onClose} />);
        fireEvent.click(screen.getByText('Maybe Later'));
        expect(onClose).toHaveBeenCalled();
    });
});
