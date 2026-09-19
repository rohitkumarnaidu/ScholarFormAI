'use client';

import { useState } from 'react';
import { ArrowDownToLine, Eye, FileText, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useMutation } from '@tanstack/react-query';
import { ManuscriptInput } from '@/components/ManuscriptInput';
import { FormattingOptions } from '@/components/FormattingOptions';
import { PreviewPanel } from '@/components/PreviewPanel';
import { formatManuscript, previewManuscript } from '@/services/api.format';
import Button from '@/components/ui/Button';

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
  const [previewHtml, setPreviewHtml] = useState('');
  const [showPreview, setShowPreview] = useState(false);
  const [activeTab, setActiveTab] = useState<'input' | 'preview'>('input');

  const formatMutation = useMutation({
    mutationFn: async () => {
      if (!manuscriptText.trim()) throw new Error('Please enter a manuscript to format');
      return formatManuscript({
        manuscript: { title: manuscriptText.split('\n')[0], sections: [{ heading: 'Content', level: 1, content: [{ text: manuscriptText }] }] },
        style_id: style,
        options: {
          page_size: formatting.pageSize,
          font_family: formatting.fontFamily,
          font_size: formatting.fontSize,
          line_spacing: formatting.lineSpacing,
          margins: formatting.margins,
        },
      });
    },
    onSuccess: (blob) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `manuscript_${style}.docx`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('Manuscript formatted successfully');
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Formatting failed');
    }
  });

  const previewMutation = useMutation({
    mutationFn: async () => {
      if (!manuscriptText.trim()) throw new Error('Please enter a manuscript to preview');
      return previewManuscript({
        manuscript: { title: manuscriptText.split('\n')[0], sections: [{ heading: 'Content', level: 1, content: [{ text: manuscriptText }] }] },
        style_id: style,
      });
    },
    onSuccess: (data) => {
      setPreviewHtml(data.html || (data as any).data?.html);
      setShowPreview(true);
      setActiveTab('preview');
      toast.success('Preview generated');
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Failed to generate preview');
    }
  });

  const handleFormat = () => formatMutation.mutate();
  const handlePreview = () => previewMutation.mutate();
  const isAnyLoading = formatMutation.isPending || previewMutation.isPending;

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
          <div role="tablist" className="flex items-center gap-4 border-b border-slate-200 dark:border-slate-700">
            <button
              role="tab"
              aria-selected={activeTab === 'input'}
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
              role="tab"
              aria-selected={activeTab === 'preview'}
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
            <Button
              onClick={handleFormat}
              disabled={isAnyLoading || !manuscriptText.trim()}
              loading={formatMutation.isPending}
              variant="primary"
              className="px-6 py-2.5 text-sm"
            >
              {!formatMutation.isPending && <ArrowDownToLine className="h-4 w-4" />}
              {formatMutation.isPending ? 'Formatting...' : 'Download DOCX'}
            </Button>
            <Button
              onClick={handlePreview}
              disabled={isAnyLoading || !manuscriptText.trim()}
              loading={previewMutation.isPending}
              variant="secondary"
              className="px-6 py-2.5 text-sm"
            >
              {!previewMutation.isPending && <Eye className="h-4 w-4" />}
              {previewMutation.isPending ? 'Previewing...' : 'Preview'}
            </Button>
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
