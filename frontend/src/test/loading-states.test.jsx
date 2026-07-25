import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import React from 'react';
import Skeleton from '../components/ui/Skeleton';

const LoadingSpinner = () => (
    <div role="status" aria-label="Loading" data-testid="spinner">
        <div className="animate-spin" />
        <span>Loading...</span>
    </div>
);

const DocumentListLoading = () => (
    <div aria-busy="true" data-testid="doc-list-loading">
        <Skeleton width="100%" height="20" />
        <Skeleton width="80%" height="20" />
        <Skeleton width="90%" height="20" />
    </div>
);

const AgentLoadingIndicator = () => (
    <div role="status" aria-label="Agent is typing" data-testid="agent-loading">
        <div className="typing-indicator">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
        </div>
        <span>Agent is thinking...</span>
    </div>
);

const StreamingIndicator = ({ isStreaming }) => {
    if (!isStreaming) return null;
    return (
        <div role="status" aria-label="Generating response" data-testid="streaming-indicator">
            <span className="animate-pulse">Generating...</span>
        </div>
    );
};

const LoadingTimeout = ({ timeout = 30000 }) => {
    const [showTimeout, setShowTimeout] = React.useState(false);
    React.useEffect(() => {
        const timer = setTimeout(() => setShowTimeout(true), timeout);
        return () => clearTimeout(timer);
    }, [timeout]);
    if (!showTimeout) return <div data-testid="loading">Loading...</div>;
    return (
        <div data-testid="timeout-message">
            <span>This is taking longer than expected</span>
            <button onClick={() => setShowTimeout(false)}>Try Again</button>
        </div>
    );
};

const StatefulContent = () => {
    const [isLoading, setIsLoading] = React.useState(true);
    React.useEffect(() => {
        const timer = setTimeout(() => setIsLoading(false), 100);
        return () => clearTimeout(timer);
    }, []);
    if (isLoading) return <div data-testid="loading">Loading...</div>;
    return <div data-testid="content">Content loaded</div>;
};

describe('Loading States', () => {
    describe('Skeleton component', () => {
        it('renders with correct shape', () => {
            const { container } = render(<Skeleton />);
            expect(container.firstChild).toBeInTheDocument();
            expect(container.firstChild).toHaveAttribute('aria-hidden', 'true');
        });

        it('matches expected dimensions', () => {
            const { container } = render(<Skeleton width="200px" height="100px" />);
            expect(container.firstChild).toHaveStyle('width: 200px');
            expect(container.firstChild).toHaveStyle('height: 100px');
        });

        it('has multiple variants', () => {
            const { container: c1 } = render(<Skeleton rounded="rounded-full" width="40" height="40" />);
            expect(c1.firstChild.className).toContain('rounded-full');

            const { container: c2 } = render(<Skeleton rounded="rounded-lg" />);
            expect(c2.firstChild.className).toContain('rounded-lg');

            const { container: c3 } = render(<Skeleton shimmer={false} />);
            expect(c3.firstChild.className).not.toContain('animate-pulse');
        });

        it('uses animate-pulse by default', () => {
            const { container } = render(<Skeleton />);
            expect(container.firstChild.className).toContain('animate-pulse');
        });
    });

    describe('Spinner during upload', () => {
        it('shows spinner with loading text', () => {
            render(<LoadingSpinner />);
            expect(screen.getByTestId('spinner')).toBeInTheDocument();
            expect(screen.getByText('Loading...')).toBeInTheDocument();
        });

        it('has accessible status role', () => {
            render(<LoadingSpinner />);
            expect(screen.getByRole('status')).toBeInTheDocument();
        });
    });

    describe('Document list loading', () => {
        it('renders multiple skeleton items', () => {
            const { container } = render(<DocumentListLoading />);
            const skeletons = container.querySelectorAll('[aria-hidden="true"]');
            expect(skeletons.length).toBe(3);
        });

        it('has aria-busy attribute', () => {
            render(<DocumentListLoading />);
            expect(screen.getByTestId('doc-list-loading')).toHaveAttribute('aria-busy', 'true');
        });
    });

    describe('Agent response loading', () => {
        it('shows typing indicator', () => {
            render(<AgentLoadingIndicator />);
            expect(screen.getByTestId('agent-loading')).toBeInTheDocument();
            expect(screen.getByText('Agent is thinking...')).toBeInTheDocument();
        });

        it('has accessible status role', () => {
            render(<AgentLoadingIndicator />);
            expect(screen.getByRole('status')).toBeInTheDocument();
        });
    });

    describe('Streaming indicator', () => {
        it('shows during generation', () => {
            render(<StreamingIndicator isStreaming={true} />);
            expect(screen.getByTestId('streaming-indicator')).toBeInTheDocument();
            expect(screen.getByText('Generating...')).toBeInTheDocument();
        });

        it('hides when not streaming', () => {
            render(<StreamingIndicator isStreaming={false} />);
            expect(screen.queryByTestId('streaming-indicator')).not.toBeInTheDocument();
        });
    });

    describe('Loading state transitions', () => {
        beforeEach(() => { vi.useFakeTimers(); });
        afterEach(() => { vi.useRealTimers(); });

        it('transitions from loading to content', () => {
            render(<StatefulContent />);
            expect(screen.getByTestId('loading')).toBeInTheDocument();

            act(() => { vi.advanceTimersByTime(100); });

            expect(screen.getByTestId('content')).toBeInTheDocument();
        });
    });

    describe('Loading timeout', () => {
        beforeEach(() => { vi.useFakeTimers(); });
        afterEach(() => { vi.useRealTimers(); });

        it('shows timeout message after specified delay', () => {
            render(<LoadingTimeout timeout={30000} />);
            expect(screen.getByTestId('loading')).toBeInTheDocument();

            act(() => { vi.advanceTimersByTime(30000); });

            expect(screen.getByTestId('timeout-message')).toBeInTheDocument();
            expect(screen.getByText('This is taking longer than expected')).toBeInTheDocument();
        });

        it('shows retry button on timeout', () => {
            render(<LoadingTimeout timeout={1000} />);
            act(() => { vi.advanceTimersByTime(1000); });
            expect(screen.getByText('Try Again')).toBeInTheDocument();
        });
    });
});
