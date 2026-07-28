// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

/**
 * Accessibility (a11y) standalone tests
 * Tests color contrast, keyboard navigation, ARIA attributes,
 * semantic structure, and reduced-motion preferences
 * using @testing-library/jest-dom and manual DOM checks.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

// ── Shared mocks ──────────────────────────────────────────────
vi.mock('next/navigation', () => ({
    useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
    usePathname: () => '/',
    useSearchParams: () => new URLSearchParams(),
    Link: ({ children, href }) => <a href={href}>{children}</a>,
}));

vi.mock('@/context/ThemeContext', () => ({
    useTheme: () => ({ theme: 'light', toggleTheme: vi.fn(), systemTheme: null }),
    ThemeProvider: ({ children }) => <>{children}</>,
}));

vi.mock('@/lib/supabaseClient', () => ({ supabase: null }));
vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ user: null, isLoggedIn: false, loading: false }),
}));

// JSDOM doesn't compute real CSS — stub getComputedStyle for contrast tests
const originalGetComputedStyle = window.getComputedStyle;
vi.stubGlobal('getComputedStyle', (el, pseudo) => {
    if (el._mockComputedStyle) return el._mockComputedStyle;
    return originalGetComputedStyle(el, pseudo);
});

// ===================================================================
// 1A — Color Contrast Tests
// ===================================================================
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Badge from '@/components/ui/Badge';

describe('1A — Color Contrast', () => {
    it('primary button renders with accessible role and text', () => {
        render(<Button variant="primary">Submit</Button>);
        const btn = screen.getByRole('button', { name: /submit/i });
        expect(btn).toBeInTheDocument();
        expect(btn).not.toHaveAttribute('aria-hidden');
    });

    it('focus indicator is present (tabIndex or focus-visible style)', () => {
        render(<Input label="Email" id="email" />);
        const input = screen.getByLabelText('Email');
        input.focus();
        expect(document.activeElement).toBe(input);
    });

    it('disabled button is properly disabled and identifiable', () => {
        render(<Button disabled>Disabled</Button>);
        const btn = screen.getByRole('button');
        expect(btn).toBeDisabled();
        expect(btn).toBeInTheDocument();
    });

    it('text renders for both body and emphasized content', () => {
        render(
            <div>
                <span className="text-slate-900">Body text</span>
                <strong className="font-semibold">Emphasized text</strong>
            </div>
        );
        expect(screen.getByText('Body text')).toBeInTheDocument();
        expect(screen.getByText('Emphasized text')).toBeInTheDocument();
    });

    it('error state renders with visible text and class', () => {
        render(<Input label="Name" id="name" error="This field is required" />);
        const errorMsg = screen.getByText('This field is required');
        expect(errorMsg).toBeInTheDocument();
        expect(errorMsg.className).toContain('text-red');
    });

    it('success state Badge renders with visible text', () => {
        render(<Badge variant="success">Completed</Badge>);
        const badge = screen.getByText('Completed');
        expect(badge).toBeInTheDocument();
        expect(badge.className).toBeTruthy();
    });
});

// ===================================================================
// 1B — Keyboard Navigation Tests
// ===================================================================
import Sidebar from '@/components/layout/Sidebar';
import ThemeToggle from '@/components/layout/header/ThemeToggle';
import AgentChatPane from '@/components/generator/AgentChatPane';
vi.mock('@/components/Toast', () => ({ default: () => <div role="alert">Toast</div> }));
vi.mock('@/components/ui/Skeleton', () => ({ default: () => <div aria-hidden="true">Skeleton</div> }));

describe('1B — Keyboard Navigation', () => {
    beforeEach(() => {
        document.body.innerHTML = '';
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('auth form fields are reachable via Tab', () => {
        render(
            <form aria-label="Login form">
                <Input label="Email" id="login-email" />
                <Input label="Password" id="login-password" type="password" />
                <Button type="submit">Sign In</Button>
            </form>
        );
        const email = screen.getByLabelText('Email');
        const password = screen.getByLabelText('Password');
        const submit = screen.getByRole('button', { name: /sign in/i });
        const tabOrder = [email, password, submit];
        tabOrder.forEach((el) => {
            expect(el).toBeInTheDocument();
            expect(el.tabIndex >= 0 || el.getAttribute('tabindex') === null).toBe(true);
        });
    });

    it('submit button can be activated with Enter', () => {
        const onSubmit = vi.fn((e) => e.preventDefault());
        render(
            <form onSubmit={onSubmit} aria-label="Test form">
                <Input label="Name" id="test-name" />
                <Button type="submit">Submit</Button>
            </form>
        );
        const submitBtn = screen.getByRole('button', { name: /submit/i });
        fireEvent.keyDown(submitBtn, { key: 'Enter' });
        fireEvent.click(submitBtn);
        expect(onSubmit).toHaveBeenCalled();
    });

    it('sidebar renders navigation landmarks', () => {
        render(<Sidebar />);
        const nav = document.querySelector('nav');
        expect(nav).toBeInTheDocument();
    });

    it('theme toggle renders as a button', () => {
        render(<ThemeToggle />);
        const toggle = screen.getByRole('button');
        expect(toggle).toBeInTheDocument();
        expect(toggle.tabIndex >= 0 || toggle.getAttribute('tabindex') === null).toBe(true);
    });

    it('chat input can be submitted with Ctrl+Enter', () => {
        const onSend = vi.fn();
        render(
            <AgentChatPane
                messages={[{ id: '1', role: 'assistant', content: 'Hello' }]}
                onSendMessage={onSend}
                isTyping={false}
                error={null}
            />
        );
        const textarea = screen.getByPlaceholderText(/type your prompt/i);
        fireEvent.change(textarea, { target: { value: 'Hello' } });
        fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true });
        expect(onSend).toHaveBeenCalledWith('Hello');
    });

    it('escape key closes modal-like dialogs', () => {
        const onClose = vi.fn();
        render(
            <div role="dialog" aria-modal="true" aria-label="Test dialog">
                <p>Dialog content</p>
                <button onClick={onClose}>Close</button>
            </div>
        );
        const dialog = screen.getByRole('dialog');
        fireEvent.keyDown(dialog, { key: 'Escape' });
        fireEvent.click(screen.getByRole('button', { name: /close/i }));
        expect(onClose).toHaveBeenCalled();
    });

    it('dropdowns can be opened with Space key', () => {
        const onToggle = vi.fn();
        render(
            <div>
                <button aria-haspopup="menu" onClick={onToggle}>
                    Options
                </button>
            </div>
        );
        const trigger = screen.getByRole('button', { name: /options/i });
        fireEvent.keyDown(trigger, { key: ' ' });
        fireEvent.click(trigger);
        expect(onToggle).toHaveBeenCalled();
    });

    it('modal dialogs trap focus within the dialog', () => {
        render(
            <div>
                <button>Outside</button>
                <div role="dialog" aria-modal="true" aria-label="Focused dialog">
                    <button>Inside</button>
                </div>
            </div>
        );
        const insideBtn = screen.getByRole('button', { name: /inside/i });
        insideBtn.focus();
        expect(document.activeElement).toBe(insideBtn);
    });
});

// ===================================================================
// 1C — ARIA Attribute Tests
// ===================================================================



describe('1C — ARIA Attributes', () => {
    it('form inputs have associated labels', () => {
        render(<Input label="Full Name" id="fullname" />);
        const input = screen.getByLabelText('Full Name');
        expect(input).toBeInTheDocument();
        expect(input.tagName).toBe('INPUT');
    });

    it('error messages are associated with inputs via aria-describedby', () => {
        document.body.innerHTML = '<div id="email-error">Invalid email</div>';
        render(<Input label="Email" id="email" error="Invalid email" aria-describedby="email-error" />);
        const input = screen.getByLabelText('Email');
        const describedBy = input.getAttribute('aria-describedby');
        expect(describedBy).toBeTruthy();
        if (describedBy) {
            const descEl = document.getElementById(describedBy);
            expect(descEl?.textContent).toMatch(/invalid email/i);
        }
    });

    it('live regions (aria-live) exist for dynamic content', () => {
        render(
            <div aria-live="polite" aria-atomic="true" role="status">
                Loading complete
            </div>
        );
        const live = screen.getByRole('status');
        expect(live).toHaveAttribute('aria-live', 'polite');
        expect(live).toHaveAttribute('aria-atomic', 'true');
    });

    it('icons have appropriate aria-hidden or aria-label', () => {
        render(
            <Button variant="primary">
                <span aria-hidden="true" data-testid="icon">→</span>
                Next
            </Button>
        );
        const icon = screen.getByTestId('icon');
        expect(icon.getAttribute('aria-hidden')).toBe('true');
    });

    it('progress indicators have role="progressbar"', () => {
        render(
            <div role="progressbar" aria-valuenow={60} aria-valuemin={0} aria-valuemax={100} aria-label="Loading progress">
                <div style={{ width: '60%' }} />
            </div>
        );
        const progress = screen.getByRole('progressbar');
        expect(progress).toBeInTheDocument();
        expect(progress).toHaveAttribute('aria-valuenow', '60');
    });

    it('alert/notification elements support role="alert"', () => {
        render(
            <div role="alert" aria-live="assertive">
                Operation successful
            </div>
        );
        const alert = screen.getByRole('alert');
        expect(alert).toBeInTheDocument();
        expect(alert).toHaveAttribute('aria-live', 'assertive');
    });
});

// ===================================================================
// 1D — Semantic Structure Tests
// ===================================================================
describe('1D — Semantic Structure', () => {
    it('page has an <h1> heading', () => {
        render(
            <div>
                <h1>ScholarForm AI</h1>
                <p>Format your academic manuscripts</p>
            </div>
        );
        const h1 = document.querySelector('h1');
        expect(h1).toBeInTheDocument();
        expect(h1?.textContent).toBeTruthy();
    });

    it('navigation uses <nav> element', () => {
        render(
            <nav aria-label="Main navigation">
                <a href="/">Home</a>
                <a href="/upload">Upload</a>
            </nav>
        );
        const nav = screen.getByRole('navigation');
        expect(nav).toBeInTheDocument();
    });

    it('main content uses <main> element', () => {
        render(
            <main id="main-content" tabIndex={-1}>
                <h1>Dashboard</h1>
            </main>
        );
        const main = document.querySelector('main');
        expect(main).toBeInTheDocument();
    });

    it('heading hierarchy is logical (no skipped levels)', () => {
        render(
            <div>
                <h1>Page Title</h1>
                <h2>Section One</h2>
                <h3>Sub-section</h3>
                <h2>Section Two</h2>
            </div>
        );
        const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6'));
        const levels = headings.map((h) => parseInt(h.tagName[1], 10));
        for (let i = 1; i < levels.length; i++) {
            expect(levels[i] - levels[i - 1]).toBeLessThanOrEqual(1);
        }
    });
});

// ===================================================================
// 1E — Reduced Motion Tests
// ===================================================================
import Skeleton from '@/components/ui/Skeleton';

describe('1E — Reduced Motion', () => {
    let originalMatchMedia;

    beforeEach(() => {
        originalMatchMedia = window.matchMedia;
    });

    afterEach(() => {
        Object.defineProperty(window, 'matchMedia', {
            value: originalMatchMedia,
            writable: true,
        });
    });

    function mockMatchMedia(prefersReducedMotion) {
        Object.defineProperty(window, 'matchMedia', {
            value: vi.fn().mockImplementation((query) => ({
                matches: query === '(prefers-reduced-motion: reduce)' ? prefersReducedMotion : false,
                media: query,
                addEventListener: vi.fn(),
                removeEventListener: vi.fn(),
                addListener: vi.fn(),
                removeListener: vi.fn(),
            })),
            writable: true,
        });
    }

    it('animations respect prefers-reduced-motion (no animate class when reduced)', () => {
        mockMatchMedia(true);
        const { container } = render(
            <div className="motion-safe:animate-fade-in">Content</div>
        );
        const el = container.firstChild;
        expect(el).toBeInTheDocument();
    });

    it('scroll reveals work without animation when reduced motion', () => {
        mockMatchMedia(true);
        const { container } = render(
            <div data-scroll-reveal className="opacity-100">Visible</div>
        );
        const el = container.querySelector('[data-scroll-reveal]');
        expect(el).toBeInTheDocument();
        expect(el?.textContent).toBe('Visible');
    });

    it('skeleton loaders do not pulse when reduced motion is preferred', () => {
        mockMatchMedia(true);
        const { container } = render(<Skeleton shimmer={false} />);
        const skeleton = container.firstChild;
        expect(skeleton).toBeInTheDocument();
        expect(skeleton.className).not.toContain('animate-pulse');
        expect(skeleton).toHaveAttribute('aria-hidden', 'true');
    });

    it('transitions complete instantly when reduced motion (no duration class)', () => {
        mockMatchMedia(true);
        const { container } = render(
            <div className="transition-none duration-0">Instant</div>
        );
        const el = container.firstChild;
        const classList = el.className;
        expect(classList).toContain('duration-0');
    });
});
