'use client';

interface PreviewPanelProps {
  html: string;
}

export function PreviewPanel({ html }: PreviewPanelProps) {
  if (!html) {
    return (
      <div className="flex min-h-[400px] items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 dark:border-slate-600 dark:bg-primary-900">
        <div className="text-center">
          <div className="text-4xl text-slate-300 dark:text-slate-600">&#128196;</div>
          <p className="mt-3 text-sm text-slate-400">
            Generate a preview to see your formatted manuscript
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-white">
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-2 dark:border-slate-700 dark:bg-slate-800">
        <span className="text-xs font-medium text-slate-500">Preview</span>
        <button
          onClick={() => window.print()}
          className="rounded px-2 py-1 text-xs text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700"
        >
          Print
        </button>
      </div>
      <div className="max-h-[600px] overflow-y-auto p-8">
        <div
          className="prose prose-sm max-w-none"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      </div>
    </div>
  );
}
