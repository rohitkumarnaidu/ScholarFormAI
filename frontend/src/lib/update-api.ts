"use client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface UpdateInfo {
  version: string;
  channel: string;
  published_at: string | null;
  release_notes_url: string | null;
  download_url: string | null;
  checksum: string | null;
  checksum_type: string;
  size: number;
  is_mandatory: boolean;
  is_security: boolean;
  changelog: string[] | null;
  signature?: string | null;
}

export interface UpdateCheckResult {
  status: "up-to-date" | "update-available" | "error";
  current_version: string;
  latest_version: string | null;
  update: UpdateInfo | null;
  check_mode: string;
  checked_at: string;
  error?: string;
}

export interface UpdateSettings {
  channel: string;
  auto_check: boolean;
  auto_download: boolean;
  auto_install: boolean;
  auto_restart: boolean;
  check_frequency_hours: number;
  notify_on_optional: boolean;
  notify_on_security: boolean;
  check_at_startup: boolean;
  background_download: boolean;
  proxy_url: string | null;
  github_token?: string | null;
  verify_signature: boolean;
  verify_checksum: boolean;
}

export interface VersionInfo {
  current_version: string;
  channel: string;
  auto_check: boolean;
  last_check: string | null;
  update_dir: string;
  history_count: number;
  build_hash?: string;
  arch?: string;
  platform?: string;
}

export interface ReleaseNotes {
  version: string;
  name: string | null;
  published_at: string | null;
  html_url: string | null;
  body: string | null;
  changelog: string[] | null;
  prerelease: boolean;
  author: string | null;
  found: boolean;
}

export interface Channel {
  id: string;
  name: string;
  description: string;
  recommended: boolean;
  stability_warning?: string | null;
}

export interface HistoryEntry {
  version: string;
  channel: string;
  installed_at: string;
  checksum: string;
  checksum_type: string;
  success: boolean;
  error_message: string | null;
  rolled_back: boolean;
  rollback_version: string | null;
}

export interface UpdateDownloadResponse {
  success: boolean;
  version?: string | null;
  path?: string | null;
  size?: number;
  checksum_valid?: boolean | null;
  signature_valid?: boolean | null;
  error?: string | null;
}

export interface UpdateInstallResponse {
  success: boolean;
  version?: string | null;
  previous_version?: string | null;
  backup_path?: string | null;
  error?: string | null;
}

export interface UpdateRollbackResponse {
  success: boolean;
  version?: string | null;
  previous_version?: string | null;
  error?: string | null;
}

export interface UpdateVerifyRequest {
  file_path: string;
  expected_checksum?: string | null;
  checksum_algo?: string;
  signature?: string | null;
  public_key?: string | null;
}

export interface UpdateVerifyResponse {
  valid: boolean;
  exists: boolean;
  checksum_valid: boolean;
  signature_valid: boolean;
  error?: string | null;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    let detail = body;
    try {
      const parsed = JSON.parse(body);
      detail = parsed.detail || (parsed.error && parsed.error.message) || parsed.message || body;
    } catch {
      // ignore
    }
    throw new Error(`API error ${res.status}: ${detail}`);
  }
  const json = await res.json();
  if (json && typeof json === "object" && "data" in json && "success" in json) {
    return json.data as T;
  }
  return json as T;
}

export async function checkForUpdates(channel?: string, mode: string = "manual"): Promise<UpdateCheckResult> {
  const params = new URLSearchParams();
  if (channel) params.append("channel", channel);
  if (mode) params.append("mode", mode);
  const queryString = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<UpdateCheckResult>(`/updates/check${queryString}`);
}

export async function checkForUpdatesPost(payload: { channel?: string; mode?: string; current_version?: string }): Promise<UpdateCheckResult> {
  return apiFetch<UpdateCheckResult>("/updates/check", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getVersionInfo(): Promise<VersionInfo> {
  return apiFetch<VersionInfo>("/updates/version");
}

export async function downloadUpdate(version?: string): Promise<UpdateDownloadResponse> {
  return apiFetch<UpdateDownloadResponse>("/updates/download", {
    method: "POST",
    body: JSON.stringify({ version }),
  });
}

export async function installUpdate(version?: string, source_path?: string): Promise<UpdateInstallResponse> {
  return apiFetch<UpdateInstallResponse>("/updates/install", {
    method: "POST",
    body: JSON.stringify({ version, source_path }),
  });
}

export async function verifyUpdateAsset(payload: UpdateVerifyRequest): Promise<UpdateVerifyResponse> {
  return apiFetch<UpdateVerifyResponse>("/updates/verify", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function rollbackUpdate(version?: string): Promise<UpdateRollbackResponse> {
  const params = version ? `?version=${encodeURIComponent(version)}` : "";
  return apiFetch<UpdateRollbackResponse>(`/updates/rollback${params}`, { method: "POST" });
}

export async function getUpdateHistory(limit?: number): Promise<{ history: HistoryEntry[] }> {
  const params = limit ? `?limit=${limit}` : "";
  return apiFetch<{ history: HistoryEntry[] }>(`/updates/history${params}`);
}

export async function getReleaseNotes(version?: string): Promise<ReleaseNotes> {
  const path = version ? `/updates/release-notes/${encodeURIComponent(version)}` : "/updates/release-notes";
  return apiFetch<ReleaseNotes>(path);
}

export async function getChannels(): Promise<{ channels: Channel[] }> {
  return apiFetch<{ channels: Channel[] }>("/updates/channels");
}

export async function getUpdateSettings(): Promise<UpdateSettings> {
  return apiFetch<UpdateSettings>("/updates/settings");
}

export async function updateSettings(settings: Partial<UpdateSettings>): Promise<UpdateSettings> {
  return apiFetch<UpdateSettings>("/updates/settings", {
    method: "PUT",
    body: JSON.stringify({ settings }),
  });
}
