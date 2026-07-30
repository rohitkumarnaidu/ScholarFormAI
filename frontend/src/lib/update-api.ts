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

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json();
}

export async function checkForUpdates(channel?: string): Promise<UpdateCheckResult> {
  const params = channel ? `?channel=${channel}` : "";
  return apiFetch<UpdateCheckResult>(`/updates/check${params}`);
}

export async function getVersionInfo(): Promise<VersionInfo> {
  return apiFetch<VersionInfo>("/updates/version");
}

export async function downloadUpdate(version?: string): Promise<{ success: boolean; version?: string; path?: string; size?: number; checksum_valid?: boolean; error?: string }> {
  return apiFetch("/updates/download", {
    method: "POST",
    body: JSON.stringify({ version }),
  });
}

export async function installUpdate(): Promise<{ success: boolean; version?: string; previous_version?: string; backup_path?: string; error?: string }> {
  return apiFetch("/updates/install", { method: "POST" });
}

export async function rollbackUpdate(version?: string): Promise<{ success: boolean; version?: string; previous_version?: string; error?: string }> {
  const params = version ? `?version=${version}` : "";
  return apiFetch(`/updates/rollback${params}`, { method: "POST" });
}

export async function getUpdateHistory(limit?: number): Promise<{ history: HistoryEntry[] }> {
  const params = limit ? `?limit=${limit}` : "";
  return apiFetch(`/updates/history${params}`);
}

export async function getReleaseNotes(version: string): Promise<ReleaseNotes> {
  return apiFetch(`/updates/release-notes?version=${encodeURIComponent(version)}`);
}

export async function getChannels(): Promise<{ channels: Channel[] }> {
  return apiFetch("/updates/channels");
}

export async function getUpdateSettings(): Promise<UpdateSettings> {
  return apiFetch("/updates/settings");
}

export async function updateSettings(settings: Partial<UpdateSettings>): Promise<UpdateSettings> {
  return apiFetch("/updates/settings", {
    method: "PUT",
    body: JSON.stringify({ settings }),
  });
}
