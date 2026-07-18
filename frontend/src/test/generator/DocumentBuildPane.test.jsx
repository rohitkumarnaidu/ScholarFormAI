import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import DocumentBuildPane from '../../components/generator/DocumentBuildPane';

vi.mock('framer-motion', () => ({
    motion: {
        div: ({ children, ...props }) => <div {...props}>{children}</div>,
    },
    AnimatePresence: ({ children }) => <>{children}</>,
}));

vi.mock('../../components/generator/TokenStream', () => ({
    default: ({ sessionId, isGenerating, initialSections }) => (
        <div data-testid="token-stream" data-session={sessionId} data-generating={isGenerating}>
            {initialSections?.map(s => <div key={s.id}>{s.title}</div>)}
        </div>
    ),
}));

describe('DocumentBuildPane', () => {
    const defaultProps = {
        sessionId: 'sess-1',
        stage: 'idle',
        qualityScore: null,
        initialSections: [],
        onDownload: vi.fn(),
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders header with Live Document title', () => {
        render(<DocumentBuildPane {...defaultProps} />);
        expect(screen.getByText('Live Document')).toBeInTheDocument();
    });

    it('shows idle overlay when stage is idle', () => {
        render(<DocumentBuildPane {...defaultProps} stage="idle" />);
        expect(screen.getByText('No active document')).toBeInTheDocument();
        expect(screen.getByText(/Start a new request/)).toBeInTheDocument();
    });

    it('shows Generating badge when stage is generating', () => {
        render(<DocumentBuildPane {...defaultProps} stage="generating" />);
        expect(screen.getByText('Generating')).toBeInTheDocument();
        expect(screen.queryByText('No active document')).not.toBeInTheDocument();
    });

    it('shows Complete badge when stage is complete', () => {
        render(<DocumentBuildPane {...defaultProps} stage="complete" />);
        expect(screen.getByText('Complete')).toBeInTheDocument();
    });

    it('renders download buttons when stage is complete', () => {
        render(<DocumentBuildPane {...defaultProps} stage="complete" />);
        expect(screen.getByText('Download DOCX')).toBeInTheDocument();
        expect(screen.getByText('Download PDF')).toBeInTheDocument();
    });

    it('calls onDownload with docx when DOCX button clicked', () => {
        const onDownload = vi.fn();
        render(<DocumentBuildPane {...defaultProps} stage="complete" onDownload={onDownload} />);
        fireEvent.click(screen.getByText('Download DOCX'));
        expect(onDownload).toHaveBeenCalledWith('docx');
    });

    it('calls onDownload with pdf when PDF button clicked', () => {
        const onDownload = vi.fn();
        render(<DocumentBuildPane {...defaultProps} stage="complete" onDownload={onDownload} />);
        fireEvent.click(screen.getByText('Download PDF'));
        expect(onDownload).toHaveBeenCalledWith('pdf');
    });

    it('shows QualityScoreBadge when qualityScore provided in complete stage', () => {
        render(<DocumentBuildPane {...defaultProps} stage="complete" qualityScore={{ overallScore: 92 }} />);
        expect(screen.getByText('Quality Analysis')).toBeInTheDocument();
        expect(screen.getByText('92')).toBeInTheDocument();
    });

    it('shows high quality text for score >= 85', () => {
        render(<DocumentBuildPane {...defaultProps} stage="complete" qualityScore={{ overallScore: 92 }} />);
        expect(screen.getByText('Excellent quality document')).toBeInTheDocument();
    });

    it('shows medium quality text for score 70-84', () => {
        render(<DocumentBuildPane {...defaultProps} stage="complete" qualityScore={{ overallScore: 75 }} />);
        expect(screen.getByText('Good with some potential improvements')).toBeInTheDocument();
    });

    it('shows low quality text for score < 70', () => {
        render(<DocumentBuildPane {...defaultProps} stage="complete" qualityScore={{ overallScore: 55 }} />);
        expect(screen.getByText('Review suggested before publishing')).toBeInTheDocument();
    });

    it('does not show QualityScoreBadge when qualityScore is null', () => {
        render(<DocumentBuildPane {...defaultProps} stage="complete" qualityScore={null} />);
        expect(screen.queryByText('Quality Analysis')).not.toBeInTheDocument();
    });

    it('renders TokenStream with correct props', () => {
        const sections = [{ id: 's1', title: 'Intro' }];
        render(<DocumentBuildPane {...defaultProps} stage="generating" initialSections={sections} />);
        const tokenStream = screen.getByTestId('token-stream');
        expect(tokenStream).toHaveAttribute('data-session', 'sess-1');
        expect(tokenStream).toHaveAttribute('data-generating', 'true');
    });

    it('does not render download buttons when stage is idle', () => {
        render(<DocumentBuildPane {...defaultProps} stage="idle" />);
        expect(screen.queryByText('Download DOCX')).not.toBeInTheDocument();
        expect(screen.queryByText('Download PDF')).not.toBeInTheDocument();
    });

    it('does not render download buttons when stage is generating', () => {
        render(<DocumentBuildPane {...defaultProps} stage="generating" />);
        expect(screen.queryByText('Download DOCX')).not.toBeInTheDocument();
        expect(screen.queryByText('Download PDF')).not.toBeInTheDocument();
    });

    it('accepts qualityScore with overall_score key', () => {
        render(<DocumentBuildPane {...defaultProps} stage="complete" qualityScore={{ overall_score: 88 }} />);
        expect(screen.getByText('88')).toBeInTheDocument();
        expect(screen.getByText('Excellent quality document')).toBeInTheDocument();
    });

    it('accepts qualityScore with overall key', () => {
        render(<DocumentBuildPane {...defaultProps} stage="complete" qualityScore={{ overall: 65 }} />);
        expect(screen.getByText('65')).toBeInTheDocument();
        expect(screen.getByText('Review suggested before publishing')).toBeInTheDocument();
    });

    it('accepts qualityScore with score key', () => {
        render(<DocumentBuildPane {...defaultProps} stage="complete" qualityScore={{ score: 72 }} />);
        expect(screen.getByText('72')).toBeInTheDocument();
        expect(screen.getByText('Good with some potential improvements')).toBeInTheDocument();
    });

    it('handles null qualityScore gracefully', () => {
        render(<DocumentBuildPane {...defaultProps} stage="complete" qualityScore={null} />);
        expect(screen.queryByText('/100')).not.toBeInTheDocument();
    });

    it('shows quality score /100 suffix only when score present', () => {
        render(<DocumentBuildPane {...defaultProps} stage="complete" qualityScore={{ overallScore: 80 }} />);
        expect(screen.getByText('/100')).toBeInTheDocument();
    });

    it('does not render content when stage transitions from complete to idle', () => {
        const { rerender } = render(<DocumentBuildPane {...defaultProps} stage="complete" qualityScore={{ overallScore: 90 }} />);
        expect(screen.getByText('Download DOCX')).toBeInTheDocument();
        rerender(<DocumentBuildPane {...defaultProps} stage="idle" qualityScore={{ overallScore: 90 }} />);
        expect(screen.queryByText('Download DOCX')).not.toBeInTheDocument();
        expect(screen.getByText('No active document')).toBeInTheDocument();
    });

    it('renders help text in footer when complete', () => {
        render(<DocumentBuildPane {...defaultProps} stage="complete" />);
        expect(screen.getByText(/Need changes\?/)).toBeInTheDocument();
    });

    it('download buttons have accessible roles', () => {
        render(<DocumentBuildPane {...defaultProps} stage="complete" />);
        const buttons = screen.getAllByRole('button');
        expect(buttons.length).toBeGreaterThanOrEqual(2);
    });

    it('passes sessionId to TokenStream on session change', () => {
        const { rerender } = render(<DocumentBuildPane {...defaultProps} sessionId="sess-1" stage="generating" />);
        let ts = screen.getByTestId('token-stream');
        expect(ts).toHaveAttribute('data-session', 'sess-1');
        rerender(<DocumentBuildPane {...defaultProps} sessionId="sess-2" stage="generating" />);
        ts = screen.getByTestId('token-stream');
        expect(ts).toHaveAttribute('data-session', 'sess-2');
    });
});
