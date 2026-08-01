"""Enterprise issue reporting service."""

import json
import logging
import re
import time
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

logger = logging.getLogger(__name__)

ISSUES_DIR = Path.home() / ".amf" / "issues"


class IssueCategory(StrEnum):
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


class IssueSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SUGGESTION = "suggestion"


class IssueStatus(StrEnum):
    NEW = "new"
    TRIAGED = "triaged"
    IN_PROGRESS = "in-progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    DUPLICATE = "duplicate"
    WONT_FIX = "wont-fix"
    NEEDS_INFO = "needs-info"


class ReportSource(StrEnum):
    CLI = "cli"
    WEB_UI = "web-ui"
    ERROR_DIALOG = "error-dialog"
    CRASH_SCREEN = "crash-screen"
    FEEDBACK_WIDGET = "feedback-widget"
    SETTINGS = "settings"
    DASHBOARD = "dashboard"
    API = "api"
    GITHUB_SYNC = "github-sync"


DEFAULT_LABELS = {
    "bug": {"name": "bug", "color": "#d73a4a", "description": "Something isn't working"},
    "feature": {"name": "enhancement", "color": "#a2eeef", "description": "New feature or request"},
    "feedback": {"name": "feedback", "color": "#0e8a16", "description": "General user feedback"},
    "performance": {"name": "performance", "color": "#d4c5f9", "description": "Performance issue"},
    "security": {"name": "security", "color": "#b60205", "description": "Security vulnerability"},
    "crash": {"name": "crash", "color": "#e99695", "description": "Application crash"},
    "question": {"name": "question", "color": "#cc317c", "description": "Further information is requested"},
    "duplicate": {"name": "duplicate", "color": "#cfd3d7", "description": "This issue or pull request already exists"},
    "wontfix": {"name": "wontfix", "color": "#ffffff", "description": "This will not be worked on"},
    "help-wanted": {"name": "help wanted", "color": "#008672", "description": "Extra attention is needed"},
    "good-first-issue": {"name": "good first issue", "color": "#7057ff", "description": "Good for newcomers"},
    "high-priority": {"name": "high priority", "color": "#b60205", "description": "High priority issue"},
    "needs-info": {"name": "needs info", "color": "#fbca04", "description": "Needs more information"},
}

DEFAULT_MILESTONES = [
    {"title": "v1.1.0", "description": "Next release", "due_date": ""},
    {"title": "v2.0.0", "description": "Major release", "due_date": ""},
    {"title": "Backlog", "description": "Future considerations", "due_date": ""},
]


