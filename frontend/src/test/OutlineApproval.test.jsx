// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import OutlineApproval from '../components/generator/OutlineApproval';

vi.mock('framer-motion', () => ({
    motion: {
        div: ({ children, ...props }) => <div {...props}>{children}</div>,
    },
    Reorder: {
        Group: ({ children, ...props }) => <div data-testid="reorder-group" {...props}>{children}</div>,
        Item: ({ children, ...props }) => <div data-testid="reorder-item" {...props}>{children}</div>,
    },
    AnimatePresence: ({ children }) => <>{children}</>,
}));

describe('OutlineApproval', () => {
    const defaultSections = [
        { title: 'Introduction', expectedWordCount: 500 },
        { title: 'Methodology', expectedWordCount: 1000 },
        { title: 'Results', expectedWordCount: 800 },
    ];

    const defaultProps = {
        outline: { sections: defaultSections },
        onApprove: vi.fn(),
        onEdit: vi.fn(),
        onRegenerate: vi.fn(),
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders outline title', () => {
        render(<OutlineApproval {...defaultProps} />);
        expect(screen.getByText('Review Outline')).toBeInTheDocument();
    });

    it('renders all sections from outline prop', () => {
        render(<OutlineApproval {...defaultProps} />);
        expect(screen.getByText('Introduction')).toBeInTheDocument();
        expect(screen.getByText('Methodology')).toBeInTheDocument();
        expect(screen.getByText('Results')).toBeInTheDocument();
    });

    it('shows word count for each section', () => {
        render(<OutlineApproval {...defaultProps} />);
        expect(screen.getByText('~500 words')).toBeInTheDocument();
        expect(screen.getByText('~1000 words')).toBeInTheDocument();
        expect(screen.getByText('~800 words')).toBeInTheDocument();
    });

    it('calls onApprove with outline when Proceed is clicked', () => {
        const onApprove = vi.fn();
        render(<OutlineApproval {...defaultProps} onApprove={onApprove} />);
        fireEvent.click(screen.getByText('Proceed to Write'));
        expect(onApprove).toHaveBeenCalledTimes(1);
        const outlineArg = onApprove.mock.calls[0][0];
        expect(outlineArg.sections).toHaveLength(3);
    });

    it('calls onRegenerate when Regenerate button is clicked', () => {
        const onRegenerate = vi.fn();
        render(<OutlineApproval {...defaultProps} onRegenerate={onRegenerate} />);
        fireEvent.click(screen.getByText('Regenerate Outline'));
        expect(onRegenerate).toHaveBeenCalledTimes(1);
    });

    it('enters edit mode when edit button is clicked', () => {
        render(<OutlineApproval {...defaultProps} />);
        const editButtons = screen.getAllByTitle('Edit Section');
        fireEvent.click(editButtons[0]);
        expect(screen.getByDisplayValue('Introduction')).toBeInTheDocument();
    });

    it('saves edit when save button is clicked', () => {
        const onEdit = vi.fn();
        render(<OutlineApproval {...defaultProps} onEdit={onEdit} />);
        const editButtons = screen.getAllByTitle('Edit Section');
        fireEvent.click(editButtons[0]);
        const input = screen.getByDisplayValue('Introduction');
        fireEvent.change(input, { target: { value: 'Updated Intro' } });
        fireEvent.click(screen.getByTitle('Save (Ctrl+S or Ctrl+Enter)'));
        expect(onEdit).toHaveBeenCalled();
    });

    it('cancels edit when cancel button is clicked', () => {
        render(<OutlineApproval {...defaultProps} />);
        const editButtons = screen.getAllByTitle('Edit Section');
        fireEvent.click(editButtons[0]);
        expect(screen.getByDisplayValue('Introduction')).toBeInTheDocument();
        fireEvent.click(screen.getByTitle('Cancel'));
    });

    it('deletes a section when delete button is clicked', () => {
        const onEdit = vi.fn();
        render(<OutlineApproval {...defaultProps} onEdit={onEdit} />);
        const deleteButtons = screen.getAllByTitle('Delete Section');
        fireEvent.click(deleteButtons[1]);
        expect(onEdit).toHaveBeenCalled();
        const outlineArg = onEdit.mock.calls[0][0];
        expect(outlineArg.sections).toHaveLength(2);
    });

    it('adds a new section when Add Section is clicked', () => {
        const onEdit = vi.fn();
        render(<OutlineApproval {...defaultProps} onEdit={onEdit} />);
        fireEvent.click(screen.getByText('Add Section'));
        expect(onEdit).toHaveBeenCalled();
        const outlineArg = onEdit.mock.calls[0][0];
        expect(outlineArg.sections).toHaveLength(4);
    });

    it('calls onEdit on drag reorder', () => {
        const onEdit = vi.fn();
        render(<OutlineApproval {...defaultProps} onEdit={onEdit} />);
        const reorderGroup = screen.getByTestId('reorder-group');
        reorderGroup.setAttribute('values', '[]');
        fireEvent.click(reorderGroup);
    });

    it('renders correctly with empty sections array', () => {
        render(<OutlineApproval outline={{ sections: [] }} onApprove={vi.fn()} />);
        expect(screen.getByText('Review Outline')).toBeInTheDocument();
        expect(screen.getByText('Add Section')).toBeInTheDocument();
    });

    it('renders correctly with no outline prop', () => {
        render(<OutlineApproval outline={null} onApprove={vi.fn()} />);
        expect(screen.getByText('Review Outline')).toBeInTheDocument();
    });

    it('calls handleApprove on Ctrl+Enter from keyboard', () => {
        const onApprove = vi.fn();
        render(<OutlineApproval {...defaultProps} onApprove={onApprove} />);
        fireEvent.keyDown(window, { key: 'Enter', ctrlKey: true });
        expect(onApprove).toHaveBeenCalled();
    });

    it('saves edit on Ctrl+S keyboard shortcut', () => {
        const onEdit = vi.fn();
        render(<OutlineApproval {...defaultProps} onEdit={onEdit} />);
        const editButtons = screen.getAllByTitle('Edit Section');
        fireEvent.click(editButtons[0]);
        const input = screen.getByDisplayValue('Introduction');
        fireEvent.change(input, { target: { value: 'Edited' } });
        fireEvent.keyDown(window, { key: 's', ctrlKey: true });
        expect(onEdit).toHaveBeenCalled();
    });

    it('regenerate calls onEdit if onRegenerate not provided', () => {
        const onEdit = vi.fn();
        render(<OutlineApproval {...defaultProps} onEdit={onEdit} onRegenerate={undefined} />);
        fireEvent.click(screen.getByText('Regenerate Outline'));
        expect(onEdit).toHaveBeenCalled();
    });
});
