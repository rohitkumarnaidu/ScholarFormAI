import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import ConfirmDialog from '../components/ui/ConfirmDialog';

describe('ConfirmDialog (danger variant)', () => {
    it('returns null when not open', () => {
        const { container } = render(<ConfirmDialog open={false} />);
        expect(container.innerHTML).toBe('');
    });

    it('renders when open', () => {
        render(<ConfirmDialog open title="Delete Document" confirmLabel="Delete" />);
        expect(screen.getByText('Delete Document')).toBeInTheDocument();
        expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('shows document name in description', () => {
        render(<ConfirmDialog open title="Delete Document" confirmLabel="Delete" description="Are you sure you want to delete thesis.docx? This action cannot be undone." />);
        expect(screen.getByText(/thesis\.docx/)).toBeInTheDocument();
    });

    it('calls onConfirm when delete clicked', () => {
        const onConfirm = vi.fn();
        render(<ConfirmDialog open confirmLabel="Delete" onConfirm={onConfirm} />);
        fireEvent.click(screen.getByText('Delete'));
        expect(onConfirm).toHaveBeenCalledTimes(1);
    });

    it('calls onCancel when cancel clicked', () => {
        const onCancel = vi.fn();
        render(<ConfirmDialog open onCancel={onCancel} />);
        fireEvent.click(screen.getByText('Cancel'));
        expect(onCancel).toHaveBeenCalledTimes(1);
    });

    it('disables buttons when loading', () => {
        render(<ConfirmDialog open isLoading confirmLabel="Delete" onConfirm={() => {}} />);
        expect(screen.getByRole('button', { name: 'Delete' })).toBeDisabled();
        expect(screen.getByText('Cancel').closest('button')).toBeDisabled();
    });
});
