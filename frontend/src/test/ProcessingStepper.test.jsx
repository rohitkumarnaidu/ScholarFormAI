import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import ProcessingStepper from '../components/upload/ProcessingStepper';

const mockSteps = [
    { id: 1, title: 'Upload', desc: 'Uploading file' },
    { id: 2, title: 'Process', desc: 'Processing content' },
    { id: 3, title: 'Export', desc: 'Generating output' },
];

describe('ProcessingStepper', () => {
    it('renders steps', () => {
        render(<ProcessingStepper isProcessing={false} progress={0} statusMessage="Ready" currentStep={0} steps={mockSteps} />);
        expect(screen.getByText('Upload')).toBeInTheDocument();
        expect(screen.getByText('Process')).toBeInTheDocument();
        expect(screen.getByText('Export')).toBeInTheDocument();
    });

    it('shows processing label when active', () => {
        render(<ProcessingStepper isProcessing={true} progress={50} statusMessage="Halfway" currentStep={2} steps={mockSteps} />);
        expect(screen.getByText('Processing')).toBeInTheDocument();
    });

    it('shows standby label when not processing', () => {
        render(<ProcessingStepper isProcessing={false} progress={0} statusMessage="Ready" currentStep={0} steps={mockSteps} />);
        expect(screen.getByText('Standby')).toBeInTheDocument();
    });

    it('displays progress percentage', () => {
        render(<ProcessingStepper isProcessing={true} progress={75} statusMessage="Working" currentStep={2} steps={mockSteps} />);
        expect(screen.getByText('75%')).toBeInTheDocument();
    });

    it('marks completed steps', () => {
        render(<ProcessingStepper isProcessing={true} progress={100} statusMessage="Done" currentStep={3} steps={mockSteps} />);
        expect(screen.getAllByText('Completed').length).toBe(3);
    });
});
