import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import SuggestionsPanel from '../components/suggestions/SuggestionsPanel';

const mockSuggestions = [
    { id: 's1', type: 'grammar', score: 85, originalText: 'Original text 1', suggestedText: 'Suggested text 1' },
    { id: 's2', type: 'style', score: 45, originalText: 'Original text 2', suggestedText: 'Suggested text 2' },
    { id: 's3', type: 'structure', score: 72, originalText: 'Original text 3', suggestedText: 'Suggested text 3' },
];

describe('SuggestionsPanel', () => {
    it('opens and closes correctly', () => {
        const onClose = vi.fn();
        const { rerender } = render(
            <SuggestionsPanel suggestions={mockSuggestions} isOpen={false} onClose={onClose} />
        );
        expect(screen.queryByText('AI Suggestions')).not.toBeInTheDocument();

        rerender(
            <SuggestionsPanel suggestions={mockSuggestions} isOpen={true} onClose={onClose} />
        );
        expect(screen.getByText('AI Suggestions')).toBeInTheDocument();
    });

    it('renders suggestion cards', () => {
        render(<SuggestionsPanel suggestions={mockSuggestions} isOpen={true} />);
        expect(screen.getByText('Grammar')).toBeInTheDocument();
        expect(screen.getByText('Style')).toBeInTheDocument();
        expect(screen.getByText('Structure')).toBeInTheDocument();
    });

    it('shows suggestion count', () => {
        render(<SuggestionsPanel suggestions={mockSuggestions} isOpen={true} />);
        expect(screen.getByText('3')).toBeInTheDocument();
    });

    it('accept button calls onAccept', () => {
        const onAccept = vi.fn();
        render(<SuggestionsPanel suggestions={mockSuggestions} isOpen={true} onAccept={onAccept} />);
        const acceptBtns = screen.getAllByText('Accept');
        fireEvent.click(acceptBtns[0]);
        expect(onAccept).toHaveBeenCalled();
    });

    it('reject button calls onReject', () => {
        const onReject = vi.fn();
        render(<SuggestionsPanel suggestions={mockSuggestions} isOpen={true} onReject={onReject} />);
        const rejectBtns = screen.getAllByText('Reject');
        fireEvent.click(rejectBtns[0]);
        expect(onReject).toHaveBeenCalled();
    });

    it('dismiss button calls onDismiss', () => {
        const onDismiss = vi.fn();
        render(<SuggestionsPanel suggestions={mockSuggestions} isOpen={true} onDismiss={onDismiss} />);
        const dismissBtns = screen.getAllByTitle('Dismiss');
        fireEvent.click(dismissBtns[0]);
        expect(onDismiss).toHaveBeenCalled();
    });

    it('handles empty state', () => {
        render(<SuggestionsPanel suggestions={[]} isOpen={true} />);
        expect(screen.getByText('No suggestions yet')).toBeInTheDocument();
    });

    it('handles loading state', () => {
        const { container } = render(
            <SuggestionsPanel suggestions={mockSuggestions} isOpen={true} loading={true} />
        );
        const skeletons = container.querySelectorAll('[aria-hidden="true"]');
        expect(skeletons.length).toBeGreaterThan(0);
    });

    it('close button works', () => {
        const onClose = vi.fn();
        render(<SuggestionsPanel suggestions={mockSuggestions} isOpen={true} onClose={onClose} />);
        fireEvent.click(screen.getByLabelText('Close suggestions panel'));
        expect(onClose).toHaveBeenCalledOnce();
    });
});
