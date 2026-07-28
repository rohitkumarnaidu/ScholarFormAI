// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useDocument } from '@/context/DocumentContext';
import { isCompleted, isFailed, isProcessing as isStatusProcessing } from '@/constants/status';
import {
    CHUNK_UPLOAD_THRESHOLD_BYTES,
    uploadChunked,
    uploadDocumentWithProgress,
    useDocumentStatus,
} from '@/services/api';
import { getRemainingQuota } from '@/lib/planTier';
import { UploadStartSchema } from '@/lib/schemas';
import { trackEvent } from '@/lib/analytics';

/**
 * useUpload
 * 
 * Custom hook to manage the document upload and processing workflow.
 * Encapsulates file selection, upload logic, status polling, and state sync.
 */
export function useUpload() {
    const { isLoggedIn, user } = useAuth();
    const { job, setJob } = useDocument();
    const router = useRouter();

    // -- State --
    const [file, setFile] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);
    const [activeJobId, setActiveJobId] = useState(null);
    const [progress, setProgress] = useState(0);
    const [currentStep, setCurrentStep] = useState(0);
    const [statusMessage, setStatusMessage] = useState('Initializing...');
    const [template, setTemplate] = useState('none');
    const [category, setCategory] = useState('none');
    const [fileError, setFileError] = useState(null);
    const abortControllerRef = useRef(null);

    // Formatting Options
    const [formattingOptions, setFormattingOptions] = useState({
        addPageNumbers: true,
        addBorders: false,
        addCoverPage: true,
        generateTOC: false,
        pageSize: 'Letter',
        fastMode: false
    });

    const terminalStatusHandledRef = useRef(false);
    const completionNotificationSentRef = useRef(false);

    // -- Quota --
    const { remaining } = getRemainingQuota(user, user?.uploads_count || 0);

    // -- Helpers --
    const getStepFromPhase = useCallback((phase) => {
        switch (phase) {
            case 'UPLOAD': return 1;
            case 'EXTRACTION': return 2;
            case 'NLP_ANALYSIS': return 4;
            case 'VALIDATION': return 5;
            case 'FORMATTING': return 6;
            case 'PERSISTENCE': return 7;
            default: return 1;
        }
    }, []);

    const sendCompletionNotification = useCallback(() => {
        if (typeof window === 'undefined' || !('Notification' in window)) return;
        if (Notification.permission === 'granted') {
            new Notification('ScholarForm AI', { body: 'Your document is ready!' });
        }
    }, []);

    const statusPollInterval = useCallback((query) => {
        if (!isProcessing) return false;

        const payload = query?.state?.data || {};
        const phase = String(payload.phase || payload.current_phase || '').toUpperCase();
        const progressValue = Number(payload.progress_percentage || 0);

        if (progressValue >= 90) return 1200;
        if (phase === 'UPLOAD' || phase === 'UPLOADED') return 1000;
        if (phase === 'EXTRACTION' || phase === 'NLP_ANALYSIS') return 1600;
        return 2400;
    }, [isProcessing]);

    // -- API: Status Polling --
    const { data: statusData } = useDocumentStatus(activeJobId, {
        enabled: Boolean(activeJobId) && isProcessing,
        refetchInterval: statusPollInterval,
        staleTime: 500,
        refetchOnWindowFocus: false,
        refetchOnReconnect: false,
        retry: 1,
    });

    // -- Core Logic: Sync with Persisted Job --
    useEffect(() => {
        if (!job) return;

        const normalizedStatus = job.status?.toUpperCase();
        const currentlyProcessing = isStatusProcessing(normalizedStatus)
            || ['RUNNING', 'IN_PROGRESS'].includes(normalizedStatus);

        if (currentlyProcessing) {
            setIsProcessing(true);
            setActiveJobId(job.id || null);
            if (typeof job.progress === 'number') setProgress(job.progress);
            if (job.phase) setCurrentStep(getStepFromPhase(job.phase));
            return;
        }

        if (isCompleted(normalizedStatus)) {
            setIsProcessing(false);
            setActiveJobId(null);
            setProgress(100);
            setCurrentStep(7);
            setStatusMessage('Processing complete!');
        } else if (isFailed(normalizedStatus)) {
            setIsProcessing(false);
            setActiveJobId(null);
            if (job.error) setStatusMessage(`Failed: ${job.error}`);
        }
    }, [job, getStepFromPhase]);

    // -- Core Logic: Real-time Status Updates --
    useEffect(() => {
        if (!statusData || !job) return;

        setProgress(statusData.progress_percentage || 0);
        if (statusData.message) setStatusMessage(statusData.message);
        if (statusData.phase) setCurrentStep(getStepFromPhase(statusData.phase));

        const normalizedStatus = statusData.status?.toUpperCase();
        const currentlyProcessing = isStatusProcessing(normalizedStatus)
            || ['RUNNING', 'IN_PROGRESS'].includes(normalizedStatus);

        if (currentlyProcessing) {
            terminalStatusHandledRef.current = false;
            completionNotificationSentRef.current = false;
            setIsProcessing(true);
            return;
        }

        if (isCompleted(normalizedStatus)) {
            if (terminalStatusHandledRef.current) return;
            terminalStatusHandledRef.current = true;
            setIsProcessing(false);
            setActiveJobId(null);
            setProgress(100);
            setCurrentStep(7);
            setStatusMessage(statusData.status === 'COMPLETED_WITH_WARNINGS'
                ? `Completed with warnings: ${statusData.message}`
                : 'Processing complete!');

            const completedJob = {
                ...job,
                status: statusData.status,
                progress: 100,
                outputPath: statusData.output_path,
                phase: statusData.phase,
            };
            trackEvent('upload_completed', {
                job_id: completedJob.id,
                status: statusData.status,
                template: completedJob.template || null,
                phase: statusData.phase,
            });
            setJob(completedJob);
            sessionStorage.setItem('scholarform_currentJob', JSON.stringify(completedJob));

            if (!completionNotificationSentRef.current) {
                sendCompletionNotification();
                completionNotificationSentRef.current = true;
            }

            setTimeout(() => router.push('/download'), 500);
            return;
        }

        if (isFailed(normalizedStatus)) {
            if (terminalStatusHandledRef.current) return;
            terminalStatusHandledRef.current = true;
            setIsProcessing(false);
            setActiveJobId(null);
            setStatusMessage(`Failed: ${statusData.message}`);
            setJob(prev => ({
                ...(prev || {}),
                status: statusData.status,
                error: statusData.message,
                progress: statusData.progress_percentage || 0,
                phase: statusData.phase,
            }));
        }
    }, [job, statusData, getStepFromPhase, setJob, sendCompletionNotification, router]);

    // -- Handlers --
    const updateFormattingOption = useCallback((key, value) => {
        setFormattingOptions(prev => ({ ...prev, [key]: value }));
    }, []);

    const resetProgress = useCallback(() => {
        setProgress(0);
        setCurrentStep(0);
        setStatusMessage('Ready for upload');
    }, []);

    const cancelUpload = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
        }
        setIsProcessing(false);
        setActiveJobId(null);
        setJob(null);
        setCurrentStep(0);
        setProgress(0);
        setStatusMessage('Processing cancelled.');
        terminalStatusHandledRef.current = false;
        completionNotificationSentRef.current = false;
    }, [setJob]);

    const startUpload = useCallback(async () => {
        if (!file || isProcessing) return;
        if (remaining === 0) return 'quota_exceeded';

        const validationResult = UploadStartSchema.safeParse({
            file,
            template,
            formattingOptions,
        });
        if (!validationResult.success) {
            const firstIssue = validationResult.error?.issues?.[0]?.message || 'Upload settings are invalid.';
            setFileError(firstIssue);
            setStatusMessage(firstIssue);
            return 'validation_error';
        }
        setFileError(null);

        if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission().catch(() => { });
        }

        const executeUpload = async (attempt = 0) => {
            const controller = new AbortController();
            abortControllerRef.current = controller;
            setIsProcessing(true);
            setActiveJobId(null);
            setProgress(0);
            setCurrentStep(1);
            setStatusMessage(attempt > 0 ? `Retrying upload (Attempt ${attempt + 1}/3)...` : 'Initiating upload...');
            terminalStatusHandledRef.current = false;
            completionNotificationSentRef.current = false;

            const uploadOptions = {
                add_page_numbers: formattingOptions.addPageNumbers,
                add_borders: formattingOptions.addBorders,
                add_cover_page: formattingOptions.addCoverPage,
                generate_toc: formattingOptions.generateTOC,
                page_size: formattingOptions.pageSize,
                fast_mode: formattingOptions.fastMode,
            };

            try {
                let result = null;
                const shouldUseChunkedUpload = file.size > CHUNK_UPLOAD_THRESHOLD_BYTES && isLoggedIn;

                if (shouldUseChunkedUpload) {
                    setStatusMessage('Large file detected. Uploading chunks...');
                    result = await uploadChunked(file, {
                        signal: controller.signal,
                        onProgress: ({ chunkIndex, totalChunks, percent }) => {
                            setProgress(percent);
                            setStatusMessage(`Uploading chunk ${chunkIndex + 1}/${totalChunks} (${percent}%)...`);
                        },
                    });
                }

                if (controller.signal.aborted) return;

                if (!result) {
                    result = await uploadDocumentWithProgress(file, template, uploadOptions, {
                        signal: controller.signal,
                        onProgress: (uploadPercent) => {
                            setProgress(uploadPercent);
                            setStatusMessage(`Uploading manuscript... ${uploadPercent}%`);
                        },
                    });
                }

                if (controller.signal.aborted || !result?.job_id) {
                    if (!result?.job_id) throw new Error('Upload response missing job id.');
                    return;
                }

                const newJob = {
                    id: result.job_id,
                    timestamp: new Date().toISOString(),
                    status: 'processing',
                    phase: 'UPLOAD',
                    originalFileName: file.name,
                    template,
                    flags: uploadOptions,
                    progress: 0,
                };
                setStatusMessage('Upload complete. Processing started...');
                setProgress(0);
                setJob(newJob);
                setActiveJobId(newJob.id);
                trackEvent('upload_started', {
                    job_id: newJob.id,
                    template: newJob.template,
                    file_name: file.name,
                    file_size_bytes: file.size,
                    file_extension: (file.name.split('.').pop() || '').toLowerCase(),
                    chunked: shouldUseChunkedUpload,
                    fast_mode: Boolean(uploadOptions.fast_mode),
                });
                sessionStorage.setItem('scholarform_currentJob', JSON.stringify(newJob));

            } catch (error) {
                if (controller.signal.aborted) return;
                console.error(`Upload attempt ${attempt + 1} failed:`, error);
                
                if (attempt < 2) {
                    const backoffTime = Math.pow(2, attempt) * 1000;
                    setStatusMessage(`Upload failed. Retrying in ${backoffTime / 1000}s...`);
                    setTimeout(() => executeUpload(attempt + 1), backoffTime);
                } else {
                    setIsProcessing(false);
                    setStatusMessage(`Upload failed after 3 attempts: ${error.message}`);
                }
            } finally {
                if (abortControllerRef.current === controller) {
                    abortControllerRef.current = null;
                }
            }
        };

        executeUpload();
    }, [file, isProcessing, remaining, formattingOptions, isLoggedIn, template, setJob]);

    return {
        file, setFile,
        isProcessing,
        activeJobId,
        progress,
        currentStep,
        statusMessage,
        template, setTemplate,
        category, setCategory,
        fileError, setFileError,
        formattingOptions, updateFormattingOption,
        remaining,
        startUpload,
        cancelUpload,
        resetProgress
    };
}
