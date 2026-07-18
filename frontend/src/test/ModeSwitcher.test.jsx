import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import ModeSwitcher from '../components/layout/header/ModeSwitcher';

describe('ModeSwitcher', () => {
    it('renders both mode options', () => {
        render(<ModeSwitcher activeMode="formatter" onChange={() => {}} />);
        expect(screen.getByText('Formatter')).toBeInTheDocument();
        expect(screen.getByText('Generator')).toBeInTheDocument();
    });

    it('marks formatter as checked when active', () => {
        render(<ModeSwitcher activeMode="formatter" onChange={() => {}} />);
        const radios = screen.getAllByRole('radio');
        expect(radios[0]).toBeChecked();
        expect(radios[1]).not.toBeChecked();
    });

    it('marks generator as checked when active', () => {
        render(<ModeSwitcher activeMode="generator" onChange={() => {}} />);
        const radios = screen.getAllByRole('radio');
        expect(radios[0]).not.toBeChecked();
        expect(radios[1]).toBeChecked();
    });

    it('calls onChange with formatter when clicked', () => {
        const onChange = vi.fn();
        render(<ModeSwitcher activeMode="generator" onChange={onChange} />);
        const radios = screen.getAllByRole('radio');
        fireEvent.click(radios[0]);
        expect(onChange).toHaveBeenCalledWith('formatter');
    });

    it('calls onChange with generator when clicked', () => {
        const onChange = vi.fn();
        render(<ModeSwitcher activeMode="formatter" onChange={onChange} />);
        const radios = screen.getAllByRole('radio');
        fireEvent.click(radios[1]);
        expect(onChange).toHaveBeenCalledWith('generator');
    });

    it('applies compact class when compact is true', () => {
        render(<ModeSwitcher activeMode="formatter" onChange={() => {}} compact />);
        expect(screen.getByText('Formatter').className).toContain('text-xs');
    });
});
