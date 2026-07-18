// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import ValidationCard from '../components/ValidationCard';

describe('ValidationCard', () => {
    it('renders error type icon and badge', () => {
        render(<ValidationCard type="error" title="Missing Abstract" description="Your manuscript lacks an abstract" badge="ERROR" />);
        expect(screen.getByText('Missing Abstract')).toBeInTheDocument();
        expect(screen.getByText('ERROR')).toBeInTheDocument();
        expect(screen.getByText('Your manuscript lacks an abstract')).toBeInTheDocument();
    });

    it('renders warning type with correct styling', () => {
        const { container } = render(
            <ValidationCard type="warning" title="Inconsistent Headings" description="Heading levels jump from H1 to H3" badge="WARNING" />
        );
        expect(screen.getByText('Inconsistent Headings')).toBeInTheDocument();
        const card = container.firstChild;
        expect(card.className).toContain('border-amber-400');
    });

    it('renders advisory/suggestion type', () => {
        render(
            <ValidationCard type="advisory" title="Citation Format" description="Consider using IEEE format for citations" badge="SUGGESTION" />
        );
        expect(screen.getByText('Citation Format')).toBeInTheDocument();
        expect(screen.getByText('SUGGESTION')).toBeInTheDocument();
        expect(screen.getByText('Consider using IEEE format for citations')).toBeInTheDocument();
    });

    it('calls onAction when Locate in doc is clicked', async () => {
        const onAction = vi.fn();
        render(<ValidationCard type="error" title="Error" description="Something is wrong" badge="ERR" onAction={onAction} />);
        await userEvent.click(screen.getByText('Locate in doc'));
        expect(onAction).toHaveBeenCalledOnce();
    });

    it('calls onIgnore with card data when Ignore is clicked', async () => {
        const onIgnore = vi.fn();
        render(<ValidationCard type="warning" title="Spelling" description="Check spelling" badge="WARN" onIgnore={onIgnore} />);
        await userEvent.click(screen.getByText('Ignore'));
        expect(onIgnore).toHaveBeenCalledWith(
            expect.objectContaining({ type: 'warning', title: 'Spelling', description: 'Check spelling', badge: 'WARN' })
        );
    });

    it('falls back to error styles when type is unknown', () => {
        const { container } = render(
            <ValidationCard type="unknown_type" title="Test" description="Desc" badge="?" />
        );
        const card = container.firstChild;
        expect(card.className).toContain('border-red-500');
    });
});
