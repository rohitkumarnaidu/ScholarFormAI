"use client";

import { useState } from "react";
import { AlertTriangle, ChevronDown, ChevronUp, RefreshCw, Home, Loader2 } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { submitCrashReport } from "@/lib/issue-api";

interface CrashScreenProps {
  error?: Error | null;
}

export default function CrashScreen({ error }: CrashScreenProps) {
  const [showStack, setShowStack] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleReport = async () => {
    setSubmitting(true);
    try {
      await submitCrashReport({
        error_message: error?.message || "Unknown error",
        stack_trace: error?.stack,
        system_info: {
          userAgent: navigator.userAgent,
          platform: navigator.platform,
          language: navigator.language,
          screen: `${screen.width}x${screen.height}`,
          colorDepth: screen.colorDepth,
          appVersion: navigator.appVersion,
        },
        app_version: process.env.NEXT_PUBLIC_APP_VERSION || "1.0.0",
      });
      setSubmitted(true);
      toast.success("Crash report submitted. Thank you!");
    } catch {
      toast.error("Failed to submit crash report.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-white dark:bg-primary-950">
      <div className="mx-auto max-w-md px-4 text-center">
        <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
          <AlertTriangle className="h-10 w-10 text-red-600 dark:text-red-400" />
        </div>

        <h1 className="mb-2 text-2xl font-bold text-slate-900 dark:text-white">
          Something went wrong
        </h1>
        <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">
          An unexpected error occurred. Our team has been notified if you choose to report it.
        </p>

        {error?.message && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-left dark:border-red-800 dark:bg-red-900/20">
            <p className="text-sm font-medium text-red-800 dark:text-red-300">{error.message}</p>
          </div>
        )}

        {error?.stack && (
          <div className="mb-6">
            <button
              onClick={() => setShowStack(!showStack)}
              className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700"
            >
              {showStack ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {showStack ? "Hide" : "Show"} stack trace
            </button>
            {showStack && (
              <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-slate-100 p-3 text-left text-xs text-slate-700 dark:bg-primary-900 dark:text-slate-300">
                {error.stack}
              </pre>
            )}
          </div>
        )}

        <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
          {!submitted ? (
            <button
              onClick={handleReport}
              disabled={submitting}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-red-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {submitting ? "Reporting..." : "Report this crash"}
            </button>
          ) : (
            <span className="inline-flex items-center gap-2 rounded-lg bg-green-100 px-5 py-2.5 text-sm font-medium text-green-800">
              Report submitted
            </span>
          )}

          <button
            onClick={() => window.location.reload()}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            Reload page
          </button>

          <Link
            href="/"
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <Home className="h-4 w-4" />
            Go Home
          </Link>
        </div>
      </div>
    </div>
  );
}
