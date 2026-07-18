import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import Preview from '../components/Preview';

const { mockGetPreview, mockIsCompleted } = vi.hoisted(() => ({
    mockGetPreview: vi.fn(() => Promise.resolve({
        metadata: { filename: 'thesis.docx' },
        structured_data: { sections: { Abstract: ['This is the abstract'] } },
    })),
    mockIsCompleted: vi.fn(() => true),
}));

vi.mock('@/src/services/api', () => ({
    getPreview: mockGetPreview,
}));

vi.mock('../constants/status', () => ({
    isCompleted: mockIsCompleted,
}));

describe('Preview', () => {
    const mockJob = {
        id: 'job-123',
        status: 'COMPLETED',
        originalFileName: 'thesis.docx',
        template: 'apa',
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders title from job', async () => {
        render(<Preview job={mockJob} onUpload={() => {}} onDownload={() => {}} />);
        expect(await screen.findByText('thesis')).toBeInTheDocument();
    });

    it('shows read-only badge', () => {
        render(<Preview job={mockJob} onUpload={() => {}} onDownload={() => {}} />);
        expect(screen.getByText('Read Only')).toBeInTheDocument();
    });

    it('shows zoom controls', () => {
        render(<Preview job={mockJob} onUpload={() => {}} onDownload={() => {}} />);
        expect(screen.getByLabelText('Zoom Out')).toBeInTheDocument();
        expect(screen.getByLabelText('Zoom In')).toBeInTheDocument();
    });

    it('renders formatting report section', () => {
        render(<Preview job={mockJob} onUpload={() => {}} onDownload={() => {}} />);
        expect(screen.getByText('Template Compliant')).toBeInTheDocument();
        expect(screen.getByText('Final Formatting Report')).toBeInTheDocument();
    });

    it('renders document info section', () => {
        render(<Preview job={mockJob} onUpload={() => {}} onDownload={() => {}} />);
        expect(screen.getByText('Visible Word Count')).toBeInTheDocument();
        expect(screen.getByText('Template')).toBeInTheDocument();
        expect(screen.getByText('Job Status')).toBeInTheDocument();
    });

    it('shows Download button enabled when completed', async () => {
        render(<Preview job={mockJob} onUpload={() => {}} onDownload={() => {}} />);
        const btn = screen.getByText('Download Final');
        expect(btn.closest('button')).not.toBeDisabled();
    });

    it('shows Download button disabled when job not completed', () => {
        mockIsCompleted.mockReturnValue(false);
        render(<Preview job={{ ...mockJob, status: 'PROCESSING' }} onUpload={() => {}} onDownload={() => {}} />);
        const btn = screen.getByText('Download Final');
        expect(btn.closest('button')).toBeDisabled();
    });

    it('shows Upload link', () => {
        render(<Preview job={mockJob} onUpload={() => {}} onDownload={() => {}} />);
        expect(screen.getByText('Upload')).toBeInTheDocument();
    });

    it('shows Preview loading spinner while fetching', async () => {
        mockGetPreview.mockImplementationOnce(() => new Promise(() => {}));
        render(<Preview job={mockJob} onUpload={() => {}} onDownload={() => {}} />);
        expect(await screen.findByText(/Preview loading/)).toBeInTheDocument();
    });

    it('shows error message when getPreview fails', async () => {
        mockGetPreview.mockRejectedValueOnce(new Error('Network error'));
        render(<Preview job={mockJob} onUpload={() => {}} onDownload={() => {}} />);
        await waitFor(() => {
            expect(screen.getByText(/Error loading preview content/)).toBeInTheDocument();
        });
    });

    it('handles no sections data gracefully', async () => {
        mockGetPreview.mockResolvedValueOnce({
            metadata: { filename: 'empty.docx' },
            structured_data: { sections: {} },
        });
        render(<Preview job={{ id: 'job-empty', originalFileName: 'empty.docx', template: 'ieee' }} onUpload={() => {}} onDownload={() => {}} />);
        await waitFor(() => {
            expect(screen.getByText('No structured text content available.')).toBeInTheDocument();
        });
    });

    it('handles null sections gracefully', async () => {
        mockGetPreview.mockResolvedValueOnce({
            metadata: { filename: 'null.docx' },
            structured_data: null,
        });
        render(<Preview job={{ id: 'job-null', originalFileName: 'null.docx', template: 'ieee' }} onUpload={() => {}} onDownload={() => {}} />);
        await waitFor(() => {
            expect(screen.getByText('No structured text content available.')).toBeInTheDocument();
        });
    });

    it('uses job originalFileName when metadata filename is missing', async () => {
        mockGetPreview.mockResolvedValueOnce({
            metadata: {},
            structured_data: { sections: { Intro: ['Text'] } },
        });
        render(<Preview job={{ id: 'job-99', originalFileName: 'myfile.docx', template: 'apa' }} onUpload={() => {}} onDownload={() => {}} />);
        expect(await screen.findByText((content) => content.includes('myfile') && content.includes('Preview'))).toBeInTheDocument();
    });

    it('uses Untitled fallback when no filename available', async () => {
        mockGetPreview.mockResolvedValueOnce({
            metadata: {},
            structured_data: { sections: { Intro: ['Text'] } },
        });
        render(<Preview job={{ id: 'job-100', template: 'apa' }} onUpload={() => {}} onDownload={() => {}} />);
        expect(await screen.findByText('Untitled')).toBeInTheDocument();
    });

    it('renders section content from structured data', async () => {
        mockGetPreview.mockResolvedValueOnce({
            metadata: { filename: 'paper.docx' },
            structured_data: { sections: { Introduction: ['Content here'], Conclusion: ['Final notes'] } },
        });
        render(<Preview job={{ id: 'job-sections', originalFileName: 'paper.docx', template: 'apa' }} onUpload={() => {}} onDownload={() => {}} />);
        await waitFor(() => {
            expect(screen.getByText((content) => content.includes('Introduction'))).toBeInTheDocument();
            expect(screen.getByText((content) => content.includes('Conclusion'))).toBeInTheDocument();
        });
    });

    it('shows completed load percentage when sections are loaded', async () => {
        mockGetPreview.mockResolvedValueOnce({
            metadata: { filename: 'paper.docx' },
            structured_data: { sections: { S1: ['A'], S2: ['B'] } },
        });
        render(<Preview job={mockJob} onUpload={() => {}} onDownload={() => {}} />);
        await waitFor(() => {
            expect(screen.getByText('100%')).toBeInTheDocument();
        });
    });
});
