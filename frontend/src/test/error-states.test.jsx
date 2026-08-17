import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

vi.mock('@/services/api', () => ({
    logFrontendError: vi.fn(() => Promise.resolve()),
}));

const ThrowError = ({ message = 'Test Error' }) => {
    throw new Error(message);
};

const AsyncError = () => {
    const [hasError, setHasError] = React.useState(false);
    React.useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await fetch('/api/data');
                if (!res.ok) throw new Error('Network error');
            } catch {
                setHasError(true);
            }
        };
        fetchData();
    }, []);
    if (hasError) throw new Error('Async fetch failed');
    return <div>Data loaded</div>;
};

const NetworkError = () => {
    throw new Error('Failed to fetch');
};

const Api500Error = () => {
    throw new Error('Internal Server Error');
};

const SafeChild = () => <div>Safe Content</div>;

import ErrorBoundary from '../components/ErrorBoundary';

describe('ErrorBoundary', () => {
    let suppressExpectedRenderError;

    beforeEach(() => {
        vi.spyOn(console, 'error').mockImplementation(() => { });
        suppressExpectedRenderError = (event) => {
            if (event?.error?.message && (
                event.error.message === 'Test Error' ||
                event.error.message === 'Async fetch failed' ||
                event.error.message === 'Failed to fetch' ||
                event.error.message === 'Internal Server Error'
            )) {
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
                <SafeChild />
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
        expect(screen.getByText('Reload Page')).toBeInTheDocument();
    });

    it('shows error message from thrown error', () => {
        render(
            <ErrorBoundary>
                <ThrowError message="Custom error message" />
            </ErrorBoundary>
        );
        expect(screen.getByText('Custom error message')).toBeInTheDocument();
    });

    it('resets error state when Reload Page is clicked', async () => {
        const { rerender } = render(
            <ErrorBoundary>
                <ThrowError />
            </ErrorBoundary>
        );
        expect(screen.getByText('Something went wrong')).toBeInTheDocument();

        rerender(
            <ErrorBoundary>
                <SafeChild />
            </ErrorBoundary>
        );
        fireEvent.click(screen.getByText('Reload Page'));
        expect(await screen.findByText('Safe Content')).toBeInTheDocument();
        expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument();
    });

    it('renders error UI when error is caught', () => {
        render(
            <ErrorBoundary>
                <ThrowError />
            </ErrorBoundary>
        );
        expect(screen.getByText('Something went wrong')).toBeInTheDocument();
        expect(screen.getByText('Reload Page')).toBeInTheDocument();
    });

    it('nested error boundaries catch their own errors', () => {
        render(
            <ErrorBoundary>
                <div>
                    <span>Outer content</span>
                    <ErrorBoundary>
                        <ThrowError message="Inner error" />
                    </ErrorBoundary>
                </div>
            </ErrorBoundary>
        );
        expect(screen.getByText('Outer content')).toBeInTheDocument();
        expect(screen.getByText('Inner error')).toBeInTheDocument();
    });

    it('re-shows fallback after recovery if second error occurs', async () => {
        const { rerender } = render(
            <ErrorBoundary>
                <ThrowError />
            </ErrorBoundary>
        );
        expect(screen.getByText('Something went wrong')).toBeInTheDocument();

        rerender(
            <ErrorBoundary>
                <SafeChild />
            </ErrorBoundary>
        );
        fireEvent.click(screen.getByText('Reload Page'));
        expect(await screen.findByText('Safe Content')).toBeInTheDocument();

        rerender(
            <ErrorBoundary>
                <ThrowError message="Second error" />
            </ErrorBoundary>
        );
        expect(screen.getByText('Second error')).toBeInTheDocument();
    });

    it('handles async data fetch errors', () => {
        render(
            <ErrorBoundary>
                <AsyncError />
            </ErrorBoundary>
        );
    });

    it('handles network errors with fallback', () => {
        render(
            <ErrorBoundary>
                <NetworkError />
            </ErrorBoundary>
        );
        expect(screen.getByText('Something went wrong')).toBeInTheDocument();
        expect(screen.getByText('Failed to fetch')).toBeInTheDocument();
    });

    it('handles API 500 errors gracefully', () => {
        render(
            <ErrorBoundary>
                <Api500Error />
            </ErrorBoundary>
        );
        expect(screen.getByText('Something went wrong')).toBeInTheDocument();
        expect(screen.getByText('Internal Server Error')).toBeInTheDocument();
        expect(screen.getByText('Reload Page')).toBeInTheDocument();
    });

    it('renders generic message when error has no message', () => {
        const ThrowWithNoMessage = () => { throw new Error(); };
        render(
            <ErrorBoundary>
                <ThrowWithNoMessage />
            </ErrorBoundary>
        );
        expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    });

    it('renders error icon', () => {
        render(
            <ErrorBoundary>
                <ThrowError />
            </ErrorBoundary>
        );
        expect(document.querySelector('.lucide-triangle-alert')).toBeInTheDocument();
    });

    it('preserves non-error children untouched', () => {
        render(
            <ErrorBoundary>
                <SafeChild />
                <span>Extra child</span>
            </ErrorBoundary>
        );
        expect(screen.getByText('Safe Content')).toBeInTheDocument();
        expect(screen.getByText('Extra child')).toBeInTheDocument();
    });

    it('reload button calls window.location.reload', () => {
        const reloadMock = vi.fn();
        Object.defineProperty(window, 'location', {
            value: { reload: reloadMock },
            writable: true,
        });
        render(
            <ErrorBoundary>
                <ThrowError />
            </ErrorBoundary>
        );
        fireEvent.click(screen.getByText('Reload Page'));
        expect(reloadMock).toHaveBeenCalled();
    });
});
