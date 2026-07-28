// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { DocumentProvider, useDocument } from '@/context/DocumentContext';

function DocumentStateProbe() {
    const { job, processing, startProcessing, finishProcessing, failProcessing } = useDocument();
    return (
        <div>
            <div data-testid="has-job">{job ? 'true' : 'false'}</div>
            <div data-testid="processing">{String(processing)}</div>
            <div data-testid="job-status">{job?.status ?? 'none'}</div>
            <div data-testid="job-id">{job?.id ?? 'none'}</div>
            <button data-testid="start-processing" onClick={startProcessing}>Start</button>
            <button data-testid="finish-processing" onClick={() => finishProcessing({ job_id: 'job-42' }, null, 'ieee', {})}>Finish</button>
            <button data-testid="fail-processing" onClick={() => failProcessing(new Error('Failed'))}>Fail</button>
        </div>
    );
}

describe('DocumentContext', () => {
    beforeEach(() => {
        sessionStorage.clear();
    });

    it('provides default state with no job', () => {
        render(
            <DocumentProvider>
                <DocumentStateProbe />
            </DocumentProvider>
        );
        expect(screen.getByTestId('has-job')).toHaveTextContent('false');
        expect(screen.getByTestId('processing')).toHaveTextContent('false');
    });

    it('starts processing and clears job', () => {
        render(
            <DocumentProvider>
                <DocumentStateProbe />
            </DocumentProvider>
        );
        fireEvent.click(screen.getByTestId('start-processing'));
        expect(screen.getByTestId('processing')).toHaveTextContent('true');
        expect(screen.getByTestId('has-job')).toHaveTextContent('false');
    });

    it('finishes processing with result data', () => {
        render(
            <DocumentProvider>
                <DocumentStateProbe />
            </DocumentProvider>
        );
        fireEvent.click(screen.getByTestId('finish-processing'));
        expect(screen.getByTestId('processing')).toHaveTextContent('false');
        expect(screen.getByTestId('job-status')).toHaveTextContent('completed');
        expect(screen.getByTestId('job-id')).toHaveTextContent('job-42');
    });

    it('persists job to sessionStorage', () => {
        render(
            <DocumentProvider>
                <DocumentStateProbe />
            </DocumentProvider>
        );
        fireEvent.click(screen.getByTestId('finish-processing'));
        const saved = sessionStorage.getItem('scholarform_currentJob');
        expect(saved).toBeTruthy();
        const parsed = JSON.parse(saved);
        expect(parsed.id).toBe('job-42');
    });

    it('handles processing failure', () => {
        render(
            <DocumentProvider>
                <DocumentStateProbe />
            </DocumentProvider>
        );
        fireEvent.click(screen.getByTestId('fail-processing'));
        expect(screen.getByTestId('processing')).toHaveTextContent('false');
        expect(screen.getByTestId('job-status')).toHaveTextContent('failed');
    });

    it('restores job from sessionStorage on mount', () => {
        sessionStorage.setItem('scholarform_currentJob', JSON.stringify({ id: 'restored-job', status: 'completed' }));
        render(
            <DocumentProvider>
                <DocumentStateProbe />
            </DocumentProvider>
        );
        expect(screen.getByTestId('has-job')).toHaveTextContent('true');
        expect(screen.getByTestId('job-id')).toHaveTextContent('restored-job');
    });

    it('clears corrupted sessionStorage entry', () => {
        sessionStorage.setItem('scholarform_currentJob', '{invalid json}');
        render(
            <DocumentProvider>
                <DocumentStateProbe />
            </DocumentProvider>
        );
        expect(screen.getByTestId('has-job')).toHaveTextContent('false');
        expect(sessionStorage.getItem('scholarform_currentJob')).toBeNull();
    });

    it('removes sessionStorage when job is set to null', () => {
        render(
            <DocumentProvider>
                <DocumentStateProbe />
            </DocumentProvider>
        );
        fireEvent.click(screen.getByTestId('start-processing'));
        expect(sessionStorage.getItem('scholarform_currentJob')).toBeNull();
    });
});
