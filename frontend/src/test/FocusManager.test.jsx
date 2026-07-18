import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import React from 'react';
import FocusManager from '../components/layout/FocusManager';

vi.mock('next/navigation', () => ({
    usePathname: vi.fn(() => '/dashboard'),
}));

describe('FocusManager', () => {
    it('renders null', () => {
        const { container } = render(<FocusManager />);
        expect(container.innerHTML).toBe('');
    });

    it('focuses main-content element on mount', () => {
        const main = document.createElement('div');
        main.id = 'main-content';
        main.focus = vi.fn();
        document.body.appendChild(main);

        render(<FocusManager />);
        expect(main.focus).toHaveBeenCalledWith({ preventScroll: true });

        document.body.removeChild(main);
    });
});
