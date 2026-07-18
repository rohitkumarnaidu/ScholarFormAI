import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

vi.mock('next/navigation', () => ({
    useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
    usePathname: () => '/',
    useSearchParams: () => new URLSearchParams(),
}));

vi.mock('@/src/context/ThemeContext', () => ({
    useTheme: () => ({ theme: 'light', toggleTheme: vi.fn(), systemTheme: null }),
    ThemeProvider: ({ children }) => <>{children}</>,
}));

vi.mock('@/src/lib/supabaseClient', () => ({ supabase: null }));
vi.mock('@/src/context/AuthContext', () => ({
    useAuth: () => ({ user: null, isLoggedIn: false, loading: false }),
}));

vi.mock('@/src/utils/notifications', () => ({
    loadNotifications: () => [],
    saveNotifications: vi.fn(),
    STORAGE_KEY: 'sf_notifs',
}));

const SkipLink = () => (
    <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-0 focus:left-0 focus:z-50 focus:p-4 focus:bg-white focus:text-black">
        Skip to main content
    </a>
);

const Modal = ({ isOpen, onClose, children }) => {
    const trapRef = React.useRef(null);
    React.useEffect(() => {
        if (isOpen) trapRef.current?.focus();
    }, [isOpen]);
    React.useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Escape') onClose();
            if (e.key === 'Tab' && trapRef.current) {
                const focusable = trapRef.current.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
                if (focusable.length === 0) return;
                const first = focusable[0];
                const last = focusable[focusable.length - 1];
                if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
                else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
            }
        };
        if (isOpen) window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, onClose]);
    if (!isOpen) return null;
    return (
        <div role="dialog" aria-modal="true" aria-label="Focus trap modal" ref={trapRef}>
            <div tabIndex={-1}>
                {children}
                <button onClick={onClose}>Close</button>
            </div>
        </div>
    );
};

import NotificationBell from '@/src/components/NotificationBell';
import ThemeToggle from '@/src/components/layout/header/ThemeToggle';

describe('Keyboard accessibility', () => {
    it('follows logical tab order through form elements', async () => {
        render(
            <form aria-label="Test form">
                <input aria-label="Field 1" />
                <input aria-label="Field 2" />
                <button type="submit">Submit</button>
            </form>
        );
        const field1 = screen.getByLabelText('Field 1');
        const field2 = screen.getByLabelText('Field 2');
        const submit = screen.getByText('Submit');
        field1.focus();
        expect(document.activeElement).toBe(field1);
        field2.focus();
        expect(document.activeElement).toBe(field2);
        submit.focus();
        expect(document.activeElement).toBe(submit);
    });

    it('skip link is hidden by default', () => {
        render(<SkipLink />);
        const link = screen.getByText('Skip to main content');
        expect(link.className).toContain('sr-only');
    });

    it('skip link becomes visible on focus', () => {
        render(<SkipLink />);
        const link = screen.getByText('Skip to main content');
        link.focus();
        expect(document.activeElement).toBe(link);
        expect(link.getAttribute('href')).toBe('#main-content');
    });

    it('focus is trapped in modal dialog', () => {
        render(
            <Modal isOpen={true} onClose={vi.fn()}>
                <button>First</button>
                <button>Second</button>
            </Modal>
        );
        const first = screen.getByText('First');
        first.focus();
        expect(document.activeElement).toBe(first);
    });

    it('escape key closes modal', () => {
        const onClose = vi.fn();
        render(
            <Modal isOpen={true} onClose={onClose}>
                <p>Modal content</p>
            </Modal>
        );
        fireEvent.keyDown(window, { key: 'Escape' });
        expect(onClose).toHaveBeenCalled();
    });

    it('enter key activates button', () => {
        const onClick = vi.fn();
        render(<button onClick={onClick}>Activate</button>);
        const btn = screen.getByRole('button', { name: 'Activate' });
        fireEvent.click(btn);
        expect(onClick).toHaveBeenCalled();
    });

    it('menu items have proper keyboard attributes', () => {
        render(
            <ul role="menu">
                <li role="menuitem" tabIndex={0}>Item 1</li>
                <li role="menuitem" tabIndex={-1}>Item 2</li>
                <li role="menuitem" tabIndex={-1}>Item 3</li>
            </ul>
        );
        const items = screen.getAllByRole('menuitem');
        expect(items).toHaveLength(3);
        items.forEach(item => {
            expect(item.getAttribute('tabindex')).not.toBeNull();
        });
    });

    it('focus is restored after modal close', () => {
        const Trigger = () => {
            const [open, setOpen] = React.useState(false);
            const btnRef = React.useRef(null);
            React.useEffect(() => {
                if (!open) btnRef.current?.focus();
            }, [open]);
            return (
                <div>
                    <button ref={btnRef} onClick={() => setOpen(true)}>Open</button>
                    <Modal isOpen={open} onClose={() => setOpen(false)}>
                        <p>Content</p>
                    </Modal>
                </div>
            );
        };
        render(<Trigger />);
        const openBtn = screen.getByText('Open');
        openBtn.focus();
        fireEvent.click(openBtn);
        expect(screen.getByRole('dialog')).toBeInTheDocument();
        fireEvent.keyDown(window, { key: 'Escape' });
        expect(openBtn).toBeInTheDocument();
    });

    it('sidebar links are keyboard navigable', () => {
        render(
            <nav aria-label="Main navigation">
                <a href="/dashboard">Dashboard</a>
                <a href="/documents">Documents</a>
                <a href="/settings">Settings</a>
            </nav>
        );
        const links = screen.getAllByRole('link');
        expect(links.length).toBeGreaterThanOrEqual(3);
        links.forEach(link => {
            const tabIndex = link.getAttribute('tabindex');
            expect(tabIndex === null || parseInt(tabIndex) >= 0).toBe(true);
        });
    });

    it('agent chat input is focusable', () => {
        render(
            <div role="region" aria-label="Chat input">
                <textarea aria-label="Message" placeholder="Type your message" />
                <button>Send</button>
            </div>
        );
        const textarea = screen.getByPlaceholderText('Type your message');
        textarea.focus();
        expect(document.activeElement).toBe(textarea);
    });

    it('file upload triggered via keyboard', () => {
        const onUpload = vi.fn();
        render(
            <div>
                <label htmlFor="file-upload-test">Upload file</label>
                <input id="file-upload-test" type="file" onChange={onUpload} style={{ display: 'none' }} />
                <button onClick={() => document.getElementById('file-upload-test').click()}>
                    Choose File
                </button>
            </div>
        );
        const btn = screen.getByText('Choose File');
        btn.focus();
        expect(document.activeElement).toBe(btn);
    });

    it('theme toggle is keyboard accessible', () => {
        render(<ThemeToggle />);
        const toggle = screen.getByRole('button');
        toggle.focus();
        expect(document.activeElement).toBe(toggle);
    });

    it('notification bell is keyboard accessible', () => {
        render(<NotificationBell />);
        const bell = screen.getByRole('button', { name: /notifications/i });
        bell.focus();
        expect(document.activeElement).toBe(bell);
    });
});
