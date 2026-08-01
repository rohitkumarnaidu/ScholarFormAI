"""Issue reporting CLI commands."""

import logging
import sys
from datetime import datetime
from pathlib import Path

from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from amf._console import get_console, safe_progress

logger = logging.getLogger(__name__)
console = get_console()


def _get_service():
    from app.services.issue_service import IssueService
    return IssueService()


def _get_version():
    try:
        from app import __version__
        return __version__
    except ImportError:
        return "1.0.0"


def _get_system_info():
    import platform
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "python_version": platform.python_version(),
        "hostname": platform.node(),
        "platform": platform.platform(),
    }


def _fmt_date(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return ts or "?"


SEVERITY_COLORS = {
    "critical": "red", "high": "orange3", "medium": "yellow",
    "low": "blue", "suggestion": "dim",
}

STATUS_STYLES = {
    "new": "bold cyan", "triaged": "cyan", "in-progress": "bold yellow",
    "resolved": "bold green", "closed": "dim", "duplicate": "dim",
    "wont-fix": "dim", "needs-info": "yellow",
}

CATEGORY_ICONS = {
    "bug": "\U0001f41b", "feature-request": "\u2728", "general-feedback": "\U0001f4ac",
    "performance": "\u26a1", "security": "\U0001f512", "crash": "\U0001f4a5",
    "ai-feedback": "\U0001f916", "documentation": "\U0001f4d6", "question": "\u2753",
    "other": "\U0001f4cb",
}


def run_issue_report(
    title: str, description: str, category: str, severity: str,
    name: str | None, email: str | None, anonymous: bool,
    attach_logs: bool, verbose: bool,
):
    """Report a new issue."""
    try:
        service = _get_service()
        from app.services.issue_service import (
            IssueCategory,
            IssueReport,
            IssueSeverity,
            ReportSource,
        )
    except ImportError:
        console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
        console.print("  pip install -e backend/")
        sys.exit(1)

    system_info = _get_system_info() if not anonymous else {}
    logs = ""
    if attach_logs:
        log_paths = [
            Path.home() / ".amf" / "logs" / "app.log",
            Path.home() / ".amf" / "logs" / "error.log",
        ]
        for p in log_paths:
            if p.exists():
                logs += f"--- {p.name} ---\n" + p.read_text(encoding="utf-8", errors="replace")[-5000:] + "\n\n"

    report = IssueReport(
        title=title, description=description,
        category=IssueCategory(category), severity=IssueSeverity(severity),
        source=ReportSource.CLI,
        reporter_name=name or "", reporter_email=email or "",
        anonymous=anonymous, app_version=_get_version(),
        system_info=system_info, logs=logs[:10000] if logs else "",
    )

    with safe_progress() as progress:
        progress.add_task(description="Submitting issue...")
        result = service.submit_issue(report)

    tracking = result.get("tracking_number", "?")
    console.print("[green]Issue submitted![/green]")
    console.print(f"  Tracking: [bold]{tracking}[/bold]")
    if result.get("duplicate_of"):
        console.print(f"  [yellow]Marked as duplicate of: {result['duplicate_of']}[/yellow]")
    console.print(f"  Status: {result.get('status', 'new')}")
    if result.get("ai_category"):
        console.print(f"  AI Category: {result.get('ai_category')}")
    if result.get("ai_summary"):
        console.print(f"  AI Summary: {result.get('ai_summary')}")


def run_issue_list(
    status: str | None, category: str | None, severity: str | None,
    label: str | None, search: str | None, limit: int, verbose: bool,
):
    """List issues with filtering."""
    try:
        service = _get_service()
    except ImportError:
        console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
        console.print("  pip install -e backend/")
        sys.exit(1)

    with safe_progress() as progress:
        progress.add_task(description="Fetching issues...")
        issues = service.list_issues(
            status=status, category=category, severity=severity,
            label=label, search=search, limit=limit,
        )

    if not issues:
        console.print("[yellow]No issues found.[/yellow]")
        return

    table = Table(title=f"Issues ({len(issues)} shown)")
    table.add_column("Tracking", style="bold cyan", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Category")
    table.add_column("Severity")
    table.add_column("Status")
    table.add_column("Created")
    table.add_column("Assignee")

    for issue in issues:
        cat = issue.get("category", "")
        icon = CATEGORY_ICONS.get(cat, "\U0001f4cb")
        sev = issue.get("severity", "")
        sev_style = SEVERITY_COLORS.get(sev, "")
        st = issue.get("status", "")
        st_style = STATUS_STYLES.get(st, "")

        table.add_row(
            issue.get("tracking_number", ""),
            issue.get("title", "")[:60],
            f"{icon} {cat}",
            f"[{sev_style}]{sev}[/{sev_style}]" if sev_style else sev,
            f"[{st_style}]{st}[/{st_style}]" if st_style else st,
            _fmt_date(issue.get("created_at", "")),
            issue.get("assigned_to", "") or "-",
        )

    console.print(table)


def run_issue_show(issue_id: str, verbose: bool):
    """Show issue details."""
    try:
        service = _get_service()
    except ImportError:
        console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
        console.print("  pip install -e backend/")
        sys.exit(1)

    issue = service.get_issue(issue_id)
    if not issue:
        console.print(f"[red]Issue not found:[/red] {issue_id}")
        sys.exit(1)

    tracking = issue.get("tracking_number", "")
    console.print(f"\n[bold]{tracking}: {issue.get('title', '')}[/bold]")

    info = Table.grid(padding=(0, 2))
    info.add_column(style="bold")
    info.add_column()
    info.add_row("Status", f"[{STATUS_STYLES.get(issue.get('status', ''), '')}]{issue.get('status', '')}[/]")
    info.add_row("Category", f"{CATEGORY_ICONS.get(issue.get('category', ''), '')} {issue.get('category', '')}")
    info.add_row("Severity", f"[{SEVERITY_COLORS.get(issue.get('severity', ''), '')}]{issue.get('severity', '')}[/]")
    info.add_row("Source", issue.get("source", ""))
    info.add_row("Created", _fmt_date(issue.get("created_at", "")))
    info.add_row("Updated", _fmt_date(issue.get("updated_at", "")))
    info.add_row("Reporter", issue.get("reporter_name", "Anonymous"))
    if issue.get("assigned_to"): info.add_row("Assignee", issue["assigned_to"])
    if issue.get("milestone"): info.add_row("Milestone", issue["milestone"])
    if issue.get("duplicate_of"): info.add_row("Duplicate Of", issue["duplicate_of"])
    if issue.get("github_issue_url"): info.add_row("GitHub", issue["github_issue_url"])
    if issue.get("labels"):
        info.add_row("Labels", ", ".join(f"{l}" for l in issue["labels"]))
    if issue.get("ai_summary"): info.add_row("AI Summary", issue["ai_summary"])
    console.print(Panel(info, title="Details"))

    if issue.get("description"):
        console.print(f"\n[bold]Description:[/bold]\n{issue['description']}")
    if issue.get("steps_to_reproduce"):
        console.print(f"\n[bold]Steps to Reproduce:[/bold]\n{issue['steps_to_reproduce']}")
    if issue.get("stack_trace"):
        console.print("\n[bold]Stack Trace:[/bold]")
        console.print(Syntax(issue["stack_trace"][:2000], "python", theme="monokai", word_wrap=True))
    if issue.get("ai_suggested_fix"):
        console.print(f"\n[bold]AI Suggested Fix:[/bold]\n{issue['ai_suggested_fix']}")

    comments = issue.get("comments", [])
    if comments:
        console.print(f"\n[bold]Comments ({len(comments)}):[/bold]")
        for c in comments:
            console.print(f"  [dim]{c.get('author', '?')}[/dim] at {_fmt_date(c.get('timestamp', ''))}")
            console.print(f"  {c.get('body', '')}")
            console.print()

    timeline = issue.get("timeline", [])
    if timeline and verbose:
        console.print(f"\n[bold]Timeline ({len(timeline)}):[/bold]")
        for t in timeline[-10:]:
            console.print(f"  [dim]{_fmt_date(t.get('timestamp', ''))}[/dim] {t.get('action', '')}")


def run_issue_comment(issue_id: str, body: str, verbose: bool):
    """Add a comment to an issue."""
    try:
        service = _get_service()
    except ImportError:
        console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
        console.print("  pip install -e backend/")
        sys.exit(1)

    result = service.add_comment(issue_id, {"body": body, "author": "CLI User"})
    if result:
        console.print("[green]Comment added.[/green]")
    else:
        console.print(f"[red]Issue not found:[/red] {issue_id}")
        sys.exit(1)


def run_issue_update(
    issue_id: str, status: str | None, severity: str | None,
    assign: str | None, milestone: str | None, verbose: bool,
):
    """Update an issue."""
    try:
        service = _get_service()
    except ImportError:
        console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
        console.print("  pip install -e backend/")
        sys.exit(1)

    updates = {}
    if status: updates["status"] = status
    if severity: updates["severity"] = severity
    if assign: updates["assigned_to"] = assign
    if milestone: updates["milestone"] = milestone
    updates["_actor"] = "CLI User"

    result = service.update_issue(issue_id, updates)
    if result:
        console.print(f"[green]Issue updated:[/green] {result.get('tracking_number', issue_id)}")
    else:
        console.print(f"[red]Issue not found:[/red] {issue_id}")
        sys.exit(1)


def run_issue_search(query: str, limit: int, verbose: bool):
    """Search issues."""
    try:
        service = _get_service()
    except ImportError:
        console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
        console.print("  pip install -e backend/")
        sys.exit(1)

    issues = service.list_issues(search=query, limit=limit)
    if not issues:
        console.print("[yellow]No matching issues found.[/yellow]")
        return

    table = Table(title=f"Search results for '{query}' ({len(issues)} found)")
    table.add_column("Tracking", style="cyan")
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Severity")
    for issue in issues:
        table.add_row(
            issue.get("tracking_number", ""),
            issue.get("title", "")[:60],
            issue.get("status", ""),
            issue.get("severity", ""),
        )
    console.print(table)


def run_issue_stats(verbose: bool):
    """Show issue statistics."""
    try:
        service = _get_service()
    except ImportError:
        console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
        console.print("  pip install -e backend/")
        sys.exit(1)

    stats = service.get_stats()
    sla = service.check_sla()

    table = Table(title="Issue Statistics")
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="green")
    metrics = [
        ("Total Issues", str(stats.get("total_issues", 0))),
        ("Open Issues", str(stats.get("open_issues", 0))),
        ("Resolved Issues", str(stats.get("resolved_issues", 0))),
        ("Critical Issues", str(stats.get("critical_issues", 0))),
        ("SLA Breaches", str(len(sla))),
        ("Total Comments", str(stats.get("total_comments", 0))),
    ]
    for key, value in metrics:
        table.add_row(key, value)
    console.print(table)

    if sla:
        console.print(f"\n[red]SLA Breaches ({len(sla)}):[/red]")
        for b in sla:
            console.print(f"  {b.get('tracking_number', '?')} \u2014 {b.get('severity', '?')} \u2014 {b.get('breach_hours', 0):.1f}h overdue")


def run_issue_labels(verbose: bool):
    """List issue labels."""
    try:
        service = _get_service()
    except ImportError:
        console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
        console.print("  pip install -e backend/")
        sys.exit(1)

    labels = service.list_labels()
    table = Table(title="Labels")
    table.add_column("Key", style="bold")
    table.add_column("Name")
    table.add_column("Color")
    table.add_column("Description")
    for key, label in labels.items():
        color = label.get("color", "#000")
        table.add_row(key, label.get("name", ""), f"[on #{color[1:]}]{color}[/]", label.get("description", ""))
    console.print(table)


def run_issue_backup(verbose: bool):
    """Backup issue data."""
    try:
        service = _get_service()
    except ImportError:
        console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
        console.print("  pip install -e backend/")
        sys.exit(1)

    import shutil
    from datetime import datetime

    src = service.issues_dir
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = src.parent / f"issues_backup_{ts}"
    shutil.copytree(str(src), str(dst))
    console.print(f"[green]Backup created:[/green] {dst}")
