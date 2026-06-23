// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import ErrorBoundary from '@/src/components/ErrorBoundary';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import { Table } from '@tiptap/extension-table';
import { TableRow } from '@tiptap/extension-table-row';
import { TableCell } from '@tiptap/extension-table-cell';
import { TableHeader } from '@tiptap/extension-table-header';
import { CharacterCount } from '@tiptap/extension-character-count';

import { useDocument } from '@/src/context/DocumentContext';
import { useToast } from '@/src/context/ToastContext';
import Skeleton from '@/src/components/ui/Skeleton';
const Minimap = dynamic(() => import('@/src/components/ui/Minimap'), { ssr: false, loading: () => null });
import { useUnsavedChanges } from '@/src/hooks/useUnsavedChanges';
import { isCompleted } from '@/src/constants/status';
import { submitEdit, getPreview } from '@/src/services/api';
import useJobFromUrl from '@/src/hooks/useJobFromUrl';

const getContentFromSections = (sections) => {
    if (!sections || typeof sections !== 'object') {
        return '';
    }

    return Object.values(sections)
        .map((sectionContent) => {
            if (Array.isArray(sectionContent)) {
                return sectionContent
                    .map((line) => (typeof line === 'string' ? line : String(line ?? '')))
                    .filter((line) => line.trim() !== '')
                    .join('\n');
            }

            if (typeof sectionContent === 'string') {
                return sectionContent.trim();
            }

            return sectionContent == null ? '' : String(sectionContent).trim();
        })
        .filter(Boolean)
        .join('\n\n');
};