class IssueReport:
    def __init__(
        self,
        id: str = "",
        title: str = "",
        description: str = "",
        category: IssueCategory = IssueCategory.BUG,
        severity: IssueSeverity = IssueSeverity.MEDIUM,
        status: IssueStatus = IssueStatus.NEW,
        source: ReportSource = ReportSource.API,
        reporter_name: str = "",
        reporter_email: str = "",
        anonymous: bool = False,
        tracking_number: str = "",
        labels: list[str] | None = None,
        assigned_to: str | None = None,
        milestone: str | None = None,
        priority: int = 2,
        system_info: dict | None = None,
        browser_info: dict | None = None,
        device_info: dict | None = None,
        environment_info: dict | None = None,
        app_version: str = "",
        attachments: list[dict] | None = None,
        screenshots: list[str] | None = None,
        screen_recording: str | None = None,
        logs: str | None = None,
        steps_to_reproduce: str | None = None,
        expected_behavior: str | None = None,
        actual_behavior: str | None = None,
        stack_trace: str | None = None,
        ai_category: str | None = None,
        ai_summary: str | None = None,
        ai_suggested_fix: str | None = None,
        duplicate_of: str | None = None,
        comments: list[dict] | None = None,
        timeline: list[dict] | None = None,
        created_at: str = "",
        updated_at: str = "",
        resolved_at: str | None = None,
        closed_at: str | None = None,
        github_issue_url: str | None = None,
        github_issue_number: int | None = None,
        email_notifications: bool = False,
        discord_notifications: bool = False,
        slack_notifications: bool = False,
        **kwargs,
    ):
        now = datetime.now(UTC).isoformat()
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.description = description
        self.category = category.value if isinstance(category, IssueCategory) else category
        self.severity = severity.value if isinstance(severity, IssueSeverity) else severity
        self.status = status.value if isinstance(status, IssueStatus) else status
        self.source = source.value if isinstance(source, ReportSource) else source
        self.reporter_name = reporter_name
        self.reporter_email = reporter_email
        self.anonymous = anonymous
        self.tracking_number = tracking_number or self._generate_tracking()
        self.labels = labels or []
        self.assigned_to = assigned_to
        self.milestone = milestone
        self.priority = priority
        self.system_info = system_info or {}
        self.browser_info = browser_info or {}
        self.device_info = device_info or {}
        self.environment_info = environment_info or {}
        self.app_version = app_version
        self.attachments = attachments or []
        self.screenshots = screenshots or []
        self.screen_recording = screen_recording
        self.logs = logs
        self.steps_to_reproduce = steps_to_reproduce
        self.expected_behavior = expected_behavior
        self.actual_behavior = actual_behavior
        self.stack_trace = stack_trace
        self.ai_category = ai_category
        self.ai_summary = ai_summary
        self.ai_suggested_fix = ai_suggested_fix
        self.duplicate_of = duplicate_of
        self.comments = comments or []
        self.timeline = timeline or []
        self.created_at = created_at or now
        self.updated_at = updated_at or now
        self.resolved_at = resolved_at
        self.closed_at = closed_at
        self.github_issue_url = github_issue_url
        self.github_issue_number = github_issue_number
        self.email_notifications = email_notifications
        self.discord_notifications = discord_notifications
        self.slack_notifications = slack_notifications

    def _generate_tracking(self) -> str:
        ts = datetime.now().strftime("%y%m%d%H%M%S")
        short = self.id[:6].upper()
        return f"AMF-{ts}-{short}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "severity": self.severity,
            "status": self.status,
            "source": self.source,
            "reporter_name": self.reporter_name,
            "reporter_email": self.reporter_email,
            "anonymous": self.anonymous,
            "tracking_number": self.tracking_number,
            "labels": self.labels,
            "assigned_to": self.assigned_to,
            "milestone": self.milestone,
            "priority": self.priority,
            "system_info": self.system_info,
            "browser_info": self.browser_info,
            "device_info": self.device_info,
            "environment_info": self.environment_info,
            "app_version": self.app_version,
            "attachments": self.attachments,
            "screenshots": self.screenshots,
            "screen_recording": self.screen_recording,
            "logs": self.logs,
            "steps_to_reproduce": self.steps_to_reproduce,
            "expected_behavior": self.expected_behavior,
            "actual_behavior": self.actual_behavior,
            "stack_trace": self.stack_trace,
            "ai_category": self.ai_category,
            "ai_summary": self.ai_summary,
            "ai_suggested_fix": self.ai_suggested_fix,
            "duplicate_of": self.duplicate_of,
            "comments": self.comments,
            "timeline": self.timeline,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolved_at": self.resolved_at,
            "closed_at": self.closed_at,
            "github_issue_url": self.github_issue_url,
            "github_issue_number": self.github_issue_number,
            "email_notifications": self.email_notifications,
            "discord_notifications": self.discord_notifications,
            "slack_notifications": self.slack_notifications,
        }

    @staticmethod
    def from_dict(data: dict) -> "IssueReport":
        return IssueReport(**data)


