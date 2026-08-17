"use client";

import { useEffect, useState, useCallback } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import {
  Bug, Lightbulb, MessageSquare, Zap, Shield, AlertTriangle,
  BookOpen, HelpCircle, ChevronDown, ChevronUp, Search,
  Plus, Loader2, X, ArrowLeft, Clock, MessageCircle,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import {
  listIssues, submitIssue, getIssue, addComment, getComments, getIssueStats,
  type IssueCategory, type IssueSeverity, type IssueStatus,
  type IssueStats as IssueStatsType, type IssueComment,
} from "@/lib/issue-api";

const categoryIcons: Record<string, typeof Bug> = {
  bug: Bug,
  "feature-request": Lightbulb,
  "general-feedback": MessageSquare,
  performance: Zap,
  security: Shield,
  crash: AlertTriangle,
  "ai-feedback": Lightbulb,
  documentation: BookOpen,
  question: HelpCircle,
  other: MessageSquare,
};

const categoryColors: Record<string, string> = {
  bug: "bg-red-100 text-red-700",
  "feature-request": "bg-purple-100 text-purple-700",
  "general-feedback": "bg-blue-100 text-blue-700",
  performance: "bg-amber-100 text-amber-700",
  security: "bg-red-100 text-red-700",
  crash: "bg-red-100 text-red-700",
  "ai-feedback": "bg-indigo-100 text-indigo-700",
  documentation: "bg-cyan-100 text-cyan-700",
  question: "bg-green-100 text-green-700",
  other: "bg-slate-100 text-slate-700",
};

const severityColors: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border-red-300",
  high: "bg-orange-100 text-orange-700 border-orange-300",
  medium: "bg-amber-100 text-amber-700 border-amber-300",
  low: "bg-green-100 text-green-700 border-green-300",
  suggestion: "bg-blue-100 text-blue-700 border-blue-300",
};

const statusColors: Record<string, string> = {
  new: "bg-blue-100 text-blue-700",
  triaged: "bg-purple-100 text-purple-700",
  "in-progress": "bg-amber-100 text-amber-700",
  resolved: "bg-green-100 text-green-700",
  closed: "bg-slate-100 text-slate-700",
  duplicate: "bg-slate-100 text-slate-700",
  "wont-fix": "bg-slate-100 text-slate-700",
  "needs-info": "bg-orange-100 text-orange-700",
};

const categories = [
  { value: "bug", label: "Bug" },
  { value: "feature-request", label: "Feature Request" },
  { value: "general-feedback", label: "General Feedback" },
  { value: "performance", label: "Performance" },
  { value: "security", label: "Security" },
  { value: "crash", label: "Crash" },
  { value: "ai-feedback", label: "AI Feedback" },
  { value: "documentation", label: "Documentation" },
  { value: "question", label: "Question" },
  { value: "other", label: "Other" },
];

