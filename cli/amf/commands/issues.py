"""Issue reporting CLI commands."""

import logging
import sys
import json
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error

from rich.panel import Panel
from rich.table import Table

from amf._console import get_console

logger = logging.getLogger(__name__)
console = get_console()

API_URL = "http://localhost:8000/api/v1/issues"


def _get_system_info():
    import platform
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "python_version": platform.python_version(),
        "hostname": platform.node(),
        "platform": platform.platform(),
    }


def run_issue_report(
    title: str, description: str, category: str, severity: str,
    name: str | None, email: str | None, anonymous: bool,
    attach_logs: bool, verbose: bool,
):
    """Report a new issue via the Enterprise API."""
    system_info = _get_system_info() if not anonymous else {}
    logs = ""
    
    if attach_logs:
        log_paths = [
            Path.home() / ".amf" / "logs" / "app.log",
            Path.home() / ".amf" / "logs" / "error.log",
        ]
        for p in log_paths:
            if p.exists():
                try:
                    logs += f"--- {p.name} ---\n" + p.read_text(encoding="utf-8", errors="replace")[-5000:] + "\n\n"
                except Exception:
                    pass

    payload = {
        "title": title,
        "description": description,
        "category": category,
        "severity": severity,
        "source": "cli",
        "reporter_name": name or "",
        "reporter_email": email or "",
        "anonymous": anonymous,
        "system_info": system_info,
        "logs": logs
    }

    try:
        req = urllib.request.Request(API_URL, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            console.print(f"[bold green]Success![/bold green] Issue reported successfully.")
            console.print(f"Tracking Number: [bold]{result.get('tracking_number')}[/bold]")
            if result.get('labels'):
                console.print(f"AI Categorization: {', '.join(result['labels'])}")
    except urllib.error.URLError as e:
        console.print(f"[bold red]Failed to report issue:[/bold red] API unreachable ({API_URL})")
        if verbose:
            console.print_exception()


def run_issue_list(
    status: str | None, category: str | None, severity: str | None,
    label: str | None, search: str | None, limit: int, verbose: bool,
):
    """List issues via the Enterprise API."""
    url = f"{API_URL}?limit={limit}"
    if status: url += f"&status={status}"
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            issues = data.get("issues", [])
            
            table = Table(title="Issues")
            table.add_column("Tracking #", style="cyan")
            table.add_column("Title")
            table.add_column("Status", style="green")
            table.add_column("Category")

            for issue in issues:
                table.add_row(
                    issue.get("tracking_number"),
                    issue.get("title")[:50],
                    issue.get("status"),
                    issue.get("category")
                )
            console.print(table)
    except Exception as e:
        console.print(f"[bold red]Failed to list issues:[/bold red] {e}")


def run_issue_show(issue_id: str, verbose: bool):
    """Show issue details."""
    url = f"{API_URL}/{issue_id}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            issue = json.loads(response.read().decode('utf-8'))
            panel = Panel(
                f"[bold]{issue.get('title')}[/bold]\n\n{issue.get('description')}\n\n"
                f"[dim]Status: {issue.get('status')} | Category: {issue.get('category')}[/dim]",
                title=issue.get('tracking_number')
            )
            console.print(panel)
    except Exception as e:
        console.print(f"[bold red]Failed to fetch issue:[/bold red] {e}")


def run_issue_comment(issue_id: str, body: str, verbose: bool):
    console.print("[dim]This feature is now managed via the Enterprise Web Dashboard.[/dim]")


def run_issue_update(issue_id: str, status, severity, assign, milestone, verbose: bool):
    console.print("[dim]This feature is now managed via the Enterprise Web Dashboard.[/dim]")


def run_issue_search(query: str, limit: int, verbose: bool):
    console.print("[dim]This feature is now managed via the Enterprise Web Dashboard.[/dim]")


def run_issue_stats(verbose: bool):
    console.print("[dim]This feature is now managed via the Enterprise Web Dashboard.[/dim]")


def run_issue_labels(verbose: bool):
    console.print("[dim]This feature is now managed via the Enterprise Web Dashboard.[/dim]")


def run_issue_backup(verbose: bool):
    console.print("[dim]This feature is now managed via the Enterprise Web Dashboard.[/dim]")
