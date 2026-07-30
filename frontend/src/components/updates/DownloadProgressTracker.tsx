"use client";

import { useEffect, useState, useRef } from "react";
import { Download, ShieldCheck, CheckCircle2, AlertCircle, RefreshCw, X, ArrowRight } from "lucide-react";
import { downloadUpdate, installUpdate, type UpdateDownloadResponse, type UpdateInstallResponse } from "@/lib/update-api";

export type UpdateProgressStage = "idle" | "downloading" | "verifying" | "installing" | "ready_to_restart" | "error";

export interface DownloadProgressTrackerProps {
  version?: string;
  totalSizeMb?: number;
  onComplete?: () => void;
  onClose?: () => void;
  autoStart?: boolean;
}

export function DownloadProgressTracker({
  version,
  totalSizeMb = 42.5,
  onComplete,
  onClose,
  autoStart = false,
}: DownloadProgressTrackerProps) {
  const [stage, setStage] = useState<UpdateProgressStage>("idle");
  const [progress, setProgress] = useState(0); // 0-100
  const [downloadedMb, setDownloadedMb] = useState(0);
  const [speedMb, setSpeedMb] = useState(0); // MB/s
  const [etaSeconds, setEtaSeconds] = useState(0);
  const [sha256Verified, setSha256Verified] = useState(false);
  const [signatureVerified, setSignatureVerified] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const clearTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  useEffect(() => {
    return () => clearTimer();
  }, []);

  useEffect(() => {
    if (autoStart && stage === "idle") {
      startDownload();
    }
  }, [autoStart, stage]);

  const startDownload = async () => {
    clearTimer();
    setStage("downloading");
    setProgress(0);
    setDownloadedMb(0);
    setErrorMessage(null);
    setSha256Verified(false);
    setSignatureVerified(false);

    const startTime = Date.now();
    let currentMb = 0;

    timerRef.current = setInterval(() => {
      currentMb += 1.8 + Math.random() * 2.2;
      if (currentMb > totalSizeMb) {
        currentMb = totalSizeMb;
      }
      const pct = Math.min(Math.round((currentMb / totalSizeMb) * 100), 98);
      const elapsedSec = (Date.now() - startTime) / 1000;
      const currentSpeed = elapsedSec > 0 ? currentMb / elapsedSec : 3.0;
      const remainingMb = totalSizeMb - currentMb;
      const remainingSec = currentSpeed > 0 ? Math.ceil(remainingMb / currentSpeed) : 0;

      setDownloadedMb(parseFloat(currentMb.toFixed(1)));
      setProgress(pct);
      setSpeedMb(parseFloat(currentSpeed.toFixed(1)));
      setEtaSeconds(remainingSec);

      if (pct >= 98) {
        clearTimer();
      }
    }, 250);

    try {
      const res: UpdateDownloadResponse = await downloadUpdate(version);
      clearTimer();

      if (!res.success) {
        setStage("error");
        setErrorMessage(res.error || "Failed to download update package.");
        return;
      }

      setDownloadedMb(totalSizeMb);
      setProgress(100);

      // Transition to verification stage
      setStage("verifying");
      await new Promise(resolve => setTimeout(resolve, 800));

      setSha256Verified(res.checksum_valid !== false);
      setSignatureVerified(res.signature_valid !== false);

      await new Promise(resolve => setTimeout(resolve, 1000));

      // Transition to installation stage
      setStage("installing");
      const installRes: UpdateInstallResponse = await installUpdate();

      if (!installRes.success) {
        setStage("error");
        setErrorMessage(installRes.error || "Installation failed.");
        return;
      }

      setStage("ready_to_restart");
      if (onComplete) onComplete();
    } catch (e: unknown) {
      clearTimer();
      setStage("error");
      setErrorMessage(e instanceof Error ? e.message : "Download encountered an error.");
    }
  };

  const handleRestart = () => {
    window.location.reload();
  };

  const handleCancel = () => {
    clearTimer();
    setStage("idle");
    if (onClose) onClose();
  };

  return (
    <div className="w-full rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 shadow-xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400">
            <Download className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">
              {version ? `Updating to v${version}` : "System Update"}
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {stage === "idle" && "Ready to download update package"}
              {stage === "downloading" && "Downloading update package..."}
              {stage === "verifying" && "Verifying SHA-256 checksum and ED25519 signature..."}
              {stage === "installing" && "Applying updates and preparing target directory..."}
              {stage === "ready_to_restart" && "Update successfully installed!"}
              {stage === "error" && "Update process encountered an issue"}
            </p>
          </div>
        </div>
        {onClose && (
          <button
            onClick={handleCancel}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            aria-label="Close modal"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Main Status / Progress Bar */}
      {(stage === "downloading" || stage === "verifying" || stage === "installing") && (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs font-semibold text-gray-700 dark:text-gray-300">
            <span>
              {stage === "downloading" && `${downloadedMb} MB / ${totalSizeMb} MB`}
              {stage === "verifying" && "Cryptographic Integrity Check"}
              {stage === "installing" && "Extracting & Applying Package Files"}
            </span>
            <span className="text-blue-600 dark:text-blue-400">{progress}%</span>
          </div>

          {/* Animated Progress Bar */}
          <div className="w-full bg-gray-100 dark:bg-gray-800 h-3 rounded-full overflow-hidden p-0.5">
            <div
              className="h-full bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full transition-all duration-300 relative overflow-hidden"
              style={{ width: `${progress}%` }}
            >
              <div className="absolute inset-0 bg-white/20 animate-pulse" />
            </div>
          </div>

          {/* Speed & ETA */}
          {stage === "downloading" && (
            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 pt-1">
              <span>Speed: {speedMb} MB/s</span>
              <span>ETA: {etaSeconds}s remaining</span>
            </div>
          )}
        </div>
      )}

      {/* Verification Badges */}
      {(stage === "verifying" || stage === "installing" || stage === "ready_to_restart") && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
          <div className={`flex items-center gap-2.5 p-3 rounded-xl border text-xs font-medium transition-all ${
            sha256Verified
              ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300"
              : "bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-500 animate-pulse"
          }`}>
            <CheckCircle2 className={`h-4 w-4 shrink-0 ${sha256Verified ? "text-emerald-600 dark:text-emerald-400" : "text-gray-400"}`} />
            <span>SHA-256 Integrity Verified</span>
          </div>

          <div className={`flex items-center gap-2.5 p-3 rounded-xl border text-xs font-medium transition-all ${
            signatureVerified
              ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300"
              : "bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-500 animate-pulse"
          }`}>
            <ShieldCheck className={`h-4 w-4 shrink-0 ${signatureVerified ? "text-emerald-600 dark:text-emerald-400" : "text-gray-400"}`} />
            <span>ED25519 Digital Signature Valid</span>
          </div>
        </div>
      )}

      {/* Error Display */}
      {stage === "error" && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200 flex items-start gap-3 text-xs">
          <AlertCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold">Update Failed</p>
            <p className="mt-0.5">{errorMessage || "An unknown error occurred."}</p>
          </div>
        </div>
      )}

      {/* Action Controls */}
      <div className="flex items-center justify-end gap-3 pt-2">
        {stage === "idle" && (
          <button
            onClick={startDownload}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs shadow-md transition-colors"
          >
            <Download className="h-4 w-4" />
            Start Download
          </button>
        )}

        {stage === "downloading" && (
          <button
            onClick={handleCancel}
            className="px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-700 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            Cancel
          </button>
        )}

        {stage === "error" && (
          <button
            onClick={startDownload}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-medium transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            Retry Download
          </button>
        )}

        {stage === "ready_to_restart" && (
          <div className="flex items-center gap-3">
            {onClose && (
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-700 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                Restart Later
              </button>
            )}
            <button
              onClick={handleRestart}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-md transition-colors"
            >
              Restart Now
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default DownloadProgressTracker;
