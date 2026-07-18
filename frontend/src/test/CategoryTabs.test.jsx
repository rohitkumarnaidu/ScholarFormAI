// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import CategoryTabs from '../components/upload/CategoryTabs';

describe('CategoryTabs', () => {
    it('renders the category heading', () => {
        render(<CategoryTabs />);
        expect(screen.getByText('Select Category')).toBeInTheDocument();
    });

    it('renders Documents as the active tab', () => {
        render(<CategoryTabs />);
        const documents = screen.getByText('Documents');
        expect(documents).toBeInTheDocument();
        expect(documents.closest('button')).toHaveClass('bg-primary');
    });

    it('renders Resume with Coming Soon badge', () => {
        render(<CategoryTabs />);
        expect(screen.getByText('Resume')).toBeInTheDocument();
        const comingSoon = screen.getAllByText('Coming Soon');
        expect(comingSoon).toHaveLength(2);
    });

    it('renders Portfolio with Coming Soon badge', () => {
        render(<CategoryTabs />);
        expect(screen.getByText('Portfolio')).toBeInTheDocument();
        const comingSoon = screen.getAllByText('Coming Soon');
        expect(comingSoon).toHaveLength(2);
    });

    it('disables Resume and Portfolio buttons', () => {
        render(<CategoryTabs />);
        const buttons = screen.getAllByRole('button');
        const comingSoonButtons = buttons.filter((b) => b.hasAttribute('aria-disabled'));
        expect(comingSoonButtons).toHaveLength(2);
        comingSoonButtons.forEach((b) => {
            expect(b).toBeDisabled();
        });
    });
});
