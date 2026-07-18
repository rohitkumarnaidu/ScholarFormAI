import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import SuggestionCard from '../components/suggestions/SuggestionCard';

const baseSuggestion = {
    id: 's1',
    type: 'grammar',
    score: 85,
    originalText: 'The quick brown fox jumps over the lazy dog.',
    suggestedText: 'A quick brown fox jumped over the lazy dog.',
};

describe('SuggestionCard', () => {
    it('renders all suggestion data', () => {
        render(<SuggestionCard suggestion={baseSuggestion} />);
        expect(screen.getByText('Grammar')).toBeInTheDocument();
        expect(screen.getByText('85%')).toBeInTheDocument();
        expect(screen.getByText(/The quick brown fox/)).toBeInTheDocument();
        expect(screen.getByText(/A quick brown fox/)).toBeInTheDocument();
    });

    it('shows type badge correctly', () => {
        const { rerender } = render(<SuggestionCard suggestion={baseSuggestion} />);
        expect(screen.getByText('Grammar')).toBeInTheDocument();

        rerender(<SuggestionCard suggestion={{ ...baseSuggestion, type: 'style' }} />);
        expect(screen.getByText('Style')).toBeInTheDocument();

        rerender(<SuggestionCard suggestion={{ ...baseSuggestion, type: 'structure' }} />);
        expect(screen.getByText('Structure')).toBeInTheDocument();

        rerender(<SuggestionCard suggestion={{ ...baseSuggestion, type: 'citation' }} />);
        expect(screen.getByText('Citation')).toBeInTheDocument();

        rerender(<SuggestionCard suggestion={{ ...baseSuggestion, type: 'clarity' }} />);
        expect(screen.getByText('Clarity')).toBeInTheDocument();
    });

    it('toggle expand for long text', () => {
        const longText = 'A. '.repeat(100);
        render(<SuggestionCard suggestion={{ ...baseSuggestion, originalText: longText }} />);
        expect(screen.getByText('Show more')).toBeInTheDocument();
        fireEvent.click(screen.getByText('Show more'));
        expect(screen.getByText('Show less')).toBeInTheDocument();
        fireEvent.click(screen.getByText('Show less'));
        expect(screen.getByText('Show more')).toBeInTheDocument();
    });

    it('action buttons fire callbacks', () => {
        const onAccept = vi.fn();
        const onReject = vi.fn();
        const onDismiss = vi.fn();
        render(
            <SuggestionCard
                suggestion={baseSuggestion}
                onAccept={onAccept}
                onReject={onReject}
                onDismiss={onDismiss}
            />
        );
        fireEvent.click(screen.getByText('Accept'));
        expect(onAccept).toHaveBeenCalledWith('s1');

        fireEvent.click(screen.getByText('Reject'));
        expect(onReject).toHaveBeenCalledWith('s1');

        fireEvent.click(screen.getByTitle('Dismiss'));
        expect(onDismiss).toHaveBeenCalledWith('s1');
    });

    it('score bar width matches score', () => {
        const { container } = render(
            <SuggestionCard suggestion={{ ...baseSuggestion, score: 72 }} />
        );
        const bars = container.querySelectorAll('div[class*="rounded-full"]');
        const scoreBar = Array.from(bars).find(b => b.style.width);
        expect(scoreBar.style.width).toBe('72%');
    });

    it('handles null score gracefully', () => {
        render(<SuggestionCard suggestion={{ ...baseSuggestion, score: null }} />);
        expect(screen.getByText('N/A')).toBeInTheDocument();
    });
});
