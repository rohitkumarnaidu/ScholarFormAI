// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import StatusBadge from '../components/StatusBadge';

describe('StatusBadge', () => {
    it('renders the correct label for COMPLETED status', () => {
        render(<StatusBadge status="COMPLETED" />);
        expect(screen.getByText('Completed')).toBeInTheDocument();
    });

    it('renders the correct label for PROCESSING status', () => {
        render(<StatusBadge status="PROCESSING" />);
        expect(screen.getByText('Processing')).toBeInTheDocument();
    });

    it('renders FAILED status with correct label', () => {
        render(<StatusBadge status="FAILED" />);
        expect(screen.getByText('Failed')).toBeInTheDocument();
    });

    it('falls back to STANDBY for unknown status', () => {
        render(<StatusBadge status="UNKNOWN_STATE" />);
        expect(screen.getByText('Standby')).toBeInTheDocument();
    });

    it('handles lowercase status correctly', () => {
        render(<StatusBadge status="completed" />);
        expect(screen.getByText('Completed')).toBeInTheDocument();
    });

    it('handles null/missing status by falling back to STANDBY', () => {
        render(<StatusBadge status={null} />);
        expect(screen.getByText('Standby')).toBeInTheDocument();
    });
});
