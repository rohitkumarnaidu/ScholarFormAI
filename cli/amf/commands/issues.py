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
    console.print("[dim]This feature is now managed via the Enterprise Web Dashboard.[/dim]")


def run_issue_list(
    status: str | None, category: str | None, severity: str | None,
    label: str | None, search: str | None, limit: int, verbose: bool,
):
    """List issues via the Enterprise API."""
    console.print("[dim]This feature is now managed via the Enterprise Web Dashboard.[/dim]")


def run_issue_show(issue_id: str, verbose: bool):
    """Show issue details."""
    console.print("[dim]This feature is now managed via the Enterprise Web Dashboard.[/dim]")


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
