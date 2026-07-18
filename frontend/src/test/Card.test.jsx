import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import Card from '../components/ui/Card';

describe('Card', () => {
    it('renders children', () => {
        render(<Card><p>Content</p></Card>);
        expect(screen.getByText('Content')).toBeInTheDocument();
    });

    it('renders without glass by default', () => {
        const { container } = render(<Card>Default</Card>);
        expect(container.firstChild.className).toContain('bg-white');
        expect(container.firstChild.className).not.toContain('glass');
    });

    it('applies glass class when glass is true', () => {
        const { container } = render(<Card glass>Glass</Card>);
        expect(container.firstChild.className).toContain('bg-glass-surface');
    });

    it('accepts additional className', () => {
        const { container } = render(<Card className="custom-class">Custom</Card>);
        expect(container.firstChild.className).toContain('custom-class');
    });
});
