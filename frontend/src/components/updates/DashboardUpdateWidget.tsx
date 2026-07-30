"use client";

import { useEffect, useState } from "react";
import { RefreshCw, CheckCircle2, Download, Package, Settings, ExternalLink } from "lucide-react";
import Link from "next/link";
import { getVersionInfo, checkForUpdates, type VersionInfo, type UpdateCheckResult } from "@/lib/update-api";
import { DownloadProgressTracker } from "./DownloadProgressTracker";

export function DashboardUpdateWidget() {
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null);
  const [checkResult, setCheckResult] = useState<UpdateCheckResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [showProgressTracker, setShowProgressTracker] = useState(false);

  const loadVersionInfo = async () => {
    try {
      const info = await getVersionInfo();
      setVersionInfo(info);
    } catch {
      // Fallback version info if offline
      setVersionInfo({
        current_version: "1.4.2",
        channel: "stable",
        auto_check: true,
        last_check: new Date().toISOString(),
        update_dir: "./updates",
        history_count: 0,
      });
    }
  };

  const handleCheck = async () => {
    setChecking(true);
    try {
      const result = await checkForUpdates();
      setCheckResult(result);
      await loadVersionInfo();
    } catch {
      // Silent error handling
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    loadVersionInfo();
  }, []);

  const hasUpdate = checkResult?.status === "update-available";
  const isUpToDate = checkResult?.status === "up-to-date";

  const getChannelBadgeClass = (channel?: string) => {
    switch (channel?.toLowerCase()) {
      case "stable":
        return "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800";
      case "beta":
        return "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 border-amber-200 dark:border-amber-800";
      case "nightly":
      case "pre-release":
        return "bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300 border-purple-200 dark:border-purple-800";
      default:
        return "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300 border-blue-200 dark:border-blue-800";
    }
  };

  return (
    <>
      <div className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 shadow-sm space-y-4">
        {/* Widget Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400">
              <Package className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-gray-900 dark:text-white">System Updates</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">Update channel & status</p>
            </div>
          </div>

          <button
            onClick={handleCheck}
            disabled={checking}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${checking ? "animate-spin" : ""}`} />
            {checking ? "Checking..." : "Check for Updates"}
          </button>
        </div>

        {/* Info Grid */}
        {versionInfo ? (
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800">
              <span className="text-gray-500 dark:text-gray-400 block mb-1">Installed Version</span>
              <span className="font-mono font-bold text-gray-900 dark:text-white text-sm">
                v{versionInfo.current_version}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800">
              <span className="text-gray-500 dark:text-gray-400 block mb-1">Release Channel</span>
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border uppercase ${getChannelBadgeClass(versionInfo.channel)}`}>
                {versionInfo.channel}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800">
              <span className="text-gray-500 dark:text-gray-400 block mb-1">Auto-Check</span>
              <span className={`font-semibold ${versionInfo.auto_check ? "text-emerald-600 dark:text-emerald-400" : "text-gray-400"}`}>
                {versionInfo.auto_check ? "Enabled" : "Disabled"}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800">
              <span className="text-gray-500 dark:text-gray-400 block mb-1">Last Checked</span>
              <span className="text-gray-700 dark:text-gray-300 font-medium">
                {versionInfo.last_check ? new Date(versionInfo.last_check).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "Recently"}
              </span>
            </div>
          </div>
        ) : (
          <div className="p-4 text-center text-xs text-gray-400 animate-pulse">
            Loading update details...
          </div>
        )}

        {/* Update Available Alert Box */}
        {hasUpdate && checkResult?.update && (
          <div className="p-3.5 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 flex items-start justify-between gap-3">
            <div className="flex items-start gap-2.5">
              <Download className="h-4 w-4 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-bold text-blue-950 dark:text-blue-100">
                  Update v{checkResult.latest_version} Available
                </p>
                <p className="text-[11px] text-blue-700 dark:text-blue-300 mt-0.5">
                  {checkResult.update.is_security ? "Security patch update" : "New features & improvements"}
                </p>
              </div>
            </div>

            <button
              onClick={() => setShowProgressTracker(true)}
              className="px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium shrink-0 transition-colors"
            >
              Update
            </button>
          </div>
        )}

        {/* Up to Date Box */}
        {isUpToDate && (
          <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 flex items-center gap-2.5 text-xs text-emerald-800 dark:text-emerald-300 font-medium">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            <span>ScholarFormAI is up to date</span>
          </div>
        )}

        {/* Footer Link to Settings */}
        <div className="pt-2 border-t border-gray-100 dark:border-gray-800 flex justify-between items-center">
          <Link
            href="/settings/updates"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors"
          >
            <Settings className="h-3.5 w-3.5" />
            Manage Updates
          </Link>
          <Link
            href="/settings/updates"
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
            aria-label="Open settings page"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>

      {/* Download Progress Tracker Modal */}
      {showProgressTracker && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-lg w-full">
            <DownloadProgressTracker
              version={checkResult?.latest_version || undefined}
              autoStart={true}
              onClose={() => setShowProgressTracker(false)}
            />
          </div>
        </div>
      )}
    </>
  );
}

export default DashboardUpdateWidget;
