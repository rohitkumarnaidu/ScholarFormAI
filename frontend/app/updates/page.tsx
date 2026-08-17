"use client";

import { useEffect, useState } from "react";
import {
  ArrowLeft, Download, RefreshCw, Save, RotateCcw,
  History, Radio, ChevronDown, Shield, Clock, AlertTriangle,
} from "lucide-react";
import Link from "next/link";
import {
  checkForUpdates, getUpdateSettings, getUpdateHistory, getChannels,
  updateSettings, downloadUpdate, installUpdate, rollbackUpdate,
  getReleaseNotes,
  type UpdateSettings, type HistoryEntry, type Channel,
  type UpdateCheckResult,
} from "@/lib/update-api";

type Tab = "check" | "settings" | "history" | "channels";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("check");
  const [settings, setSettings] = useState<UpdateSettings | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [checkResult, setCheckResult] = useState<UpdateCheckResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [installing, setInstalling] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    Promise.all([
      getUpdateSettings().then(setSettings),
      getChannels().then(c => setChannels(c.channels)),
      getUpdateHistory(10).then(h => setHistory(h.history)),
    ]).catch(() => setMessage({ type: "error", text: "Failed to load settings" }));
  }, []);

  const handleCheck = async () => {
    setChecking(true);
    setMessage(null);
    try {
      const result = await checkForUpdates();
      setCheckResult(result);
    } catch (e: unknown) {
      setMessage({ type: "error", text: `Check failed: ${e instanceof Error ? e.message : "Unknown error"}` });
    } finally {
      setChecking(false);
    }
  };

  const handleDownload = async () => {
    setDownloading(true);
    setMessage(null);
    try {
      const result = await downloadUpdate();
      if (result.success) {
        setMessage({ type: "success", text: `Downloaded v${result.version}` });
        const r = await installUpdate();
        if (r.success) {
          setMessage({ type: "success", text: `Installed v${r.version}. Please restart.` });
          setCheckResult(prev => prev ? { ...prev, status: "up-to-date", latest_version: prev.current_version } : prev);
          getUpdateHistory(10).then(h => setHistory(h.history));
        } else {
          setMessage({ type: "error", text: r.error || "Install failed" });
        }
      } else {
        setMessage({ type: "error", text: result.error || "Download failed" });
      }
    } catch (e: unknown) {
      setMessage({ type: "error", text: `Error: ${e instanceof Error ? e.message : "Unknown"}` });
    } finally {
      setDownloading(false);
    }
  };

  const handleRollback = async () => {
    setInstalling(true);
    setMessage(null);
    try {
      const result = await rollbackUpdate();
      if (result.success) {
        setMessage({ type: "success", text: `Rolled back to v${result.version}` });
        getUpdateHistory(10).then(h => setHistory(h.history));
      } else {
        setMessage({ type: "error", text: result.error || "Rollback failed" });
      }
    } catch (e: unknown) {
      setMessage({ type: "error", text: `Error: ${e instanceof Error ? e.message : "Unknown"}` });
    } finally {
      setInstalling(false);
    }
  };

  const handleSaveSettings = async () => {
    if (!settings) return;
    setSaving(true);
    setMessage(null);
    try {
      const updated = await updateSettings(settings);
      setSettings(updated);
      setMessage({ type: "success", text: "Settings saved" });
    } catch (e: unknown) {
      setMessage({ type: "error", text: `Failed to save: ${e instanceof Error ? e.message : "Unknown"}` });
    } finally {
      setSaving(false);
    }
  };

  const tabs: { id: Tab; label: string; icon: typeof Download }[] = [
    { id: "check", label: "Check Updates", icon: RefreshCw },
    { id: "settings", label: "Settings", icon: Radio },
    { id: "history", label: "History", icon: History },
    { id: "channels", label: "Channels", icon: ChevronDown },
  ];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <Link href="/" className="inline-flex items-center gap-1 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:text-slate-300 mb-4">
            <ArrowLeft className="h-4 w-4" />
            Back to Home
          </Link>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Update Settings</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Manage application updates, channels, and release history</p>
        </div>

        {/* Message */}
        {message && (
          <div className={`mb-4 rounded-lg border p-3 text-sm ${
            message.type === "success"
              ? "bg-green-50 border-green-200 text-green-800"
              : "bg-red-50 border-red-200 text-red-800"
          }`}>
            {message.text}
          </div>
        )}

        {/* Tabs */}
        <div className="flex border-b border-slate-200 dark:border-slate-700 mb-6">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "border-accent-500 text-accent-500"
                  : "border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:text-slate-300 hover:border-slate-200 dark:border-slate-700"
              }`}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === "check" && (
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Check for Updates</h2>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Check if a new version is available</p>
                </div>
                <button
                  onClick={handleCheck}
                  disabled={checking}
                  className="inline-flex items-center gap-2 rounded-lg bg-accent-500 px-4 py-2 text-sm font-medium text-white hover:bg-accent-400 disabled:opacity-50 transition-colors"
                >
                  <RefreshCw className={`h-4 w-4 ${checking ? "animate-spin" : ""}`} />
                  {checking ? "Checking..." : "Check Now"}
                </button>
              </div>

              {checkResult && (
                <div className={`rounded-lg border p-4 ${
                  checkResult.status === "up-to-date"
                    ? "bg-green-50 border-green-200"
                    : checkResult.status === "update-available"
                    ? "bg-accent-50 dark:bg-accent-500/10 border-blue-200"
                    : "bg-red-50 border-red-200"
                }`}>
                  <div className="flex items-start gap-3">
                    {checkResult.status === "up-to-date" ? (
                      <div className="rounded-full bg-green-100 p-1.5"><Download className="h-4 w-4 text-green-600" /></div>
                    ) : checkResult.status === "update-available" ? (
                      <div className="rounded-full bg-accent-100 dark:bg-accent-500/20 p-1.5"><AlertTriangle className="h-4 w-4 text-accent-500" /></div>
                    ) : (
                      <div className="rounded-full bg-red-100 p-1.5"><AlertTriangle className="h-4 w-4 text-red-600" /></div>
                    )}
                    <div className="flex-1">
                      <p className="font-medium text-slate-900 dark:text-slate-100">
                        {checkResult.status === "up-to-date" && `Up to date (v${checkResult.current_version})`}
                        {checkResult.status === "update-available" && `Update available: v${checkResult.latest_version}`}
                        {checkResult.status === "error" && "Check failed"}
                      </p>
                      <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                        {checkResult.error || `Checked at ${new Date(checkResult.checked_at).toLocaleString()}`}
                      </p>
                      {checkResult.update?.changelog && (
                        <ul className="mt-2 text-sm text-slate-600 dark:text-slate-400 list-disc list-inside space-y-0.5">
                          {checkResult.update.changelog.slice(0, 5).map((c, i) => <li key={i}>{c}</li>)}
                        </ul>
                      )}
                      {checkResult.status === "update-available" && (
                        <div className="mt-3 flex gap-2">
                          <button
                            onClick={handleDownload}
                            disabled={downloading}
                            className="inline-flex items-center gap-1 rounded-md bg-accent-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-400 disabled:opacity-50 transition-colors"
                          >
                            <Download className="h-3 w-3" />
                            {downloading ? "Downloading..." : "Download & Install"}
                          </button>
                          {checkResult.update?.release_notes_url && (
                            <a
                              href={checkResult.update.release_notes_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 rounded-md border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                            >
                              Release Notes
                            </a>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <button
                onClick={handleRollback}
                disabled={installing}
                className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-4 hover:shadow-md transition-shadow text-left disabled:opacity-50"
              >
                <div className="flex items-center gap-3">
                  <div className="rounded-full bg-amber-100 p-2">
                    <RotateCcw className="h-4 w-4 text-amber-600" />
                  </div>
                  <div>
                    <p className="font-medium text-slate-900 dark:text-slate-100 text-sm">Rollback Update</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Revert to previous version</p>
                  </div>
                </div>
              </button>
              <a
                href="https://github.com/amf/automated-manuscript-formatter/releases"
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-4 hover:shadow-md transition-shadow block"
              >
                <div className="flex items-center gap-3">
                  <div className="rounded-full bg-purple-100 p-2">
                    <Download className="h-4 w-4 text-purple-600" />
                  </div>
                  <div>
                    <p className="font-medium text-slate-900 dark:text-slate-100 text-sm">GitHub Releases</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">View all releases on GitHub</p>
                  </div>
                </div>
              </a>
            </div>
          </div>
        )}

        {activeTab === "settings" && settings && (
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-6">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">Update Preferences</h2>
            <div className="space-y-4">
              {/* Channel */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Release Channel</label>
                <select
                  value={settings.channel}
                  onChange={e => setSettings({ ...settings, channel: e.target.value })}
                  className="w-full rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm"
                >
                  {channels.map(c => (
                    <option key={c.id} value={c.id}>{c.name} {c.recommended ? "(Recommended)" : ""}</option>
                  ))}
                </select>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{channels.find(c => c.id === settings.channel)?.description}</p>
              </div>

              {/* Toggles */}
              {([
                ["auto_check", "Auto Check", "Automatically check for updates"],
                ["auto_download", "Auto Download", "Automatically download available updates"],
                ["auto_install", "Auto Install", "Automatically install downloaded updates"],
                ["auto_restart", "Auto Restart", "Automatically restart after installation"],
                ["notify_on_optional", "Notify Optional", "Notify about optional updates"],
                ["notify_on_security", "Notify Security", "Notify about security updates"],
                ["check_at_startup", "Check at Startup", "Check for updates on application startup"],
                ["background_download", "Background Download", "Download updates in background"],
                ["verify_signature", "Verify Signature", "Verify digital signatures before installing"],
                ["verify_checksum", "Verify Checksum", "Verify file checksums before installing"],
              ] as const).map(([key, label, desc]) => (
                <div key={key} className="flex items-center justify-between py-2">
                  <div>
                    <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{label}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{desc}</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={(settings as unknown as Record<string, boolean>)[key]}
                      onChange={e => setSettings({ ...settings, [key]: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-slate-200 rounded-full peer peer-checked:bg-accent-500 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all" />
                  </label>
                </div>
              ))}

              {/* Frequency */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Check Frequency (hours)
                </label>
                <input
                  type="number"
                  min={1}
                  max={720}
                  value={settings.check_frequency_hours}
                  onChange={e => setSettings({ ...settings, check_frequency_hours: parseInt(e.target.value) || 24 })}
                  className="w-24 rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm"
                />
              </div>

              {/* Proxy */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Proxy URL (optional)</label>
                <input
                  type="text"
                  value={settings.proxy_url || ""}
                  onChange={e => setSettings({ ...settings, proxy_url: e.target.value || null })}
                  placeholder="http://proxy:8080"
                  className="w-full rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm"
                />
              </div>

              <button
                onClick={handleSaveSettings}
                disabled={saving}
                className="inline-flex items-center gap-2 rounded-lg bg-accent-500 px-4 py-2 text-sm font-medium text-white hover:bg-accent-400 disabled:opacity-50 transition-colors"
              >
                <Save className={`h-4 w-4 ${saving ? "animate-spin" : ""}`} />
                {saving ? "Saving..." : "Save Settings"}
              </button>
            </div>
          </div>
        )}

        {activeTab === "history" && (
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-6">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">Update History</h2>
            {history.length === 0 ? (
              <p className="text-sm text-slate-500 dark:text-slate-400">No update history yet.</p>
            ) : (
              <div className="space-y-3">
                {history.map((entry, i) => (
                  <div key={i} className={`rounded-lg border p-3 ${
                    entry.success ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"
                  }`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                          entry.success ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
                        }`}>
                          v{entry.version}
                        </span>
                        <span className="text-xs text-slate-500 dark:text-slate-400 capitalize">{entry.channel}</span>
                      </div>
                      <span className="text-xs text-slate-500 dark:text-slate-400">
                        {new Date(entry.installed_at).toLocaleString()}
                      </span>
                    </div>
                    {entry.error_message && (
                      <p className="text-xs text-red-600 mt-1">{entry.error_message}</p>
                    )}
                    {entry.rolled_back && (
                      <p className="text-xs text-amber-600 mt-1">
                        Rolled back to v{entry.rollback_version}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "channels" && (
          <div className="space-y-4">
            {channels.map((channel, i) => (
              <div key={i} className={`rounded-xl border p-5 ${
                channel.recommended ? "border-blue-200 bg-accent-50 dark:bg-accent-500/10" : "border-slate-200 dark:border-slate-700 bg-white"
              }`}>
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-slate-900 dark:text-slate-100 capitalize">
                      {channel.name}
                      {channel.recommended && (
                        <span className="ml-2 inline-flex items-center rounded-full bg-accent-100 dark:bg-accent-500/20 px-2 py-0.5 text-xs font-medium text-blue-800">
                          Recommended
                        </span>
                      )}
                    </h3>
                    <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">{channel.description}</p>
                  </div>
                  {settings?.channel === channel.id && (
                    <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                      Active
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
