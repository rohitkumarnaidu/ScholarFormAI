// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import ErrorBoundary from '../components/ErrorBoundary';

// Mock the API service
vi.mock('@/src/services/api', () => ({
    logFrontendError: vi.fn(() => Promise.resolve()),
}));

const ThrowError = () => {
    throw new Error('Test Error');
};

describe('ErrorBoundary', () => {
    let suppressExpectedRenderError;

    beforeEach(() => {
        vi.spyOn(console, 'error').mockImplementation(() => { });
        suppressExpectedRenderError = (event) => {
            if (event?.error?.message === 'Test Error') {
                event.preventDefault();
            }
        };
        window.addEventListener('error', suppressExpectedRenderError);
    });

    afterEach(() => {
        window.removeEventListener('error', suppressExpectedRenderError);
        vi.restoreAllMocks();
    });

    it('renders children when there is no error', () => {
        render(
            <ErrorBoundary>
                <div>Safe Content</div>
            </ErrorBoundary>
        );
        expect(screen.getByText('Safe Content')).toBeInTheDocument();
    });

    it('renders error UI when a child throws', () => {
        render(
            <ErrorBoundary>
                <ThrowError />
            </ErrorBoundary>
        );

        expect(screen.getByText('Something went wrong')).toBeInTheDocument();
        expect(screen.getByText('Try Again')).toBeInTheDocument();
    });

    it('recovers from error when "Try Again" is clicked', async () => {
        const { rerender } = render(
            <ErrorBoundary>
                <ThrowError />
            </ErrorBoundary>
        );

        expect(screen.getByText('Something went wrong')).toBeInTheDocument();

        // Swap in safe children first, then trigger boundary reset.
        rerender(
            <ErrorBoundary>
                <div>Recovered</div>
            </ErrorBoundary>
        );
        fireEvent.click(screen.getByText('Try Again'));

        expect(await screen.findByText('Recovered')).toBeInTheDocument();
        expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument();
    });
});
