import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

vi.mock('../components/ui/Button', () => ({
    default: ({ children, onClick, variant }) => (
        <button onClick={onClick} data-variant={variant}>{children}</button>
    ),
}));

import EmptyState from '../components/ui/EmptyState';

describe('EmptyState component', () => {
    it('renders default title and description', () => {
        render(<EmptyState />);
        expect(screen.getByText('No data yet')).toBeInTheDocument();
        expect(screen.getByText('There is nothing to show right now.')).toBeInTheDocument();
    });

    it('renders custom title and description', () => {
        render(<EmptyState title="Custom Title" description="Custom description here" />);
        expect(screen.getByText('Custom Title')).toBeInTheDocument();
        expect(screen.getByText('Custom description here')).toBeInTheDocument();
    });

    it('renders action button with actionLabel and onAction', () => {
        const onAction = vi.fn();
        render(<EmptyState actionLabel="Create" onAction={onAction} />);
        const btn = screen.getByText('Create');
        expect(btn).toBeInTheDocument();
        fireEvent.click(btn);
        expect(onAction).toHaveBeenCalledTimes(1);
    });

    it('renders with icon', () => {
        const { container } = render(<EmptyState icon="search" />);
        expect(container.querySelector('.lucide-search')).toBeInTheDocument();
    });

    it('does not render action button when only actionLabel given without onAction', () => {
        render(<EmptyState actionLabel="Alone" />);
        expect(screen.queryByText('Alone')).not.toBeInTheDocument();
    });

    it('renders custom action element when action prop provided', () => {
        render(<EmptyState action={<button>Custom Button</button>} />);
        expect(screen.getByText('Custom Button')).toBeInTheDocument();
    });

    it('renders with default icon when no icon specified', () => {
        const { container } = render(<EmptyState />);
        expect(container.querySelector('.lucide-inbox')).toBeInTheDocument();
    });

    it('renders action with secondary variant', () => {
        const onAction = vi.fn();
        render(<EmptyState actionLabel="Get Started" onAction={onAction} />);
        const btn = screen.getByText('Get Started');
        expect(btn).toHaveAttribute('data-variant', 'secondary');
    });
});

describe('Empty dashboard', () => {
    it('shows getting started message', () => {
        const onAction = vi.fn();
        render(<EmptyState title="Welcome!" description="Upload your first document to get started" actionLabel="Upload Document" onAction={onAction} />);
        expect(screen.getByText('Welcome!')).toBeInTheDocument();
        expect(screen.getByText('Upload your first document to get started')).toBeInTheDocument();
        expect(screen.getByText('Upload Document')).toBeInTheDocument();
    });
});

describe('Empty document list', () => {
    it('shows upload prompt', () => {
        render(<EmptyState icon="description" title="No documents yet" description="Upload a manuscript to begin formatting" />);
        expect(screen.getByText('No documents yet')).toBeInTheDocument();
        expect(screen.getByText('Upload a manuscript to begin formatting')).toBeInTheDocument();
    });
});

describe('Empty history', () => {
    it('shows no jobs message', () => {
        render(<EmptyState icon="history" title="No formatting history" description="Your completed formatting jobs will appear here" />);
        expect(screen.getByText('No formatting history')).toBeInTheDocument();
    });
});

describe('Empty notifications', () => {
    it('shows all clear message', () => {
        render(<EmptyState icon="notifications_off" title="All caught up" description="You have no unread notifications" />);
        expect(screen.getByText('All caught up')).toBeInTheDocument();
        expect(screen.getByText('You have no unread notifications')).toBeInTheDocument();
    });
});
