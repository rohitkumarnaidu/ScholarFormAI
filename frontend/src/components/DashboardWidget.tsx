"use client";

import { useEffect, useState } from "react";
import { RefreshCw, CheckCircle, AlertTriangle, Clock, Download, Package } from "lucide-react";
import { getVersionInfo, checkForUpdates, type VersionInfo, type UpdateCheckResult } from "@/lib/update-api";

export default function DashboardWidget() {
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null);
  const [checkResult, setCheckResult] = useState<UpdateCheckResult | null>(null);
  const [checking, setChecking] = useState(false);

  const load = async () => {
    try {
      const info = await getVersionInfo();
      setVersionInfo(info);
    } catch {
      // silent
    }
  };

  const handleCheck = async () => {
    setChecking(true);
    try {
      const result = await checkForUpdates();
      setCheckResult(result);
      await load();
    } catch {
      // silent
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => { load(); }, []);

  const hasUpdate = checkResult?.status === "update-available";
  const isLatest = checkResult?.status === "up-to-date";

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
          <Package className="h-4 w-4 text-blue-500" />
          Updates
        </h3>
        <button
          onClick={handleCheck}
          disabled={checking}
          className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
        >
          <RefreshCw className={`h-3 w-3 ${checking ? "animate-spin" : ""}`} />
          {checking ? "Checking..." : "Check"}
        </button>
      </div>

      {versionInfo && (
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-500">Current Version</span>
            <span className="font-medium text-slate-900">{versionInfo.current_version}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Channel</span>
            <span className="font-medium text-slate-900 capitalize">{versionInfo.channel}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Auto-Check</span>
            <span className={`font-medium ${versionInfo.auto_check ? "text-green-600" : "text-slate-400"}`}>
              {versionInfo.auto_check ? "Enabled" : "Disabled"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Last Check</span>
            <span className="text-slate-600">
              {versionInfo.last_check
                ? new Date(versionInfo.last_check).toLocaleDateString()
                : "Never"}
            </span>
          </div>
        </div>
      )}

      {hasUpdate && (
        <div className="mt-3 rounded-lg bg-blue-50 border border-blue-200 p-3 flex items-start gap-2">
          <Download className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
          <div>
            <p className="text-xs font-medium text-blue-900">
              v{checkResult?.latest_version} available
            </p>
            {checkResult?.update?.is_security && (
              <p className="text-xs text-red-600 mt-0.5">Security update</p>
            )}
            <a href="/settings" className="text-xs text-blue-600 hover:underline mt-1 inline-block">
              Update Now →
            </a>
          </div>
        </div>
      )}

      {isLatest && (
        <div className="mt-3 rounded-lg bg-green-50 border border-green-200 p-3 flex items-center gap-2">
          <CheckCircle className="h-4 w-4 text-green-500" />
          <span className="text-xs text-green-800">You have the latest version</span>
        </div>
      )}

      <a
        href="/settings"
        className="mt-4 block text-center text-xs text-slate-500 hover:text-slate-700 underline underline-offset-2"
      >
        Update Settings
      </a>
    </div>
  );
}
