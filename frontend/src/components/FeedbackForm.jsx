// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { useRef, useState } from 'react';
import { submitFeedback } from '@/services/api';
import { FeedbackSubmissionSchema, getFirstZodError } from '@/lib/schemas';

export default function FeedbackForm({ documentId: propDocId, onSubmitted }) {
    const formRef = useRef(null);
    const [documentId, setDocumentId] = useState(propDocId || '');
    const [fieldName, setFieldName] = useState('');
    const [originalValue, setOriginalValue] = useState('');
    const [correctedValue, setCorrectedValue] = useState('');
    const [comment, setComment] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        const validation = FeedbackSubmissionSchema.safeParse({
            document_id: documentId,
            field: fieldName,
            original_value: originalValue,
            corrected_value: correctedValue,
            comments: comment,
        });
        if (!validation.success) {
            setError(getFirstZodError(validation.error?.issues, 'Feedback input is invalid.'));
            return;
        }

        setSubmitting(true);
        setError('');
        setSuccess(false);

        try {
            await submitFeedback(validation.data);
            setSuccess(true);
            setFieldName('');
            setOriginalValue('');
            setCorrectedValue('');
            setComment('');
            onSubmitted?.();
        } catch (err) {
            setError(err.message || 'Failed to submit feedback. Please try again.');
        } finally {
            setSubmitting(false);
        }
    };

    const handleFormKeyDown = (event) => {
        if (!(event.ctrlKey || event.metaKey) || event.key !== 'Enter') return;
        event.preventDefault();
        if (submitting) return;
        formRef.current?.requestSubmit();
    };

    return (
        <form ref={formRef} onSubmit={handleSubmit} onKeyDown={handleFormKeyDown} className="space-y-4">
            {!propDocId && (
                <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Document Job ID *
                    </label>
                    <input
                        type="text"
                        value={documentId}
                        onChange={(e) => setDocumentId(e.target.value)}
                        placeholder="e.g. abc-123-def"
                        className="w-full p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-primary outline-none"
                        required
                    />
                </div>
            )}

            <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Field Name *
                </label>
                <input
                    type="text"
                    value={fieldName}
                    onChange={(e) => setFieldName(e.target.value)}
                    placeholder="e.g. title, abstract, authors, references"
                    className="w-full p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-primary outline-none"
                    required
                />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label className="flex justify-between items-baseline mb-1">
                        <span className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                            Original Value
                        </span>
                        <span className={`text-xs ${originalValue.length > 900 ? 'text-red-500 font-bold' : 'text-slate-500'}`}>
                            {originalValue.length}/1000
                        </span>
                    </label>
                    <textarea
                        value={originalValue}
                        onChange={(e) => setOriginalValue(e.target.value)}
                        placeholder="What the AI produced"
                        rows={3}
                        maxLength={1000}
                        className="w-full p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-primary outline-none resize-none"
                    />
                </div>
                <div>
                    <label className="flex justify-between items-baseline mb-1">
                        <span className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                            Corrected Value *
                        </span>
                        <span className={`text-xs ${correctedValue.length > 900 ? 'text-red-500 font-bold' : 'text-slate-500'}`}>
                            {correctedValue.length}/1000
                        </span>
                    </label>
                    <textarea
                        value={correctedValue}
                        onChange={(e) => setCorrectedValue(e.target.value)}
                        placeholder="What it should be"
                        rows={3}
                        maxLength={1000}
                        className="w-full p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-primary outline-none resize-none"
                        required
                    />
                </div>
            </div>

            <div>
                <label className="flex justify-between items-baseline mb-1">
                    <span className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                        Additional Comment
                    </span>
                    <span className={`text-xs ${comment.length > 450 ? 'text-red-500 font-bold' : 'text-slate-500'}`}>
                        {comment.length}/500
                    </span>
                </label>
                <textarea
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="Any notes about why this correction is needed"
                    rows={2}
                    maxLength={500}
                    className="w-full p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-primary outline-none resize-none"
                />
            </div>

            {error && (
                <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-sm">
                    {error}
                </div>
            )}

            {success && (
                <div className="p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 text-sm flex items-center gap-2">
                    <span className="material-symbols-outlined text-sm">check_circle</span>
                    Feedback submitted successfully! Thank you for helping improve our AI.
                </div>
            )}

            <button
                type="submit"
                disabled={submitting}
                title="Submit Correction (Ctrl+Enter)"
                className="w-full py-3 bg-primary hover:bg-blue-700 text-white font-bold rounded-xl shadow-lg shadow-primary/25 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
            >
                {submitting ? (
                    <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Submitting...
                    </>
                ) : (
                    <>
                        <span className="material-symbols-outlined">send</span>
                        Submit Correction
                    </>
                )}
            </button>
        </form>
    );
}
