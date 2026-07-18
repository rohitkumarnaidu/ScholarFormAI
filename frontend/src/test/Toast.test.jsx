import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import React from 'react';
import { ToastProvider, useToast } from '../components/Toast';

function TestConsumer() {
    const toast = useToast();
    return (
        <div>
            <button onClick={() => toast.success('Success!')}>Show Success</button>
            <button onClick={() => toast.error('Error!')}>Show Error</button>
            <button onClick={() => toast.info('Info!')}>Show Info</button>
        </div>
    );
}

describe('Toast', () => {
    it('renders children via provider', () => {
        render(<ToastProvider><p>Child</p></ToastProvider>);
        expect(screen.getByText('Child')).toBeInTheDocument();
    });

    it('shows success toast', () => {
        render(<ToastProvider><TestConsumer /></ToastProvider>);
        fireEvent.click(screen.getByText('Show Success'));
        expect(screen.getByText('Success!')).toBeInTheDocument();
    });

    it('shows error toast', () => {
        render(<ToastProvider><TestConsumer /></ToastProvider>);
        fireEvent.click(screen.getByText('Show Error'));
        expect(screen.getByText('Error!')).toBeInTheDocument();
    });

    it('shows info toast', () => {
        render(<ToastProvider><TestConsumer /></ToastProvider>);
        fireEvent.click(screen.getByText('Show Info'));
        expect(screen.getByText('Info!')).toBeInTheDocument();
    });

    it('removes toast when close button clicked', () => {
        render(<ToastProvider><TestConsumer /></ToastProvider>);
        fireEvent.click(screen.getByText('Show Success'));
        expect(screen.getByText('Success!')).toBeInTheDocument();

        const closeBtn = document.querySelector('[class*="text-current"]');
        fireEvent.click(closeBtn);
        expect(screen.queryByText('Success!')).not.toBeInTheDocument();
    });

    it('auto-removes toast after duration', () => {
        vi.useFakeTimers();
        render(<ToastProvider><TestConsumer /></ToastProvider>);
        fireEvent.click(screen.getByText('Show Success'));
        expect(screen.getByText('Success!')).toBeInTheDocument();

        act(() => { vi.advanceTimersByTime(4000); });
        expect(screen.queryByText('Success!')).not.toBeInTheDocument();
        vi.useRealTimers();
    });
});
