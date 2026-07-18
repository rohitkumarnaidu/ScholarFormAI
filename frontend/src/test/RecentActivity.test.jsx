import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import RecentActivity, { formatTimestamp } from '../components/dashboard/RecentActivity';

const activities = [
    { id: '1', type: 'upload', description: 'Uploaded manuscript', timestamp: new Date().toISOString(), documentName: 'paper1.docx' },
    { id: '2', type: 'format', description: 'Formatted document', timestamp: new Date(Date.now() - 3600000).toISOString(), documentName: 'paper2.docx' },
    { id: '3', type: 'download', description: 'Downloaded result', timestamp: new Date(Date.now() - 86400000).toISOString(), documentName: 'paper3.docx' },
    { id: '4', type: 'edit', description: 'Edited section 2', timestamp: new Date(Date.now() - 172800000).toISOString(), documentName: 'paper1.docx' },
    { id: '5', type: 'export', description: 'Exported to PDF', timestamp: new Date(Date.now() - 604800000).toISOString(), documentName: 'paper4.docx' },
];

describe('RecentActivity', () => {
    it('renders activity items', () => {
        render(<RecentActivity activities={activities} />);
        expect(screen.getByText('Uploaded manuscript')).toBeInTheDocument();
        expect(screen.getByText('Formatted document')).toBeInTheDocument();
        expect(screen.getByText('Downloaded result')).toBeInTheDocument();
        expect(screen.getByText('Edited section 2')).toBeInTheDocument();
        expect(screen.getByText('Exported to PDF')).toBeInTheDocument();
    });

    it('shows correct icons per type', () => {
        const { container } = render(<RecentActivity activities={activities} />);
        const icons = container.querySelectorAll('.flex.items-center.justify-center.text-sm.font-bold');
        expect(icons.length).toBe(5);
        expect(icons[0].textContent).toBe('↑');
        expect(icons[1].textContent).toBe('⚙');
        expect(icons[2].textContent).toBe('↓');
        expect(icons[3].textContent).toBe('✏');
        expect(icons[4].textContent).toBe('📄');
    });

    it('handles empty state', () => {
        render(<RecentActivity activities={[]} />);
        expect(screen.getByText('No recent activity')).toBeInTheDocument();
    });

    it('handles loading state', () => {
        const { container } = render(<RecentActivity activities={activities} loading={true} />);
        const skeletons = container.querySelectorAll('[aria-hidden="true"]');
        expect(skeletons.length).toBeGreaterThan(0);
    });

    it('formats timestamps correctly via formatTimestamp', () => {
        const justNow = formatTimestamp(new Date().toISOString());
        expect(justNow).toBe('Just now');
        const fiveMinAgo = formatTimestamp(new Date(Date.now() - 300000).toISOString());
        expect(fiveMinAgo).toBe('5m ago');
        const twoHoursAgo = formatTimestamp(new Date(Date.now() - 7200000).toISOString());
        expect(twoHoursAgo).toBe('2h ago');
        const threeDaysAgo = formatTimestamp(new Date(Date.now() - 259200000).toISOString());
        expect(threeDaysAgo).toBe('3d ago');
    });

    it('shows "View all" link', () => {
        render(<RecentActivity activities={activities} />);
        expect(screen.getByText('View all')).toBeInTheDocument();
    });

    it('shows document names', () => {
        render(<RecentActivity activities={activities} />);
        const papers1 = screen.getAllByText('paper1.docx');
        expect(papers1.length).toBe(2);
        expect(screen.getByText('paper2.docx')).toBeInTheDocument();
    });
});
