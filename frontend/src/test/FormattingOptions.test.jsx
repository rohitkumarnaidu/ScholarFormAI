// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import FormattingOptions from '../components/upload/FormattingOptions';

describe('FormattingOptions', () => {
    const defaultProps = {
        addPageNumbers: false,
        setAddPageNumbers: vi.fn(),
        addBorders: false,
        setAddBorders: vi.fn(),
        addCoverPage: false,
        setAddCoverPage: vi.fn(),
        generateTOC: false,
        setGenerateTOC: vi.fn(),
        pageSize: 'Letter',
        setPageSize: vi.fn(),
        isProcessing: false,
        progress: 0,
        file: { name: 'test.docx', size: 1024 },
        onProcess: vi.fn(),
    };

    it('renders all formatting option labels', () => {
        render(<FormattingOptions {...defaultProps} />);
        expect(screen.getByText('Add Page Numbers')).toBeInTheDocument();
        expect(screen.getByText('Add Borders')).toBeInTheDocument();
        expect(screen.getByText('Add Cover Page')).toBeInTheDocument();
        expect(screen.getByText('Generate TOC')).toBeInTheDocument();
    });

    it('renders page size selector with default value', () => {
        render(<FormattingOptions {...defaultProps} />);
        const select = screen.getByDisplayValue('Letter (US Default)');
        expect(select).toBeInTheDocument();
    });

    it('renders 4 toggle checkboxes', async () => {
        render(<FormattingOptions {...defaultProps} />);
        await waitFor(() => {
            const checkboxes = screen.getAllByRole('checkbox');
            expect(checkboxes).toHaveLength(4);
        });
    });

    it('calls setAddPageNumbers when page numbers checkbox is changed', async () => {
        const setAddPageNumbers = vi.fn();
        render(<FormattingOptions {...defaultProps} setAddPageNumbers={setAddPageNumbers} />);
        const checkboxes = screen.getAllByRole('checkbox');
        await userEvent.click(checkboxes[0]);
        expect(setAddPageNumbers).toHaveBeenCalledWith(true);
    });

    it('calls setGenerateTOC when TOC checkbox is changed', async () => {
        const setGenerateTOC = vi.fn();
        render(<FormattingOptions {...defaultProps} setGenerateTOC={setGenerateTOC} />);
        const checkboxes = screen.getAllByRole('checkbox');
        await userEvent.click(checkboxes[3]);
        expect(setGenerateTOC).toHaveBeenCalledWith(true);
    });

    it('calls setPageSize when page size is changed', async () => {
        const setPageSize = vi.fn();
        render(<FormattingOptions {...defaultProps} setPageSize={setPageSize} />);
        const select = screen.getByDisplayValue('Letter (US Default)');
        await userEvent.selectOptions(select, 'A4');
        expect(setPageSize).toHaveBeenCalledWith('A4');
    });

    it('disables inputs during processing', () => {
        render(<FormattingOptions {...defaultProps} isProcessing={true} />);
        const checkboxes = screen.getAllByRole('checkbox');
        checkboxes.forEach((cb) => expect(cb).toBeDisabled());
        expect(screen.getByRole('combobox')).toBeDisabled();
    });

    it('shows Processing button text when processing', () => {
        render(<FormattingOptions {...defaultProps} isProcessing={true} progress={50} />);
        expect(screen.getByText('Processing Manuscript...')).toBeInTheDocument();
    });
});
