import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import HealthStatusIndicator from '../components/HealthStatusIndicator';

describe('HealthStatusIndicator', () => {
    it('renders label', () => {
        render(<HealthStatusIndicator status="healthy" label="API Server" />);
        expect(screen.getByText('API Server')).toBeInTheDocument();
    });

    it('renders status text', () => {
        render(<HealthStatusIndicator status="healthy" label="API" />);
        expect(screen.getByText('healthy')).toBeInTheDocument();
    });

    it('renders details when provided', () => {
        render(<HealthStatusIndicator status="degraded" label="DB" details="High latency" />);
        expect(screen.getByText('High latency')).toBeInTheDocument();
    });

    it('falls back to unknown for unknown status', () => {
        const { container } = render(<HealthStatusIndicator status="weird" label="X" />);
        expect(container.firstChild.className).toContain('bg-slate-100');
    });

    it('renders all known status variants', () => {
        const { rerender, container } = render(<HealthStatusIndicator status="healthy" label="A" />);
        expect(container.firstChild.className).toContain('bg-green-100');

        rerender(<HealthStatusIndicator status="degraded" label="B" />);
        expect(container.firstChild.className).toContain('bg-amber-100');

        rerender(<HealthStatusIndicator status="unavailable" label="C" />);
        expect(container.firstChild.className).toContain('bg-red-100');
    });
});
