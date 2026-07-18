// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import SectionDnD from '../components/edit/SectionDnD';

describe('SectionDnD', () => {
    const sections = [
        { id: 'intro', title: 'Introduction' },
        { id: 'methods', title: 'Methods' },
        { id: 'results', title: 'Results' },
        { id: 'conclusion', title: 'Conclusion' },
    ];

    it('renders all sections by their title', () => {
        render(<SectionDnD sections={sections} />);
        expect(screen.getByText('Introduction')).toBeInTheDocument();
        expect(screen.getByText('Methods')).toBeInTheDocument();
        expect(screen.getByText('Results')).toBeInTheDocument();
        expect(screen.getByText('Conclusion')).toBeInTheDocument();
    });

    it('renders fallback label when section has no title', () => {
        render(<SectionDnD sections={[{ id: 'sec1' }]} />);
        expect(screen.getByText('Section 1')).toBeInTheDocument();
    });

    it('handles empty state', () => {
        render(<SectionDnD sections={[]} />);
        expect(screen.getByText('No sections to reorder')).toBeInTheDocument();
    });

    it('shows draggable attribute on each section', () => {
        render(<SectionDnD sections={sections} />);
        const items = screen.getAllByRole('listitem');
        expect(items).toHaveLength(4);
        items.forEach((item) => {
            expect(item.getAttribute('draggable')).toBe('true');
        });
    });

    it('calls onReorder when a section is dropped onto another', () => {
        const onReorder = vi.fn();
        render(<SectionDnD sections={sections} onReorder={onReorder} />);
        const items = screen.getAllByRole('listitem');

        fireEvent.dragStart(items[0], { dataTransfer: { setData: vi.fn(), effectAllowed: 'move', getData: () => '0' } });
        fireEvent.dragOver(items[2], { dataTransfer: { dropEffect: 'move' } });
        fireEvent.drop(items[2], { dataTransfer: { getData: () => '0' } });

        expect(onReorder).toHaveBeenCalledWith(0, 2);
    });

    it('renders custom renderSection when provided', () => {
        const renderSection = vi.fn((section) => `Custom: ${section.title}`);
        render(<SectionDnD sections={sections} renderSection={renderSection} />);
        expect(screen.getByText('Custom: Introduction')).toBeInTheDocument();
    });
});
