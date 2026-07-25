const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Author {
  first_name: string;
  last_name: string;
  affiliation?: string;
  email?: string;
  orcid?: string;
}

interface Manuscript {
  title: string;
  authors?: Author[];
  abstract?: string;
  keywords?: string[];
  sections: {
    heading: string;
    level: number;
    content: { text: string; style?: string; alignment?: string }[];
  }[];
  references?: {
    authors?: Author[];
    year?: string;
    title: string;
    journal?: string;
  }[];
}

interface FormatResponse {
  download_url: string;
  preview_url?: string;
  pages: number;
  metadata: Record<string, unknown>;
  style_applied: string;
  formatted_at: string;
}

interface StyleInfo {
  id: string;
  name: string;
  version: string;
  description: string;
  citation_format: string;
  is_builtin: boolean;
}

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: response.statusText }));
    throw new ApiError(response.status, error.message || 'Request failed');
  }

  return response.json();
}

export async function formatManuscript(
  manuscript: Manuscript,
  styleId: string = 'apa',
  options?: Record<string, unknown>,
): Promise<FormatResponse> {
  return request<FormatResponse>('/api/v1/format', {
    method: 'POST',
    body: JSON.stringify({ manuscript, style_id: styleId, options }),
  });
}

export async function formatAndDownload(
  manuscript: Manuscript,
  styleId: string = 'apa',
  options?: Record<string, unknown>,
): Promise<Blob> {
  const url = `${API_BASE}/api/v1/format`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ manuscript, style_id: styleId, options }),
  });

  if (!response.ok) throw new ApiError(response.status, 'Download failed');
  return response.blob();
}

export async function validateManuscript(
  manuscript: Manuscript,
  styleId: string = 'apa',
): Promise<{ valid: boolean; errors: any[]; warnings: any[] }> {
  return request('/api/v1/validate', {
    method: 'POST',
    body: JSON.stringify({ manuscript, style_id: styleId }),
  });
}

export async function getStyles(): Promise<StyleInfo[]> {
  return request<StyleInfo[]>('/api/v1/styles');
}

export async function getStyle(styleId: string): Promise<StyleInfo> {
  return request<StyleInfo>(`/api/v1/styles/${styleId}`);
}

export async function getPreview(
  manuscript: Manuscript,
  styleId: string = 'apa',
): Promise<{ html: string; style_applied: string }> {
  return request('/api/v1/preview', {
    method: 'POST',
    body: JSON.stringify({ manuscript, style_id: styleId }),
  });
}
