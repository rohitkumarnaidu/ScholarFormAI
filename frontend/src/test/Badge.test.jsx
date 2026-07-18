import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import Badge from '../components/ui/Badge';

describe('Badge', () => {
    it('renders children', () => {
        render(<Badge>Active</Badge>);
        expect(screen.getByText('Active')).toBeInTheDocument();
    });

    it('renders status text when no children', () => {
        render(<Badge status="completed" />);
        expect(screen.getByText('completed')).toBeInTheDocument();
    });

    it('applies correct class for completed status', () => {
        const { container } = render(<Badge status="completed">Done</Badge>);
        expect(container.firstChild.className).toContain('green');
    });

    it('applies correct class for failed status', () => {
        const { container } = render(<Badge status="failed">Fail</Badge>);
        expect(container.firstChild.className).toContain('red');
    });

    it('applies correct class for processing status', () => {
        const { container } = render(<Badge status="processing">Proc</Badge>);
        expect(container.firstChild.className).toContain('blue');
    });

    it('falls back to pending for unknown status', () => {
        render(<Badge status="unknown_status">Unknown</Badge>);
        expect(screen.getByText('Unknown')).toBeInTheDocument();
    });

    it('handles null status', () => {
        render(<Badge status={null}>Null</Badge>);
        expect(screen.getByText('Null')).toBeInTheDocument();
    });

    it('accepts additional className', () => {
        const { container } = render(<Badge className="extra-class">Test</Badge>);
        expect(container.firstChild.className).toContain('extra-class');
    });
});
