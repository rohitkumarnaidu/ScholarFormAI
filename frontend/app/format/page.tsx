'use client';

import { useState } from 'react';
import { ArrowDownToLine, Eye, FileText, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { ManuscriptInput } from '@/components/ManuscriptInput';
import { FormattingOptions } from '@/components/FormattingOptions';
import { PreviewPanel } from '@/components/PreviewPanel';

export default function FormatPage() {
  const [manuscriptText, setManuscriptText] = useState('');
  const [style, setStyle] = useState('apa');
  const [formatting, setFormatting] = useState({
    pageSize: 'A4',
    fontFamily: 'Times New Roman',
    fontSize: 12,
    lineSpacing: 2.0,
    margins: { top: 1, bottom: 1, left: 1, right: 1 },
  });
  const [loading, setLoading] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');
  const [showPreview, setShowPreview] = useState(false);
  const [activeTab, setActiveTab] = useState<'input' | 'preview'>('input');

  const handleFormat = async () => {
    if (!manuscriptText.trim()) {
      toast.error('Please enter a manuscript to format');
      return;
    }

    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const response = await fetch(`${apiUrl}/api/v1/format/format`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          manuscript: { title: manuscriptText.split('\n')[0], sections: [{ heading: 'Content', level: 1, content: [{ text: manuscriptText }] }] },
          style_id: style,
          options: {
            page_size: formatting.pageSize,
            font_family: formatting.fontFamily,
            font_size: formatting.fontSize,
            line_spacing: formatting.lineSpacing,
            margins: formatting.margins,
          },
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Formatting failed');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `manuscript_${style}.docx`;
      a.click();
      window.URL.revokeObjectURL(url);

      toast.success('Manuscript formatted successfully');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Formatting failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = async () => {
    if (!manuscriptText.trim()) {
      toast.error('Please enter a manuscript to preview');
      return;
    }

    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const response = await fetch(`${apiUrl}/api/v1/format/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          manuscript: {
            title: manuscriptText.split('\n')[0],
            sections: [{ heading: 'Content', level: 1, content: [{ text: manuscriptText }] }],
          },
          style_id: style,
        }),
      });

      if (!response.ok) throw new Error('Preview failed');

      const data = await response.json();
      setPreviewHtml(data.html);
      setShowPreview(true);
      setActiveTab('preview');
      toast.success('Preview generated');
    } catch (err) {
      toast.error('Failed to generate preview');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto max-w-7xl px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-primary-800 dark:text-white">
          Format Manuscript
        </h1>
        <p className="mt-2 text-slate-600 dark:text-slate-400">
          Paste your manuscript text, select a style, and generate a formatted DOCX
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          <div className="flex items-center gap-4 border-b border-slate-200 dark:border-slate-700">
            <button
              onClick={() => setActiveTab('input')}
              className={`border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === 'input'
                  ? 'border-accent-500 text-accent-600 dark:text-accent-400'
                  : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
              }`}
            >
              <FileText className="mr-2 inline-block h-4 w-4" />
              Input
            </button>
            <button
              onClick={() => setActiveTab('preview')}
              disabled={!showPreview}
              className={`border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === 'preview'
                  ? 'border-accent-500 text-accent-600 dark:text-accent-400'
                  : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
              } ${!showPreview ? 'cursor-not-allowed opacity-50' : ''}`}
            >
              <Eye className="mr-2 inline-block h-4 w-4" />
              Preview
            </button>
          </div>

          {activeTab === 'input' ? (
            <ManuscriptInput value={manuscriptText} onChange={setManuscriptText} />
          ) : (
            <PreviewPanel html={previewHtml} />
          )}

          <div className="flex gap-3">
            <button
              onClick={handleFormat}
              disabled={loading || !manuscriptText.trim()}
              className="inline-flex items-center gap-2 rounded-lg bg-accent-500 px-6 py-2.5 text-sm font-semibold text-white transition-all hover:bg-accent-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ArrowDownToLine className="h-4 w-4" />
              )}
              {loading ? 'Formatting...' : 'Download DOCX'}
            </button>
            <button
              onClick={handlePreview}
              disabled={loading || !manuscriptText.trim()}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-6 py-2.5 text-sm font-semibold text-slate-700 transition-all hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <Eye className="h-4 w-4" />
              Preview
            </button>
          </div>
        </div>

        <div>
          <FormattingOptions
            style={style}
            onStyleChange={setStyle}
            options={formatting}
            onOptionsChange={setFormatting}
          />
        </div>
      </div>
    </div>
  );
}
