// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import TemplateSelector from '../components/upload/TemplateSelector';

vi.mock('../services/api.templates', () => ({
    fetchTemplates: vi.fn().mockResolvedValue([]),
}));

describe('TemplateSelector', () => {
    const defaultProps = {
        category: 'none',
        template: '',
        isProcessing: false,
        file: { name: 'paper.docx', size: 2048 },
        formatFileSize: (size) => `${size} bytes`,
        onCategoryChange: vi.fn(),
        onTemplateSelect: vi.fn(),
    };

    it('renders template options in the dropdown', () => {
        render(<TemplateSelector {...defaultProps} />);
        expect(screen.getByText('None (No formatting)')).toBeInTheDocument();
        expect(screen.getByText('APA (7th Edition)')).toBeInTheDocument();
        expect(screen.getByText('IEEE')).toBeInTheDocument();
    });

    it('renders Browse Library link', () => {
        render(<TemplateSelector {...defaultProps} />);
        const link = screen.getByRole('link', { name: /browse library/i });
        expect(link).toHaveAttribute('href', '/templates');
    });

    it('handles category selection change', () => {
        const onCategoryChange = vi.fn();
        render(<TemplateSelector {...defaultProps} onCategoryChange={onCategoryChange} />);
        const select = screen.getByRole('combobox');
        fireEvent.change(select, { target: { value: 'ieee' } });
        expect(onCategoryChange).toHaveBeenCalledWith('ieee');
    });

    it('renders file info text', () => {
        render(<TemplateSelector {...defaultProps} />);
        expect(screen.getByText('paper.docx (2048 bytes)')).toBeInTheDocument();
    });

    it('disables the dropdown during processing', () => {
        render(<TemplateSelector {...defaultProps} isProcessing={true} />);
        expect(screen.getByRole('combobox')).toBeDisabled();
    });
});
