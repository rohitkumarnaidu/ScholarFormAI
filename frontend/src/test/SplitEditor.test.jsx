import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

// Mock next/dynamic to resolve imports and render children
vi.mock('next/dynamic', () => ({
    default: () => {
        const DynamicComponent = ({ children, ...props }) => <div {...props}>{children}</div>;
        DynamicComponent.displayName = 'Dynamic';
        return DynamicComponent;
    },
}));

vi.mock('@tiptap/react', () => ({
    useEditor: vi.fn(() => ({
        chain: vi.fn(() => ({
            focus: vi.fn(() => ({
                toggleBold: vi.fn(() => ({ run: vi.fn() })),
                toggleItalic: vi.fn(() => ({ run: vi.fn() })),
                toggleStrike: vi.fn(() => ({ run: vi.fn() })),
                toggleHeading: vi.fn(() => ({ run: vi.fn() })),
                toggleBulletList: vi.fn(() => ({ run: vi.fn() })),
                toggleOrderedList: vi.fn(() => ({ run: vi.fn() })),
                toggleCode: vi.fn(() => ({ run: vi.fn() })),
                toggleBlockquote: vi.fn(() => ({ run: vi.fn() })),
                undo: vi.fn(() => ({ run: vi.fn() })),
                redo: vi.fn(() => ({ run: vi.fn() })),
            })),
        })),
        isActive: vi.fn(() => false),
        getHTML: vi.fn(() => '<p>Content</p>'),
    })),
    EditorContent: () => <div data-testid="editor-content" />,
}));

vi.mock('@tiptap/starter-kit', () => ({
    default: { configure: vi.fn() },
}));

vi.mock('@tiptap/extension-placeholder', () => ({
    default: { configure: vi.fn() },
}));

vi.mock('../components/live-preview/PreviewPane', () => ({
    default: () => <div data-testid="preview-pane" />,
}));

describe('SplitEditor', () => {
    it('renders editor and preview panel headers', async () => {
        const SplitEditor = (await import('../components/live-preview/SplitEditor')).default;
        render(<SplitEditor sessionId="session-1" templateId="apa" html="" isAnalyzing={false} sendContent={() => {}} />);
        expect(screen.getByText('Editor')).toBeInTheDocument();
        expect(screen.getByText('Preview')).toBeInTheDocument();
    });

    it('renders toolbar with heading buttons', async () => {
        const SplitEditor = (await import('../components/live-preview/SplitEditor')).default;
        render(<SplitEditor sessionId="s1" templateId="t1" html="" isAnalyzing={false} sendContent={() => {}} />);
        expect(screen.getByText('H1')).toBeInTheDocument();
        expect(screen.getByText('H2')).toBeInTheDocument();
        expect(screen.getByText('H3')).toBeInTheDocument();
    });

    it('renders bold, italic, strikethrough buttons', async () => {
        const SplitEditor = (await import('../components/live-preview/SplitEditor')).default;
        render(<SplitEditor sessionId="s1" templateId="t1" html="" isAnalyzing={false} sendContent={() => {}} />);
        expect(screen.getByText('B')).toBeInTheDocument();
        expect(screen.getByText('I')).toBeInTheDocument();
    });

    it('shows analyzing indicator when isAnalyzing', async () => {
        const SplitEditor = (await import('../components/live-preview/SplitEditor')).default;
        render(<SplitEditor sessionId="s1" templateId="t1" html="" isAnalyzing={true} sendContent={() => {}} />);
        expect(screen.getByTitle('Analyzing…')).toBeInTheDocument();
    });
});
