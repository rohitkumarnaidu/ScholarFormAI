import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import React from 'react';
import Skeleton from '../components/ui/Skeleton';

describe('Skeleton', () => {
    it('renders with aria-hidden', () => {
        const { container } = render(<Skeleton />);
        expect(container.firstChild).toHaveAttribute('aria-hidden', 'true');
    });

    it('has animate-pulse by default', () => {
        const { container } = render(<Skeleton />);
        expect(container.firstChild.className).toContain('animate-pulse');
    });

    it('removes shimmer when shimmer is false', () => {
        const { container } = render(<Skeleton shimmer={false} />);
        expect(container.firstChild.className).not.toContain('animate-pulse');
    });

    it('applies width and height as inline style', () => {
        const { container } = render(<Skeleton width="200" height="100" />);
        expect(container.firstChild).toHaveStyle('width: 200');
        expect(container.firstChild).toHaveStyle('height: 100');
    });

    it('uses default rounded class', () => {
        const { container } = render(<Skeleton />);
        expect(container.firstChild.className).toContain('rounded-lg');
    });

    it('accepts custom rounded class', () => {
        const { container } = render(<Skeleton rounded="rounded-full" />);
        expect(container.firstChild.className).toContain('rounded-full');
    });
});
