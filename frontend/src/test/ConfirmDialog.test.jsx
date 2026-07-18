import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { ConfirmProvider, useConfirm } from '../components/ConfirmDialog';

function TestConsumer() {
    const confirm = useConfirm();
    return (
        <div>
            <button onClick={async () => {
                const result = await confirm('Delete this item?', 'Confirm Delete', 'Delete', 'danger');
                document.body.setAttribute('data-result', String(result));
            }}>
                Trigger Confirm
            </button>
        </div>
    );
}

describe('ConfirmDialog context', () => {
    it('renders children', () => {
        render(<ConfirmProvider><p>Child</p></ConfirmProvider>);
        expect(screen.getByText('Child')).toBeInTheDocument();
    });

    it('shows dialog when confirm triggered', () => {
        render(<ConfirmProvider><TestConsumer /></ConfirmProvider>);
        fireEvent.click(screen.getByText('Trigger Confirm'));
        expect(screen.getByText('Delete this item?')).toBeInTheDocument();
    });

    it('resolves true on confirm', async () => {
        render(<ConfirmProvider><TestConsumer /></ConfirmProvider>);
        fireEvent.click(screen.getByText('Trigger Confirm'));
        fireEvent.click(screen.getByText('Delete'));

        await waitFor(() => {
            expect(document.body.getAttribute('data-result')).toBe('true');
        });
    });

    it('resolves false on cancel', async () => {
        render(<ConfirmProvider><TestConsumer /></ConfirmProvider>);
        fireEvent.click(screen.getByText('Trigger Confirm'));
        fireEvent.click(screen.getByText('Cancel'));

        await waitFor(() => {
            expect(document.body.getAttribute('data-result')).toBe('false');
        });
    });
});