const severities = [
  { value: "critical", label: "Critical" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
  { value: "suggestion", label: "Suggestion" },
];

const pageSize = 20;

const reportSchema = z.object({
  title: z.string().min(1, "Title is required").max(200),
  description: z.string().min(1, "Description is required").max(5000),
  category: z.enum([
    "bug", "feature-request", "general-feedback", "performance",
    "security", "crash", "ai-feedback", "documentation", "question", "other",
  ] as const),
  severity: z.enum(["critical", "high", "medium", "low", "suggestion"] as const).optional(),
  reporter_name: z.string().optional(),
  reporter_email: z.string().optional(),
  steps_to_reproduce: z.string().optional(),
  expected_behavior: z.string().optional(),
  actual_behavior: z.string().optional(),
});

type ReportForm = z.infer<typeof reportSchema>;

export default function IssuesPage() {
  const [issues, setIssues] = useState<Record<string, unknown>[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [stats, setStats] = useState<IssueStatsType | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedData, setExpandedData] = useState<Record<string, unknown> | null>(null);
  const [expandedComments, setExpandedComments] = useState<IssueComment[]>([]);
  const [expandedLoading, setExpandedLoading] = useState(false);
  const [newComment, setNewComment] = useState("");
  const [commenting, setCommenting] = useState(false);

  // Filters
  const [statusFilter, setStatusFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  // Report modal
  const [reportOpen, setReportOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<ReportForm>({
    resolver: zodResolver(reportSchema),
  });

  const fetchIssues = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = { limit: String(pageSize), offset: String(offset) };
      if (statusFilter) params.status = statusFilter;
      if (categoryFilter) params.category = categoryFilter;
      if (severityFilter) params.severity = severityFilter;
      if (searchQuery) params.search = searchQuery;
      const data = await listIssues(params);
      setIssues(data.issues);
      setTotal(data.total);
    } catch {
      toast.error("Failed to load issues");
    } finally {
      setLoading(false);
    }
  }, [offset, statusFilter, categoryFilter, severityFilter, searchQuery]);

  useEffect(() => {
    fetchIssues();
  }, [fetchIssues]);

  useEffect(() => {
    getIssueStats().then(setStats).catch(() => {});
  }, []);

  const handleExpand = async (id: string) => {
    if (expandedId === id) {
      setExpandedId(null);
      setExpandedData(null);
      return;
    }
    setExpandedId(id);
    setExpandedLoading(true);
    try {
      const [issue, comments] = await Promise.all([getIssue(id), getComments(id)]);
      setExpandedData(issue);
      setExpandedComments(comments);
    } catch {
      toast.error("Failed to load issue details");
    } finally {
      setExpandedLoading(false);
    }
  };

  const handleAddComment = async (issueId: string) => {
    if (!newComment.trim()) return;
    setCommenting(true);
    try {
      await addComment(issueId, newComment, "User");
      setNewComment("");
      const comments = await getComments(issueId);
      setExpandedComments(comments);
      toast.success("Comment added");
    } catch {
      toast.error("Failed to add comment");
    } finally {
      setCommenting(false);
    }
  };

  const handleReport = async (data: ReportForm) => {
    setSubmitting(true);
    try {
      await submitIssue({
        title: data.title,
        description: data.description,
        category: data.category,
        severity: data.severity,
        reporter_name: data.reporter_name,
        reporter_email: data.reporter_email,
        steps_to_reproduce: data.steps_to_reproduce,
        expected_behavior: data.expected_behavior,
        actual_behavior: data.actual_behavior,
      });
      toast.success("Issue reported successfully");
      setReportOpen(false);
      reset();
      fetchIssues();
    } catch {
      toast.error("Failed to submit issue");
    } finally {
      setSubmitting(false);
    }
  };

  const totalPages = Math.ceil(total / pageSize);
  const currentPage = Math.floor(offset / pageSize) + 1;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <div className="mx-auto max-w-6xl px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <Link href="/" className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:text-slate-300">
            <ArrowLeft className="h-4 w-4" />
            Back to Home
          </Link>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Issues</h1>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Track bugs, feature requests, and feedback</p>
            </div>
            <div className="flex items-center gap-3">
              <Link
                href="/issues/admin"
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 px-3.5 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                Admin
              </Link>
              <button
                onClick={() => setReportOpen(true)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-accent-500 px-4 py-2 text-sm font-medium text-white hover:bg-accent-400 transition-colors"
              >
                <Plus className="h-4 w-4" />
                Report Issue
              </button>
            </div>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-4">
              <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">{stats.total_issues}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Total Issues</p>
            </div>
            <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-4">
              <p className="text-2xl font-bold text-accent-500">{stats.open_issues}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Open</p>
            </div>
            <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-4">
              <p className="text-2xl font-bold text-green-600">{stats.resolved_issues}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Resolved</p>
            </div>
            <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-4">
              <p className="text-2xl font-bold text-red-600">{stats.critical_issues}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Critical</p>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 dark:text-slate-500" />
            <input
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setOffset(0); }}
              placeholder="Search issues..."
              className="w-full rounded-lg border border-slate-200 dark:border-slate-700 py-2 pl-9 pr-3 text-sm"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setOffset(0); }}
            className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm"
          >
            <option value="">All statuses</option>
            {Object.keys(statusColors).map((s) => (
              <option key={s} value={s}>{s.replace("-", " ")}</option>
            ))}
          </select>
          <select
            value={categoryFilter}
            onChange={(e) => { setCategoryFilter(e.target.value); setOffset(0); }}
            className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm"
          >
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
          <select
            value={severityFilter}
            onChange={(e) => { setSeverityFilter(e.target.value); setOffset(0); }}
            className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm"
          >
            <option value="">All severities</option>
            {severities.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>

        {/* Issue List */}
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-slate-400 dark:text-slate-500" />
            </div>
          ) : issues.length === 0 ? (
            <div className="py-16 text-center">
              <MessageSquare className="mx-auto h-8 w-8 text-slate-300 dark:text-slate-600" />
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">No issues found</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {issues.map((issue) => {
                const cat = (issue.category as string) || "other";
                const CatIcon = categoryIcons[cat] || MessageSquare;
                const sev = (issue.severity as string) || "";
                const stat = (issue.status as string) || "new";
                const id = issue.id as string;

                return (
                  <div key={id}>
                    <button
                      onClick={() => handleExpand(id)}
                      className="flex w-full items-center gap-3 px-5 py-3.5 text-left transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
                    >
                      <div className={`rounded-full p-1.5 ${categoryColors[cat] || "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300"}`}>
                        <CatIcon className="h-3.5 w-3.5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-slate-400 dark:text-slate-500">
                            {issue.tracking_number ? `#${String(issue.tracking_number)}` : `#${id.slice(0, 8)}`}
                          </span>
                          <span className="truncate text-sm font-medium text-slate-900 dark:text-slate-100">
                            {issue.title as string}
                          </span>
                        </div>
                        <div className="mt-0.5 flex items-center gap-2">
                          {sev && (
                            <span className={`inline-flex items-center rounded-full border px-1.5 py-0.5 text-[10px] font-medium ${severityColors[sev] || ""}`}>
                              {sev}
                            </span>
                          )}
                          <span className={`inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium ${statusColors[stat] || ""}`}>
                            {stat.replace("-", " ")}
                          </span>
                          <span className="text-[10px] text-slate-400 dark:text-slate-500">
                            {issue.created_at ? new Date(String(issue.created_at)).toLocaleDateString() : ""}
                          </span>
                        </div>
                      </div>
                      {expandedId === id ? <ChevronUp className="h-4 w-4 text-slate-400 dark:text-slate-500" /> : <ChevronDown className="h-4 w-4 text-slate-400 dark:text-slate-500" />}
                    </button>

                    {/* Expanded detail */}
                    {expandedId === id && (
                      <div className="border-t border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-5 py-4">
                        {expandedLoading ? (
                          <div className="flex items-center justify-center py-4">
                            <Loader2 className="h-5 w-5 animate-spin text-slate-400 dark:text-slate-500" />
                          </div>
                        ) : expandedData ? (
                          <div className="space-y-4">
                            <p className="text-sm text-slate-700 dark:text-slate-300">
                              {(expandedData.description as string) || (expandedData.body as string) || "No description"}
                            </p>

                            {expandedData.steps_to_reproduce ? (
                              <div>
                                <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Steps to reproduce</p>
                                <p className="mt-1 text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">{String(expandedData.steps_to_reproduce)}</p>
                              </div>
                            ) : null}

                            {expandedData.expected_behavior ? (
                              <div>
                                <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Expected behavior</p>
                                <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{String(expandedData.expected_behavior)}</p>
                              </div>
                            ) : null}

                            {expandedData.actual_behavior ? (
                              <div>
                                <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Actual behavior</p>
                                <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{String(expandedData.actual_behavior)}</p>
                              </div>
                            ) : null}

                            {/* Comments */}
                            <div>
                              <p className="flex items-center gap-1 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                                <MessageCircle className="h-3 w-3" />
                                Comments ({expandedComments.length})
                              </p>
                              <div className="mt-2 space-y-2">
                                {expandedComments.map((comment, i) => (
                                  <div key={comment.id || i} className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white p-3">
                                    <div className="flex items-center justify-between">
                                      <span className="text-xs font-medium text-slate-700 dark:text-slate-300">{comment.author}</span>
                                      <span className="text-[10px] text-slate-400 dark:text-slate-500">
                                        {new Date(comment.timestamp).toLocaleString()}
                                      </span>
                                    </div>
                                    <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{comment.body}</p>
                                  </div>
                                ))}
                              </div>
                            </div>

                            {/* Add comment */}
                            <div className="flex gap-2">
                              <input
                                value={newComment}
                                onChange={(e) => setNewComment(e.target.value)}
                                placeholder="Add a comment..."
                                className="flex-1 rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm"
                                onKeyDown={(e) => {
                                  if (e.key === "Enter" && !e.shiftKey) {
                                    e.preventDefault();
                                    handleAddComment(id);
                                  }
                                }}
                              />
                              <button
                                onClick={() => handleAddComment(id)}
                                disabled={commenting || !newComment.trim()}
                                className="inline-flex items-center gap-1 rounded-lg bg-accent-500 px-3 py-2 text-sm font-medium text-white hover:bg-accent-400 disabled:opacity-50 transition-colors"
                              >
                                {commenting ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
                                Send
                              </button>
                            </div>
                          </div>
                        ) : null}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="mt-4 flex items-center justify-between">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Showing {offset + 1}–{Math.min(offset + pageSize, total)} of {total}
            </p>
            <div className="flex gap-1">
              <button
                onClick={() => setOffset(Math.max(0, offset - pageSize))}
                disabled={offset === 0}
                className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-50 transition-colors"
              >
                Previous
              </button>
              {Array.from({ length: totalPages }, (_, i) => (
                <button
                  key={i}
                  onClick={() => setOffset(i * pageSize)}
                  className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
                    currentPage === i + 1
                      ? "bg-accent-500 text-white"
                      : "border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                  }`}
                >
                  {i + 1}
                </button>
              ))}
              <button
                onClick={() => setOffset(Math.min((totalPages - 1) * pageSize, offset + pageSize))}
                disabled={offset + pageSize >= total}
                className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-50 transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Report Issue Modal */}
      <Dialog.Root open={reportOpen} onOpenChange={setReportOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[85vh] w-full max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-6 shadow-2xl">
            <Dialog.Close className="absolute right-4 top-4 text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:text-slate-400">
              <X className="h-4 w-4" />
            </Dialog.Close>
            <Dialog.Title className="text-lg font-semibold text-slate-900 dark:text-slate-100">Report Issue</Dialog.Title>
            <Dialog.Description className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Submit a bug report, feature request, or feedback.
            </Dialog.Description>

            <form onSubmit={handleSubmit(handleReport)} className="mt-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Title *</label>
                <input
                  {...register("title")}
                  placeholder="Brief descriptive title"
                  className="mt-1 w-full rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm"
                />
                {errors.title && <p className="mt-1 text-xs text-red-600">{errors.title.message}</p>}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Category *</label>
                  <select {...register("category")} className="mt-1 w-full rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm">
                    {categories.map((c) => (
                      <option key={c.value} value={c.value}>{c.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Severity</label>
                  <select {...register("severity")} className="mt-1 w-full rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm">
                    <option value="">Select...</option>
                    {severities.map((s) => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Description *</label>
                <textarea
                  {...register("description")}
                  rows={4}
                  placeholder="Detailed description of the issue..."
                  className="mt-1 w-full rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm resize-none"
                />
                {errors.description && <p className="mt-1 text-xs text-red-600">{errors.description.message}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Steps to reproduce</label>
                <textarea
                  {...register("steps_to_reproduce")}
                  rows={3}
                  placeholder="1. Go to...&#x0a;2. Click on...&#x0a;3. See error..."
                  className="mt-1 w-full rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm resize-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Expected behavior</label>
                  <textarea
                    {...register("expected_behavior")}
                    rows={2}
                    className="mt-1 w-full rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm resize-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Actual behavior</label>
                  <textarea
                    {...register("actual_behavior")}
                    rows={2}
                    className="mt-1 w-full rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm resize-none"
                  />
                </div>
              </div>

              <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
                <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">Reporter info (optional)</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Name</label>
                    <input
                      {...register("reporter_name")}
                      placeholder="Your name"
                      className="mt-1 w-full rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Email</label>
                    <input
                      {...register("reporter_email")}
                      placeholder="email@example.com"
                      className="mt-1 w-full rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm"
                    />
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-accent-500 px-4 py-2.5 text-sm font-medium text-white hover:bg-accent-400 disabled:opacity-50 transition-colors"
              >
                {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
                {submitting ? "Submitting..." : "Submit Issue"}
              </button>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
