"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Download, X, Shield, ChevronDown, ChevronUp } from "lucide-react";
import { checkForUpdates, getVersionInfo, type UpdateCheckResult, type VersionInfo } from "@/lib/update-api";
import { DownloadProgressTracker } from "./DownloadProgressTracker";

const DISMISSAL_KEY = "scholarform_update_dismissed";

interface DismissalData {
  version: string;
  timestamp: number;
}

export default function UpdateBanner() {
  const [checkResult, setCheckResult] = useState<UpdateCheckResult | null>(null);
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showChangelog, setShowChangelog] = useState(false);
  const [showProgressTracker, setShowProgressTracker] = useState(false);

  const check = async () => {
    try {
      const [result, info] = await Promise.all([
        checkForUpdates(undefined, "auto").catch(() => null),
        getVersionInfo().catch(() => null),
      ]);

      if (result) setCheckResult(result);
      if (info) setVersionInfo(info);

      // Check 24-hour dismissal in localStorage
      if (result?.update?.version) {
        const raw = localStorage.getItem(DISMISSAL_KEY);
        if (raw) {
          try {
            const data: DismissalData = JSON.parse(raw);
            const isSameVersion = data.version === result.update.version;
            const hoursPassed = (Date.now() - data.timestamp) / (1000 * 60 * 60);

            // Security updates ignore 24h dismissal unless explicitly dismissed in current session
            if (isSameVersion && hoursPassed < 24 && !result.update.is_security) {
              setDismissed(true);
            }
          } catch {
            localStorage.removeItem(DISMISSAL_KEY);
          }
        }
      }
    } catch {
      // Silent fail — banner will not render on network errors
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    check();
    // 1-hour interval auto-check (3,600,000 ms)
    const interval = setInterval(check, 3600000);
    return () => clearInterval(interval);
  }, []);

  const handleDismiss = () => {
    setDismissed(true);
    if (checkResult?.update?.version) {
      const data: DismissalData = {
        version: checkResult.update.version,
        timestamp: Date.now(),
      };
      localStorage.setItem(DISMISSAL_KEY, JSON.stringify(data));
    }
  };

  if (loading || dismissed) return null;
  if (!checkResult || checkResult.status !== "update-available" || !checkResult.update) return null;

  const update = checkResult.update;
  const isSecurity = update.is_security;
  const isMandatory = update.is_mandatory;

  return (
    <>
      <div
        role="region"
        aria-label="Software Update Notification"
        className={`fixed bottom-5 right-5 z-50 max-w-md w-full sm:w-96 rounded-2xl shadow-2xl border ${
          isSecurity
            ? "border-red-500 bg-red-50 dark:bg-red-950/95 text-red-950 dark:text-red-100"
            : isMandatory
            ? "border-amber-500 bg-amber-50 dark:bg-amber-950/95 text-amber-950 dark:text-amber-100"
            : "border-blue-500 bg-white dark:bg-slate-900 text-gray-900 dark:text-slate-100"
        } p-4 transition-all duration-300 animate-in slide-in-from-bottom-5`}
      >
        <button
          onClick={handleDismiss}
          className="absolute top-3 right-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-1 rounded-lg transition-colors"
          aria-label="Dismiss update banner for 24 hours"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="flex items-start gap-3">
          <div
            className={`mt-0.5 rounded-xl p-2 shrink-0 ${
              isSecurity
                ? "bg-red-100 dark:bg-red-900/50 text-red-600 dark:text-red-300"
                : isMandatory
                ? "bg-amber-100 dark:bg-amber-900/50 text-amber-600 dark:text-amber-300"
                : "bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-300"
            }`}
          >
            {isSecurity ? (
              <Shield className="h-5 w-5" />
            ) : isMandatory ? (
              <AlertTriangle className="h-5 w-5" />
            ) : (
              <Download className="h-5 w-5" />
            )}
          </div>

          <div className="flex-1 min-w-0 pr-4">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-sm font-bold">
                {isSecurity
                  ? "Security Update Available"
                  : isMandatory
                  ? "Mandatory Update Required"
                  : "Update Available"}
              </h4>
              {update.channel && (
                <span className="text-[10px] uppercase font-semibold tracking-wider px-2 py-0.5 rounded-full bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
                  {update.channel}
                </span>
              )}
            </div>

            <p className="text-xs text-gray-600 dark:text-gray-300 mt-1">
              v{update.version} is available (installed: v{checkResult.current_version || versionInfo?.current_version || "1.4.2"})
            </p>

            {/* Inline Changelog Preview */}
            {update.changelog && update.changelog.length > 0 && (
              <div className="mt-2 text-xs">
                <button
                  onClick={() => setShowChangelog(!showChangelog)}
                  className="flex items-center gap-1 font-medium text-blue-600 dark:text-blue-400 hover:underline focus:outline-none"
                >
                  <span>{showChangelog ? "Hide release details" : "Preview changelog"}</span>
                  {showChangelog ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                </button>

                {showChangelog ? (
                  <ul className="mt-1.5 space-y-1 pl-4 list-disc text-gray-600 dark:text-gray-300 max-h-32 overflow-y-auto">
                    {update.changelog.map((item, i) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <ul className="mt-1 text-gray-500 dark:text-gray-400 list-disc list-inside space-y-0.5">
                    {update.changelog.slice(0, 2).map((item, i) => (
                      <li key={i} className="truncate">{item}</li>
                    ))}
                    {update.changelog.length > 2 && (
                      <li className="text-[11px] text-gray-400">+{update.changelog.length - 2} more changes...</li>
                    )}
                  </ul>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="mt-3 flex items-center gap-2">
              <button
                onClick={() => setShowProgressTracker(true)}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 rounded-xl px-3 py-1.5 shadow-sm transition-colors"
              >
                <Download className="h-3.5 w-3.5" />
                Update Now
              </button>

              <button
                onClick={handleDismiss}
                className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 px-2.5 py-1.5 rounded-lg transition-colors"
              >
                Remind Me Later
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Download Progress Tracker Modal */}
      {showProgressTracker && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-lg w-full">
            <DownloadProgressTracker
              version={update.version}
              totalSizeMb={update.size ? parseFloat((update.size / (1024 * 1024)).toFixed(1)) : 42.5}
              autoStart={true}
              onClose={() => setShowProgressTracker(false)}
            />
          </div>
        </div>
      )}
    </>
  );
}
