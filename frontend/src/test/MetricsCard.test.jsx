import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import MetricsCard from '../components/MetricsCard';

describe('MetricsCard', () => {
    it('renders title and value', () => {
        render(<MetricsCard title="Documents" value="42" />);
        expect(screen.getByText('Documents')).toBeInTheDocument();
        expect(screen.getByText('42')).toBeInTheDocument();
    });

    it('shows dash for null value', () => {
        render(<MetricsCard title="Docs" value={null} />);
        expect(screen.getByText('—')).toBeInTheDocument();
    });

    it('shows loading skeleton when isLoading', () => {
        const { container } = render(<MetricsCard title="Docs" value="42" isLoading />);
        expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    });

    it('renders subtitle when provided', () => {
        render(<MetricsCard title="Docs" value="5" subtitle="Last 7 days" />);
        expect(screen.getByText('Last 7 days')).toBeInTheDocument();
    });

    it('renders trend indicator', () => {
        render(<MetricsCard title="Docs" value="10" trend={15} />);
        expect(screen.getByText('15%')).toBeInTheDocument();
    });

    it('shows negative trend in red', () => {
        render(<MetricsCard title="Docs" value="10" trend={-5} />);
        expect(screen.getByText('5%')).toBeInTheDocument();
    });

    it('renders icon when provided', () => {
        const { container } = render(<MetricsCard title="Docs" value="3" icon="description" />);
        expect(container.querySelector('.material-symbols-outlined')).toHaveTextContent('description');
    });
});
