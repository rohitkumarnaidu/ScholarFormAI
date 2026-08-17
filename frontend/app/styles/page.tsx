'use client';

import { useEffect, useState } from 'react';
import { BookOpen, Check, ExternalLink } from 'lucide-react';

interface StyleInfo {
  id: string;
  name: string;
  version: string;
  description: string;
  citation_format: string;
  is_builtin: boolean;
}

const fallbackStyles: StyleInfo[] = [
  { id: 'apa', name: 'APA 7th Edition', version: '7.0', description: 'American Psychological Association — social sciences, education, psychology', citation_format: 'apa', is_builtin: true },
  { id: 'mla', name: 'MLA 9th Edition', version: '9.0', description: 'Modern Language Association — humanities, literature, arts', citation_format: 'mla', is_builtin: true },
  { id: 'chicago', name: 'Chicago 17th Edition', version: '17.0', description: 'Chicago Manual of Style — history, arts, humanities', citation_format: 'chicago', is_builtin: true },
  { id: 'ieee', name: 'IEEE', version: '2023', description: 'Institute of Electrical and Electronics Engineers — engineering, CS, technology', citation_format: 'ieee', is_builtin: true },
  { id: 'harvard', name: 'Harvard', version: '2023', description: 'Harvard referencing — UK/Australian universities, multi-discipline', citation_format: 'harvard', is_builtin: true },
  { id: 'vancouver', name: 'Vancouver', version: '2023', description: 'Vancouver style — biomedical and health sciences', citation_format: 'vancouver', is_builtin: true },
  { id: 'turabian', name: 'Turabian 9th Ed.', version: '9.0', description: 'Turabian — student research papers, theses, dissertations', citation_format: 'chicago', is_builtin: true },
  { id: 'acs', name: 'ACS', version: '2023', description: 'American Chemical Society — chemistry and related sciences', citation_format: 'acs', is_builtin: true },
  { id: 'ama', name: 'AMA 11th Ed.', version: '11.0', description: 'American Medical Association — medical research, health sciences', citation_format: 'ama', is_builtin: true },
];

export default function StylesPage() {
  const [styles, setStyles] = useState<StyleInfo[]>(fallbackStyles);
  const [selectedStyle, setSelectedStyle] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/v1/styles')
      .then((res) => res.json())
      .then((data) => { if (Array.isArray(data)) setStyles(data); })
      .catch(() => {});
  }, []);

  const selected = styles.find((s) => s.id === selectedStyle);

  return (
    <div className="container mx-auto max-w-6xl px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-primary-800 dark:text-white">
          Citation Styles
        </h1>
        <p className="mt-2 text-slate-600 dark:text-slate-400">
          ScholarForm AI supports {styles.length} major academic citation styles
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {styles.map((style) => (
          <button
            key={style.id}
            onClick={() => setSelectedStyle(style.id === selectedStyle ? null : style.id)}
            className={`group relative rounded-xl border p-5 text-left transition-all ${
              selectedStyle === style.id
                ? 'border-accent-500 bg-accent-50 shadow-md dark:bg-accent-900/20'
                : 'border-slate-200 bg-white hover:border-accent-300 hover:shadow-sm dark:border-slate-700 dark:bg-primary-900'
            }`}
          >
            {selectedStyle === style.id && (
              <div className="absolute right-3 top-3 text-accent-500">
                <Check className="h-5 w-5" />
              </div>
            )}
            <div className="mb-3 inline-flex rounded-lg bg-primary-50 p-2.5 text-primary-600 dark:bg-primary-800 dark:text-primary-300">
              <BookOpen className="h-5 w-5" />
            </div>
            <h3 className="font-semibold text-primary-800 dark:text-white">
              {style.name}
            </h3>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              v{style.version} &middot; {style.citation_format.toUpperCase()}
            </p>
          </button>
        ))}
      </div>

      {selected && (
        <div className="mt-8 rounded-xl border border-accent-200 bg-accent-50 p-6 dark:border-accent-800 dark:bg-accent-900/20">
          <h2 className="text-xl font-bold text-primary-800 dark:text-white">
            {selected.name}
          </h2>
          <p className="mt-2 text-slate-600 dark:text-slate-400">
            {selected.description}
          </p>
          <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div className="rounded-lg bg-white p-3 dark:bg-primary-800">
              <span className="text-slate-500">Style ID</span>
              <p className="font-mono font-medium text-primary-700 dark:text-white">
                {selected.id}
              </p>
            </div>
            <div className="rounded-lg bg-white p-3 dark:bg-primary-800">
              <span className="text-slate-500">Citation Format</span>
              <p className="font-medium text-primary-700 dark:text-white">
                {selected.citation_format.toUpperCase()}
              </p>
            </div>
            <div className="rounded-lg bg-white p-3 dark:bg-primary-800">
              <span className="text-slate-500">Version</span>
              <p className="font-medium text-primary-700 dark:text-white">
                {selected.version}
              </p>
            </div>
            <div className="rounded-lg bg-white p-3 dark:bg-primary-800">
              <span className="text-slate-500">Type</span>
              <p className="font-medium text-primary-700 dark:text-white">
                {selected.is_builtin ? 'Built-in' : 'Custom'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
