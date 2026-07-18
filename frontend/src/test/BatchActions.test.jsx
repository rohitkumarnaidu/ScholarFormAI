import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import React from 'react';
import BatchActions from '../components/history/BatchActions';

describe('BatchActions', () => {
    it('shows correct selected count (multi)', () => {
        render(<BatchActions selectedIds={['a', 'b', 'c']} />);
        expect(screen.getByText('3 items selected')).toBeInTheDocument();
    });

    it('shows correct selected count (single)', () => {
        render(<BatchActions selectedIds={['a']} />);
        expect(screen.getByText('1 item selected')).toBeInTheDocument();
    });

    it('delete button shows confirmation dialog', () => {
        render(<BatchActions selectedIds={['a', 'b']} />);
        fireEvent.click(screen.getByText('Delete'));
        expect(screen.getByText('Delete 2 items?')).toBeInTheDocument();
        expect(screen.getByText(/This action cannot be undone/)).toBeInTheDocument();
    });

    it('export button calls onExport', () => {
        const onExport = vi.fn();
        render(<BatchActions selectedIds={['a']} onExport={onExport} />);
        fireEvent.click(screen.getByText('Export'));
        expect(onExport).toHaveBeenCalledOnce();
    });

    it('deselect all clears selection', () => {
        const onDeselectAll = vi.fn();
        render(<BatchActions selectedIds={['a', 'b']} onDeselectAll={onDeselectAll} />);
        fireEvent.click(screen.getByText('Deselect all'));
        expect(onDeselectAll).toHaveBeenCalledOnce();
    });

    it('hidden when nothing selected', () => {
        const { container } = render(<BatchActions selectedIds={[]} />);
        expect(container.innerHTML).toBe('');
    });

    it('handles single selection vs multi-selection display', () => {
        const { rerender } = render(<BatchActions selectedIds={['a']} />);
        expect(screen.getByText('1 item selected')).toBeInTheDocument();

        rerender(<BatchActions selectedIds={['a', 'b', 'c']} />);
        expect(screen.getByText('3 items selected')).toBeInTheDocument();
    });

    it('confirm delete calls onDelete', () => {
        const onDelete = vi.fn();
        render(<BatchActions selectedIds={['a']} onDelete={onDelete} />);
        fireEvent.click(screen.getByText('Delete'));
        const dialog = screen.getByRole('dialog');
        fireEvent.click(within(dialog).getByText('Delete'));
        expect(onDelete).toHaveBeenCalledOnce();
    });

    it('cancel does not call onDelete', () => {
        const onDelete = vi.fn();
        render(<BatchActions selectedIds={['a']} onDelete={onDelete} />);
        fireEvent.click(screen.getByText('Delete'));
        fireEvent.click(screen.getByText('Cancel'));
        expect(onDelete).not.toHaveBeenCalled();
    });
});
