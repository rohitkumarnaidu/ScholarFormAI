import { getV1, unwrapResponse } from '../services/api.v1';

export interface AdminApplication {
  id: string;
  name: string;
  description?: string;
  public_key?: string;
  created_at: string;
}

export interface AdminChannel {
  id: string;
  app_id: string;
  name: string;
  is_active: boolean;
  created_at: string;
}

export interface AdminRelease {
  id: string;
  app_id: string;
  channel_id: string;
  version: string;
  release_notes?: string;
  is_mandatory: boolean;
  is_security_update: boolean;
  published_at?: string;
  created_at: string;
}

export async function getAdminApplications(): Promise<AdminApplication[]> {
  const envelope = await getV1('/admin/updates/applications');
  return unwrapResponse(envelope) as AdminApplication[];
}

export async function getAdminReleases(appId?: string): Promise<AdminRelease[]> {
  const query = appId ? `?app_id=${encodeURIComponent(appId)}` : '';
  const envelope = await getV1(`/admin/updates/releases${query}`);
  return unwrapResponse(envelope) as AdminRelease[];
}
