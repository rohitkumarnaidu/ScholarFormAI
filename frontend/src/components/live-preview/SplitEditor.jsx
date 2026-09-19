"use client";
import React from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import PreviewPane from './PreviewPane';
import Button from '@/src/components/ui/Button';

export default function SplitEditor({ sessionId, templateId, html, isAnalyzing, sendContent }) {
    const editor = useEditor({
        extensions: [
            StarterKit,
            Placeholder.configure({ placeholder: 'Start typing...' })
        ],
        content: html,
        onUpdate: ({ editor }) => {
            sendContent(editor.getHTML());
        }
    });

    return (
        <div className="flex h-full w-full">
            <div className="flex-1 flex flex-col border-r">
                <div className="flex items-center justify-between p-2 border-b">
                    <span className="font-bold">Editor</span>
                    {isAnalyzing && <span title="Analyzing…">Analyzing…</span>}
                </div>
                <div className="flex items-center p-2 border-b space-x-2">
                    <Button variant="outline" size="sm" onClick={() => editor?.chain().focus().toggleHeading({ level: 1 }).run()}>H1</Button>
                    <Button variant="outline" size="sm" onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}>H2</Button>
                    <Button variant="outline" size="sm" onClick={() => editor?.chain().focus().toggleHeading({ level: 3 }).run()}>H3</Button>
                    <Button variant="outline" size="sm" onClick={() => editor?.chain().focus().toggleBold().run()}>B</Button>
                    <Button variant="outline" size="sm" onClick={() => editor?.chain().focus().toggleItalic().run()}>I</Button>
                </div>
                <div className="flex-1 overflow-auto p-4">
                    <EditorContent editor={editor} />
                </div>
            </div>
            <div className="flex-1 flex flex-col">
                <div className="p-2 border-b">
                    <span className="font-bold">Preview</span>
                </div>
                <div className="flex-1 overflow-auto">
                    {PreviewPane ? <PreviewPane sessionId={sessionId} templateId={templateId} /> : null}
                </div>
            </div>
        </div>
    );
}
