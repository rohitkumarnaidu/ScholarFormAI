import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import SuggestionHistory from '../components/suggestions/SuggestionHistory';

const mockHistory = [
    { id: '1', type: 'style', status: 'accepted', originalText: 'old text', suggestedText: 'new text', actionedAt: '2026-01-01T12:00:00Z' },
    { id: '2', type: 'grammar', status: 'rejected', originalText: 'bad grammar', suggestedText: 'good grammar', actionedAt: '2026-01-02T12:00:00Z' },
];

const mockHistoryWithDismissed = [
    ...mockHistory,
    { id: '3', type: 'structure', status: 'dismissed', originalText: 'messy', suggestedText: 'organized', actionedAt: '2026-01-03T12:00:00Z' },
];

describe('SuggestionHistory', () => {
    it('renders empty state when no history', () => {
        render(<SuggestionHistory history={[]} />);
        expect(screen.getByText('No suggestion history')).toBeInTheDocument();
    });

    it('renders history items', () => {
        render(<SuggestionHistory history={mockHistory} />);
        expect(screen.getByText('old text')).toBeInTheDocument();
        expect(screen.getByText('bad grammar')).toBeInTheDocument();
    });

    it('filters by accepted status', () => {
        render(<SuggestionHistory history={mockHistoryWithDismissed} />);
        fireEvent.click(screen.getByText('Accepted'));
        expect(screen.getByText('old text')).toBeInTheDocument();
        expect(screen.queryByText('bad grammar')).not.toBeInTheDocument();
    });

    it('shows all items by default', () => {
        render(<SuggestionHistory history={mockHistory} />);
        expect(screen.getAllByText(/new text|good grammar/).length).toBe(2);
    });

    it('shows empty state for filter with no matches', () => {
        render(<SuggestionHistory history={mockHistory} />);
        fireEvent.click(screen.getByText('Dismissed'));
        expect(screen.getByText('No dismissed suggestions')).toBeInTheDocument();
    });

    it('displays type badges', () => {
        render(<SuggestionHistory history={mockHistory} />);
        expect(screen.getByText('style')).toBeInTheDocument();
        expect(screen.getByText('grammar')).toBeInTheDocument();
    });
});
