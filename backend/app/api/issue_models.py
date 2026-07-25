"""Pydantic models for issue reporting API."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class IssueCategoryEnum(StrEnum):
    BUG = "bug"
    FEATURE_REQUEST = "feature-request"
    GENERAL_FEEDBACK = "general-feedback"
    PERFORMANCE = "performance"
    SECURITY = "security"
    CRASH = "crash"
    AI_FEEDBACK = "ai-feedback"
    DOCUMENTATION = "documentation"
    QUESTION = "question"
    OTHER = "other"


class IssueSeverityEnum(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SUGGESTION = "suggestion"


class IssueStatusEnum(StrEnum):
    NEW = "new"
    TRIAGED = "triaged"
    IN_PROGRESS = "in-progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    DUPLICATE = "duplicate"
    WONT_FIX = "wont-fix"
    NEEDS_INFO = "needs-info"


class ReportSourceEnum(StrEnum):
    CLI = "cli"
    WEB_UI = "web-ui"
    ERROR_DIALOG = "error-dialog"
    CRASH_SCREEN = "crash-screen"
    FEEDBACK_WIDGET = "feedback-widget"
    SETTINGS = "settings"
    DASHBOARD = "dashboard"
    API = "api"
    GITHUB_SYNC = "github-sync"


class IssueReportRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500, description="Issue title")
    description: str = Field(..., description="Detailed description")
    category: IssueCategoryEnum = Field(default=IssueCategoryEnum.BUG, description="Issue category")
    severity: IssueSeverityEnum = Field(default=IssueSeverityEnum.MEDIUM, description="Issue severity")
    source: ReportSourceEnum = Field(default=ReportSourceEnum.API, description="Report source")
    reporter_name: str = Field(default="", description="Reporter name")
    reporter_email: str = Field(default="", description="Reporter email")
    anonymous: bool = Field(default=False, description="Whether report is anonymous")
    system_info: dict[str, Any] | None = Field(default=None, description="System information")
    browser_info: dict[str, Any] | None = Field(default=None, description="Browser information")
    device_info: dict[str, Any] | None = Field(default=None, description="Device information")
    environment_info: dict[str, Any] | None = Field(default=None, description="Environment information")
    app_version: str = Field(default="", description="Application version")
    screenshots: list[str] | None = Field(default=None, description="Screenshot URLs or paths")
    logs: str | None = Field(default=None, description="Application logs")
    steps_to_reproduce: str | None = Field(default=None, description="Steps to reproduce")
    expected_behavior: str | None = Field(default=None, description="Expected behavior")
    actual_behavior: str | None = Field(default=None, description="Actual behavior")
    stack_trace: str | None = Field(default=None, description="Stack trace")
    email_notifications: bool = Field(default=False, description="Send email notifications")
    discord_notifications: bool = Field(default=False, description="Send Discord notifications")
    slack_notifications: bool = Field(default=False, description="Send Slack notifications")


class IssueReportResponse(BaseModel):
    id: str = Field(description="Issue ID")
    title: str = Field(description="Issue title")
    description: str = Field(description="Issue description")
    category: str = Field(description="Issue category")
    severity: str = Field(description="Issue severity")
    status: str = Field(description="Issue status")
    source: str = Field(description="Report source")
    reporter_name: str = Field(description="Reporter name")
    reporter_email: str = Field(description="Reporter email")
    anonymous: bool = Field(description="Whether report is anonymous")
    tracking_number: str = Field(description="Human-readable tracking number")
    labels: list[str] = Field(description="Issue labels")
    assigned_to: str | None = Field(default=None, description="Assigned user")
    milestone: str | None = Field(default=None, description="Milestone")
    priority: int = Field(description="Priority (1-5)")
    system_info: dict = Field(description="System information")
    browser_info: dict = Field(description="Browser information")
    device_info: dict = Field(description="Device information")
    environment_info: dict = Field(description="Environment information")
    app_version: str = Field(description="Application version")
    attachments: list[dict] = Field(description="File attachments")
    screenshots: list[str] = Field(description="Screenshot URLs")
    screen_recording: str | None = Field(default=None, description="Screen recording URL")
    logs: str | None = Field(default=None, description="Application logs")
    steps_to_reproduce: str | None = Field(default=None, description="Steps to reproduce")
    expected_behavior: str | None = Field(default=None, description="Expected behavior")
    actual_behavior: str | None = Field(default=None, description="Actual behavior")
    stack_trace: str | None = Field(default=None, description="Stack trace")
    ai_category: str | None = Field(default=None, description="AI-predicted category")
    ai_summary: str | None = Field(default=None, description="AI-generated summary")
    ai_suggested_fix: str | None = Field(default=None, description="AI-suggested fix")
    duplicate_of: str | None = Field(default=None, description="ID of duplicate issue")
    comments: list[dict] = Field(description="Issue comments")
    timeline: list[dict] = Field(description="Issue timeline")
    created_at: str = Field(description="Creation timestamp")
    updated_at: str = Field(description="Last update timestamp")
    resolved_at: str | None = Field(default=None, description="Resolution timestamp")
    closed_at: str | None = Field(default=None, description="Closure timestamp")
    github_issue_url: str | None = Field(default=None, description="GitHub issue URL")
    github_issue_number: int | None = Field(default=None, description="GitHub issue number")
    email_notifications: bool = Field(description="Email notifications enabled")
    discord_notifications: bool = Field(description="Discord notifications enabled")
    slack_notifications: bool = Field(description="Slack notifications enabled")


class IssueListResponse(BaseModel):
    issues: list[dict[str, Any]] = Field(description="List of issues")
    total: int = Field(description="Total number of matching issues")
    offset: int = Field(description="Pagination offset")
    limit: int = Field(description="Pagination limit")


class IssueUpdateRequest(BaseModel):
    status: str | None = Field(default=None, description="New status")
    severity: str | None = Field(default=None, description="New severity")
    assigned_to: str | None = Field(default=None, description="Assignee")
    milestone: str | None = Field(default=None, description="Milestone")
    labels: list[str] | None = Field(default=None, description="Labels")
    priority: int | None = Field(default=None, ge=1, le=5, description="Priority")
    _actor: str | None = None


class CommentRequest(BaseModel):
    body: str = Field(..., description="Comment body")
    author: str | None = Field(default=None, description="Comment author")


class IssueStatsResponse(BaseModel):
    total_issues: int = Field(description="Total issues")
    open_issues: int = Field(description="Open issues count")
    resolved_issues: int = Field(description="Resolved issues count")
    critical_issues: int = Field(description="Critical issues count")
    by_status: dict[str, int] = Field(description="Issues grouped by status")
    by_category: dict[str, int] = Field(description="Issues grouped by category")
    by_severity: dict[str, int] = Field(description="Issues grouped by severity")
    sla_breaches: int = Field(description="SLA breaches count")
    total_comments: int = Field(description="Total comments across all issues")
    avg_resolution_time_hours: float = Field(description="Average resolution time in hours")


class SLABreachResponse(BaseModel):
    issue_id: str = Field(description="Issue ID")
    tracking_number: str | None = Field(default=None, description="Tracking number")
    severity: str = Field(description="Issue severity")
    elapsed_hours: float = Field(description="Hours elapsed since creation")
    sla_hours: int = Field(description="SLA limit in hours")
    breach_hours: float = Field(description="Hours past SLA limit")


class LabelCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Label name")
    color: str = Field(..., pattern=r"^#[0-9a-fA-F]{6}$", description="Hex color code")
    description: str = Field(default="", max_length=200, description="Label description")


class MilestoneCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="Milestone title")
    description: str = Field(default="", max_length=500, description="Milestone description")
    due_date: str = Field(default="", description="Due date (ISO format)")


class SettingsUpdateRequest(BaseModel):
    settings: dict[str, Any] = Field(description="Settings to update")


class CrashReportRequest(BaseModel):
    error_message: str = Field(..., description="Crash error message")
    stack_trace: str | None = Field(default=None, description="Stack trace")
    system_info: dict[str, Any] | None = Field(default=None, description="System information")
    app_version: str = Field(default="", description="Application version")
    logs: str | None = Field(default=None, description="Application logs")


class FeedbackRequest(BaseModel):
    title: str = Field(default="User Feedback", max_length=200, description="Feedback title")
    message: str = Field(..., description="Feedback message")
    category: str = Field(default="general-feedback", description="Feedback category")
    rating: int | None = Field(default=None, ge=1, le=5, description="Rating (1-5)")
    reporter_name: str = Field(default="", description="Reporter name")
    reporter_email: str = Field(default="", description="Reporter email")
    create_issue: bool = Field(default=True, description="Create an issue from feedback")
