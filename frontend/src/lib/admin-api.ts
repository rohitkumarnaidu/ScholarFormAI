
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

const API_BASE = "/api/v1/admin/updates";

export async function getAdminApplications(): Promise<AdminApplication[]> {
  const res = await fetch(`${API_BASE}/applications`);
  if (!res.ok) throw new Error("Failed to fetch applications");
  return res.json();
}

export async function getAdminReleases(appId?: string): Promise<AdminRelease[]> {
  const url = appId ? `${API_BASE}/releases?app_id=${appId}` : `${API_BASE}/releases`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch releases");
  return res.json();
}
