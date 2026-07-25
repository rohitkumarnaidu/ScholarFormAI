"use client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export type IssueCategory = "bug" | "feature-request" | "general-feedback" | "performance" | "security" | "crash" | "ai-feedback" | "documentation" | "question" | "other";
export type IssueSeverity = "critical" | "high" | "medium" | "low" | "suggestion";
export type IssueStatus = "new" | "triaged" | "in-progress" | "resolved" | "closed" | "duplicate" | "wont-fix" | "needs-info";

export interface IssueReportRequest {
  title: string;
  description: string;
  category: IssueCategory;
  severity?: IssueSeverity;
  source?: string;
  reporter_name?: string;
  reporter_email?: string;
  anonymous?: boolean;
  system_info?: Record<string, unknown>;
  browser_info?: Record<string, unknown>;
  device_info?: Record<string, unknown>;
  environment_info?: Record<string, unknown>;
  app_version?: string;
  screenshots?: string[];
  logs?: string;
  steps_to_reproduce?: string;
  expected_behavior?: string;
  actual_behavior?: string;
  stack_trace?: string;
  email_notifications?: boolean;
  discord_notifications?: boolean;
  slack_notifications?: boolean;
}

export interface CrashReportRequest {
  error_message: string;
  stack_trace?: string;
  system_info?: Record<string, unknown>;
  app_version?: string;
  logs?: string;
  screenshot?: string;
}

export interface FeedbackRequest {
  title?: string;
  message: string;
  category?: string;
  rating?: number;
  reporter_name?: string;
  reporter_email?: string;
  create_issue?: boolean;
}

export interface IssueComment {
  id: string;
  body: string;
  author: string;
  timestamp: string;
}

export interface IssueStats {
  total_issues: number;
  open_issues: number;
  resolved_issues: number;
  critical_issues: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  by_severity: Record<string, number>;
  sla_breaches: number;
  total_comments: number;
  avg_resolution_time_hours: number;
}

export interface SLABreach {
  issue_id: string;
  tracking_number: string;
  severity: string;
  elapsed_hours: number;
  sla_hours: number;
  breach_hours: number;
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}/api/v1${path}`;
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: response.statusText }));
    throw new ApiError(response.status, error.message || "Request failed");
  }
  return response.json();
}

export async function submitIssue(data: IssueReportRequest): Promise<Record<string, unknown>> {
  return request("/issues", { method: "POST", body: JSON.stringify(data) });
}

export async function listIssues(params?: Record<string, string>): Promise<{ issues: Record<string, unknown>[]; total: number; offset: number; limit: number }> {
  const qs = params ? "?" + new URLSearchParams(params) : "";
  return request(`/issues${qs}`);
}

export async function getIssue(issueId: string): Promise<Record<string, unknown>> {
  return request(`/issues/${issueId}`);
}

export async function updateIssue(issueId: string, data: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request(`/issues/${issueId}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function deleteIssue(issueId: string): Promise<void> {
  await fetch(`${API_BASE}/api/v1/issues/${issueId}`, { method: "DELETE" });
}

export async function addComment(issueId: string, body: string, author: string): Promise<Record<string, unknown>> {
  return request(`/issues/${issueId}/comments`, { method: "POST", body: JSON.stringify({ body, author }) });
}

export async function getComments(issueId: string): Promise<IssueComment[]> {
  return request(`/issues/${issueId}/comments`);
}

export async function getTimeline(issueId: string): Promise<Record<string, unknown>[]> {
  return request(`/issues/${issueId}/timeline`);
}

export async function submitCrashReport(data: CrashReportRequest): Promise<Record<string, unknown>> {
  return request("/issues/crash", { method: "POST", body: JSON.stringify(data) });
}

export async function submitFeedback(data: FeedbackRequest): Promise<Record<string, unknown>> {
  return request("/issues/feedback", { method: "POST", body: JSON.stringify(data) });
}

export async function listLabels(): Promise<Record<string, { name: string; color: string; description: string }>> {
  return request("/issues/labels");
}

export async function createLabel(name: string, color: string, description?: string): Promise<Record<string, unknown>> {
  return request("/issues/labels", { method: "POST", body: JSON.stringify({ name, color, description }) });
}

export async function deleteLabel(key: string): Promise<void> {
  await fetch(`${API_BASE}/api/v1/issues/labels/${key}`, { method: "DELETE" });
}

export async function listMilestones(): Promise<Record<string, unknown>[]> {
  return request("/issues/milestones");
}

export async function createMilestone(title: string, description?: string, dueDate?: string): Promise<Record<string, unknown>> {
  return request("/issues/milestones", { method: "POST", body: JSON.stringify({ title, description, due_date: dueDate }) });
}

export async function getIssueStats(): Promise<IssueStats> {
  return request("/issues/stats");
}

export async function checkSLA(): Promise<SLABreach[]> {
  return request("/issues/sla");
}

export async function getIssueSettings(): Promise<Record<string, unknown>> {
  return request("/issues/settings");
}

export async function updateIssueSettings(settings: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request("/issues/settings", { method: "PUT", body: JSON.stringify({ settings }) });
}

export async function getTrackingNumber(issueId: string): Promise<{ tracking_number: string }> {
  return request(`/issues/${issueId}/tracking`);
}
