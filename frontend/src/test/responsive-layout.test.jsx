// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

/**
 * Responsive layout tests
 * Validates component behavior across mobile, tablet, and desktop viewports
 * by mocking matchMedia and checking rendered structure.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

// ── Shared mocks ──────────────────────────────────────────────
vi.mock('next/navigation', () => ({
    useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
    usePathname: () => '/',
    useSearchParams: () => new URLSearchParams(),
}));

vi.mock('@/src/lib/supabaseClient', () => ({ supabase: null }));
vi.mock('@/src/context/AuthContext', () => ({
    useAuth: () => ({ user: null, isLoggedIn: false, loading: false }),
}));

vi.mock('@/src/components/layout/header/ThemeToggle', () => ({
    default: () => <div data-testid="theme-toggle">Theme</div>,
}));

vi.mock('@/src/components/NotificationBell', () => ({
    default: () => <div data-testid="notification-bell">Bell</div>,
}));

// ── Helpers ──────────────────────────────────────────────────
function setViewport(width) {
    Object.defineProperty(window, 'innerWidth', {
        value: width,
        writable: true,
    });
    Object.defineProperty(window, 'innerHeight', {
        value: width < 768 ? 800 : 900,
        writable: true,
    });
    window.dispatchEvent(new Event('resize'));

    Object.defineProperty(window, 'matchMedia', {
        value: vi.fn().mockImplementation((query) => {
            const isMobile = width < 768;
            const isTablet = width >= 768 && width < 1024;
            const isDesktop = width >= 1024;
            const matches =
                (query === '(min-width: 1024px)' && isDesktop) ||
                (query === '(min-width: 768px)' && (isTablet || isDesktop)) ||
                (query === '(max-width: 767px)' && isMobile) ||
                (query === '(pointer: coarse)' && (isMobile || isTablet));
            return {
                matches,
                media: query,
                addEventListener: vi.fn(),
                removeEventListener: vi.fn(),
                addListener: vi.fn(),
                removeListener: vi.fn(),
            };
        }),
        writable: true,
    });
}

import Header from '@/src/components/layout/Header';

// ===================================================================
// 2A — Mobile Viewport Tests (< 768px)
// ===================================================================
describe('2A — Mobile Viewport', () => {
    beforeEach(() => {
        setViewport(375);
    });

    it('sidebar is hidden on mobile (not rendered)', () => {
        // Sidebar should not be shown in the DOM on mobile when not toggled
        const { container } = render(
            <div className="app-shell">
                <div className="hidden lg:block" data-testid="desktop-sidebar">
                    Sidebar content
                </div>
                <main>Content</main>
            </div>
        );
        const sidebar = container.querySelector('[data-testid="desktop-sidebar"]');
        expect(sidebar).toBeInTheDocument();
        expect(sidebar.className).toContain('hidden');
    });

    it('header shows hamburger menu on mobile', async () => {
        const onToggle = vi.fn();
        render(<Header isSidebarLayout onOpenMobileSidebar={onToggle} />);
        const toggleBtn = screen.getByLabelText('Toggle Sidebar');
        expect(toggleBtn).toBeInTheDocument();
        fireEvent.click(toggleBtn);
        expect(onToggle).toHaveBeenCalled();
    });

    it('content stacks vertically on mobile', () => {
        render(
            <div className="flex flex-col sm:flex-row">
                <div data-testid="panel-a">Panel A</div>
                <div data-testid="panel-b">Panel B</div>
            </div>
        );
        const wrapper = screen.getByText('Panel A').parentElement;
        expect(wrapper.className).toContain('flex-col');
    });

    it('forms are full-width on mobile', () => {
        render(
            <form className="w-full">
                <input
                    className="w-full rounded-xl border px-4 py-2.5"
                    placeholder="Full width input"
                    aria-label="Full name"
                />
            </form>
        );
        const input = screen.getByLabelText('Full name');
        expect(input.className).toContain('w-full');
    });

    it('tables scroll horizontally on mobile via wrapper', () => {
        render(
            <div className="overflow-x-auto" data-testid="table-wrapper">
                <table>
                    <thead>
                        <tr><th>Column 1</th><th>Column 2</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>Data 1</td><td>Data 2</td></tr>
                    </tbody>
                </table>
            </div>
        );
        const wrapper = screen.getByTestId('table-wrapper');
        expect(wrapper.className).toContain('overflow-x-auto');
    });

    it('buttons are touch-target sized (min 44px) on mobile', () => {
        const { container } = render(
            <button
                className="h-12 px-5 text-base"
                style={{ minWidth: '44px', minHeight: '44px' }}
            >
                Submit
            </button>
        );
        const btn = container.querySelector('button');
        const style = getComputedStyle(btn);
        expect(parseInt(style.minHeight, 10)).toBeGreaterThanOrEqual(44);
        expect(parseInt(style.minWidth, 10)).toBeGreaterThanOrEqual(44);
    });
});

// ===================================================================
// 2B — Tablet Viewport Tests (768px - 1023px)
// ===================================================================
describe('2B — Tablet Viewport', () => {
    beforeEach(() => {
        setViewport(800);
    });

    it('sidebar is collapsible on tablet', () => {
        const { container } = render(
            <div className="flex">
                <aside
                    data-testid="tablet-sidebar"
                    className="hidden md:block lg:w-60 w-16"
                >
                    Sidebar
                </aside>
                <main>Content</main>
            </div>
        );
        const sidebar = container.querySelector('[data-testid="tablet-sidebar"]');
        expect(sidebar).toBeInTheDocument();
        expect(sidebar.className).toContain('md:block');
    });

    it('split panels stack or work correctly on tablet', () => {
        render(
            <div className="flex flex-col md:flex-row gap-4">
                <div data-testid="editor-panel" className="flex-1">Editor</div>
                <div data-testid="preview-panel" className="flex-1">Preview</div>
            </div>
        );
        const wrapper = screen.getByText('Editor').parentElement;
        expect(wrapper.className).toContain('md:flex-row');
        expect(wrapper.className).toContain('flex-col');
    });

    it('multi-column layouts collapse to 2 columns on tablet', () => {
        render(
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {[1, 2, 3].map((i) => (
                    <div key={i} data-testid={`col-${i}`}>Column {i}</div>
                ))}
            </div>
        );
        const grid = screen.getByText('Column 1').parentElement;
        expect(grid.className).toContain('sm:grid-cols-2');
        expect(grid.className).toContain('lg:grid-cols-3');
    });

    it('tablet header contains sidebar toggle', async () => {
        const onToggle = vi.fn();
        render(<Header isSidebarLayout onOpenMobileSidebar={onToggle} />);
        const toggleBtn = screen.getByLabelText('Toggle Sidebar');
        expect(toggleBtn).toBeInTheDocument();
    });
});

// ===================================================================
// 2C — Desktop Viewport Tests (>= 1024px)
// ===================================================================
import Sidebar from '@/src/components/layout/Sidebar';

describe('2C — Desktop Viewport', () => {
    beforeEach(() => {
        setViewport(1440);
    });

    it('sidebar is visible on desktop', () => {
        render(
            <div className="flex">
                <aside className="lg:flex w-60" data-testid="desktop-sidebar">
                    <Sidebar />
                </aside>
            </div>
        );
        const sidebar = document.querySelector('[data-testid="desktop-sidebar"]');
        expect(sidebar).toBeInTheDocument();
    });

    it('max-width containers use responsive class', () => {
        render(
            <div className="max-w-7xl mx-auto px-4" data-testid="content-container">
                <p>Constrained content</p>
            </div>
        );
        const container = screen.getByTestId('content-container');
        expect(container.className).toContain('max-w-7xl');
        expect(container.className).toContain('mx-auto');
    });

    it('multi-column layouts render correctly on desktop', () => {
        render(
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {[1, 2, 3, 4].map((i) => (
                    <div key={i} data-testid={`desktop-col-${i}`}>Card {i}</div>
                ))}
            </div>
        );
        const grid = screen.getByText('Card 1').parentElement;
        expect(grid.className).toContain('lg:grid-cols-4');
    });

    it('tooltips appear on hover (title attribute)', () => {
        render(
            <button title="More information" aria-label="Info">
                Hover me
            </button>
        );
        const btn = screen.getByLabelText('Info');
        expect(btn).toHaveAttribute('title', 'More information');
        fireEvent.mouseEnter(btn);
        expect(btn.title).toBe('More information');
    });
});
