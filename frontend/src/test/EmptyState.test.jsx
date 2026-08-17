import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import EmptyState from '../components/ui/EmptyState';

describe('EmptyState', () => {
    it('renders default title and description', () => {
        render(<EmptyState />);
        expect(screen.getByText('No data yet')).toBeInTheDocument();
        expect(screen.getByText('There is nothing to show right now.')).toBeInTheDocument();
    });

    it('renders custom title and description', () => {
        render(<EmptyState title="Empty" description="Nothing here" />);
        expect(screen.getByText('Empty')).toBeInTheDocument();
        expect(screen.getByText('Nothing here')).toBeInTheDocument();
    });

    it('renders action button when actionLabel and onAction provided', () => {
        const onAction = vi.fn();
        render(<EmptyState actionLabel="Add Item" onAction={onAction} />);
        const btn = screen.getByText('Add Item');
        expect(btn).toBeInTheDocument();
        fireEvent.click(btn);
        expect(onAction).toHaveBeenCalledTimes(1);
    });

    it('does not render action button when only actionLabel given', () => {
        render(<EmptyState actionLabel="Add" />);
        expect(screen.queryByText('Add')).not.toBeInTheDocument();
    });

    it('renders custom action element when action prop provided', () => {
        render(<EmptyState action={<button>Custom</button>} />);
        expect(screen.getByText('Custom')).toBeInTheDocument();
    });

    it('renders with icon', () => {
        const { container } = render(<EmptyState icon="search" />);
        expect(container.querySelector('.lucide-search')).toBeInTheDocument();
    });
});
