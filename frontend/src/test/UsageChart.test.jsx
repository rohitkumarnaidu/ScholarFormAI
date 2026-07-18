import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import UsageChart from '../components/dashboard/UsageChart';

const sampleData = [
    { label: 'Mon', value: 10, date: '2026-06-01' },
    { label: 'Tue', value: 25, date: '2026-06-02' },
    { label: 'Wed', value: 15, date: '2026-06-03' },
    { label: 'Thu', value: 30, date: '2026-06-04' },
    { label: 'Fri', value: 8, date: '2026-06-05' },
];

describe('UsageChart', () => {
    it('renders bars for each data point', () => {
        const { container } = render(<UsageChart data={sampleData} />);
        const bars = container.querySelectorAll('[title]');
        expect(bars.length).toBe(sampleData.length);
    });

    it('scales bars correctly (largest value gets max height)', () => {
        const { container } = render(<UsageChart data={sampleData} height={200} />);
        const bars = container.querySelectorAll('div[class*="rounded-t-sm"]');
        expect(bars.length).toBe(sampleData.length);
        const heights = Array.from(bars).map(b => b.style.height);
        const maxH = Math.max(...heights.map(h => parseFloat(h)));
        const maxBar = heights.find(h => parseFloat(h) === maxH);
        expect(maxBar).toBeTruthy();
    });

    it('handles empty data', () => {
        render(<UsageChart data={[]} />);
        expect(screen.getByText('No activity data available')).toBeInTheDocument();
    });

    it('handles single data point', () => {
        const single = [{ label: 'Mon', value: 5, date: '2026-06-01' }];
        const { container } = render(<UsageChart data={single} />);
        const bars = container.querySelectorAll('[title]');
        expect(bars.length).toBe(1);
        expect(bars[0].getAttribute('title')).toContain('5');
    });

    it('shows tooltip on hover via title attribute', () => {
        render(<UsageChart data={sampleData} />);
        expect(screen.getByTitle('Mon: 10')).toBeInTheDocument();
        expect(screen.getByTitle('Tue: 25')).toBeInTheDocument();
        expect(screen.getByTitle('Wed: 15')).toBeInTheDocument();
    });

    it('handles loading state', () => {
        const { container } = render(<UsageChart data={sampleData} loading={true} />);
        const skeletons = container.querySelectorAll('[aria-hidden="true"]');
        expect(skeletons.length).toBeGreaterThan(0);
    });

    it('respects days prop', () => {
        const longData = Array.from({ length: 30 }, (_, i) => ({
            label: `D${i + 1}`,
            value: Math.floor(Math.random() * 20) + 1,
            date: `2026-06-${String(i + 1).padStart(2, '0')}`,
        }));
        const { container } = render(<UsageChart data={longData} days={7} />);
        const bars = container.querySelectorAll('[title]');
        expect(bars.length).toBe(7);
    });
});
