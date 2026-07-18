import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { SynthesisDownloadSection, SynthesisQualityPanel } from '../../components/synthesis/SynthesisComponents';

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

    it('uses different API URLs for href construction', () => {
        render(<SynthesisDownloadSection apiUrl="https://api.example.com" documentUrl="/v1/doc.docx" pdfUrl="/v1/doc.pdf" />);
        const docxLink = screen.getByText('Download DOCX').closest('a');
        const pdfLink = screen.getByText('Download PDF').closest('a');
        expect(docxLink.getAttribute('href')).toBe('https://api.example.com/v1/doc.docx');
        expect(pdfLink.getAttribute('href')).toBe('https://api.example.com/v1/doc.pdf');
    });

    it('has download attribute on both links', () => {
        render(<SynthesisDownloadSection apiUrl="http://localhost:8000" documentUrl="/doc.docx" pdfUrl="/doc.pdf" />);
        const docxLink = screen.getByText('Download DOCX').closest('a');
        const pdfLink = screen.getByText('Download PDF').closest('a');
        expect(docxLink.getAttribute('download')).not.toBeNull();
        expect(pdfLink.getAttribute('download')).not.toBeNull();
    });

    it('renders download icons in both links', () => {
        const { container } = render(<SynthesisDownloadSection apiUrl="http://localhost:8000" documentUrl="/doc.docx" pdfUrl="/doc.pdf" />);
        const svgs = container.querySelectorAll('svg');
        expect(svgs.length).toBe(2);
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

    it('handles empty metrics array gracefully', () => {
        const { container } = render(<SynthesisQualityPanel score={75} metrics={[]} />);
        expect(screen.getByText('75')).toBeInTheDocument();
        const metricRows = container.querySelectorAll('.border-t ~ *');
    });

    it('renders score of 0 correctly', () => {
        render(<SynthesisQualityPanel score={0} metrics={[]} />);
        expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('renders score of 100 correctly', () => {
        render(<SynthesisQualityPanel score={100} metrics={[]} />);
        expect(screen.getByText('100')).toBeInTheDocument();
    });

    it('shows /100 label next to score', () => {
        render(<SynthesisQualityPanel score={85} metrics={[]} />);
        expect(screen.getByText('/ 100')).toBeInTheDocument();
    });

    it('renders metric with 0% value', () => {
        render(<SynthesisQualityPanel score={50} metrics={[{ label: 'Accuracy', value: 0 }]} />);
        expect(screen.getByText('0%')).toBeInTheDocument();
    });

    it('renders multiple metrics in order', () => {
        const metrics = [
            { label: 'Accuracy', value: 10 },
            { label: 'Brevity', value: 20 },
            { label: 'Completeness', value: 30 },
        ];
        render(<SynthesisQualityPanel score={50} metrics={metrics} />);
        expect(screen.getByText('Accuracy')).toBeInTheDocument();
        expect(screen.getByText('Brevity')).toBeInTheDocument();
        expect(screen.getByText('Completeness')).toBeInTheDocument();
    });
});
