import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import JobStatusCard from '../components/layout/JobStatusCard';

describe('JobStatusCard', () => {
    it('renders with mock data when no job provided', () => {
        render(<JobStatusCard />);
        expect(screen.getByText('Thesis_Final_Draft_v2.docx')).toBeInTheDocument();
    });

    it('renders job filename', () => {
        render(<JobStatusCard job={{ filename: 'paper.docx', status: 'completed', template: 'APA', timeAgo: '5m', size: '1MB', description: 'Done' }} />);
        expect(screen.getByText('paper.docx')).toBeInTheDocument();
    });

    it('shows ready badge for completed jobs', () => {
        render(<JobStatusCard job={{ filename: 'paper.docx', status: 'completed', template: 'APA', timeAgo: '5m', size: '1MB', description: 'Done' }} />);
        expect(screen.getByText('Ready')).toBeInTheDocument();
    });

    it('shows processing badge', () => {
        render(<JobStatusCard job={{ filename: 'paper.docx', status: 'processing', template: 'APA', timeAgo: '5m', size: '1MB', description: 'Working' }} />);
        expect(screen.getByText('Processing')).toBeInTheDocument();
    });

    it('shows failed badge', () => {
        render(<JobStatusCard job={{ filename: 'paper.docx', status: 'failed', template: 'APA', timeAgo: '5m', size: '1MB', description: 'Error' }} />);
        expect(screen.getByText('Failed')).toBeInTheDocument();
    });

    it('shows download button for completed', () => {
        render(<JobStatusCard job={{ filename: 'paper.docx', status: 'completed', template: 'APA', timeAgo: '5m', size: '1MB', description: 'Done' }} />);
        expect(screen.getByText('Download')).toBeInTheDocument();
        expect(screen.getByText('Preview')).toBeInTheDocument();
    });

    it('shows cancel button for processing', () => {
        render(<JobStatusCard job={{ filename: 'paper.docx', status: 'processing', template: 'APA', timeAgo: '5m', size: '1MB', description: 'Working' }} />);
        expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    it('shows retry for failed', () => {
        render(<JobStatusCard job={{ filename: 'paper.docx', status: 'failed', template: 'APA', timeAgo: '5m', size: '1MB', description: 'Error' }} />);
        expect(screen.getByText('Retry')).toBeInTheDocument();
        expect(screen.getByText('View Logs')).toBeInTheDocument();
    });
});
