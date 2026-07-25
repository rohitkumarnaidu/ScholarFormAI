export const STYLES = [
  { id: 'apa', name: 'APA 7th Edition', citation_format: 'Author-Year' },
  { id: 'mla', name: 'MLA 9th Edition', citation_format: 'Author-Page' },
  { id: 'chicago', name: 'Chicago 17th Edition', citation_format: 'Notes-Bibliography' },
  { id: 'ieee', name: 'IEEE', citation_format: 'Numbered' },
  { id: 'harvard', name: 'Harvard', citation_format: 'Author-Date' },
  { id: 'vancouver', name: 'Vancouver', citation_format: 'Numbered' },
  { id: 'turabian', name: 'Turabian 9th Edition', citation_format: 'Notes-Bibliography' },
  { id: 'acs', name: 'ACS', citation_format: 'Numbered' },
  { id: 'ama', name: 'AMA 11th Edition', citation_format: 'Numbered' },
] as const;

export const DEFAULT_OPTIONS = {
  output_format: 'docx' as const,
  page_size: 'A4' as const,
  font_family: 'Times New Roman',
  font_size: 12,
  line_spacing: 2.0,
  margins: { top: 1, bottom: 1, left: 1, right: 1 },
  include_page_numbers: true,
  include_running_header: true,
};

export const PAGE_SIZES = [
  { id: 'A4', label: 'A4 (210 × 297 mm)', width: 210, height: 297 },
  { id: 'Letter', label: 'Letter (8.5 × 11 in)', width: 215.9, height: 279.4 },
  { id: 'Legal', label: 'Legal (8.5 × 14 in)', width: 215.9, height: 355.6 },
] as const;

export const FONT_OPTIONS = [
  'Times New Roman',
  'Arial',
  'Calibri',
  'Georgia',
  'Palatino',
  'Garamond',
  'Helvetica',
] as const;
