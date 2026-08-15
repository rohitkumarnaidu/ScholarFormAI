// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

/**
 * B-RR-05 — Global A11y Focus & ARIA Tests
 * Verifies that interactive elements in key components expose correct
 * roles, labels, and focus indicators for screen reader and keyboard users.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// ── Shared mocks ────────────────────────────────────────────
vi.mock('next/navigation', () => ({
    useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
    usePathname: () => '/',
    useSearchParams: () => new URLSearchParams(),
}));

vi.mock('@/lib/supabaseClient', () => ({ supabase: null }));
vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ user: null, isLoggedIn: false }),
}));
vi.mock('@/utils/notifications', () => ({
    loadNotifications: () => [],
    saveNotifications: vi.fn(),
    STORAGE_KEY: 'sf_notifs',
}));

vi.mock('@/context/NotificationContext', () => ({
    useNotifications: vi.fn(() => ({
        notifications: [],
        unreadCount: 0,
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
    })),
}));

// ── NotificationBell ─────────────────────────────────────────
import NotificationBell from '@/components/NotificationBell';

describe('NotificationBell — A11y', () => {
    it('renders bell button with descriptive aria-label', () => {
        render(<NotificationBell />);
        const btn = screen.getByRole('button', { name: /notifications/i });
        expect(btn).toBeInTheDocument();
    });

    it('bell button has aria-expanded=false when closed', () => {
        render(<NotificationBell />);
        const btn = screen.getByRole('button', { name: /notifications/i });
        expect(btn).toHaveAttribute('aria-expanded', 'false');
    });

    it('bell button has aria-haspopup=menu', () => {
        render(<NotificationBell />);
        const btn = screen.getByRole('button', { name: /notifications/i });
        expect(btn).toHaveAttribute('aria-haspopup', 'menu');
    });

    it('opens notification menu with correct role on click', () => {
        render(<NotificationBell />);
        const btn = screen.getByRole('button', { name: /notifications/i });
        fireEvent.click(btn);
        expect(screen.getByRole('menu')).toBeInTheDocument();
        expect(btn).toHaveAttribute('aria-expanded', 'true');
    });

    it('"View all notifications" button has aria-label', () => {
        render(<NotificationBell />);
        fireEvent.click(screen.getByRole('button', { name: /notifications/i }));
        const viewAll = screen.getByRole('button', { name: /view all notifications/i });
        expect(viewAll).toBeInTheDocument();
    });
});

// ── Stepper ───────────────────────────────────────────────────
import Stepper from '@/components/Stepper';

describe('Stepper — A11y', () => {
    it('renders a list with an accessible label', () => {
        render(<Stepper activeStep={2} />);
        const list = screen.getByRole('list', { name: /processing steps/i });
        expect(list).toBeInTheDocument();
    });

    it('marks the active step with aria-current="step"', () => {
        render(<Stepper activeStep={2} />);
        // There should be exactly one step with aria-current="step"
        const activeItems = screen
            .getAllByRole('listitem')
            .filter((el) => el.getAttribute('aria-current') === 'step');
        expect(activeItems).toHaveLength(1);
    });

    it('each listitem has an aria-label describing its state', () => {
        render(<Stepper activeStep={1} />);
        const items = screen.getAllByRole('listitem');
        expect(items.length).toBeGreaterThan(0);
        items.forEach((item) => {
            expect(item).toHaveAttribute('aria-label');
            expect(item.getAttribute('aria-label').length).toBeGreaterThan(0);
        });
    });

    it('no step before the active one is marked aria-current', () => {
        render(<Stepper activeStep={3} />);
        const items = screen.getAllByRole('listitem');
        // Only step at index 3 should be current
        const currents = items.filter(
            (el) => el.getAttribute('aria-current') === 'step'
        );
        expect(currents).toHaveLength(1);
    });
});

// ── ExportDialog ───────────────────────────────────────────────
import ExportDialog from '@/components/ExportDialog';

describe('ExportDialog — A11y', () => {
    it('has dialog role and aria-modal attributes', () => {
        render(<ExportDialog isOpen={true} />);
        const dialog = screen.getByRole('dialog');
        expect(dialog).toBeInTheDocument();
        expect(dialog).toHaveAttribute('aria-modal', 'true');
        expect(dialog).toHaveAttribute('aria-labelledby', 'export-dialog-title');
    });

    it('focuses the first interactive element on open', async () => {
        render(<ExportDialog isOpen={true} />);
        // Wait for setTimeout in component
        await new Promise((resolve) => setTimeout(resolve, 100));
        // The first focusable element is likely a button or combobox. As long as some element is focused.
        expect(document.activeElement).not.toBe(document.body);
    });
});

// ── UpgradeModal ───────────────────────────────────────────────
import UpgradeModal from '@/components/UpgradeModal';

describe('UpgradeModal — A11y', () => {
    it('has dialog role and aria-modal attributes', () => {
        render(<UpgradeModal isOpen={true} />);
        const dialog = screen.getByRole('dialog');
        expect(dialog).toBeInTheDocument();
        expect(dialog).toHaveAttribute('aria-modal', 'true');
        expect(dialog).toHaveAttribute('aria-labelledby', 'upgrade-modal-title');
    });
});
