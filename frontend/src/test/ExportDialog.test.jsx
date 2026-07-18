// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import ExportDialog from '../components/ExportDialog';

describe('ExportDialog', () => {
    it('returns null when not open', () => {
        const { container } = render(<ExportDialog isOpen={false} />);
        expect(container.innerHTML).toBe('');
    });

    it('renders export dialog with format options', () => {
        render(<ExportDialog isOpen={true} />);
        expect(screen.getByTestId('export-dialog')).toBeInTheDocument();
        expect(screen.getByText('Export Document')).toBeInTheDocument();
        expect(screen.getByText('DOCX (.docx)')).toBeInTheDocument();
        expect(screen.getByText('PDF (.pdf)')).toBeInTheDocument();
        expect(screen.getByText('LaTeX (.tex)')).toBeInTheDocument();
    });

    it('calls onDownload with selected format', async () => {
        const onDownload = vi.fn();
        render(<ExportDialog isOpen={true} onDownload={onDownload} />);
        await userEvent.click(screen.getByTestId('export-download-button'));
        expect(onDownload).toHaveBeenCalledWith('docx');
    });

    it('changes format and calls onDownload with new format', async () => {
        const onDownload = vi.fn();
        render(<ExportDialog isOpen={true} onDownload={onDownload} />);
        const select = screen.getByTestId('export-format-select');
        await userEvent.selectOptions(select, 'pdf');
        await userEvent.click(screen.getByTestId('export-download-button'));
        expect(onDownload).toHaveBeenCalledWith('pdf');
    });

    it('handles loading state with disabled buttons', () => {
        render(<ExportDialog isOpen={true} isDownloading={true} />);
        expect(screen.getByText('Downloading...')).toBeInTheDocument();
        expect(screen.getByTestId('export-download-button')).toBeDisabled();
        expect(screen.getByText('Cancel')).toBeDisabled();
    });

    it('shows error message when error prop is provided', () => {
        render(<ExportDialog isOpen={true} error="Network error occurred" />);
        expect(screen.getByText('Network error occurred')).toBeInTheDocument();
    });

    it('calls onClose when Cancel is clicked', async () => {
        const onClose = vi.fn();
        render(<ExportDialog isOpen={true} onClose={onClose} />);
        await userEvent.click(screen.getByText('Cancel'));
        expect(onClose).toHaveBeenCalledOnce();
    });
});
