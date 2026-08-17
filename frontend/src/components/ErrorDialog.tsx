"use client";

import { useState, useCallback } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { AlertCircle, X, Copy, Loader2, FileText } from "lucide-react";
import { toast } from "sonner";
import { submitIssue } from "@/lib/issue-api";

interface ErrorDialogProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  title?: string;
  message?: string;
  details?: string;
  error?: Error | null;
}

export function showError(error: Error | string, details?: string) {
  const event = new CustomEvent("amf:show-error", {
    detail: {
      title: typeof error === "string" ? error : error.message,
      message: typeof error === "string" ? details || "" : error.message,
      details: typeof error === "string" ? details : error.stack || details,
      error: error instanceof Error ? error : null,
    },
  });
  window.dispatchEvent(event);
}

export default function ErrorDialog({
  open: controlledOpen,
  onOpenChange: controlledOnOpenChange,
  title: propTitle,
  message: propMessage,
  details: propDetails,
  error: propError,
}: ErrorDialogProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const [internalTitle, setInternalTitle] = useState("");
  const [internalMessage, setInternalMessage] = useState("");
  const [internalDetails, setInternalDetails] = useState("");
  const [internalError, setInternalError] = useState<Error | null>(null);
  const [reporting, setReporting] = useState(false);
  const [showReportForm, setShowReportForm] = useState(false);
  const [reportTitle, setReportTitle] = useState("");
  const [reportDescription, setReportDescription] = useState("");

  const isControlled = controlledOpen !== undefined;
  const open = isControlled ? controlledOpen : internalOpen;

  const setOpen = useCallback(
    (val: boolean) => {
      if (isControlled) {
        controlledOnOpenChange?.(val);
      } else {
        setInternalOpen(val);
      }
    },
    [isControlled, controlledOnOpenChange],
  );

  const title = propTitle || internalTitle;
  const message = propMessage || internalMessage;
  const details = propDetails || internalDetails;
  const error = propError || internalError;

  useState(() => {
    if (typeof window !== "undefined") {
      const handler = (e: Event) => {
        const detail = (e as CustomEvent).detail;
        setInternalTitle(detail.title);
        setInternalMessage(detail.message);
        setInternalDetails(detail.details);
        setInternalError(detail.error);
        setInternalOpen(true);
      };
      window.addEventListener("amf:show-error", handler);
      return () => window.removeEventListener("amf:show-error", handler);
    }
  });

  const handleCopy = () => {
    const text = [message, details].filter(Boolean).join("\n\n");
    navigator.clipboard.writeText(text);
    toast.success("Error details copied to clipboard");
  };

  const handleReport = async () => {
    setReporting(true);
    try {
      await submitIssue({
        title: reportTitle || title || "Error Report",
        description: reportDescription || message || "No description provided",
        category: "bug",
        severity: "medium",
        stack_trace: details,
        system_info: typeof window !== "undefined" ? {
          userAgent: navigator.userAgent,
          platform: navigator.platform,
          screen: `${screen.width}x${screen.height}`,
        } : undefined,
      });
      toast.success("Issue reported successfully");
      setShowReportForm(false);
      setOpen(false);
    } catch {
      toast.error("Failed to report issue");
    } finally {
      setReporting(false);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 data-[state=open]:animate-in data-[state=closed]:animate-out" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[85vh] w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl border border-slate-200 bg-white p-6 shadow-2xl data-[state=open]:animate-in data-[state=closed]:animate-out">
          <Dialog.Close className="absolute right-4 top-4 text-slate-400 hover:text-slate-600">
            <X className="h-4 w-4" />
          </Dialog.Close>

          <div className="flex items-start gap-3">
            <div className="rounded-full bg-red-100 p-2">
              <AlertCircle className="h-5 w-5 text-red-600" />
            </div>
            <div className="flex-1 min-w-0">
              <Dialog.Title className="text-lg font-semibold text-slate-900">
                {title || "Error"}
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-sm text-slate-500">
                {message || "An unexpected error occurred."}
              </Dialog.Description>
            </div>
          </div>

          {details && (
            <pre className="mt-4 max-h-32 overflow-auto rounded-lg bg-slate-100 p-3 text-xs text-slate-700">
              {details}
            </pre>
          )}

          {!showReportForm ? (
            <div className="mt-5 flex gap-2">
              <button
                onClick={() => setShowReportForm(true)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
              >
                <FileText className="h-4 w-4" />
                Report this issue
              </button>
              <button
                onClick={handleCopy}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
              >
                <Copy className="h-4 w-4" />
                Copy error
              </button>
              <Dialog.Close asChild>
                <button className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors">
                  Dismiss
                </button>
              </Dialog.Close>
            </div>
          ) : (
            <div className="mt-5 space-y-3">
              <div>
                <label className="block text-sm font-medium text-slate-700">Title</label>
                <input
                  value={reportTitle}
                  onChange={(e) => setReportTitle(e.target.value)}
                  placeholder={title || "Brief title"}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">Description</label>
                <textarea
                  value={reportDescription}
                  onChange={(e) => setReportDescription(e.target.value)}
                  rows={3}
                  placeholder="What were you doing when this happened?"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm resize-none"
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleReport}
                  disabled={reporting}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
                >
                  {reporting && <Loader2 className="h-4 w-4 animate-spin" />}
                  {reporting ? "Submitting..." : "Submit report"}
                </button>
                <button
                  onClick={() => setShowReportForm(false)}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