export default function Edit() {
    usePageTitle('Edit Document');
    const router = useRouter();
    const navigate = useCallback((href, options = {}) => {
        if (options?.replace) {
            router.replace(href);
            return;
        }
        router.push(href);
    }, [router]);
    const { setJob } = useDocument();
    const { addToast } = useToast();
    const { job, isLoading: isJobLoading, error: jobLoadError } = useJobFromUrl();
    const [content, setContent] = useState('');
    const [title, setTitle] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [lastSaved, setLastSaved] = useState('Just now');
    const [validationMessage, setValidationMessage] = useState(null);
    const initialContentRef = useRef('');
    const editorScrollRef = useRef(null);
    const isDirty = content !== initialContentRef.current;
    useUnsavedChanges(isDirty);

    const editor = useEditor({
        immediatelyRender: false,
        extensions: [
            StarterKit,
            Placeholder.configure({
                placeholder: 'Edit your document content here...',
            }),
            Table.configure({ resizable: true }),
            TableRow,
            TableHeader,
            TableCell,
            CharacterCount.configure({ limit: null }),
        ],
        content: '',
        onUpdate: ({ editor: e }) => {
            // Sync TipTap HTML → content state (for word count and save)
            setContent(e.getText({ blockSeparator: '\n\n' }));
        },
        editorProps: {
            attributes: {
                class: 'prose prose-slate dark:prose-invert max-w-none focus:outline-none min-h-[520px] sm:min-h-[700px] text-base sm:text-lg leading-relaxed text-slate-700 dark:text-slate-300 font-serif',
            },
        },
    });

    // Keep editor in sync when content loaded from job
    const setEditorContent = useCallback((text) => {
        if (!editor || editor.isDestroyed) return;
        // Convert plain text to basic HTML paragraphs for TipTap
        const html = text
            .split(/\n{2,}/)
            .map(para => para.trim() ? `<p>${para.replace(/\n/g, '<br/>')}</p>` : '<p></p>')
            .join('');
        editor.commands.setContent(html, false);
    }, [editor]);

    useEffect(() => {
        let isMounted = true;

        const loadEditorContent = async () => {
            if (!job) return;

            setTitle(job.originalFileName?.split('.')[0] || 'Untitled Manuscript');

            const processedText = typeof job.processedText === 'string' ? job.processedText.trim() : '';
            if (processedText) {
                if (isMounted) {
                    setContent(job.processedText);
                    initialContentRef.current = job.processedText;
                    setEditorContent(job.processedText);
                }
                return;
            }

            const reconstructedFromJob = getContentFromSections(job.result?.structured_data?.sections);
            if (reconstructedFromJob) {
                if (isMounted) {
                    setContent(reconstructedFromJob);
                    initialContentRef.current = reconstructedFromJob;
                    setEditorContent(reconstructedFromJob);
                }
                return;
            }

            if (!job.id) {
                if (isMounted) setContent('');
                return;
            }

            try {
                const previewData = await getPreview(job.id, { debounceMs: 0 });
                const reconstructedFromPreview = getContentFromSections(previewData?.structured_data?.sections);
                if (isMounted) {
                    const val = reconstructedFromPreview || '';
                    setContent(val);
                    initialContentRef.current = val;
                    setEditorContent(val);
                }
            } catch (error) {
                console.error('Failed to load preview content:', error);
                if (isMounted) setContent('');
            }
        };

        loadEditorContent();
        return () => {
            isMounted = false;
        };
    }, [job, editor, setEditorContent]);

    const handleSave = useCallback(async () => {
        if (!job) return;
        if (isSaving) return;
        setIsSaving(true);
        try {
            // Get the structured TipTap data
            const currentContent = editor
                ? editor.getJSON()
                : { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: content }] }] };

            await submitEdit(job.id, currentContent);

            setLastSaved(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
            initialContentRef.current = editor ? editor.getText() : content;

            // Redirect to processing/upload page to show progress of re-formatting
            const updatedJob = { ...job, status: 'processing', progress: 0 };
            setJob(updatedJob);
            sessionStorage.setItem('scholarform_currentJob', JSON.stringify(updatedJob));
            navigate('/upload');

        } catch (error) {
            console.error("Save failed:", error);
            addToast('Failed to save edit. Please try again.', 'error');
        } finally {
            setIsSaving(false);
        }
    }, [addToast, content, editor, isSaving, job, navigate, setJob]);

    const handleCancel = useCallback(() => {
        navigate('/history');
    }, [navigate]);

    const handleRevalidate = () => {
        // Simple local validation check
        const hasAbstract = content.toLowerCase().includes('abstract');
        if (!hasAbstract) {
            setValidationMessage({ type: 'warning', text: "Missing 'Abstract' section" });
        } else {
            setValidationMessage({ type: 'success', text: 'Basic structure looks good' });
        }
        // Clear message after 5 seconds
        setTimeout(() => setValidationMessage(null), 5000);
    };

    useEffect(() => {
        const handler = (e) => {
            if ((e.ctrlKey || e.metaKey) && (e.key === 'Enter' || e.key.toLowerCase() === 's')) {
                e.preventDefault();
                handleSave();
            }
            if (e.key === 'Escape') {
                e.preventDefault();
                handleCancel();
            }
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [handleCancel, handleSave]);

    // Gate: loading job from URL
    if (isJobLoading && !job) {
        return (
            <div className="min-h-screen flex flex-col bg-background-light dark:bg-background-dark animate-in fade-in duration-300">
                <div className="px-6 py-3 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center">
                    <Skeleton className="h-6 w-1/3 max-w-[200px]" rounded="rounded" />
                    <Skeleton className="h-8 w-24" />
                </div>
                <main className="flex-1 p-8 flex justify-center">
                    <div className="w-full max-w-[850px] space-y-4">
                        <Skeleton className="h-[200px] w-full" rounded="rounded-xl" />
                        <Skeleton className="h-[100px] w-full" rounded="rounded-xl" />
                        <Skeleton className="h-[300px] w-full" rounded="rounded-xl" />
                    </div>
                </main>
            </div>
        );
    }

    // Gate: error loading job from URL
    if (jobLoadError && !job) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-background-light dark:bg-background-dark px-4 text-center">
                <p className="text-red-600 dark:text-red-400 mb-3">{jobLoadError}</p>
                <button onClick={() => navigate('/history')} className="text-primary font-bold hover:underline">
                    Return to History
                </button>
            </div>
        );
    }

    // Gate: no job in context or URL
    if (!job) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-background-light dark:bg-background-dark">
                <p className="text-slate-500 dark:text-slate-400 mb-4">No document loaded for editing.</p>
                <button onClick={() => navigate('/upload')} className="text-primary font-bold hover:underline">Return to Upload</button>
            </div>
        );
    }

    return (
        <ErrorBoundary>
            <div className="bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100 min-h-screen flex flex-col font-display animate-in zoom-in-95 duration-300">

                {/* Sub-Header / Breadcrumbs & Quick Actions */}
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 px-4 sm:px-6 py-2 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 animate-in slide-in-from-top duration-300">
                    <div className="flex items-center gap-2 overflow-hidden min-w-0">
                        <button onClick={() => navigate('/history')} className="text-slate-500 dark:text-slate-400 text-sm font-medium hover:text-primary whitespace-nowrap">My Manuscripts</button>
                        <span className="text-slate-400">/</span>
                        <span className="text-slate-900 dark:text-white text-sm font-semibold truncate">{title}</span>
                        <span className={`ml-2 px-2 py-0.5 ${isSaving ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'} dark:bg-green-900/30 dark:text-green-400 text-[10px] font-bold uppercase rounded`}>
                            {isSaving ? 'Saving...' : 'Saved'}
                        </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                        <button onClick={handleSave} 
                            disabled={isSaving}
                            title="Save (Ctrl+S or Ctrl+Enter)"
                            className="flex items-center gap-1.5 px-3 py-1.5 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors" aria-label="Save">
                            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">save</span>
                            <span className="text-sm font-medium hidden sm:inline">Save</span>
                        </button>
                        <button onClick={handleRevalidate} className="flex items-center gap-1.5 px-3 py-1.5 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors" aria-label="Local Validate">
                            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">refresh</span>
                            <span className="text-sm font-medium hidden sm:inline">Local Validate</span>
                        </button>
                        <button
                            onClick={() => navigate('/download')}
                            disabled={!isCompleted(job?.status)}
                            className="flex items-center gap-1.5 px-3 sm:px-4 py-1.5 bg-primary text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-slate-400"
                            aria-label="Export"
                        >
                            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">description</span>
                            <span className="text-sm font-bold hidden sm:inline">Export</span>
                        </button>
                    </div>
                </div>

                {/* Main Layout */}
                <div className="flex flex-1 flex-col xl:flex-row overflow-hidden">
                    {/* Editor View */}
                    <main ref={editorScrollRef} className="flex-1 overflow-y-auto bg-background-light dark:bg-background-dark p-4 sm:p-6 lg:p-8 flex justify-center scroll-smooth">
                        <div className="w-full max-w-[850px]">
                            {/* Validation Message Banner */}
                            {validationMessage && (
                                <div className={`mb-6 p-4 rounded-xl border animate-in fade-in slide-in-from-top duration-300 ${validationMessage.type === 'success'
                                    ? 'bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-900/30'
                                    : 'bg-amber-50 dark:bg-amber-900/10 border-amber-200 dark:border-amber-900/30'
                                    }`}>
                                    <div className="flex items-center gap-2">
                                        <span className={`material-symbols-outlined text-sm ${validationMessage.type === 'success' ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400'
                                            }`}>
                                            {validationMessage.type === 'success' ? 'check_circle' : 'warning'}
                                        </span>
                                        <p className={`text-sm font-medium ${validationMessage.type === 'success' ? 'text-green-900 dark:text-green-300' : 'text-amber-900 dark:text-amber-300'
                                            }`}>
                                            {validationMessage.text}
                                        </p>
                                    </div>
                                </div>
                            )}

                            {/* Manuscript Paper Area */}
                            <article className="manuscript-paper bg-white dark:bg-slate-900 min-h-[700px] lg:min-h-[1100px] p-5 sm:p-8 lg:p-16 rounded-sm border border-slate-200 dark:border-slate-800 shadow-xl overflow-hidden">
                                <h1
                                    className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white mb-6 sm:mb-8 focus:outline-none"
                                    contentEditable
                                    suppressContentEditableWarning
                                    spellCheck={false}
                                >
                                    {title.replace(/_/g, ' ')}
                                </h1>

                                {/* TipTap Formatting Toolbar */}
                                <div className="flex flex-wrap items-center gap-1 mb-4 pb-3 border-b border-slate-200 dark:border-slate-700">
                                    <button
                                        type="button"
                                        onClick={() => editor?.chain().focus().toggleBold().run()}
                                        className={`px-2 py-1 rounded text-sm font-bold transition-colors ${
                                            editor?.isActive('bold')
                                                ? 'bg-primary text-white'
                                                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                                        }`}
                                        title="Bold (Ctrl+B)"
                                    >B</button>
                                    <button
                                        type="button"
                                        onClick={() => editor?.chain().focus().toggleItalic().run()}
                                        className={`px-2 py-1 rounded text-sm italic transition-colors ${
                                            editor?.isActive('italic')
                                                ? 'bg-primary text-white'
                                                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                                        }`}
                                        title="Italic (Ctrl+I)"
                                    >I</button>
                                    <div className="w-px h-5 bg-slate-200 dark:bg-slate-700 mx-1" />
                                    <button
                                        type="button"
                                        onClick={() => editor?.chain().focus().toggleHeading({ level: 1 }).run()}
                                        className={`px-2 py-1 rounded text-sm font-bold transition-colors ${
                                            editor?.isActive('heading', { level: 1 })
                                                ? 'bg-primary text-white'
                                                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                                        }`}
                                        title="Heading 1"
                                    >H1</button>
                                    <button
                                        type="button"
                                        onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}
                                        className={`px-2 py-1 rounded text-sm font-bold transition-colors ${
                                            editor?.isActive('heading', { level: 2 })
                                                ? 'bg-primary text-white'
                                                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                                        }`}
                                        title="Heading 2"
                                    >H2</button>
                                    <div className="w-px h-5 bg-slate-200 dark:bg-slate-700 mx-1" />
                                    <button
                                        type="button"
                                        onClick={() => editor?.chain().focus().toggleBulletList().run()}
                                        className={`px-2 py-1 rounded text-sm transition-colors ${
                                            editor?.isActive('bulletList')
                                                ? 'bg-primary text-white'
                                                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                                        }`}
                                        title="Bullet List"
                                    >
                                        <span className="material-symbols-outlined text-[14px]">format_list_bulleted</span>
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => editor?.chain().focus().toggleOrderedList().run()}
                                        className={`px-2 py-1 rounded text-sm transition-colors ${
                                            editor?.isActive('orderedList')
                                                ? 'bg-primary text-white'
                                                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                                        }`}
                                        title="Numbered List"
                                    >
                                        <span className="material-symbols-outlined text-[14px]">format_list_numbered</span>
                                    </button>
                                    <div className="w-px h-5 bg-slate-200 dark:bg-slate-700 mx-1" />
                                    <button
                                        type="button"
                                        onClick={() => editor?.chain().focus().undo().run()}
                                        className="px-2 py-1 rounded text-sm bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                                        title="Undo (Ctrl+Z)"
                                    >
                                        <span className="material-symbols-outlined text-[14px]">undo</span>
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => editor?.chain().focus().redo().run()}
                                        className="px-2 py-1 rounded text-sm bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                                        title="Redo (Ctrl+Y)"
                                    >
                                        <span className="material-symbols-outlined text-[14px]">redo</span>
                                    </button>
                                    <div className="w-px h-5 bg-slate-200 dark:bg-slate-700 mx-1" />
                                    <button
                                        type="button"
                                        onClick={() => editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()}
                                        className="px-2 py-1 rounded text-sm bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                                        title="Insert Table"
                                    >
                                        <span className="material-symbols-outlined text-[14px]">table</span>
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => editor?.chain().focus().toggleCodeBlock().run()}
                                        className={`px-2 py-1 rounded text-sm transition-colors ${
                                            editor?.isActive('codeBlock')
                                                ? 'bg-primary text-white'
                                                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                                        }`}
                                        title="Code Block"
                                    >
                                        <span className="material-symbols-outlined text-[14px]">code</span>
                                    </button>
                                </div>

                                {/* TipTap Editor */}
                                <EditorContent editor={editor} />
                            </article>
                        </div>
                    </main>

                    <Minimap content={content} targetRef={editorScrollRef} />

                    {/* Right Sidebar: Validation Feedback */}
                    <aside className="w-full xl:w-80 border-t xl:border-t-0 xl:border-l border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col max-h-[360px] xl:max-h-none">
                        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
                            <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                <span className="material-symbols-outlined text-primary">analytics</span>
                                Live Report
                            </h3>
                            <span className="text-xs font-semibold bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded text-slate-600 dark:text-slate-400">
                                {(job.result?.errors?.length || 0) + (job.result?.warnings?.length || 0)} Issues
                            </span>
                        </div>
                        <div className="flex-1 overflow-y-auto p-4 space-y-4">
                            {job.result?.errors?.map((err, i) => (
                                <div key={i} className="p-4 bg-red-50 dark:bg-red-900/10 border border-red-100 dark:border-red-900/30 rounded-xl">
                                    <div className="flex gap-2">
                                        <span className="material-symbols-outlined text-red-500 text-sm">error</span>
                                        <h4 className="text-sm font-bold text-red-900 dark:text-red-400">{err.issue || "Formatting Error"}</h4>
                                    </div>
                                    <p className="text-xs text-red-700 dark:text-red-300 mt-1">{err.message || err}</p>
                                </div>
                            ))}
                            {job.result?.warnings?.map((warn, i) => (
                                <div key={i} className="p-4 bg-amber-50 dark:bg-amber-900/10 border border-amber-100 dark:border-amber-900/30 rounded-xl">
                                    <div className="flex gap-2">
                                        <span className="material-symbols-outlined text-amber-500 text-sm">warning</span>
                                        <h4 className="text-sm font-bold text-amber-900 dark:text-amber-400">Suggestion</h4>
                                    </div>
                                    <p className="text-xs text-amber-700 dark:text-amber-300 mt-1">{warn.message || warn}</p>
                                </div>
                            ))}
                        </div>
                    </aside>
                </div>

                {/* Bottom Status Bar */}
                <footer className="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 px-4 sm:px-6 py-2 text-[10px] font-medium text-slate-500 dark:text-slate-400">
                    <div className="flex flex-wrap items-center gap-4">
                        <span>Words: {editor ? editor.storage.characterCount.words() : 0}</span>
                        <span>Status: {isSaving ? 'Syncing...' : 'Up to date'}</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-4">
                        <div className="flex items-center gap-1.5">
                            <span className="material-symbols-outlined text-[12px]">schedule</span>
                            <span>Last saved: {lastSaved}</span>
                        </div>
                        <span className="break-all">ID: {job.id}</span>
                    </div>
                </footer>
            </div>
        </ErrorBoundary>
    );
}




