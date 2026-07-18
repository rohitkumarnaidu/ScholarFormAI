import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

let mockSubmitFeedback;
let mockSafeParse;
let mockGetFirstZodError;

vi.mock('../services/api', () => ({
    submitFeedback: (...args) => mockSubmitFeedback(...args),
}));

vi.mock('../lib/schemas', () => ({
    FeedbackSubmissionSchema: {
        safeParse: (...args) => mockSafeParse(...args),
    },
    getFirstZodError: (...args) => mockGetFirstZodError(...args),
}));

describe('FeedbackForm', () => {
    beforeEach(() => {
        mockSubmitFeedback = vi.fn(() => Promise.resolve({ ok: true }));
        mockSafeParse = vi.fn((data) => ({
            success: true,
            data,
            error: undefined,
        }));
        mockGetFirstZodError = vi.fn((issues, fallback = 'Invalid input.') =>
            issues?.[0]?.message || fallback
        );
    });

    async function getComponent() {
        return (await import('../components/FeedbackForm')).default;
    }

    it('renders form fields', async () => {
        const FeedbackForm = await getComponent();
        render(<FeedbackForm documentId="doc-123" />);
        expect(screen.getByText('Field Name *')).toBeInTheDocument();
        expect(screen.getByText('Original Value')).toBeInTheDocument();
        expect(screen.getByText('Corrected Value *')).toBeInTheDocument();
    });

    it('does not show document ID field when documentId prop is provided', async () => {
        const FeedbackForm = await getComponent();
        render(<FeedbackForm documentId="doc-123" />);
        expect(screen.queryByText('Document Job ID *')).not.toBeInTheDocument();
    });

    it('shows document ID field when not provided', async () => {
        const FeedbackForm = await getComponent();
        render(<FeedbackForm />);
        expect(screen.getByText('Document Job ID *')).toBeInTheDocument();
    });

    it('submits feedback on form submit', async () => {
        mockSubmitFeedback = vi.fn(() => Promise.resolve({ ok: true }));
        const FeedbackForm = await getComponent();
        const onSubmitted = vi.fn();
        render(<FeedbackForm documentId="doc-123" onSubmitted={onSubmitted} />);

        fireEvent.change(screen.getByPlaceholderText('e.g. title, abstract, authors, references'), {
            target: { value: 'title' },
        });
        fireEvent.change(screen.getByPlaceholderText('What it should be'), {
            target: { value: 'Corrected Title' },
        });

        fireEvent.click(screen.getByRole('button', { name: /Submit Correction/i }));

        await waitFor(() => {
            expect(screen.getByText(/submitted successfully/i)).toBeInTheDocument();
        });
    });

    it('shows error message on API failure', async () => {
        mockSubmitFeedback = vi.fn(() => Promise.reject(new Error('Server error')));
        const FeedbackForm = await getComponent();
        render(<FeedbackForm documentId="doc-123" />);
        fireEvent.change(screen.getByPlaceholderText('e.g. title, abstract, authors, references'), {
            target: { value: 'title' },
        });
        fireEvent.change(screen.getByPlaceholderText('What it should be'), {
            target: { value: 'Corrected' },
        });
        fireEvent.click(screen.getByText('Submit Correction'));

        await waitFor(() => {
            expect(screen.getByText(/Server error/)).toBeInTheDocument();
        });
    });

    it('shows validation error on empty submission', async () => {
        mockSafeParse = vi.fn(() => ({
            success: false,
            data: undefined,
            error: { issues: [{ message: 'Field name is required.' }] },
        }));

        const FeedbackForm = await getComponent();
        render(<FeedbackForm documentId="doc-123" />);

        fireEvent.change(screen.getByPlaceholderText('e.g. title, abstract, authors, references'), {
            target: { value: 'title' },
        });
        fireEvent.change(screen.getByPlaceholderText('What it should be'), {
            target: { value: 'corrected' },
        });

        fireEvent.click(screen.getByRole('button', { name: /Submit Correction/i }));

        expect(await screen.findByText('Field name is required.')).toBeInTheDocument();
    });

    it('shows character counters on text fields', async () => {
        const FeedbackForm = await getComponent();
        render(<FeedbackForm documentId="doc-123" />);

        expect(screen.getAllByText('0/1000').length).toBe(2);

        fireEvent.change(screen.getByPlaceholderText('What it should be'), {
            target: { value: 'Test' },
        });

        expect(screen.getByText('4/1000')).toBeInTheDocument();
    });

    it('resets form fields after successful submission', async () => {
        mockSubmitFeedback = vi.fn(() => Promise.resolve({ ok: true }));

        const FeedbackForm = await getComponent();
        const onSubmitted = vi.fn();
        render(<FeedbackForm documentId="doc-123" onSubmitted={onSubmitted} />);

        fireEvent.change(screen.getByPlaceholderText('e.g. title, abstract, authors, references'), {
            target: { value: 'title' },
        });
        fireEvent.change(screen.getByPlaceholderText('What the AI produced'), {
            target: { value: 'Old Title' },
        });
        fireEvent.change(screen.getByPlaceholderText('What it should be'), {
            target: { value: 'New Title' },
        });

        fireEvent.click(screen.getByRole('button', { name: /Submit Correction/i }));

        expect(await screen.findByText(/submitted successfully/i)).toBeInTheDocument();

        expect(screen.getByPlaceholderText('e.g. title, abstract, authors, references').value).toBe('');
        expect(screen.getByPlaceholderText('What the AI produced').value).toBe('');
        expect(screen.getByPlaceholderText('What it should be').value).toBe('');
    });
});
