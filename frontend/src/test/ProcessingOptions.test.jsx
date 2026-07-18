import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import ProcessingOptions from '../components/ProcessingOptions';

describe('ProcessingOptions', () => {
    it('renders select with default options', () => {
        render(<ProcessingOptions />);
        expect(screen.getByText('DOCX (.docx)')).toBeInTheDocument();
        expect(screen.getByText('PDF (.pdf)')).toBeInTheDocument();
        expect(screen.getByText('LaTeX (.tex)')).toBeInTheDocument();
    });

    it('renders default label', () => {
        render(<ProcessingOptions />);
        expect(screen.getByText('Export format')).toBeInTheDocument();
    });

    it('renders custom label', () => {
        render(<ProcessingOptions label="Choose format" />);
        expect(screen.getByText('Choose format')).toBeInTheDocument();
    });

    it('has default selected format', () => {
        render(<ProcessingOptions />);
        expect(screen.getByTestId('export-format-select').value).toBe('docx');
    });

    it('respects selectedFormat prop', () => {
        render(<ProcessingOptions selectedFormat="pdf" />);
        expect(screen.getByTestId('export-format-select').value).toBe('pdf');
    });

    it('respects selectedFormat as tex', () => {
        render(<ProcessingOptions selectedFormat="tex" />);
        expect(screen.getByTestId('export-format-select').value).toBe('tex');
    });

    it('calls onFormatChange when selection changes', () => {
        const onFormatChange = vi.fn();
        render(<ProcessingOptions onFormatChange={onFormatChange} />);
        fireEvent.change(screen.getByTestId('export-format-select'), { target: { value: 'pdf' } });
        expect(onFormatChange).toHaveBeenCalledWith('pdf');
    });

    it('calls onFormatChange to tex', () => {
        const onFormatChange = vi.fn();
        render(<ProcessingOptions onFormatChange={onFormatChange} />);
        fireEvent.change(screen.getByTestId('export-format-select'), { target: { value: 'tex' } });
        expect(onFormatChange).toHaveBeenCalledWith('tex');
    });

    it('does not throw when onFormatChange is not provided', () => {
        render(<ProcessingOptions />);
        expect(() => {
            fireEvent.change(screen.getByTestId('export-format-select'), { target: { value: 'pdf' } });
        }).not.toThrow();
    });

    it('disables select when disabled prop is true', () => {
        render(<ProcessingOptions disabled />);
        expect(screen.getByTestId('export-format-select')).toBeDisabled();
    });

    it('disables select when disabled prop is true with selectedFormat', () => {
        render(<ProcessingOptions disabled selectedFormat="tex" />);
        expect(screen.getByTestId('export-format-select')).toBeDisabled();
        expect(screen.getByTestId('export-format-select').value).toBe('tex');
    });

    it('renders with all props combined', () => {
        const onFormatChange = vi.fn();
        render(<ProcessingOptions selectedFormat="pdf" disabled={false} onFormatChange={onFormatChange} label="Output" />);
        expect(screen.getByText('Output')).toBeInTheDocument();
        expect(screen.getByTestId('export-format-select').value).toBe('pdf');
        expect(screen.getByTestId('export-format-select')).not.toBeDisabled();
    });
});