class IssueService:
    def __init__(self, issues_dir: str | Path | None = None):
        self.issues_dir = Path(issues_dir or ISSUES_DIR)
        self.issues_file = self.issues_dir / "issues.json"
        self.feedback_file = self.issues_dir / "feedback.json"
        self.crash_file = self.issues_dir / "crash-reports.json"
        self.labels_file = self.issues_dir / "labels.json"
        self.milestones_file = self.issues_dir / "milestones.json"
        self.settings_file = self.issues_dir / "settings.json"
        self._issues: list[dict] = []
        self._feedback: list[dict] = []
        self._crashes: list[dict] = []
        self._labels: dict[str, dict] = dict(DEFAULT_LABELS)
        self._milestones: list[dict] = list(DEFAULT_MILESTONES)
        self._settings: dict = self._default_settings()
        self._load_all()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _default_settings(self):
        return {
            "github_sync_enabled": False,
            "github_repo": "amf/automated-manuscript-formatter",
            "github_token": None,
            "auto_create_github_issues": True,
            "slack_webhook_url": None,
            "discord_webhook_url": None,
            "email_smtp_server": None,
            "email_smtp_port": 587,
            "email_username": None,
            "email_password": None,
            "email_from": "issues@amf.dev",
            "email_notify_reporters": True,
            "sla_critical_hours": 4,
            "sla_high_hours": 24,
            "sla_medium_hours": 72,
            "sla_low_hours": 168,
            "spam_threshold": 10,
            "spam_window_minutes": 60,
            "duplicate_similarity_threshold": 0.8,
            "ai_enabled": False,
            "ai_provider": "openai",
            "ai_api_key": None,
            "ai_model": "gpt-4",
            "webhook_urls": [],
            "max_attachments_per_issue": 5,
            "max_attachment_size_mb": 25,
            "allow_anonymous_reports": True,
            "require_email_for_followup": False,
            "auto_assign_enabled": False,
            "auto_assign_users": [],
        }

    def _load_all(self):
        for attr, file_key in [
            ("_issues", "issues_file"),
            ("_feedback", "feedback_file"),
            ("_crashes", "crash_file"),
            ("_milestones", "milestones_file"),
            ("_settings", "settings_file"),
        ]:
            path = getattr(self, file_key)
            try:
                if path.exists():
                    setattr(self, attr, json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load %s: %s", path, e)
        try:
            if self.labels_file.exists():
                data = json.loads(self.labels_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._labels = {**DEFAULT_LABELS, **data}
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load labels: %s", e)

    def _save_issues(self):
        self.issues_dir.mkdir(parents=True, exist_ok=True)
        self.issues_file.write_text(json.dumps(self._issues, indent=2, default=str), encoding="utf-8")

    def _save_feedback(self):
        self.feedback_file.write_text(json.dumps(self._feedback, indent=2, default=str), encoding="utf-8")

    def _save_crashes(self):
        self.crash_file.write_text(json.dumps(self._crashes, indent=2, default=str), encoding="utf-8")

    def _save_labels(self):
        self.labels_file.write_text(json.dumps(self._labels, indent=2, default=str), encoding="utf-8")

    def _save_milestones(self):
        self.milestones_file.write_text(json.dumps(self._milestones, indent=2, default=str), encoding="utf-8")

    def _save_settings(self):
        self.settings_file.write_text(json.dumps(self._settings, indent=2, default=str), encoding="utf-8")

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def get_settings(self) -> dict:
        return dict(self._settings)

    def update_settings(self, updates: dict) -> dict:
        for k, v in updates.items():
            if k in self._default_settings():
                self._settings[k] = v
        self._save_settings()
        return self.get_settings()

    # ------------------------------------------------------------------
    # Issue CRUD
    # ------------------------------------------------------------------

    def submit_issue(self, report: IssueReport) -> dict:
        if self._is_spam(report):
            report.status = IssueStatus.CLOSED.value
            report.labels.append("spam")
        dup = self._find_duplicate(report)
        if dup:
            report.duplicate_of = dup["id"]
            report.status = IssueStatus.DUPLICATE.value
            report.labels.append("duplicate")
        if self._settings.get("ai_enabled"):
            try:
                report.ai_category = self._ai_categorize(report)
                report.ai_summary = self._ai_summarize(report)
                if report.category == IssueCategory.BUG.value:
                    report.ai_suggested_fix = self._ai_suggest_fix(report)
            except Exception as e:
                logger.warning("AI processing failed: %s", e)
        if not report.tracking_number:
            report.tracking_number = self._generate_tracking_number()
        now = datetime.now(UTC).isoformat()
        report.created_at = now
        report.updated_at = now
        report.timeline.append(
            {
                "action": "created",
                "timestamp": now,
                "actor": report.reporter_name or "Anonymous",
            }
        )
        if report.category not in report.labels:
            report.labels.append(report.category)
        data = report.to_dict()
        self._issues.append(data)
        self._save_issues()
        if report.category == IssueCategory.CRASH.value:
            self._crashes.append(data)
            self._save_crashes()
        elif report.category in (IssueCategory.GENERAL_FEEDBACK.value, IssueCategory.AI_FEEDBACK.value):
            self._feedback.append(data)
            self._save_feedback()
        self._try_github_sync(data)
        self._dispatch_notifications(data, "new_issue")
        return data

    def get_issue(self, issue_id: str) -> dict | None:
        for issue in self._issues:
            if issue["id"] == issue_id:
                return issue
        for issue in self._issues:
            if issue.get("tracking_number") == issue_id:
                return issue
        return None

    def list_issues(
        self,
        status: str | None = None,
        category: str | None = None,
        severity: str | None = None,
        assigned_to: str | None = None,
        label: str | None = None,
        milestone: str | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        result = list(self._issues)
        if status:
            result = [i for i in result if i.get("status") == status]
        if category:
            result = [i for i in result if i.get("category") == category]
        if severity:
            result = [i for i in result if i.get("severity") == severity]
        if assigned_to:
            result = [i for i in result if i.get("assigned_to") == assigned_to]
        if label:
            result = [i for i in result if label in i.get("labels", [])]
        if milestone:
            result = [i for i in result if i.get("milestone") == milestone]
        if search:
            q = search.lower()
            result = [
                i
                for i in result
                if q in i.get("title", "").lower()
                or q in i.get("description", "").lower()
                or q in i.get("tracking_number", "").lower()
            ]
        reverse = sort_order.lower() == "desc"
        result.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse)
        return result[offset : offset + limit]

    def update_issue(self, issue_id: str, updates: dict) -> dict | None:
        issue = self.get_issue(issue_id)
        if not issue:
            return None
        now = datetime.now(UTC).isoformat()
        timeline_entries = []
        for key, value in updates.items():
            if key in ("id", "created_at", "tracking_number"):
                continue
            if key in issue and issue[key] != value:
                timeline_entries.append(
                    {
                        "action": f"changed_{key}",
                        "from": str(issue.get(key, "")),
                        "to": str(value),
                        "timestamp": now,
                        "actor": updates.get("_actor", "System"),
                    }
                )
            if key in issue:
                issue[key] = value
        issue["updated_at"] = now
        if updates.get("status") == IssueStatus.RESOLVED.value and not issue.get("resolved_at"):
            issue["resolved_at"] = now
        if updates.get("status") == IssueStatus.CLOSED.value and not issue.get("closed_at"):
            issue["closed_at"] = now
        issue["timeline"] = issue.get("timeline", []) + timeline_entries
        self._save_issues()
        self._dispatch_notifications(issue, "issue_updated", changes=timeline_entries)
        return issue

    def delete_issue(self, issue_id: str) -> bool:
        for i, issue in enumerate(self._issues):
            if issue["id"] == issue_id:
                self._issues.pop(i)
                self._save_issues()
                return True
        return False

    def add_comment(self, issue_id: str, comment: dict) -> dict | None:
        issue = self.get_issue(issue_id)
        if not issue:
            return None
        now = datetime.now(UTC).isoformat()
        comment["id"] = str(uuid.uuid4())
        comment["timestamp"] = now
        issue.setdefault("comments", []).append(comment)
        issue["updated_at"] = now
        issue["timeline"].append(
            {
                "action": "commented",
                "timestamp": now,
                "actor": comment.get("author", "Anonymous"),
                "comment_id": comment["id"],
            }
        )
        self._save_issues()
        self._dispatch_notifications(issue, "new_comment", comment=comment)
        return issue

    def get_comments(self, issue_id: str) -> list[dict]:
        issue = self.get_issue(issue_id)
        return issue.get("comments", []) if issue else []

    def get_timeline(self, issue_id: str) -> list[dict]:
        issue = self.get_issue(issue_id)
        return issue.get("timeline", []) if issue else []

    def get_tracking_number(self, issue_id: str) -> str | None:
        issue = self.get_issue(issue_id)
        return issue.get("tracking_number") if issue else None

    # ------------------------------------------------------------------
    # Labels & Milestones
    # ------------------------------------------------------------------

    def list_labels(self) -> dict[str, dict]:
        return dict(self._labels)

    def create_label(self, name: str, color: str, description: str = "") -> dict:
        key = name.lower().replace(" ", "-")
        label = {"name": name, "color": color, "description": description}
        self._labels[key] = label
        self._save_labels()
        return label

    def delete_label(self, key: str) -> bool:
        if key in DEFAULT_LABELS:
            return False
        return bool(self._labels.pop(key, None))

    def list_milestones(self) -> list[dict]:
        return list(self._milestones)

    def create_milestone(self, title: str, description: str = "", due_date: str = "") -> dict:
        milestone = {"title": title, "description": description, "due_date": due_date}
        self._milestones.append(milestone)
        self._save_milestones()
        return milestone

    # ------------------------------------------------------------------
    # Stats / Analytics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        total = len(self._issues)
        by_status = {}
        by_category = {}
        by_severity = {}
        open_count = 0
        resolved_count = 0
        critical_count = 0
        for issue in self._issues:
            s = issue.get("status", "unknown")
            by_status[s] = by_status.get(s, 0) + 1
            c = issue.get("category", "unknown")
            by_category[c] = by_category.get(c, 0) + 1
            sev = issue.get("severity", "unknown")
            by_severity[sev] = by_severity.get(sev, 0) + 1
            if s in (
                IssueStatus.NEW.value,
                IssueStatus.TRIAGED.value,
                IssueStatus.IN_PROGRESS.value,
                IssueStatus.NEEDS_INFO.value,
            ):
                open_count += 1
            if s == IssueStatus.RESOLVED.value:
                resolved_count += 1
            if sev == IssueSeverity.CRITICAL.value:
                critical_count += 1
        return {
            "total_issues": total,
            "open_issues": open_count,
            "resolved_issues": resolved_count,
            "critical_issues": critical_count,
            "by_status": by_status,
            "by_category": by_category,
            "by_severity": by_severity,
            "sla_breaches": 0,
            "total_comments": sum(len(i.get("comments", [])) for i in self._issues),
            "avg_resolution_time_hours": 0,
        }

    def check_sla(self) -> list[dict]:
        now = datetime.now(UTC)
        breaches = []
        sla_map = {
            IssueSeverity.CRITICAL.value: self._settings.get("sla_critical_hours", 4),
            IssueSeverity.HIGH.value: self._settings.get("sla_high_hours", 24),
            IssueSeverity.MEDIUM.value: self._settings.get("sla_medium_hours", 72),
            IssueSeverity.LOW.value: self._settings.get("sla_low_hours", 168),
        }
        for issue in self._issues:
            if issue.get("status") in (IssueStatus.RESOLVED.value, IssueStatus.CLOSED.value):
                continue
            sev = issue.get("severity", "low")
            max_hours = sla_map.get(sev, 168)
            try:
                created = datetime.fromisoformat(issue["created_at"])
                elapsed = (now - created).total_seconds() / 3600
                if elapsed > max_hours:
                    breaches.append(
                        {
                            "issue_id": issue["id"],
                            "tracking_number": issue.get("tracking_number"),
                            "severity": sev,
                            "elapsed_hours": round(elapsed, 1),
                            "sla_hours": max_hours,
                            "breach_hours": round(elapsed - max_hours, 1),
                        }
                    )
            except (ValueError, KeyError):
                pass  # intentionally ignored
        return breaches

    # ------------------------------------------------------------------
    # Duplicate & Spam Detection
    # ------------------------------------------------------------------

    def _is_spam(self, report: IssueReport) -> bool:
        threshold = self._settings.get("spam_threshold", 10)
        window = self._settings.get("spam_window_minutes", 60)
        cutoff = time.time() - (window * 60)
        recent = [
            i
            for i in self._issues
            if i.get("source") == (report.source or "") and self._ts_to_epoch(i.get("created_at", "")) > cutoff
        ]
        return len(recent) >= threshold

    def _find_duplicate(self, report: IssueReport) -> dict | None:
        threshold = self._settings.get("duplicate_similarity_threshold", 0.8)
        title = (report.title or "").lower()
        desc = (report.description or "").lower()
        for existing in self._issues:
            if existing.get("status") in (IssueStatus.CLOSED.value, IssueStatus.DUPLICATE.value):
                continue
            et = existing.get("title", "").lower()
            ed = existing.get("description", "").lower()
            score = self._text_similarity(title + " " + desc, et + " " + ed)
            if score >= threshold:
                return existing
        return None

    def _text_similarity(self, a: str, b: str) -> float:
        words_a = set(re.findall(r"\w+", a.lower()))
        words_b = set(re.findall(r"\w+", b.lower()))
        if not words_a and not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) if union else 0.0

    def _ts_to_epoch(self, ts: str) -> float:
        try:
            return datetime.fromisoformat(ts).timestamp()
        except (ValueError, TypeError):
            return 0.0

    # ------------------------------------------------------------------
    # AI Processing
    # ------------------------------------------------------------------

    def _ai_categorize(self, report: IssueReport) -> str:
        title_lower = (report.title or "").lower()
        desc_lower = (report.description or "").lower()
        combined = title_lower + " " + desc_lower
        if any(w in combined for w in ("crash", "freeze", "hang", "die", "deadlock")):
            return IssueCategory.CRASH.value
        if any(w in combined for w in ("security", "vulnerability", "exploit", "xss", "injection")):
            return IssueCategory.SECURITY.value
        if any(w in combined for w in ("slow", "performance", "lag", "memory", "timeout")):
            return IssueCategory.PERFORMANCE.value
        if any(w in combined for w in ("feature", "request", "would like", "please add", "suggest")):
            return IssueCategory.FEATURE_REQUEST.value
        if any(w in combined for w in ("bug", "error", "broken", "wrong", "issue", "not working")):
            return IssueCategory.BUG.value
        return report.category

    def _ai_summarize(self, report: IssueReport) -> str:
        desc = report.description or ""
        words = desc.split()
        if len(words) <= 50:
            return desc
        return " ".join(words[:50]) + "..."

    def _ai_suggest_fix(self, report: IssueReport) -> str:
        return ""

    def _generate_tracking_number(self) -> str:
        ts = datetime.now().strftime("%y%m%d%H%M%S")
        count = len(self._issues) + 1
        return f"AMF-{ts}-{count:04d}"

    # ------------------------------------------------------------------
    # GitHub Integration
    # ------------------------------------------------------------------

    def _try_github_sync(self, issue_data: dict):
        if not self._settings.get("github_sync_enabled"):
            return
        token = self._settings.get("github_token")
        repo = self._settings.get("github_repo", "amf/automated-manuscript-formatter")
        if not token:
            logger.warning("GitHub sync enabled but no token configured")
            return
        try:
            import httpx

            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "AMF-Issue-Service/1.0",
            }
            body = {
                "title": issue_data.get("title", ""),
                "body": self._format_github_body(issue_data),
                "labels": issue_data.get("labels", []),
            }
            resp = httpx.post(
                f"https://api.github.com/repos/{repo}/issues",
                json=body,
                headers=headers,
                timeout=15.0,
            )
            resp.raise_for_status()
            gh_data = resp.json()
            issue_data["github_issue_url"] = gh_data.get("html_url")
            issue_data["github_issue_number"] = gh_data.get("number")
            self._save_issues()
        except Exception as e:
            logger.error("GitHub sync failed: %s", e)

    def _format_github_body(self, issue_data: dict) -> str:
        lines = [f"## Description\n{issue_data.get('description', '')}\n"]
        if issue_data.get("steps_to_reproduce"):
            lines.append(f"## Steps to Reproduce\n{issue_data['steps_to_reproduce']}\n")
        if issue_data.get("system_info"):
            lines.append(f"## System Info\n```json\n{json.dumps(issue_data['system_info'], indent=2)}\n```\n")
        lines.append("---")
        lines.append(f"*Reported via: {issue_data.get('source', 'API')}*")
        lines.append(f"*Tracking: `{issue_data.get('tracking_number', '')}`*")
        lines.append(f"*Severity: {issue_data.get('severity', 'medium')}*")
        lines.append(f"*App Version: {issue_data.get('app_version', '?')}*")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    def _dispatch_notifications(self, issue_data: dict, event: str, **kwargs):
        webhooks = self._settings.get("webhook_urls", [])
        for url in webhooks:
            try:
                import httpx

                httpx.post(
                    url,
                    json={
                        "event": event,
                        "issue": issue_data,
                        **kwargs,
                    },
                    timeout=10.0,
                )
            except Exception as e:
                logger.warning("Webhook dispatch failed for %s: %s", url, e)
        discord_url = self._settings.get("discord_webhook_url")
        if discord_url:
            try:
                import httpx

                embed = self._build_discord_embed(issue_data, event)
                httpx.post(discord_url, json={"embeds": [embed]}, timeout=10.0)
            except Exception as e:
                logger.warning("Discord notification failed: %s", e)
        slack_url = self._settings.get("slack_webhook_url")
        if slack_url:
            try:
                import httpx

                blocks = self._build_slack_blocks(issue_data, event)
                httpx.post(slack_url, json={"blocks": blocks}, timeout=10.0)
            except Exception as e:
                logger.warning("Slack notification failed: %s", e)

    def _build_discord_embed(self, issue: dict, event: str) -> dict:
        color_map = {
            "critical": 15158332,
            "high": 15105570,
            "medium": 16776960,
            "low": 5763719,
        }
        status_colors = {
            "new": 3447003,
            "in-progress": 15844367,
            "resolved": 3066993,
            "closed": 10070709,
        }
        color = color_map.get(issue.get("severity"), status_colors.get(issue.get("status"), 5814783))
        tracking = issue.get("tracking_number", "")
        return {
            "title": f"{tracking}: {issue.get('title', '')}",
            "url": issue.get("github_issue_url", ""),
            "description": (issue.get("description", "") or "")[:500],
            "color": color,
            "fields": [
                {"name": "Status", "value": issue.get("status", ""), "inline": True},
                {"name": "Severity", "value": issue.get("severity", ""), "inline": True},
                {"name": "Category", "value": issue.get("category", ""), "inline": True},
                {"name": "Source", "value": issue.get("source", ""), "inline": True},
            ],
            "footer": {"text": f"Event: {event}"},
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def _build_slack_blocks(self, issue: dict, event: str) -> list[dict]:
        tracking = issue.get("tracking_number", "")
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": f"{tracking}: {issue.get('title', '')}"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": (issue.get("description", "") or "")[:300]}},
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Status:* {issue.get('status', '')}"},
                    {"type": "mrkdwn", "text": f"*Severity:* {issue.get('severity', '')}"},
                    {"type": "mrkdwn", "text": f"*Category:* {issue.get('category', '')}"},
                    {"type": "mrkdwn", "text": f"*Tracking:* `{tracking}`"},
                ],
            },
        ]
        if issue.get("github_issue_url"):
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"<{issue['github_issue_url']}|View on GitHub>"},
                }
            )
        return blocks

    # ------------------------------------------------------------------
    # Crash Reports (specialized)
    # ------------------------------------------------------------------

    def submit_crash_report(self, crash_data: dict) -> dict:
        crash_data["id"] = crash_data.get("id", str(uuid.uuid4()))
        crash_data["created_at"] = crash_data.get("created_at", datetime.now(UTC).isoformat())
        crash_data["category"] = IssueCategory.CRASH.value
        crash_data["tracking_number"] = self._generate_tracking_number()
        self._crashes.append(crash_data)
        self._save_crashes()
        report = IssueReport(
            title=f"Crash: {crash_data.get('error_message', 'Unknown crash')[:100]}",
            description=crash_data.get("stack_trace", ""),
            category=IssueCategory.CRASH,
            severity=IssueSeverity.CRITICAL,
            source=ReportSource.CRASH_SCREEN,
            stack_trace=crash_data.get("stack_trace"),
            system_info=crash_data.get("system_info"),
            app_version=crash_data.get("app_version", ""),
            logs=crash_data.get("logs"),
        )
        issue_data = self.submit_issue(report)
        return {**crash_data, "issue": issue_data}

    # ------------------------------------------------------------------
    # Feedback (specialized)
    # ------------------------------------------------------------------

    def submit_feedback(self, feedback_data: dict) -> dict:
        feedback_data["id"] = feedback_data.get("id", str(uuid.uuid4()))
        feedback_data["created_at"] = feedback_data.get("created_at", datetime.now(UTC).isoformat())
        self._feedback.append(feedback_data)
        self._save_feedback()
        if feedback_data.get("create_issue", True):
            report = IssueReport(
                title=feedback_data.get("title", "User Feedback")[:200],
                description=feedback_data.get("message", ""),
                category=IssueCategory(feedback_data.get("category", "general-feedback")),
                severity=IssueSeverity.SUGGESTION,
                source=ReportSource.FEEDBACK_WIDGET,
                reporter_name=feedback_data.get("reporter_name", ""),
                reporter_email=feedback_data.get("reporter_email", ""),
                rating=feedback_data.get("rating"),
            )
            return self.submit_issue(report)
        return feedback_data
