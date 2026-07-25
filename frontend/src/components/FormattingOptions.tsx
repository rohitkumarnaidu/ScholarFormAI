'use client';

interface FormattingOptionsProps {
  style: string;
  onStyleChange: (style: string) => void;
  options: {
    pageSize: string;
    fontFamily: string;
    fontSize: number;
    lineSpacing: number;
    margins: { top: number; bottom: number; left: number; right: number };
  };
  onOptionsChange: (options: any) => void;
}

const styles = [
  { id: 'apa', label: 'APA 7th Edition' },
  { id: 'mla', label: 'MLA 9th Edition' },
  { id: 'chicago', label: 'Chicago 17th Edition' },
  { id: 'ieee', label: 'IEEE' },
  { id: 'harvard', label: 'Harvard' },
  { id: 'vancouver', label: 'Vancouver' },
  { id: 'turabian', label: 'Turabian' },
  { id: 'acs', label: 'ACS' },
  { id: 'ama', label: 'AMA 11th Edition' },
];

export function FormattingOptions({
  style,
  onStyleChange,
  options,
  onOptionsChange,
}: FormattingOptionsProps) {
  const update = (key: string, value: any) => {
    onOptionsChange({ ...options, [key]: value });
  };

  const updateMargins = (side: string, value: number) => {
    onOptionsChange({
      ...options,
      margins: { ...options.margins, [side]: value },
    });
  };

  return (
    <div className="space-y-6 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-primary-900">
      <h3 className="font-semibold text-primary-800 dark:text-white">Formatting Options</h3>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
          Citation Style
        </label>
        <select
          value={style}
          onChange={(e) => onStyleChange(e.target.value)}
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 focus:border-accent-500 focus:outline-none focus:ring-2 focus:ring-accent-500/20 dark:border-slate-600 dark:bg-primary-800 dark:text-slate-200"
        >
          {styles.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
          Page Size
        </label>
        <select
          value={options.pageSize}
          onChange={(e) => update('pageSize', e.target.value)}
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 focus:border-accent-500 focus:outline-none focus:ring-2 focus:ring-accent-500/20 dark:border-slate-600 dark:bg-primary-800 dark:text-slate-200"
        >
          <option value="A4">A4</option>
          <option value="Letter">Letter</option>
          <option value="Legal">Legal</option>
        </select>
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
          Font Family
        </label>
        <select
          value={options.fontFamily}
          onChange={(e) => update('fontFamily', e.target.value)}
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 focus:border-accent-500 focus:outline-none focus:ring-2 focus:ring-accent-500/20 dark:border-slate-600 dark:bg-primary-800 dark:text-slate-200"
        >
          <option value="Times New Roman">Times New Roman</option>
          <option value="Arial">Arial</option>
          <option value="Calibri">Calibri</option>
          <option value="Georgia">Georgia</option>
          <option value="Palatino">Palatino</option>
        </select>
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
          Font Size: {options.fontSize}pt
        </label>
        <input
          type="range"
          min={10}
          max={14}
          step={1}
          value={options.fontSize}
          onChange={(e) => update('fontSize', parseInt(e.target.value))}
          className="w-full accent-accent-500"
        />
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
          Line Spacing: {options.lineSpacing.toFixed(1)}
        </label>
        <input
          type="range"
          min={1.0}
          max={2.5}
          step={0.25}
          value={options.lineSpacing}
          onChange={(e) => update('lineSpacing', parseFloat(e.target.value))}
          className="w-full accent-accent-500"
        />
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
          Margins (inches)
        </label>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-slate-400">Top</label>
            <input
              type="number"
              min={0.5}
              max={2}
              step={0.25}
              value={options.margins.top}
              onChange={(e) => updateMargins('top', parseFloat(e.target.value))}
              className="w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-700 focus:border-accent-500 focus:outline-none dark:border-slate-600 dark:bg-primary-800 dark:text-slate-200"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400">Bottom</label>
            <input
              type="number"
              min={0.5}
              max={2}
              step={0.25}
              value={options.margins.bottom}
              onChange={(e) => updateMargins('bottom', parseFloat(e.target.value))}
              className="w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-700 focus:border-accent-500 focus:outline-none dark:border-slate-600 dark:bg-primary-800 dark:text-slate-200"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400">Left</label>
            <input
              type="number"
              min={0.5}
              max={2}
              step={0.25}
              value={options.margins.left}
              onChange={(e) => updateMargins('left', parseFloat(e.target.value))}
              className="w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-700 focus:border-accent-500 focus:outline-none dark:border-slate-600 dark:bg-primary-800 dark:text-slate-200"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400">Right</label>
            <input
              type="number"
              min={0.5}
              max={2}
              step={0.25}
              value={options.margins.right}
              onChange={(e) => updateMargins('right', parseFloat(e.target.value))}
              className="w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-700 focus:border-accent-500 focus:outline-none dark:border-slate-600 dark:bg-primary-800 dark:text-slate-200"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
