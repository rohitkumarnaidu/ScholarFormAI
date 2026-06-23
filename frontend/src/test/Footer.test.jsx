// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import Footer from '../components/Footer';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
vi.mock('@/src/services/api', () => ({
    useMetricsHealth: () => ({ data: { status: 'healthy', version: '1.0' } })
}));

describe('Footer', () => {
    it('renders app footer with policy and support links', () => {
        render(<QueryClientProvider client={queryClient}><Footer variant="app" /></QueryClientProvider>);

        expect(screen.getByRole('link', { name: /terms of service/i })).toHaveAttribute('href', '/terms');
        expect(screen.getByRole('link', { name: /privacy policy/i })).toHaveAttribute('href', '/privacy');
        expect(screen.getByRole('link', { name: /support/i })).toHaveAttribute('href', 'mailto:support@scholarform.ai');
    });

    it('renders landing footer core navigation links', () => {
        render(<QueryClientProvider client={queryClient}><Footer variant="landing" /></QueryClientProvider>);

        expect(screen.getByRole('link', { name: /^templates$/i })).toHaveAttribute('href', '/templates');
        expect(screen.getByRole('link', { name: /^pricing$/i })).toHaveAttribute('href', '/#pricing');
        expect(screen.getByRole('link', { name: /privacy policy/i })).toHaveAttribute('href', '/privacy');
    });
});
