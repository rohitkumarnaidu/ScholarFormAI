// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import DashboardRow from '../components/dashboard/DashboardRow';

describe('DashboardRow', () => {
    it('returns null when no item is provided', () => {
        const { container } = render(<DashboardRow item={null} />);
        expect(container.innerHTML).toBe('');
    });

    it('renders document filename', () => {
        render(
            <table>
                <tbody>
                    <DashboardRow item={{ id: 'abc123', originalFileName: 'thesis.docx', status: 'completed' }} />
                </tbody>
            </table>
        );
        expect(screen.getByText('thesis.docx')).toBeInTheDocument();
    });

    it('falls back to Untitled Manuscript when filename is missing', () => {
        render(
            <table>
                <tbody>
                    <DashboardRow item={{ id: 'abc123', status: 'completed' }} />
                </tbody>
            </table>
        );
        expect(screen.getByText('Untitled Manuscript')).toBeInTheDocument();
    });

    it('shows Download button for completed status', async () => {
        render(
            <table>
                <tbody>
                    <DashboardRow item={{ id: 'abc123', originalFileName: 'doc.docx', status: 'completed' }} />
                </tbody>
            </table>
        );
        await waitFor(() => {
            expect(screen.getByRole('button', { name: /download/i })).toBeInTheDocument();
        });
    });

    it('shows Resume link for non-completed status', () => {
        render(
            <table>
                <tbody>
                    <DashboardRow item={{ id: 'abc123', originalFileName: 'doc.docx', status: 'processing' }} />
                </tbody>
            </table>
        );
        expect(screen.getByRole('link', { name: /resume/i })).toHaveAttribute('href', '/upload');
    });

    it('shows Pending status badge when status is missing', () => {
        render(
            <table>
                <tbody>
                    <DashboardRow item={{ id: 'abc123', originalFileName: 'doc.docx' }} />
                </tbody>
            </table>
        );
        expect(screen.getByText('Pending')).toBeInTheDocument();
    });
});
