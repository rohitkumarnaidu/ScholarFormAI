import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import Stepper from '../components/Stepper';

describe('Stepper', () => {
    it('renders static steps when no stages provided', () => {
        render(<Stepper activeStep={0} />);
        expect(screen.getByText('Uploading Manuscript')).toBeInTheDocument();
    });

    it('marks active step', () => {
        render(<Stepper activeStep={1} />);
        const runningSteps = screen.getAllByText('Converting Format');
        expect(runningSteps.length).toBeGreaterThan(0);
    });

    it('renders with dynamic stages', () => {
        const stages = [
            { id: 'step1', title: 'Step 1', status: 'success' },
            { id: 'step2', title: 'Step 2', status: 'running' },
        ];
        render(<Stepper stages={stages} />);
        expect(screen.getByText('Step 1')).toBeInTheDocument();
        expect(screen.getByText('Step 2')).toBeInTheDocument();
    });

    it('normalizes status aliases', () => {
        const stages = [
            { id: 's1', title: 'Done', status: 'COMPLETED' },
            { id: 's2', title: 'Processing', status: 'processing' },
            { id: 's3', title: 'Errored', status: 'error' },
        ];
        render(<Stepper stages={stages} />);
        expect(screen.getByText('Done')).toBeInTheDocument();
        expect(screen.getByText('Processing')).toBeInTheDocument();
        expect(screen.getByText('Errored')).toBeInTheDocument();
    });

    it('has role="list" for accessibility', () => {
        render(<Stepper activeStep={0} />);
        expect(screen.getByRole('list')).toBeInTheDocument();
    });

    it('marks list items with aria-current', () => {
        render(<Stepper activeStep={0} />);
        const items = screen.getAllByRole('listitem');
        expect(items[0]).toHaveAttribute('aria-current', 'step');
    });
});
