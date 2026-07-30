"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Download, X, RefreshCw, Shield } from "lucide-react";
import { checkForUpdates, getVersionInfo, type UpdateCheckResult, type VersionInfo } from "@/lib/update-api";

export default function UpdateBanner() {
  const [checkResult, setCheckResult] = useState<UpdateCheckResult | null>(null);
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const check = async () => {
      try {
        const [result, info] = await Promise.all([
          checkForUpdates(),
          getVersionInfo(),
        ]);
        setCheckResult(result);
        setVersionInfo(info);
      } catch {
        // Silent fail — banner just won't show
      } finally {
        setLoading(false);
      }
    };
    check();
    // Check every hour
    const interval = setInterval(check, 3600000);
    return () => clearInterval(interval);
  }, []);

  if (loading || dismissed) return null;
  if (!checkResult || checkResult.status !== "update-available") return null;

  const update = checkResult.update;

  return (
    <div className={`fixed bottom-4 right-4 z-50 max-w-md rounded-lg shadow-2xl border ${
      update?.is_security ? "border-red-500 bg-red-50" : update?.is_mandatory ? "border-amber-500 bg-amber-50" : "border-blue-500 bg-white"
    } p-4`}>
      <button
        onClick={() => setDismissed(true)}
        className="absolute top-2 right-2 text-gray-400 hover:text-gray-600"
        aria-label="Dismiss"
      >
        <X className="h-4 w-4" />
      </button>

      <div className="flex items-start gap-3">
        <div className={`mt-0.5 rounded-full p-1.5 ${
          update?.is_security ? "bg-red-100 text-red-600" : update?.is_mandatory ? "bg-amber-100 text-amber-600" : "bg-blue-100 text-blue-600"
        }`}>
          {update?.is_security ? <Shield className="h-4 w-4" /> : <Download className="h-4 w-4" />}
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-900">
            {update?.is_security ? "Security Update Available" : update?.is_mandatory ? "Mandatory Update Required" : "Update Available"}
          </p>
          <p className="text-xs text-gray-600 mt-0.5">
            v{update?.version} is available (current: v{checkResult.current_version})
            {update?.channel && ` • ${update.channel} channel`}
          </p>
          {update?.changelog && update.changelog.length > 0 && (
            <ul className="mt-1 text-xs text-gray-500 list-disc list-inside">
              {update.changelog.slice(0, 3).map((item, i) => (
                <li key={i} className="truncate">{item}</li>
              ))}
              {update.changelog.length > 3 && (
                <li className="text-blue-500">+{update.changelog.length - 3} more</li>
              )}
            </ul>
          )}
          <div className="mt-2 flex gap-2">
            <a
              href="/settings"
              className="inline-flex items-center gap-1 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md px-2.5 py-1 transition-colors"
            >
              <Download className="h-3 w-3" />
              Update Now
            </a>
            <button
              onClick={() => setDismissed(true)}
              className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1"
            >
              Later
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
