import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import ConfirmDialog from '../components/ui/ConfirmDialog';

describe('ui/ConfirmDialog', () => {
    it('returns null when not open', () => {
        const { container } = render(<ConfirmDialog open={false} />);
        expect(container.innerHTML).toBe('');
    });

    it('renders when open', () => {
        render(<ConfirmDialog open title="Are you sure?" />);
        expect(screen.getByText('Are you sure?')).toBeInTheDocument();
        expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('renders default confirm button', () => {
        render(<ConfirmDialog open onConfirm={() => {}} />);
        expect(screen.getByText('Confirm')).toBeInTheDocument();
    });

    it('renders default cancel button', () => {
        render(<ConfirmDialog open onCancel={() => {}} />);
        expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    it('calls onConfirm when confirm clicked', () => {
        const onConfirm = vi.fn();
        render(<ConfirmDialog open onConfirm={onConfirm} />);
        fireEvent.click(screen.getByText('Confirm'));
        expect(onConfirm).toHaveBeenCalledTimes(1);
    });

    it('calls onCancel when cancel clicked', () => {
        const onCancel = vi.fn();
        render(<ConfirmDialog open onCancel={onCancel} />);
        fireEvent.click(screen.getByText('Cancel'));
        expect(onCancel).toHaveBeenCalledTimes(1);
    });

    it('shows loading state', () => {
        render(<ConfirmDialog open isLoading onConfirm={() => {}} />);
        expect(screen.getByRole('button', { name: 'Confirm' })).toBeDisabled();
    });

    it('shows description when provided', () => {
        render(<ConfirmDialog open description="This action cannot be undone" />);
        expect(screen.getByText('This action cannot be undone')).toBeInTheDocument();
    });

    it('uses danger variant buttons by default', () => {
        render(<ConfirmDialog open onConfirm={() => {}} />);
        const confirmBtn = screen.getByText('Confirm').closest('button');
        expect(confirmBtn.className).toContain('bg-red');
    });
});
