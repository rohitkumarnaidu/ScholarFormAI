'use client';

import { useRef } from 'react';
import { FileText } from 'lucide-react';
import Button from '@/src/components/ui/Button';

interface ManuscriptInputProps {
  value: string;
  onChange: (value: string) => void;
}

export function ManuscriptInput({ value, onChange }: ManuscriptInputProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const wordCount = value ? value.split(/\s+/).filter(Boolean).length : 0;
  const charCount = value.length;

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      onChange(event.target?.result as string || '');
    };
    reader.readAsText(file);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
          Manuscript Content
        </label>
        <div className="flex items-center gap-4 text-xs text-slate-400">
          <span>{wordCount} words</span>
          <span>{charCount} characters</span>
        </div>
      </div>

      <div className="relative">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={`# Your Manuscript Title

Paste your manuscript here...

## Introduction
Start writing your paper using Markdown or plain text.

## Methods
Describe your research methodology.

## Results
Present your findings.

## Conclusion
Summarize your contributions.`}
          className="min-h-[400px] w-full resize-y rounded-xl border border-slate-300 bg-white p-4 font-mono text-sm leading-relaxed text-slate-800 placeholder-slate-400 focus:border-accent-500 focus:outline-none focus:ring-2 focus:ring-accent-500/20 dark:border-slate-600 dark:bg-primary-900 dark:text-slate-200 dark:placeholder-slate-500"
          spellCheck={false}
        />
      </div>

      <div className="flex items-center gap-3">
        <Button variant="outline" onClick={() => fileInputRef.current?.click()} className="text-slate-600 dark:text-slate-400">
          <FileText className="h-4 w-4 mr-2" />
          Upload .md / .tex / .txt
        </Button>
        <input ref={fileInputRef} type="file" accept=".md,.tex,.txt,.text" onChange={handleFileUpload} className="hidden" />
        <span className="text-xs text-slate-400">Supports Markdown, LaTeX, and plain text</span>
      </div>
    </div>
  );
}
