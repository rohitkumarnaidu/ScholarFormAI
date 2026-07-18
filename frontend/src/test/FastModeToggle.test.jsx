import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import FastModeToggle from '../components/FastModeToggle';

describe('FastModeToggle', () => {
    it('renders label', () => {
        render(<FastModeToggle fastMode={false} setFastMode={() => {}} />);
        expect(screen.getByText('Fast Mode')).toBeInTheDocument();
    });

    it('renders checkbox with correct checked state', () => {
        render(<FastModeToggle fastMode={true} setFastMode={() => {}} />);
        expect(screen.getByRole('checkbox')).toBeChecked();
    });

    it('calls setFastMode when toggled', () => {
        const setFastMode = vi.fn();
        render(<FastModeToggle fastMode={false} setFastMode={setFastMode} />);
        fireEvent.click(screen.getByRole('checkbox'));
        expect(setFastMode).toHaveBeenCalledWith(true);
    });

    it('disables checkbox when disabled prop is true', () => {
        render(<FastModeToggle fastMode={false} setFastMode={() => {}} disabled />);
        expect(screen.getByRole('checkbox')).toBeDisabled();
    });
});
