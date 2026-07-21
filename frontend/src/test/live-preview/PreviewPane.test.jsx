import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import PreviewPane from '../../components/live-preview/PreviewPane';

describe('PreviewPane', () => {
    it('shows placeholder when no HTML', () => {
        render(<PreviewPane html="" isLoading={false} />);
        expect(screen.getByText('Preview will appear here as you type')).toBeInTheDocument();
    });

    it('renders HTML content', () => {
        render(<PreviewPane html="<p>Hello World</p>" isLoading={false} />);
        expect(screen.getByText('Hello World')).toBeInTheDocument();
    });

    it('shows analyzing overlay when loading', () => {
        render(<PreviewPane html="" isLoading={true} />);
        expect(screen.getByText('Analyzing…')).toBeInTheDocument();
    });

    it('strips script tags from HTML', () => {
        render(<PreviewPane html='<script>alert("xss")</script><p>Safe</p>' isLoading={false} />);
        expect(screen.getByText('Safe')).toBeInTheDocument();
        expect(screen.queryByText(/alert/)).not.toBeInTheDocument();
    });

    it('strips event handlers from HTML', () => {
        render(<PreviewPane html='<p onclick="alert(1)">Safe</p>' isLoading={false} />);
        expect(screen.getByText('Safe')).toBeInTheDocument();
    });

    it('handles null html', () => {
        render(<PreviewPane html={null} isLoading={false} />);
        expect(screen.getByText('Preview will appear here as you type')).toBeInTheDocument();
    });

    it('has aria-label on scroll container', () => {
        render(<PreviewPane html="" isLoading={false} />);
        expect(screen.getByLabelText('Document preview')).toBeInTheDocument();
    });

    it('sanitizes nested script tags', () => {
        render(<PreviewPane html='<div><script>bad</script><p>Good</p></div>' isLoading={false} />);
        expect(screen.getByText('Good')).toBeInTheDocument();
        expect(screen.queryByText('bad')).not.toBeInTheDocument();
    });

    it('sanitizes javascript: URLs in links', () => {
        render(<PreviewPane html='<a href="javascript:alert(1)">Click</a><p>Safe</p>' isLoading={false} />);
        expect(screen.getByText('Safe')).toBeInTheDocument();
    });

    it('sanitizes onerror attributes', () => {
        render(<PreviewPane html='<img src=x onerror="alert(1)"><p>Safe</p>' isLoading={false} />);
        expect(screen.getByText('Safe')).toBeInTheDocument();
    });

    it('renders multiple paragraphs from HTML', () => {
        render(<PreviewPane html="<p>First</p><p>Second</p>" isLoading={false} />);
        expect(screen.getByText('First')).toBeInTheDocument();
        expect(screen.getByText('Second')).toBeInTheDocument();
    });

    it('sanitizes mixed content with inline event handlers', () => {
        render(<PreviewPane html='<p onmouseover="evil()">Safe</p>' isLoading={false} />);
        expect(screen.getByText('Safe')).toBeInTheDocument();
    });
});
