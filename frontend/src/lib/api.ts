/**
 * Unified API Client for ScholarForm AI
 * Replaces 19 legacy untyped JS service modules.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface User {
  id: string;
  email: string;
  name: string;
}

export interface DocumentInfo {
  id: string;
  filename: string;
  template: string;
  status: string;
  progress: number;
  current_stage?: string;
  error_message?: string;
  created_at: string;
  updated_at?: string;
}

export interface ListDocumentsResponse {
  documents: DocumentInfo[];
  total: number;
  limit: number;
  offset: number;
}

export interface UploadResponse {
  message: string;
  job_id: string;
  status: string;
}

export interface StatusResponse {
  job_id: string;
  status: string;
  current_phase: string;
  progress_percentage: number;
  message: string;
  updated_at?: string;
  phases: any[];
  quality?: any;
}

export class ApiClient {
  private static async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = localStorage.getItem('access_token');
    const headers = new Headers(options.headers || {});
    
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    const config: RequestInit = {
      ...options,
      headers,
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw new Error(errorData?.detail || `API Error: ${response.status} ${response.statusText}`);
    }

    // Some endpoints (like download) return blobs
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return response.json();
    }
    
    return response.blob() as unknown as T;
  }

  // --- Auth & Users ---
  static async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  // --- Documents ---
  static async listDocuments(params?: { status?: string; limit?: number; offset?: number }): Promise<ListDocumentsResponse> {
    const qs = new URLSearchParams();
    if (params?.status) qs.append('status', params.status);
    if (params?.limit) qs.append('limit', params.limit.toString());
    if (params?.offset) qs.append('offset', params.offset.toString());
    
    return this.request<ListDocumentsResponse>(`/documents?${qs.toString()}`);
  }

  static async uploadDocument(file: File, options: Record<string, any> = {}): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    Object.entries(options).forEach(([key, value]) => {
      formData.append(key, value.toString());
    });

    return this.request<UploadResponse>('/documents/upload', {
      method: 'POST',
      body: formData,
    });
  }

  static async getStatus(jobId: string): Promise<StatusResponse> {
    return this.request<StatusResponse>(`/documents/${jobId}/status`);
  }

  static async getPreview(jobId: string): Promise<{ html: string; style_applied: string }> {
    return this.request<{ html: string; style_applied: string }>(`/documents/${jobId}/preview`);
  }

  static async deleteDocument(jobId: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>(`/documents/${jobId}`, {
      method: 'DELETE',
    });
  }
}

export default ApiClient;
