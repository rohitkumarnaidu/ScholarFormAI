// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import TokenStream from '../components/generator/TokenStream';

vi.mock('framer-motion', () => ({
    motion: {
        div: ({ children, ...props }) => <div {...props}>{children}</div>,
    },
    AnimatePresence: ({ children }) => <>{children}</>,
}));

vi.mock('@/src/lib/supabaseClient', () => ({
    supabase: {
        auth: {
            getSession: vi.fn().mockResolvedValue({
                data: { session: { access_token: 'test-token' } },
            }),
        },
    },
}));

describe('TokenStream', () => {
    let mockEventSourceCtor;
    let eventSourceInstances;

    beforeEach(() => {
        vi.useFakeTimers();
        Element.prototype.scrollIntoView = vi.fn();
        mockEventSourceCtor = vi.fn();
        eventSourceInstances = [];
        vi.stubGlobal('EventSource', class {
            constructor(url) {
                mockEventSourceCtor(url);
                this.close = vi.fn();
                this.addEventListener = vi.fn();
                this.onerror = null;
                this.readyState = 0;
                eventSourceInstances.push(this);
            }
        });
    });

    afterEach(() => {
        vi.useRealTimers();
        vi.unstubAllGlobals();
    });

    const defaultProps = {
        sessionId: null,
        isGenerating: false,
        initialSections: [],
    };

    it('renders empty state when no sections and not generating', () => {
        render(<TokenStream {...defaultProps} />);
        expect(screen.getByText('Document Area')).toBeInTheDocument();
        expect(screen.getByText(/Approve the outline/)).toBeInTheDocument();
    });

    it('renders initial sections when provided', () => {
        const sections = [
            { id: 's1', title: 'Introduction', content: 'Hello', isCompleted: true, wordCount: 1 },
            { id: 's2', title: 'Methodology', content: '', isCompleted: false, wordCount: 0 },
        ];
        render(<TokenStream {...defaultProps} initialSections={sections} />);
        expect(screen.getByText('Introduction')).toBeInTheDocument();
        expect(screen.getByText('Methodology')).toBeInTheDocument();
    });

    it('shows Queued label for incomplete sections', () => {
        const sections = [
            { id: 's1', title: 'Pending', content: '', isCompleted: false, wordCount: 0 },
        ];
        render(<TokenStream {...defaultProps} initialSections={sections} />);
        expect(screen.getByText('Queued')).toBeInTheDocument();
    });

    it('shows word count for each section', () => {
        const sections = [
            { id: 's1', title: 'Intro', content: 'Hello world', isCompleted: false, wordCount: 2 },
        ];
        render(<TokenStream {...defaultProps} initialSections={sections} />);
        expect(screen.getByText('2 words')).toBeInTheDocument();
    });

    it('resets state when sessionId changes', async () => {
        const sections = [
            { id: 's1', title: 'Introduction', content: 'Hello', isCompleted: true, wordCount: 1 },
        ];
        const { rerender } = render(<TokenStream {...defaultProps} sessionId="sess-1" initialSections={sections} />);
        expect(screen.getByText('Introduction')).toBeInTheDocument();

        rerender(<TokenStream {...defaultProps} sessionId="sess-2" initialSections={[]} />);
        expect(screen.queryByText('Introduction')).not.toBeInTheDocument();
        expect(screen.getByText('Document Area')).toBeInTheDocument();
    });

    it('creates SSE connection when sessionId is provided', async () => {
        render(<TokenStream {...defaultProps} sessionId="sess-1" isGenerating={true} />);
        await vi.advanceTimersToNextTimerAsync();
        expect(mockEventSourceCtor).toHaveBeenCalled();
    });

    it('cleans up SSE connection on unmount', async () => {
        const { unmount } = render(<TokenStream {...defaultProps} sessionId="sess-1" isGenerating={true} />);
        await vi.advanceTimersToNextTimerAsync();
        expect(eventSourceInstances.length).toBeGreaterThan(0);
        const es = eventSourceInstances[0];
        unmount();
        expect(es.close).toHaveBeenCalled();
    });

    it('updates content on SSE writing_chunk message', async () => {
        render(<TokenStream {...defaultProps} sessionId="sess-1" isGenerating={true} initialSections={[
            { id: 'section-introduction', title: 'Introduction', content: '', isCompleted: false, wordCount: 0 },
        ]} />);
        await vi.advanceTimersToNextTimerAsync();
        expect(eventSourceInstances.length).toBeGreaterThan(0);
        const es = eventSourceInstances[0];

        const writingHandler = es.addEventListener.mock.calls.find(call => call[0] === 'writing_chunk')[1];
        writingHandler({
            data: JSON.stringify({
                stage: 'writing',
                payload: { section: 'Introduction', content: 'Hello world' },
            }),
        });

        await vi.advanceTimersByTimeAsync(200);
        expect(screen.getByText('Hello world')).toBeInTheDocument();
    });

    it('handles SSE error and creates new connection on retry', async () => {
        render(<TokenStream {...defaultProps} sessionId="sess-1" isGenerating={true} />);
        await vi.advanceTimersToNextTimerAsync();
        expect(eventSourceInstances.length).toBe(1);
        const es = eventSourceInstances[0];

        const initialCallCount = mockEventSourceCtor.mock.calls.length;

        es.onerror(new Event('error'));

        expect(es.close).toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(3000);

        expect(mockEventSourceCtor.mock.calls.length).toBe(initialCallCount + 1);
        expect(eventSourceInstances.length).toBe(2);
    });
});
