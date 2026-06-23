// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useGeneratorState } from '@/app/(generator)/(protected)/generate/_components/useGeneratorState';

const {
    addToastMock,
    generateDocumentMock,
    streamGenerationStatusMock,
    downloadGeneratedDocumentMock,
    getBuiltinTemplatesMock,
    clearDraftMock,
} = vi.hoisted(() => ({
    addToastMock: vi.fn(),
    generateDocumentMock: vi.fn(),
    streamGenerationStatusMock: vi.fn(),
    downloadGeneratedDocumentMock: vi.fn(),
    getBuiltinTemplatesMock: vi.fn(),
    clearDraftMock: vi.fn(),
}));

vi.mock('@/src/context/ToastContext', () => ({
    useToast: () => ({ addToast: addToastMock, showToast: addToastMock }),
}));

vi.mock('@/src/services/api', () => ({
    generateDocument: generateDocumentMock,
    streamGenerationStatus: streamGenerationStatusMock,
    downloadGeneratedDocument: downloadGeneratedDocumentMock,
    getBuiltinTemplates: getBuiltinTemplatesMock,
}));

vi.mock('@/src/hooks/useAutosave', () => ({
    useAutosave: () => ({
        restoreDraft: () => null,
        clearDraft: clearDraftMock,
    }),
}));

vi.mock('@/src/hooks/useUnsavedChanges', () => ({
    useUnsavedChanges: vi.fn(),
}));

const moveToMetadataStep = (result) => {
    act(() => {
        result.current.selectDocType('academic_paper');
    });
    act(() => {
        result.current.setTemplate('ieee');
    });
    act(() => {
        result.current.goNext();
    });
    act(() => {
        result.current.setMetadata({ title: 'Generated Paper' });
    });
};

describe('useGeneratorState', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        getBuiltinTemplatesMock.mockResolvedValue([]);
    });

    it('handles step navigation and template filtering', () => {
        const { result } = renderHook(() => useGeneratorState());

        expect(result.current.step).toBe(1);

        act(() => {
            result.current.selectDocType('resume');
        });

        expect(result.current.step).toBe(2);
        expect(result.current.templates.length).toBeGreaterThan(0);
        expect(result.current.templates.every((entry) => entry.category === 'Resume')).toBe(true);

        act(() => {
            result.current.setTemplate('ats');
        });
        act(() => {
            result.current.goNext();
        });

        expect(result.current.step).toBe(3);
    });

    it('transitions to done state from generation stream events', async () => {
        generateDocumentMock.mockResolvedValue({ job_id: 'job-42' });

        const closeStreamMock = vi.fn();
        let onStreamEvent;
        streamGenerationStatusMock.mockImplementation((jobId, onEvent) => {
            onStreamEvent = onEvent;
            return closeStreamMock;
        });

        const { result } = renderHook(() => useGeneratorState());
        moveToMetadataStep(result);

        await act(async () => {
            await result.current.handleGenerate();
        });

        expect(result.current.step).toBe(4);
        expect(result.current.jobStatus.status).toBe('generating');
        expect(streamGenerationStatusMock).toHaveBeenCalledWith(
            'job-42',
            expect.any(Function),
            expect.any(Function)
        );

        act(() => {
            onStreamEvent({
                event: 'progress',
                data: { status: 'generating', progress: 45, stage: 'structuring', message: 'Structuring blocks' },
            });
        });
        expect(result.current.jobStatus.progress).toBe(45);
        expect(result.current.jobStatus.stage).toBe('structuring');

        act(() => {
            onStreamEvent({
                event: 'complete',
                data: { status: 'done', message: 'Document ready' },
            });
        });

        expect(result.current.jobStatus.status).toBe('done');
        expect(result.current.jobStatus.progress).toBe(100);
        expect(result.current.jobStatus.jobId).toBe('job-42');
        expect(clearDraftMock).toHaveBeenCalledTimes(1);
        expect(closeStreamMock).toHaveBeenCalledTimes(1);
    });

    it('downloads generated file and triggers cleanup', async () => {
        generateDocumentMock.mockResolvedValue({ job_id: 'job-77' });

        let onStreamEvent;
        streamGenerationStatusMock.mockImplementation((jobId, onEvent) => {
            onStreamEvent = onEvent;
            return vi.fn();
        });

        const cleanupMock = vi.fn();
        downloadGeneratedDocumentMock.mockResolvedValue({
            url: 'blob:generated-file',
            cleanup: cleanupMock,
        });

        const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => { });
        vi.useFakeTimers();

        const { result } = renderHook(() => useGeneratorState());
        moveToMetadataStep(result);

        await act(async () => {
            await result.current.handleGenerate();
        });
        act(() => {
            onStreamEvent({
                event: 'complete',
                data: { status: 'done', message: 'Document ready' },
            });
        });

        await act(async () => {
            await result.current.handleDownload('pdf');
            await vi.runAllTimersAsync();
        });

        expect(downloadGeneratedDocumentMock).toHaveBeenCalledWith('job-77', 'pdf');
        expect(cleanupMock).toHaveBeenCalledTimes(1);
        expect(addToastMock).toHaveBeenCalledWith({ message: 'Download started!', type: 'success' });

        clickSpy.mockRestore();
        vi.useRealTimers();
    });

    it('resets state and closes active stream', async () => {
        generateDocumentMock.mockResolvedValue({ job_id: 'job-90' });
        const closeStreamMock = vi.fn();
        streamGenerationStatusMock.mockReturnValue(closeStreamMock);

        const { result } = renderHook(() => useGeneratorState());
        moveToMetadataStep(result);

        await act(async () => {
            await result.current.handleGenerate();
        });

        act(() => {
            result.current.handleReset();
        });

        expect(closeStreamMock).toHaveBeenCalledTimes(1);
        expect(result.current.step).toBe(1);
        expect(result.current.docType).toBe('');
        expect(result.current.template).toBe('');
        expect(result.current.jobStatus.status).toBe('idle');
    });
});
