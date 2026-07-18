import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { SynthesisDownloadSection, SynthesisQualityPanel } from '../components/synthesis/SynthesisComponents';

describe('SynthesisDownloadSection', () => {
    it('renders download links', () => {
        render(<SynthesisDownloadSection apiUrl="http://localhost:8000" documentUrl="/doc.docx" pdfUrl="/doc.pdf" />);
        expect(screen.getByText('Download DOCX')).toBeInTheDocument();
        expect(screen.getByText('Download PDF')).toBeInTheDocument();
    });

    it('has correct href for DOCX', () => {
        render(<SynthesisDownloadSection apiUrl="http://localhost:8000" documentUrl="/doc.docx" pdfUrl="/doc.pdf" />);
        const docxLink = screen.getByText('Download DOCX').closest('a');
        expect(docxLink.getAttribute('href')).toBe('http://localhost:8000/doc.docx');
    });

    it('has correct href for PDF', () => {
        render(<SynthesisDownloadSection apiUrl="http://localhost:8000" documentUrl="/doc.docx" pdfUrl="/doc.pdf" />);
        const pdfLink = screen.getByText('Download PDF').closest('a');
        expect(pdfLink.getAttribute('href')).toBe('http://localhost:8000/doc.pdf');
    });
});

describe('SynthesisQualityPanel', () => {
    it('renders score', () => {
        render(<SynthesisQualityPanel score={85} metrics={[]} />);
        expect(screen.getByText('85')).toBeInTheDocument();
    });

    it('renders default score when not provided', () => {
        render(<SynthesisQualityPanel metrics={[]} />);
        expect(screen.getByText('92')).toBeInTheDocument();
    });

    it('renders metrics', () => {
        const metrics = [
            { label: 'Relevance', value: 90 },
            { label: 'Coherence', value: 85 },
        ];
        render(<SynthesisQualityPanel score={80} metrics={metrics} />);
        expect(screen.getByText('Relevance')).toBeInTheDocument();
        expect(screen.getByText('Coherence')).toBeInTheDocument();
        expect(screen.getByText('90%')).toBeInTheDocument();
        expect(screen.getByText('85%')).toBeInTheDocument();
    });

    it('renders Confidence Score heading', () => {
        render(<SynthesisQualityPanel metrics={[]} />);
        expect(screen.getByText('Confidence Score')).toBeInTheDocument();
    });
});
