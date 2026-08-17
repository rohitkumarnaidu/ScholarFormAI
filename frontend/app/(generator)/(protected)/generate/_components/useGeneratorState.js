// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { toast } from 'sonner';
import {
    generateDocument,
    streamGenerationStatus,
    downloadGeneratedDocument,
    getBuiltinTemplates,
} from '@/services/api';
import { useAutosave } from '@/hooks/useAutosave';
import { useUnsavedChanges } from '@/hooks/useUnsavedChanges';
import { GeneratorStartSchema, getFirstZodError } from '@/lib/schemas';

// ── Exported constants (used by MetadataStep) ───────────────────────────
export const DEFAULT_PAPER_SECTIONS = [
    { name: 'Abstract', include: true },
    { name: 'Introduction', include: true },
    { name: 'Related Work', include: true },
    { name: 'Methodology', include: true },
    { name: 'Results', include: true },
    { name: 'Discussion', include: true },
    { name: 'Conclusion', include: true },
    { name: 'References', include: true },
];

export const DEFAULT_RESUME_EDUCATION = [
    { institution: '', degree: '', year: '' },
];

export const DEFAULT_RESUME_EXPERIENCE = [
    { company: '', role: '', duration: '', bullets_raw: '' },
];

// ── Templates (hardcoded fallback) ──────────────────────────────────────
const TEMPLATES = [
    { id: 'ieee', name: 'IEEE', category: 'Engineering' },
    { id: 'apa7', name: 'APA 7th', category: 'Social Science' },
    { id: 'chicago', name: 'Chicago', category: 'Humanities' },
    { id: 'mla', name: 'MLA', category: 'Humanities' },
    { id: 'harvard', name: 'Harvard', category: 'General' },
    { id: 'vancouver', name: 'Vancouver', category: 'Medical' },
    { id: 'acm', name: 'ACM', category: 'Computing' },
    { id: 'springer', name: 'Springer', category: 'Science' },
    { id: 'elsevier', name: 'Elsevier', category: 'Science' },
    { id: 'nature', name: 'Nature', category: 'Science' },
    { id: 'ats', name: 'ATS-Optimized', category: 'Resume' },
    { id: 'modern', name: 'Modern Clean', category: 'Resume' },
    { id: 'classic', name: 'Classic Professional', category: 'Resume' },
    { id: 'formal_letter', name: 'Formal Letter', category: 'Letter' },
    { id: 'cover_letter', name: 'Cover Letter', category: 'Letter' },
];

// ── Step definitions ────────────────────────────────────────────────────
const STEPS = [
    { label: 'Document Type', icon: 'description' },
    { label: 'Template', icon: 'dashboard_customize' },
    { label: 'Details', icon: 'edit_note' },
    { label: 'Generate', icon: 'auto_awesome' },
];

