import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import Input from '../components/ui/Input';

describe('Input', () => {
    it('renders an input element', () => {
        render(<Input />);
        expect(screen.getByRole('textbox')).toBeInTheDocument();
    });

    it('renders label when provided', () => {
        render(<Input label="Email" />);
        expect(screen.getByText('Email')).toBeInTheDocument();
    });

    it('does not render label when not provided', () => {
        const { container } = render(<Input />);
        expect(container.querySelector('label')).not.toBeInTheDocument();
    });

    it('renders error message when error is provided', () => {
        render(<Input error="This field is required" />);
        expect(screen.getByText('This field is required')).toBeInTheDocument();
    });

    it('renders helper text when no error', () => {
        render(<Input helperText="Enter your email" />);
        expect(screen.getByText('Enter your email')).toBeInTheDocument();
    });

    it('prioritizes error over helper text', () => {
        render(<Input error="Error message" helperText="Helper text" />);
        expect(screen.getByText('Error message')).toBeInTheDocument();
        expect(screen.queryByText('Helper text')).not.toBeInTheDocument();
    });

    it('uses custom id prop', () => {
        render(<Input id="custom-id" label="Name" />);
        expect(screen.getByLabelText('Name')).toHaveAttribute('id', 'custom-id');
    });

    it('passes extra props to input', () => {
        render(<Input placeholder="Enter text" />);
        expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument();
    });

    it('handles value changes', () => {
        const onChange = vi.fn();
        render(<Input onChange={onChange} />);
        fireEvent.change(screen.getByRole('textbox'), { target: { value: 'test' } });
        expect(onChange).toHaveBeenCalled();
    });
});
