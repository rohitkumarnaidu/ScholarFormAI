// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import DashboardStats, { StatsCard as StatCard } from '../components/dashboard/DashboardStats';

describe('StatCard', () => {
    const baseProps = {
        title: 'Total Documents',
        value: '12',
        description: 'All manuscripts processed',
        icon: 'description',
        iconColor: 'text-blue-600',
        bgColor: 'bg-blue-50',
    };

    it('renders title and value', () => {
        render(<StatCard {...baseProps} />);
        expect(screen.getByText('Total Documents')).toBeInTheDocument();
        expect(screen.getByText('12')).toBeInTheDocument();
    });

    it('renders subtitle when provided', () => {
        render(<StatCard {...baseProps} description="All manuscripts processed" />);
        expect(screen.getByText('All manuscripts processed')).toBeInTheDocument();
    });

    it('renders icon', () => {
        render(<StatCard {...baseProps} />);
        expect(document.querySelector('.lucide-file-text')).toBeInTheDocument();
    });
});

describe('DashboardStats', () => {
    const baseStats = {
        totalDocuments: 42,
        formattedThisMonth: 15,
        successRate: 0.89,
        avgProcessingTime: '12s',
        storageUsed: '256 MB',
    };

    it('renders all stat cards', () => {
        render(<DashboardStats stats={baseStats} />);
        expect(screen.getByText('Total Documents')).toBeInTheDocument();
        expect(screen.getByText('Formatted This Month')).toBeInTheDocument();
        expect(screen.getByText('Success Rate')).toBeInTheDocument();
        expect(screen.getByText('Avg Processing Time')).toBeInTheDocument();
        expect(screen.getByText('Storage Used')).toBeInTheDocument();
    });

    it('shows formatted count correctly', () => {
        render(<DashboardStats stats={baseStats} />);
        expect(screen.getByText('15')).toBeInTheDocument();
    });

    it('shows success rate as percentage', () => {
        render(<DashboardStats stats={baseStats} />);
        expect(screen.getByText('89%')).toBeInTheDocument();
    });

    it('shows average processing time', () => {
        render(<DashboardStats stats={baseStats} />);
        expect(screen.getByText('12s')).toBeInTheDocument();
    });

    it('handles loading skeleton state', () => {
        const { container } = render(<DashboardStats stats={baseStats} loading={true} />);
        const skeletons = container.querySelectorAll('[class*="animate-pulse"]');
        expect(skeletons.length).toBeGreaterThan(0);
    });

    it('handles null stats gracefully', () => {
        render(<DashboardStats stats={null} />);
        expect(screen.getByText('Total Documents')).toBeInTheDocument();
    });

    it('shows chart bars in activity section', () => {
        render(<DashboardStats stats={baseStats} />);
        expect(screen.getByText('Activity (Last 7 Days)')).toBeInTheDocument();
    });
});
