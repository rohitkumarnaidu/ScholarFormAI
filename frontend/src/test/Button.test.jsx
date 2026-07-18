import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import Button from '../components/ui/Button';

describe('Button', () => {
    it('renders children', () => {
        render(<Button>Click Me</Button>);
        expect(screen.getByText('Click Me')).toBeInTheDocument();
    });

    it('renders as button element by default', () => {
        render(<Button>Test</Button>);
        expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('calls onClick when clicked', () => {
        const onClick = vi.fn();
        render(<Button onClick={onClick}>Click</Button>);
        fireEvent.click(screen.getByRole('button'));
        expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('shows spinner when loading', () => {
        const { container } = render(<Button loading>Loading</Button>);
        const spinner = container.querySelector('.animate-spin');
        expect(spinner).toBeInTheDocument();
    });

    it('disables button when loading', () => {
        render(<Button loading>Loading</Button>);
        expect(screen.getByRole('button')).toBeDisabled();
    });

    it('disables button when disabled', () => {
        render(<Button disabled>Disabled</Button>);
        expect(screen.getByRole('button')).toBeDisabled();
    });

    it('applies primary variant by default', () => {
        const { container } = render(<Button>Primary</Button>);
        expect(container.firstChild.className).toContain('bg-primary');
    });

    it('applies secondary variant', () => {
        const { container } = render(<Button variant="secondary">Secondary</Button>);
        expect(container.firstChild.className).toContain('bg-slate-100');
    });

    it('applies danger variant', () => {
        const { container } = render(<Button variant="danger">Danger</Button>);
        expect(container.firstChild.className).toContain('bg-red-600');
    });

    it('applies size classes', () => {
        const { container } = render(<Button size="lg">Large</Button>);
        expect(container.firstChild.className).toContain('h-12');
    });

    it('supports different type attributes', () => {
        render(<Button type="submit">Submit</Button>);
        expect(screen.getByRole('button')).toHaveAttribute('type', 'submit');
    });

    it('forwards ref to the button element', () => {
        const ref = React.createRef();
        render(<Button ref={ref}>Ref Test</Button>);
        expect(ref.current).toBeInstanceOf(HTMLButtonElement);
    });

    it('sets aria-busy when loading', () => {
        render(<Button loading>Loading</Button>);
        expect(screen.getByRole('button')).toHaveAttribute('aria-busy', 'true');
    });

    it('merges custom className with component classes', () => {
        const { container } = render(<Button className="my-custom-class">Custom</Button>);
        expect(container.firstChild.className).toContain('my-custom-class');
        expect(container.firstChild.className).toContain('bg-primary');
    });

    it('does not submit a form when pressing Enter with type="button"', () => {
        const onSubmit = vi.fn(e => e.preventDefault());
        render(
            <form onSubmit={onSubmit}>
                <Button type="button">Non-submit</Button>
            </form>
        );
        const button = screen.getByRole('button');
        fireEvent.keyDown(button, { key: 'Enter' });
        expect(onSubmit).not.toHaveBeenCalled();
    });

    it('renders with type="submit" when explicitly set', () => {
        render(<Button type="submit">Submit</Button>);
        expect(screen.getByRole('button')).toHaveAttribute('type', 'submit');
    });
});
