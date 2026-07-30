"use client";

import { useEffect, useState } from "react";
import {
  ArrowLeft, Download, RefreshCw, Save, RotateCcw,
  History, Shield, AlertTriangle, CheckCircle2,
  Lock, Server, Sliders, FileText, Check, X
} from "lucide-react";
import Link from "next/link";
import {
  checkForUpdates, getUpdateSettings, getUpdateHistory, getChannels,
  updateSettings, rollbackUpdate, getReleaseNotes, getVersionInfo,
  type UpdateSettings, type HistoryEntry, type Channel,
  type UpdateCheckResult, type ReleaseNotes, type VersionInfo
} from "@/lib/update-api";
import { DownloadProgressTracker } from "@/components/updates/DownloadProgressTracker";

export function UpdateSettingsContent() {
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null);
  const [settings, setSettings] = useState<UpdateSettings | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [checkResult, setCheckResult] = useState<UpdateCheckResult | null>(null);
  const [selectedReleaseNotes, setSelectedReleaseNotes] = useState<ReleaseNotes | null>(null);

  const [checking, setChecking] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showTrackerModal, setShowTrackerModal] = useState(false);
  const [rollbackTarget, setRollbackTarget] = useState<string | null>(null);
  const [rollingBack, setRollingBack] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const loadData = async () => {
    try {
      const [vInfo, uSettings, chRes, histRes] = await Promise.all([
        getVersionInfo().catch(() => null),
        getUpdateSettings().catch(() => null),
        getChannels().catch(() => ({ channels: [] })),
        getUpdateHistory(20).catch(() => ({ history: [] })),
      ]);

      if (vInfo) setVersionInfo(vInfo);
      if (uSettings) setSettings(uSettings);
      if (chRes.channels && chRes.channels.length > 0) {
        setChannels(chRes.channels);
      } else {
        // Fallback default channels
        setChannels([
          { id: "stable", name: "Stable", description: "Production-ready releases tested for enterprise stability.", recommended: true },
          { id: "beta", name: "Beta", description: "Preview upcoming features and improvements before public release.", recommended: false, stability_warning: "Beta releases may contain minor unverified features." },
          { id: "nightly", name: "Nightly", description: "Bleeding-edge daily builds directly from active development.", recommended: false, stability_warning: "Nightly builds are experimental and may contain breaking changes." },
          { id: "pre-release", name: "Pre-release", description: "Release candidates undergoing final compliance checks.", recommended: false, stability_warning: "Pre-release builds are feature complete but still under audit." },
        ]);
      }
      if (histRes.history) setHistory(histRes.history);
    } catch {
      setMessage({ type: "error", text: "Failed to connect to update service." });
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleManualCheck = async () => {
    setChecking(true);
    setMessage(null);
    try {
      const result = await checkForUpdates(settings?.channel);
      setCheckResult(result);
      if (result.status === "update-available" && result.latest_version) {
        const notes = await getReleaseNotes(result.latest_version).catch(() => null);
        if (notes) setSelectedReleaseNotes(notes);
      }
      await loadData();
    } catch (e: unknown) {
      setMessage({ type: "error", text: `Check failed: ${e instanceof Error ? e.message : "Unknown error"}` });
    } finally {
      setChecking(false);
    }
  };

  const handleSaveSettings = async () => {
    if (!settings) return;
    setSaving(true);
    setMessage(null);
    try {
      const updated = await updateSettings(settings);
      setSettings(updated);
      setMessage({ type: "success", text: "Update preferences saved successfully." });
    } catch (e: unknown) {
      setMessage({ type: "error", text: `Failed to save preferences: ${e instanceof Error ? e.message : "Unknown error"}` });
    } finally {
      setSaving(false);
    }
  };

  const handleConfirmRollback = async () => {
    if (!rollbackTarget && history.length === 0) return;
    setRollingBack(true);
    setMessage(null);
    try {
      const res = await rollbackUpdate(rollbackTarget || undefined);
      if (res.success) {
        setMessage({ type: "success", text: `Successfully rolled back to version v${res.version || rollbackTarget || "previous"}` });
        setRollbackTarget(null);
        await loadData();
      } else {
        setMessage({ type: "error", text: res.error || "Rollback failed." });
      }
    } catch (e: unknown) {
      setMessage({ type: "error", text: `Rollback error: ${e instanceof Error ? e.message : "Unknown error"}` });
    } finally {
      setRollingBack(false);
    }
  };

  const getStabilityWarning = (channelId: string) => {
    const ch = channels.find(c => c.id === channelId);
    if (ch?.stability_warning) return ch.stability_warning;
    if (channelId === "nightly") return "Nightly builds are experimental and updated daily. May contain breaking changes.";
    if (channelId === "beta") return "Beta channel features preview code that may be subject to change.";
    if (channelId === "pre-release") return "Pre-release builds are release candidates undergoing validation.";
    return null;
  };

  return (
    <div className="space-y-8">
      {/* Toast Notification Banner */}
      {message && (
        <div className={`p-4 rounded-xl border flex items-center justify-between text-xs font-semibold ${
          message.type === "success"
            ? "bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300"
            : "bg-red-50 dark:bg-red-950/40 border-red-200 dark:border-red-800 text-red-800 dark:text-red-300"
        }`}>
          <span>{message.text}</span>
          <button onClick={() => setMessage(null)} className="p-1 hover:opacity-75">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* 1. System Summary Card */}
      <section className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 rounded-xl bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400">
            <Server className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-gray-900 dark:text-white">System Information</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">Current version specifications and runtime directories</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-800">
            <span className="text-xs text-gray-500 dark:text-gray-400 block mb-1">Installed Version</span>
            <span className="font-mono text-base font-bold text-gray-900 dark:text-white">
              v{versionInfo?.current_version || "1.4.2"}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-800">
            <span className="text-xs text-gray-500 dark:text-gray-400 block mb-1">Release Channel</span>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300">
              {versionInfo?.channel || settings?.channel || "stable"}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-800">
            <span className="text-xs text-gray-500 dark:text-gray-400 block mb-1">Build Hash</span>
            <span className="font-mono text-xs font-semibold text-gray-700 dark:text-gray-300">
              {versionInfo?.build_hash || "a7f9c2d8e41"}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-800 truncate">
            <span className="text-xs text-gray-500 dark:text-gray-400 block mb-1">Update Directory</span>
            <span className="font-mono text-[11px] text-gray-600 dark:text-gray-400 truncate block" title={versionInfo?.update_dir}>
              {versionInfo?.update_dir || "./updates"}
            </span>
          </div>
        </div>
      </section>

      {/* 2. Channel Selection Control */}
      <section className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-purple-50 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400">
            <Sliders className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-gray-900 dark:text-white">Release Channel</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">Select release train for automated software updates</p>
          </div>
        </div>

        {/* Radio Grid / Segmented Control */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {["stable", "beta", "nightly", "pre-release"].map((chId) => {
            const channelObj = channels.find(c => c.id === chId) || {
              id: chId,
              name: chId.charAt(0).toUpperCase() + chId.slice(1),
              description: chId === "stable" ? "Recommended for enterprise stability." : `${chId} release channel.`,
              recommended: chId === "stable",
            };

            const isSelected = (settings?.channel || "stable") === chId;

            return (
              <label
                key={chId}
                className={`relative flex flex-col justify-between p-4 rounded-xl border cursor-pointer transition-all ${
                  isSelected
                    ? "bg-blue-50/60 dark:bg-blue-950/40 border-blue-500 ring-2 ring-blue-500/20"
                    : "bg-gray-50/50 dark:bg-gray-800/30 border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-sm text-gray-900 dark:text-white capitalize flex items-center gap-1.5">
                    {channelObj.name}
                    {channelObj.recommended && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 font-semibold">
                        Rec
                      </span>
                    )}
                  </span>
                  <input
                    type="radio"
                    name="update_channel"
                    value={chId}
                    checked={isSelected}
                    onChange={() => settings && setSettings({ ...settings, channel: chId })}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600"
                  />
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{channelObj.description}</p>
              </label>
            );
          })}
        </div>

        {/* Stability Warning Notice */}
        {settings?.channel && settings.channel !== "stable" && (
          <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-200 flex items-start gap-3 text-xs">
            <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">Stability Warning: {settings.channel.toUpperCase()} Channel Selected</p>
              <p className="mt-0.5">{getStabilityWarning(settings.channel)}</p>
            </div>
          </div>
        )}
      </section>

      {/* 3. Automation Toggles & Schedules */}
      <section className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 shadow-sm space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400">
            <RefreshCw className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-gray-900 dark:text-white">Automation & Schedules</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">Configure background update checks and automatic installation policy</p>
          </div>
        </div>

        {settings && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              {/* auto_check */}
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-gray-50 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-800">
                <div>
                  <p className="text-xs font-bold text-gray-900 dark:text-white">Auto-Check for Updates</p>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400">Periodically poll update service for releases</p>
                </div>
                <input
                  type="checkbox"
                  checked={settings.auto_check}
                  onChange={e => setSettings({ ...settings, auto_check: e.target.checked })}
                  className="h-5 w-5 rounded text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-700 cursor-pointer"
                />
              </div>

              {/* auto_download */}
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-gray-50 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-800">
                <div>
                  <p className="text-xs font-bold text-gray-900 dark:text-white">Auto-Download Packages</p>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400">Download verified packages in background</p>
                </div>
                <input
                  type="checkbox"
                  checked={settings.auto_download}
                  onChange={e => setSettings({ ...settings, auto_download: e.target.checked })}
                  className="h-5 w-5 rounded text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-700 cursor-pointer"
                />
              </div>

              {/* auto_install */}
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-gray-50 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-800">
                <div>
                  <p className="text-xs font-bold text-gray-900 dark:text-white">Auto-Install on Restart</p>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400">Apply pending updates during application restart</p>
                </div>
                <input
                  type="checkbox"
                  checked={settings.auto_install}
                  onChange={e => setSettings({ ...settings, auto_install: e.target.checked })}
                  className="h-5 w-5 rounded text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-700 cursor-pointer"
                />
              </div>
            </div>

            <div className="space-y-4">
              {/* check_at_startup */}
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-gray-50 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-800">
                <div>
                  <p className="text-xs font-bold text-gray-900 dark:text-white">Check at Startup</p>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400">Trigger update check whenever application starts</p>
                </div>
                <input
                  type="checkbox"
                  checked={settings.check_at_startup}
                  onChange={e => setSettings({ ...settings, check_at_startup: e.target.checked })}
                  className="h-5 w-5 rounded text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-700 cursor-pointer"
                />
              </div>

              {/* check_frequency_hours */}
              <div className="p-3.5 rounded-xl bg-gray-50 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-800">
                <label className="block text-xs font-bold text-gray-900 dark:text-white mb-1">
                  Check Frequency
                </label>
                <div className="flex items-center gap-3">
                  <select
                    value={settings.check_frequency_hours}
                    onChange={e => setSettings({ ...settings, check_frequency_hours: parseInt(e.target.value) || 24 })}
                    className="w-full rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-xs font-medium text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                  >
                    <option value={1}>Every 1 hour</option>
                    <option value={6}>Every 6 hours</option>
                    <option value={12}>Every 12 hours</option>
                    <option value={24}>Every 24 hours (Daily)</option>
                    <option value={168}>Every 7 days (Weekly)</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* 4. Security & Integrity Controls */}
      <section className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 shadow-sm space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
            <Lock className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-gray-900 dark:text-white">Security & Integrity Controls</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">Enforce cryptographic signature and checksum validation policies</p>
          </div>
        </div>

        {settings && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* verify_signature */}
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-gray-50 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-800">
                <div>
                  <p className="text-xs font-bold text-gray-900 dark:text-white flex items-center gap-1.5">
                    <Shield className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                    Require Digital Signature (ED25519)
                  </p>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400">Block unsigned or corrupted update packages</p>
                </div>
                <input
                  type="checkbox"
                  checked={settings.verify_signature}
                  onChange={e => setSettings({ ...settings, verify_signature: e.target.checked })}
                  className="h-5 w-5 rounded text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-700 cursor-pointer"
                />
              </div>

              {/* verify_checksum */}
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-gray-50 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-800">
                <div>
                  <p className="text-xs font-bold text-gray-900 dark:text-white flex items-center gap-1.5">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                    Require SHA-256 Checksum Validation
                  </p>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400">Verify file hash matches manifest before extraction</p>
                </div>
                <input
                  type="checkbox"
                  checked={settings.verify_checksum}
                  onChange={e => setSettings({ ...settings, verify_checksum: e.target.checked })}
                  className="h-5 w-5 rounded text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-700 cursor-pointer"
                />
              </div>
            </div>

            {/* proxy_url */}
            <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-800">
              <label className="block text-xs font-bold text-gray-900 dark:text-white mb-1">
                Enterprise Custom Update Proxy URL
              </label>
              <input
                type="text"
                value={settings.proxy_url || ""}
                onChange={e => setSettings({ ...settings, proxy_url: e.target.value || null })}
                placeholder="https://updates-proxy.internal.enterprise.org:8443"
                className="w-full rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-xs font-mono text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1">
                Optional custom HTTP/HTTPS proxy endpoint for restricted corporate networks.
              </p>
            </div>
          </div>
        )}

        {/* Save Settings Bar */}
        <div className="flex justify-end pt-2">
          <button
            onClick={handleSaveSettings}
            disabled={saving}
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md disabled:opacity-50 transition-colors"
          >
            <Save className={`h-4 w-4 ${saving ? "animate-spin" : ""}`} />
            {saving ? "Saving Preferences..." : "Save Preferences"}
          </button>
        </div>
      </section>

      {/* 5. Manual Update Check & Release Notes Viewer */}
      <section className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 shadow-sm space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">Manual Update & Release Notes</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">Check for available updates manually and inspect full release logs</p>
            </div>
          </div>

          <button
            onClick={handleManualCheck}
            disabled={checking}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${checking ? "animate-spin" : ""}`} />
            {checking ? "Checking..." : "Check for Updates Now"}
          </button>
        </div>

        {/* Check Result Banner */}
        {checkResult && (
          <div className={`p-4 rounded-xl border ${
            checkResult.status === "up-to-date"
              ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-900 dark:text-emerald-100"
              : checkResult.status === "update-available"
              ? "bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800 text-blue-900 dark:text-blue-100"
              : "bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800 text-red-900 dark:text-red-100"
          }`}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <h4 className="font-bold text-sm">
                  {checkResult.status === "up-to-date" && `ScholarFormAI is up to date (v${checkResult.current_version})`}
                  {checkResult.status === "update-available" && `New Version Available: v${checkResult.latest_version}`}
                  {checkResult.status === "error" && `Update Check Failed`}
                </h4>
                <p className="text-xs opacity-80 mt-0.5">
                  Checked at {new Date(checkResult.checked_at).toLocaleString()}
                </p>
              </div>

              {checkResult.status === "update-available" && (
                <button
                  onClick={() => setShowTrackerModal(true)}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-md transition-colors"
                >
                  Download & Install
                </button>
              )}
            </div>
          </div>
        )}

        {/* Release Notes Viewer */}
        {selectedReleaseNotes && (
          <div className="p-5 rounded-xl bg-gray-50 dark:bg-gray-800/40 border border-gray-200 dark:border-gray-800 space-y-4">
            <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 pb-3">
              <div>
                <h3 className="font-bold text-base text-gray-900 dark:text-white">
                  Release Notes — v{selectedReleaseNotes.version} {selectedReleaseNotes.name && `(${selectedReleaseNotes.name})`}
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  Published {selectedReleaseNotes.published_at ? new Date(selectedReleaseNotes.published_at).toLocaleDateString() : "recently"} by {selectedReleaseNotes.author || "ScholarFormAI Team"}
                </p>
              </div>
              {selectedReleaseNotes.html_url && (
                <a
                  href={selectedReleaseNotes.html_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                >
                  GitHub Release →
                </a>
              )}
            </div>

            {selectedReleaseNotes.changelog && (
              <div>
                <h4 className="text-xs font-bold text-gray-900 dark:text-white uppercase tracking-wider mb-2">Changelog</h4>
                <ul className="space-y-1.5 pl-4 list-disc text-xs text-gray-700 dark:text-gray-300">
                  {selectedReleaseNotes.changelog.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </div>
            )}

            {selectedReleaseNotes.body && (
              <div className="pt-2">
                <h4 className="text-xs font-bold text-gray-900 dark:text-white uppercase tracking-wider mb-1">Release Description</h4>
                <div className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-line font-mono bg-white dark:bg-gray-900 p-3 rounded-lg border border-gray-200 dark:border-gray-800 max-h-48 overflow-y-auto">
                  {selectedReleaseNotes.body}
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      {/* 6. Update History & Audit Log (with 1-Click Rollback) */}
      <section className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400">
              <History className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">Update History & Audit Log</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">Historical records of previous update deployments with rollback controls</p>
            </div>
          </div>
        </div>

        {history.length === 0 ? (
          <div className="p-6 text-center text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/40 rounded-xl">
            No update history recorded yet.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-800">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50 dark:bg-gray-800/60 text-gray-700 dark:text-gray-300 font-bold uppercase tracking-wider border-b border-gray-200 dark:border-gray-800">
                <tr>
                  <th className="p-3.5">Version</th>
                  <th className="p-3.5">Channel</th>
                  <th className="p-3.5">Installed Date</th>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5">Checksum (SHA-256)</th>
                  <th className="p-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {history.map((entry, idx) => (
                  <tr key={idx} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors">
                    <td className="p-3.5 font-bold font-mono text-gray-900 dark:text-white">
                      v{entry.version}
                    </td>
                    <td className="p-3.5">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
                        {entry.channel}
                      </span>
                    </td>
                    <td className="p-3.5 text-gray-600 dark:text-gray-400">
                      {new Date(entry.installed_at).toLocaleString()}
                    </td>
                    <td className="p-3.5">
                      {entry.rolled_back ? (
                        <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400 font-semibold">
                          <RotateCcw className="h-3.5 w-3.5" />
                          Rolled Back
                        </span>
                      ) : entry.success ? (
                        <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold">
                          <Check className="h-3.5 w-3.5" />
                          Success
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-red-600 dark:text-red-400 font-semibold">
                          <X className="h-3.5 w-3.5" />
                          Failed
                        </span>
                      )}
                    </td>
                    <td className="p-3.5 font-mono text-[11px] text-gray-500 dark:text-gray-400 truncate max-w-[120px]" title={entry.checksum}>
                      {entry.checksum ? `${entry.checksum.slice(0, 12)}...` : "—"}
                    </td>
                    <td className="p-3.5 text-right">
                      {!entry.rolled_back && entry.success && (
                        <button
                          onClick={() => setRollbackTarget(entry.version)}
                          className="inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-amber-100 dark:bg-amber-950/60 hover:bg-amber-200 dark:hover:bg-amber-900 text-amber-800 dark:text-amber-200 font-semibold text-[11px] transition-colors"
                        >
                          <RotateCcw className="h-3 w-3" />
                          Rollback
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Download Progress Tracker Modal */}
      {showTrackerModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-lg w-full">
            <DownloadProgressTracker
              version={checkResult?.latest_version || undefined}
              autoStart={true}
              onClose={() => setShowTrackerModal(false)}
            />
          </div>
        </div>
      )}

      {/* Rollback Confirmation Modal */}
      {rollbackTarget && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-md w-full rounded-2xl bg-white dark:bg-gray-900 p-6 border border-gray-200 dark:border-gray-800 shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-600 dark:text-amber-400">
                <AlertTriangle className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-gray-900 dark:text-white">Confirm System Rollback</h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">Target version: v{rollbackTarget}</p>
              </div>
            </div>

            <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">
              Are you sure you want to revert ScholarFormAI to <strong>v{rollbackTarget}</strong>?
              This will restore the previous application snapshot and may require restarting background services.
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setRollbackTarget(null)}
                disabled={rollingBack}
                className="px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-700 text-xs font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                Cancel
              </button>

              <button
                onClick={handleConfirmRollback}
                disabled={rollingBack}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs shadow-md disabled:opacity-50 transition-colors"
              >
                <RotateCcw className={`h-3.5 w-3.5 ${rollingBack ? "animate-spin" : ""}`} />
                {rollingBack ? "Rolling back..." : "Confirm Rollback"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function UpdateSettingsPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-800 pb-6">
          <div>
            <Link href="/" className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 mb-3 transition-colors">
              <ArrowLeft className="h-4 w-4" />
              Back to Home
            </Link>
            <h1 className="text-2xl font-extrabold text-gray-900 dark:text-white">Enterprise Update Management</h1>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Configure release channels, automated download schedules, security verification, and rollbacks.
            </p>
          </div>
        </div>

        {/* Content */}
        <UpdateSettingsContent />
      </div>
    </div>
  );
}
