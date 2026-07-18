import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import ToggleSwitch from '../components/ToggleSwitch';

describe('ToggleSwitch', () => {
    it('renders label and sublabel', () => {
        render(<ToggleSwitch id="test" label="Enable" sublabel="Turn on feature" checked={false} onChange={() => {}} />);
        expect(screen.getByText('Enable')).toBeInTheDocument();
        expect(screen.getByText('Turn on feature')).toBeInTheDocument();
    });

    it('renders checkbox input', () => {
        render(<ToggleSwitch id="test" label="Test" checked={false} onChange={() => {}} />);
        expect(screen.getByRole('checkbox')).toBeInTheDocument();
    });

    it('shows checked state', () => {
        render(<ToggleSwitch id="test" label="Test" checked={true} onChange={() => {}} />);
        expect(screen.getByRole('checkbox')).toBeChecked();
    });

    it('calls onChange when toggled', () => {
        const onChange = vi.fn();
        render(<ToggleSwitch id="test" label="Test" checked={false} onChange={onChange} />);
        fireEvent.click(screen.getByRole('checkbox'));
        expect(onChange).toHaveBeenCalledTimes(1);
    });

    it('links label htmlFor to checkbox id', () => {
        render(<ToggleSwitch id="toggle-id" label="Test" checked={false} onChange={() => {}} />);
        const checkbox = screen.getByRole('checkbox');
        expect(checkbox.id).toBe('toggle-id');
        const label = checkbox.nextElementSibling;
        expect(label.getAttribute('for')).toBe('toggle-id');
    });
});
