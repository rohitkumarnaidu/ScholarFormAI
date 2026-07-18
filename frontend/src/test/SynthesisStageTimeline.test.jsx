// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import SynthesisStageTimeline from '../components/generator/SynthesisStageTimeline';

vi.mock('framer-motion', () => ({
    motion: {
        div: ({ children, ...props }) => <div {...props}>{children}</div>,
    },
}));

describe('SynthesisStageTimeline', () => {
    it('renders all 8 expected stages', () => {
        render(<SynthesisStageTimeline />);
        expect(screen.getByText('Upload Validation')).toBeInTheDocument();
        expect(screen.getByText('Document Extraction')).toBeInTheDocument();
        expect(screen.getByText('Embedding')).toBeInTheDocument();
        expect(screen.getByText('Cross-Document Analysis')).toBeInTheDocument();
        expect(screen.getByText('Synthesis Planning')).toBeInTheDocument();
        expect(screen.getByText('Content Generation')).toBeInTheDocument();
        expect(screen.getByText('Citation Insertion')).toBeInTheDocument();
        expect(screen.getByText('Template Rendering')).toBeInTheDocument();
    });

    it('renders Synthesis Progress heading', () => {
        render(<SynthesisStageTimeline />);
        expect(screen.getByText('Synthesis Progress')).toBeInTheDocument();
    });

    it('shows pending status for all stages when no stages provided', () => {
        render(<SynthesisStageTimeline />);
        const pendingTexts = screen.getAllByText('Pending');
        expect(pendingTexts).toHaveLength(8);
    });

    it('shows completed status for done stages', () => {
        const stages = [{ name: 'Upload Validation', status: 'done' }];
        render(<SynthesisStageTimeline stages={stages} />);
        expect(screen.getByText('Completed successfully')).toBeInTheDocument();
    });

    it('shows running status for current stage', () => {
        const stages = [{ name: 'Document Extraction', status: 'running' }];
        render(<SynthesisStageTimeline stages={stages} currentStage="Document Extraction" />);
        expect(screen.getByText('Processing...')).toBeInTheDocument();
    });

    it('shows error status with message', () => {
        const stages = [{ name: 'Embedding', status: 'error', message: 'Failed to embed' }];
        render(<SynthesisStageTimeline stages={stages} />);
        expect(screen.getByText('Failed to embed')).toBeInTheDocument();
    });

    it('shows progress percentage when available', () => {
        const stages = [{ name: 'Content Generation', status: 'running', progress: 65 }];
        render(<SynthesisStageTimeline stages={stages} currentStage="Content Generation" />);
        expect(screen.getByText('65%')).toBeInTheDocument();
    });

    it('renders progress bar for running stage with progress', () => {
        const stages = [{ name: 'Content Generation', status: 'running', progress: 45 }];
        const { container } = render(<SynthesisStageTimeline stages={stages} currentStage="Content Generation" />);
        const progressBar = container.querySelector('.bg-indigo-500');
        expect(progressBar).toBeInTheDocument();
    });

    it('marks stage as completed when subsequent stage has passed', () => {
        const stages = [
            { name: 'Upload Validation', status: 'done' },
            { name: 'Document Extraction', status: 'running' },
        ];
        render(<SynthesisStageTimeline stages={stages} currentStage="Document Extraction" />);
        expect(screen.getAllByText('Completed successfully').length).toBeGreaterThanOrEqual(1);
    });

    it('handles empty stages array gracefully', () => {
        render(<SynthesisStageTimeline stages={[]} currentStage="" />);
        expect(screen.getAllByText('Pending').length).toBe(8);
    });

    it('shows progress bar with minimum width for low percentages', () => {
        const stages = [{ name: 'Embedding', status: 'running', progress: 2 }];
        const { container } = render(<SynthesisStageTimeline stages={stages} currentStage="Embedding" />);
        const progressDiv = container.querySelector('[style*="width"]');
        expect(progressDiv).toBeInTheDocument();
    });
});
