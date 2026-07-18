import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import React from 'react';
import Minimap from '../components/ui/Minimap';

describe('Minimap', () => {
    it('renders without crashing', () => {
        const { container } = render(<Minimap content="line1\nline2" targetRef={{ current: null }} />);
        expect(container.firstChild).toBeInTheDocument();
    });

    it('renders lines from content', () => {
        const { container } = render(<Minimap content={'hello\nworld'} targetRef={{ current: null }} />);
        const lineElements = container.querySelectorAll('.bg-slate-400');
        expect(lineElements.length).toBe(2);
    });

    it('has click handler on container', () => {
        const { container } = render(<Minimap content="test" targetRef={{ current: null }} />);
        expect(container.firstChild.className).toContain('cursor-pointer');
    });

    it('handles empty content', () => {
        const { container } = render(<Minimap content="" targetRef={{ current: null }} />);
        expect(container.firstChild).toBeInTheDocument();
    });
});
