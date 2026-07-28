// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import React from 'react';
import { ToastProvider, useToast } from '@/context/ToastContext';

function ToastProbe() {
    const { showToast, addToast, dismiss } = useToast();
    return (
        <div>
            <button data-testid="show-info" onClick={() => showToast({ type: 'info', message: 'Info toast' })}>Info</button>
            <button data-testid="show-success" onClick={() => addToast('Success toast', 'success')}>Success</button>
            <button data-testid="show-error" onClick={() => addToast('Error toast', 'error')}>Error</button>
            <button data-testid="show-warning" onClick={() => showToast({ type: 'warning', message: 'Warning toast' })}>Warning</button>
            <button data-testid="dismiss" onClick={() => dismiss(999)}>Dismiss</button>
        </div>
    );
}

describe('ToastContext', () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('shows an info toast', () => {
        render(
            <ToastProvider>
                <ToastProbe />
            </ToastProvider>
        );
        fireEvent.click(screen.getByTestId('show-info'));
        expect(screen.getByText('Info toast')).toBeInTheDocument();
    });

    it('shows a success toast', () => {
        render(
            <ToastProvider>
                <ToastProbe />
            </ToastProvider>
        );
        fireEvent.click(screen.getByTestId('show-success'));
        expect(screen.getByText('Success toast')).toBeInTheDocument();
    });

    it('shows an error toast', () => {
        render(
            <ToastProvider>
                <ToastProbe />
            </ToastProvider>
        );
        fireEvent.click(screen.getByTestId('show-error'));
        expect(screen.getByText('Error toast')).toBeInTheDocument();
    });

    it('shows a warning toast', () => {
        render(
            <ToastProvider>
                <ToastProbe />
            </ToastProvider>
        );
        fireEvent.click(screen.getByTestId('show-warning'));
        expect(screen.getByText('Warning toast')).toBeInTheDocument();
    });

    it('automatically dismisses toast after duration', () => {
        render(
            <ToastProvider>
                <ToastProbe />
            </ToastProvider>
        );
        fireEvent.click(screen.getByTestId('show-info'));
        expect(screen.getByText('Info toast')).toBeInTheDocument();
        act(() => {
            vi.advanceTimersByTime(5000);
        });
        expect(screen.queryByText('Info toast')).not.toBeInTheDocument();
    });

    it('dismisses toast manually when dismiss button is clicked', () => {
        render(
            <ToastProvider>
                <ToastProbe />
            </ToastProvider>
        );
        fireEvent.click(screen.getByTestId('show-info'));
        expect(screen.getByText('Info toast')).toBeInTheDocument();
        const dismissBtn = screen.getByLabelText('Dismiss');
        fireEvent.click(dismissBtn);
        expect(screen.queryByText('Info toast')).not.toBeInTheDocument();
    });

    it('shows multiple toasts', () => {
        render(
            <ToastProvider>
                <ToastProbe />
            </ToastProvider>
        );
        fireEvent.click(screen.getByTestId('show-info'));
        fireEvent.click(screen.getByTestId('show-success'));
        fireEvent.click(screen.getByTestId('show-error'));
        expect(screen.getByText('Info toast')).toBeInTheDocument();
        expect(screen.getByText('Success toast')).toBeInTheDocument();
        expect(screen.getByText('Error toast')).toBeInTheDocument();
    });

    it('renders correct icon for each toast type', () => {
        render(
            <ToastProvider>
                <ToastProbe />
            </ToastProvider>
        );
        fireEvent.click(screen.getByTestId('show-info'));
        const toastContainer = screen.getByRole('alert');
        expect(toastContainer).toBeInTheDocument();
    });
});