// ── Hook ────────────────────────────────────────────────────────────────
export function useGeneratorState() {
    

    const [step, setStep] = useState(1);
    const [docType, setDocType] = useState('');
    const [template, setTemplate] = useState('');
    const [metadata, setMetadata] = useState({});
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [allTemplates, setAllTemplates] = useState(TEMPLATES);
    const [jobStatus, setJobStatus] = useState({
        status: 'idle',
        progress: 0,
        stage: '',
        message: '',
        error: '',
        outline: [],
    });

    const abortRef = useRef(null);

    // ── Fetch templates from API on mount (B5.3) ─────────────────
    useEffect(() => {
        let cancelled = false;
        getBuiltinTemplates()
            .then((data) => {
                if (cancelled) return;
                const list = data?.templates ?? data ?? [];
                if (Array.isArray(list) && list.length > 0) {
                    const mapped = list.map((t) => ({
                        id: t.id || t.name?.toLowerCase().replace(/\s+/g, '_'),
                        name: t.name || t.id,
                        category: t.category || 'General',
                    }));
                    // Merge with hardcoded fallback to keep any missing items
                    const byId = new Map(mapped.map((t) => [t.id, t]));
                    const merged = TEMPLATES.map((t) => byId.get(t.id) || t);
                    const extra = mapped.filter((t) => !TEMPLATES.some((ht) => ht.id === t.id));
                    setAllTemplates([...merged, ...extra]);
                }
            })
            .catch(() => {
                // Silently fall back to hardcoded templates
            });
        return () => { cancelled = true; };
    }, []);

    // ── Autosave: saves form data every 10 s ─────────────────────────
    const formData = { docType, template, metadata };
    const { restoreDraft, clearDraft } = useAutosave(formData, step);

    // ── Unsaved-changes warning ──────────────────────────────────────
    const isDirty = Boolean(docType || template || Object.keys(metadata).length > 0);
    useUnsavedChanges(isDirty && step < 4);

    // ── Restore draft on mount ───────────────────────────────────────
    useEffect(() => {
        const draft = restoreDraft();
        if (draft?.formData) {
            if (draft.formData.docType) setDocType(draft.formData.docType);
            if (draft.formData.template) setTemplate(draft.formData.template);
            if (draft.formData.metadata && Object.keys(draft.formData.metadata).length) {
                setMetadata(draft.formData.metadata);
            }
            if (draft.currentStep && draft.currentStep >= 1 && draft.currentStep <= 3) {
                setStep(draft.currentStep);
            }
            showToast({ message: 'Draft restored from your last session.', type: 'info' });
        }
        // Only run once on mount
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // ── Computed ──────────────────────────────────────────────────────
    const filteredTemplates = allTemplates.filter((t) => {
        if (docType === 'resume') return t.category === 'Resume';
        if (docType === 'letter' || docType === 'cover_letter') return t.category === 'Letter';
        return t.category !== 'Resume' && t.category !== 'Letter';
    });

    const canAdvance = (() => {
        if (step === 1) return Boolean(docType);
        if (step === 2) return Boolean(template);
        if (step === 3) {
            if (docType === 'resume') return Boolean(metadata.name);
            return Boolean(metadata.title);
        }
        return false;
    })();

    // ── Navigation ───────────────────────────────────────────────────
    const selectDocType = useCallback((type) => {
        setDocType(type);
        setTemplate('');
        setMetadata({});
        setStep(2);
    }, []);

    const goBack = useCallback(() => setStep((s) => Math.max(1, s - 1)), []);
    const goNext = useCallback(() => {
        if (canAdvance) setStep((s) => Math.min(4, s + 1));
    }, [canAdvance]);

    // ── Generate ─────────────────────────────────────────────────────
    const handleGenerate = useCallback(async () => {
        if (isSubmitting) return;

        const validation = GeneratorStartSchema.safeParse({
            doc_type: docType,
            template,
            metadata,
        });
        if (!validation.success) {
            showToast({
                message: getFirstZodError(validation.error?.issues, 'Generator input is invalid.'),
                type: 'error',
            });
            return;
        }
        const payload = validation.data;

        if (abortRef.current) {
            abortRef.current();
            abortRef.current = null;
        }

        setIsSubmitting(true);
        setStep(4);
        setJobStatus({ status: 'generating', progress: 0, stage: 'generating', message: 'Starting generation…', error: '', outline: [] });

        try {
            const response = await generateDocument(payload);
            const jobId = response?.job_id || response?.id;

            if (!jobId) throw new Error('No job ID returned from server.');

            // Subscribe to SSE stream
            abortRef.current = streamGenerationStatus(
                jobId,
                ({ event, data }) => {
                    if (event === 'progress' || event === 'message') {
                        setJobStatus((prev) => ({
                            ...prev,
                            status: data?.status || prev.status,
                            progress: data?.progress ?? prev.progress,
                            stage: data?.stage || prev.stage,
                            message: data?.message || prev.message,
                            outline: data?.outline || prev.outline,
                        }));
                    }
                    if (event === 'complete' || data?.status === 'done') {
                        setJobStatus((prev) => ({
                            ...prev,
                            status: 'done',
                            progress: 100,
                            stage: 'done',
                            message: data?.message || 'Document ready!',
                            outline: data?.outline || prev.outline,
                            jobId,
                        }));
                        clearDraft();
                        if (abortRef.current) {
                            abortRef.current();
                            abortRef.current = null;
                        }
                    }
                    if (event === 'error' || data?.status === 'failed') {
                        setJobStatus((prev) => ({
                            ...prev,
                            status: 'failed',
                            error: data?.error || data?.message || 'Generation failed.',
                        }));
                        if (abortRef.current) {
                            abortRef.current();
                            abortRef.current = null;
                        }
                    }
                },
                (error) => {
                    setJobStatus((prev) => ({
                        ...prev,
                        status: 'failed',
                        error: error?.message || 'Stream connection lost.',
                    }));
                    if (abortRef.current) {
                        abortRef.current();
                        abortRef.current = null;
                    }
                }
            );
        } catch (error) {
            setJobStatus((prev) => ({
                ...prev,
                status: 'failed',
                error: error?.message || 'Failed to start generation.',
            }));
            showToast({ message: 'Failed to start generation: ' + (error?.message || 'Unknown error'), type: 'error' });
        } finally {
            setIsSubmitting(false);
        }
    }, [isSubmitting, docType, template, metadata, clearDraft, showToast]);

    // ── Download ─────────────────────────────────────────────────────
    const handleDownload = useCallback(async (format = 'docx') => {
        let cleanup = null;
        try {
            const jobId = jobStatus.jobId;
            if (!jobId) throw new Error('No job ID available for download');
            const download = await downloadGeneratedDocument(jobId, format);
            const { url, cleanup: downloadCleanup } = download || {};
            if (!url || typeof downloadCleanup !== 'function') {
                throw new Error('Download link unavailable');
            }
            cleanup = downloadCleanup;
            const a = document.createElement('a');
            a.href = url;
            a.download = `generated_document.${format}`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            showToast({ message: 'Download started!', type: 'success' });
        } catch (error) {
            showToast({ message: 'Download failed: ' + (error?.message || 'Unknown error'), type: 'error' });
        } finally {
            if (cleanup) {
                setTimeout(cleanup, 0);
            }
        }
    }, [jobStatus.jobId, showToast]);

    // ── Reset ────────────────────────────────────────────────────────
    const handleReset = useCallback(() => {
        if (abortRef.current) {
            abortRef.current();
            abortRef.current = null;
        }
        setStep(1);
        setDocType('');
        setTemplate('');
        setMetadata({});
        setJobStatus({ status: 'idle', progress: 0, stage: '', message: '', error: '', outline: [] });
        clearDraft();
    }, [clearDraft]);

    // Cleanup stream on unmount
    useEffect(() => {
        return () => {
            if (abortRef.current) abortRef.current();
        };
    }, []);

    return {
        step,
        docType,
        template,
        metadata,
        templates: filteredTemplates,
        jobStatus,
        isSubmitting,
        canAdvance,
        steps: STEPS,
        selectDocType,
        setTemplate,
        setMetadata,
        goBack,
        goNext,
        handleGenerate,
        handleDownload,
        handleReset,
    };
}
