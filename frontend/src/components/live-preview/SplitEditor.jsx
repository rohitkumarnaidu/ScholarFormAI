// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import { useCallback, useState, useEffect } from 'react';
import dynamic from 'next/dynamic';

const PanelGroup = dynamic(() => import('react-resizable-panels').then(mod => mod.PanelGroup || mod.Group), { ssr: false });
const Panel = dynamic(() => import('react-resizable-panels').then(mod => mod.Panel), { ssr: false });
const PanelResizeHandle = dynamic(() => import('react-resizable-panels').then(mod => mod.PanelResizeHandle || mod.Separator), { ssr: false });
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import PreviewPane from './PreviewPane';

const LS_KEY = 'live-preview-panel-sizes';

function loadSavedSizes() {
    if (typeof window === 'undefined') return [50, 50];
    try {
        const raw = localStorage.getItem(LS_KEY);
        if (raw) {
            const parsed = JSON.parse(raw);
            if (Array.isArray(parsed) && parsed.length === 2) return parsed;
        }
    } catch { /* ignore */ }
    return [50, 50];
}

// ── Formatting Toolbar ─────────────────────────────────────────────────────────
function Toolbar({ editor }) {
    if (!editor) return null;

    const btn = (label, action, active, title) => (
        <button
            key={label}
            type="button"
            onClick={action}
            title={title}
            className={`px-2 py-1 rounded text-xs font-bold transition-colors ${
                active
                    ? 'bg-primary text-white'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
        >
            {label}
        </button>
    );

    const iconBtn = (icon, action, active, title) => (
        <button
            key={icon}
            type="button"
            onClick={action}
            title={title}
            className={`px-2 py-1 rounded text-xs transition-colors ${
                active
                    ? 'bg-primary text-white'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
        >
            <span className="material-symbols-outlined text-[14px] leading-none">{icon}</span>
        </button>
    );

    const sep = <div key="sep" className="w-px h-4 bg-slate-200 dark:bg-slate-700 mx-0.5" />;

    return (
        <div className="flex flex-wrap items-center gap-1 px-3 py-2 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shrink-0">
            {btn('B',  () => editor.chain().focus().toggleBold().run(),   editor.isActive('bold'),   'Bold (Ctrl+B)')}
            {btn('I',  () => editor.chain().focus().toggleItalic().run(), editor.isActive('italic'), 'Italic (Ctrl+I)')}
            {btn('S̶',  () => editor.chain().focus().toggleStrike().run(), editor.isActive('strike'), 'Strikethrough')}
            {sep}
            {btn('H1', () => editor.chain().focus().toggleHeading({ level: 1 }).run(), editor.isActive('heading', { level: 1 }), 'Heading 1')}
            {btn('H2', () => editor.chain().focus().toggleHeading({ level: 2 }).run(), editor.isActive('heading', { level: 2 }), 'Heading 2')}
            {btn('H3', () => editor.chain().focus().toggleHeading({ level: 3 }).run(), editor.isActive('heading', { level: 3 }), 'Heading 3')}
            {sep}
            {iconBtn('format_list_bulleted',  () => editor.chain().focus().toggleBulletList().run(),  editor.isActive('bulletList'),  'Bullet List')}
            {iconBtn('format_list_numbered',  () => editor.chain().focus().toggleOrderedList().run(), editor.isActive('orderedList'), 'Numbered List')}
            {sep}
            {btn('`',  () => editor.chain().focus().toggleCode().run(),      editor.isActive('code'),      'Inline Code')}
            {iconBtn('format_quote',          () => editor.chain().focus().toggleBlockquote().run(), editor.isActive('blockquote'),   'Blockquote')}
            {sep}
            {iconBtn('undo', () => editor.chain().focus().undo().run(), false, 'Undo (Ctrl+Z)')}
            {iconBtn('redo', () => editor.chain().focus().redo().run(), false, 'Redo (Ctrl+Y)')}
        </div>
    );
}

/**
 * SplitEditor – resizable two-pane editor+preview layout.
 *
 * Props:
 *   sessionId    {string}
 *   templateId   {string}
 *   html         {string}   – Current preview HTML (from parent's WS hook)
 *   isAnalyzing  {boolean}
 *   sendContent  {Function} – from useLivePreviewSocket
 */
export default function SplitEditor({ sessionId, templateId, html, isAnalyzing, sendContent }) {
    const defaultSizes = loadSavedSizes();
    const [isMobile, setIsMobile] = useState(false);
    const [activeTab, setActiveTab] = useState('editor');

    useEffect(() => {
        const checkMobile = () => setIsMobile(window.innerWidth < 640);
        checkMobile();
        window.addEventListener('resize', checkMobile);
        return () => window.removeEventListener('resize', checkMobile);
    }, []);

    const handleLayout = useCallback((sizes) => {
        try {
            localStorage.setItem(LS_KEY, JSON.stringify(sizes));
        } catch { /* quota exceeded etc. */ }
    }, []);

    const editor = useEditor({
        immediatelyRender: false,
        extensions: [
            StarterKit,
            Placeholder.configure({
                placeholder: 'Start writing your manuscript here…',
            }),
        ],
        content: '',
        onUpdate: ({ editor: e }) => {
            const currentHtml = e.getHTML();
            sendContent(currentHtml, templateId);
        },
        editorProps: {
            attributes: {
                class: [
                    'prose prose-slate dark:prose-invert max-w-none focus:outline-none',
                    'min-h-full text-base leading-relaxed',
                    'text-slate-700 dark:text-slate-300',
                    'font-serif px-2',
                ].join(' '),
            },
        },
    });

    return (
        <div className="flex flex-col h-full min-h-0">
            {/* Toolbar sits above both panels */}
            <Toolbar editor={editor} />

            {isMobile ? (
                <div className="flex-1 min-h-0 flex flex-col bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800">
                    <div className="flex shrink-0 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950">
                        <button
                            onClick={() => setActiveTab('editor')}
                            className={`flex flex-1 items-center justify-center gap-2 py-3 text-xs font-bold uppercase tracking-wider transition-colors ${
                                activeTab === 'editor' 
                                    ? 'text-primary border-b-2 border-primary bg-primary/5' 
                                    : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                            }`}
                        >
                            <span className="material-symbols-outlined text-[16px]">edit_note</span>
                            Editor
                        </button>
                        <button
                            onClick={() => setActiveTab('preview')}
                            className={`flex flex-1 items-center justify-center gap-2 py-3 text-xs font-bold uppercase tracking-wider transition-colors ${
                                activeTab === 'preview' 
                                    ? 'text-primary border-b-2 border-primary bg-primary/5' 
                                    : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                            }`}
                        >
                            <span className="material-symbols-outlined text-[16px]">preview</span>
                            Preview
                            {isAnalyzing && (
                                <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                            )}
                        </button>
                    </div>
                    
                    {/* Editor tab content */}
                    <div className={`flex-1 overflow-y-auto p-4 scroll-smooth bg-white dark:bg-slate-900 ${activeTab !== 'editor' ? 'hidden' : 'block'}`}>
                        <EditorContent editor={editor} className="min-h-[500px] h-full" />
                    </div>
                    
                    {/* Preview tab content */}
                    <div className={`flex-1 min-h-0 ${activeTab !== 'preview' ? 'hidden' : 'flex flex-col'}`}>
                        <PreviewPane html={html} isLoading={isAnalyzing} />
                    </div>
                </div>
            ) : (
                <PanelGroup
                    direction="horizontal"
                    onLayout={handleLayout}
                    className="flex-1 min-h-0 border-t border-slate-200 dark:border-slate-800"
                >
                    {/* ── Left: Editor ──────────────────────────────────────── */}
                    <Panel
                        defaultSize={defaultSizes[0]}
                        minSize={20}
                        className="flex flex-col min-h-0 bg-white dark:bg-slate-900"
                    >
                        {/* Panel header */}
                        <div className="flex items-center gap-2 px-3 py-1.5 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 shrink-0">
                            <span className="material-symbols-outlined text-[14px] text-slate-400">edit_note</span>
                            <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Editor</span>
                            {sessionId && (
                                <span className="ml-auto text-[10px] text-slate-300 dark:text-slate-700 font-mono truncate max-w-[120px]" title={sessionId}>
                                    {sessionId.slice(0, 8)}…
                                </span>
                            )}
                        </div>

                        {/* TipTap scroll area */}
                        <div className="flex-1 overflow-y-auto p-4 sm:p-6 scroll-smooth">
                            <EditorContent editor={editor} className="min-h-[500px] h-full" />
                        </div>
                    </Panel>

                    {/* ── Divider ────────────────────────────────────────────── */}
                    <PanelResizeHandle className="
                        w-1.5 flex-shrink-0 cursor-col-resize
                        bg-slate-200 dark:bg-slate-800
                        hover:bg-primary/40 active:bg-primary/60
                        transition-colors duration-150
                        flex items-center justify-center
                        group relative
                    ">
                        {/* Drag grip dots */}
                        <div className="absolute w-1 flex flex-col gap-0.5 pointer-events-none opacity-40 group-hover:opacity-100 transition-opacity">
                            {[0, 1, 2, 3, 4].map(i => (
                                <div key={i} className="w-1 h-1 rounded-full bg-slate-500 dark:bg-slate-400" />
                            ))}
                        </div>
                    </PanelResizeHandle>

                    {/* ── Right: Preview ─────────────────────────────────────── */}
                    <Panel
                        defaultSize={defaultSizes[1]}
                        minSize={20}
                        className="flex flex-col min-h-0"
                    >
                        {/* Panel header */}
                        <div className="flex items-center gap-2 px-3 py-1.5 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 shrink-0">
                            <span className="material-symbols-outlined text-[14px] text-slate-400">preview</span>
                            <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Preview</span>
                            <div className="ml-auto flex items-center gap-1.5">
                                {isAnalyzing && (
                                    <div className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse" title="Analyzing…" />
                                )}
                            </div>
                        </div>

                        <PreviewPane html={html} isLoading={isAnalyzing} />
                    </Panel>
                </PanelGroup>
            )}
        </div>
    );
}
