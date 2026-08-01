"""Update management CLI commands."""

import logging
import sys
from datetime import datetime

from rich.panel import Panel
from rich.table import Table
from rich.progress import BarColumn, DownloadColumn, Progress, TextColumn, TimeRemainingColumn

from amf._console import get_console, safe_progress

logger = logging.getLogger(__name__)
console = get_console()


def _get_update_service():
    """Get or create an UpdateService instance."""
    from app.services.update_service import UpdateService
    from app import __version__
    return UpdateService(current_version=__version__)


def run_update_check(channel: str | None = None, verbose: bool = False):
    """Check for available updates."""
    try:
        service = _get_update_service()
    except ImportError:
        console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
        console.print("  pip install -e backend/")
        sys.exit(1)

    with safe_progress() as progress:
        progress.add_task(description="Checking for updates...")
        try:
            result = service.check_for_updates(channel=channel)
        except Exception as e:
            console.print(f"[red]Error:[/red] Update check failed: {e}")
            sys.exit(1)

    console.print()
    status = result.get("status", "error")
    current = result.get("current_version", "?")
    latest = result.get("latest_version")

    if status == "up-to-date":
        console.print(Panel(
            f"[green]You are up to date![/green]\n\n"
            f"  Current version: [bold]{current}[/bold]\n"
            f"  Checked at: {result.get('checked_at', '?')}",
            title="Update Status",
        ))
    elif status == "update-available":
        update = result.get("update", {})
        console.print(Panel(
            f"[yellow]Update available![/yellow]\n\n"
            f"  Current version: [bold]{current}[/bold]\n"
            f"  Latest version:  [bold green]{latest}[/bold green]\n"
            f"  Channel:         {update.get('channel', '?')}\n"
            f"  Published:       {update.get('published_at', '?')}\n"
            f"  Size:            {_format_size(update.get('size', 0))}\n"
            f"  {'[red]SECURITY UPDATE[/red]' if update.get('is_security') else ''}"
            f"  {'[red]MANDATORY[/red]' if update.get('is_mandatory') else ''}",
            title="Update Available",
        ))

        if update.get("changelog"):
            console.print("\n[bold]What's new:[/bold]")
            for line in update["changelog"][:10]:
                console.print(f"  {line}")
            if len(update["changelog"]) > 10:
                console.print(f"  ... and {len(update['changelog']) - 10} more changes")

        console.print()
        console.print("Run [bold]amf update download[/bold] to download this update")
    else:
        console.print(f"[red]Error checking updates:[/red] {result.get('error', 'Unknown error')}")
        sys.exit(1)


def _format_size(size: int) -> str:
    if size >= 1_000_000:
        return f"{size / 1_000_000:.1f} MB"
    if size >= 1_000:
        return f"{size / 1_000:.1f} KB"
    return f"{size} B"


def run_update_download(version: str | None = None, verbose: bool = False):
    """Download an update."""
    try:
        service = _get_update_service()
    except ImportError:
        console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
        console.print("  pip install -e backend/")
        sys.exit(1)

    check_result = service.check_for_updates()
    if check_result.get("status") != "update-available" and not version:
        console.print("[green]No updates available.[/green]")
        return

    update = check_result.get("update", {})
    target_version = version or update.get("version")

    if not target_version:
        console.print("[red]Error:[/red] No update version specified or available.")
        sys.exit(1)

    console.print(f"[bold]Downloading[/bold] AMF v{target_version}...")
    console.print(f"  Size: {_format_size(update.get('size', 0))}")

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(description="Downloading...", total=update.get("size", 0) or None)

        def _on_progress(downloaded: int, total: int):
            if total:
                progress.update(task, completed=downloaded, total=total)
            else:
                progress.update(task, completed=downloaded)

        result = service.download_update(version=target_version, progress_callback=_on_progress)

    if result.get("success"):
        console.print(f"[green]Downloaded:[/green] {result.get('path')}")
        checksum_ok = result.get("checksum_valid")
        if checksum_ok is False:
            console.print("[red]Warning:[/red] Checksum verification failed!")
        elif checksum_ok is True:
            console.print("[green]Checksum verified.[/green]")

        console.print()
        console.print("Run [bold]amf update install[/bold] to install this update")
    else:
        console.print(f"[red]Download failed:[/red] {result.get('error', 'Unknown error')}")
        sys.exit(1)


def run_update_install(verbose: bool = False):
    """Install a downloaded update."""
    try:
        service = _get_update_service()
    except ImportError:
        console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
        console.print("  pip install -e backend/")
        sys.exit(1)

    with safe_progress() as progress:
        progress.add_task(description="Installing update...")
        result = service.install_update()

    if result.get("success"):
        console.print(f"[green]Installed:[/green] v{result.get('version')}")
        if result.get("previous_version"):
            console.print(f"  Previous version: {result['previous_version']}")
        if result.get("backup_path"):
            console.print(f"  Backup: {result['backup_path']}")
        console.print()
        console.print("[yellow]Please restart the application to apply the update.[/yellow]")
    else:
        console.print(f"[red]Installation failed:[/red] {result.get('error', 'Unknown error')}")
        sys.exit(1)


def run_update_rollback(version: str | None = None, verbose: bool = False):
    """Rollback to a previous version."""
    try:
        service = _get_update_service()
    except ImportError:
        console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
        console.print("  pip install -e backend/")
        sys.exit(1)

    with safe_progress() as progress:
        progress.add_task(description="Rolling back...")
        result = service.rollback(target_version=version)

    if result.get("success"):
        console.print(f"[green]Rolled back to:[/green] v{result.get('version')}")
        console.print("[yellow]Please restart the application.[/yellow]")
    else:
        console.print(f"[red]Rollback failed:[/red] {result.get('error', 'Unknown error')}")
        sys.exit(1)


def run_update_history(limit: int = 20, verbose: bool = False):
    """Show update history."""
    try:
        service = _get_update_service()
    except ImportError:
        console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
        console.print("  pip install -e backend/")
        sys.exit(1)

    history = service.get_history(limit=limit)

    if not history:
        console.print("[yellow]No update history found.[/yellow]")
        return

    table = Table(title=f"Update History (last {len(history)} entries)")
    table.add_column("Version", style="bold")
    table.add_column("Channel", style="cyan")
    table.add_column("Date", style="green")
    table.add_column("Status")
    table.add_column("Notes")

    for entry in history:
        version = entry.get("version", "?")
        channel = entry.get("channel", "?")
        installed = entry.get("installed_at", "?")
        try:
            date_str = datetime.fromisoformat(installed).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            date_str = installed

        if entry.get("rolled_back"):
            status = "[yellow]Rolled Back[/yellow]"
        elif entry.get("success"):
            status = "[green]Success[/green]"
        else:
            status = "[red]Failed[/red]"

        notes = ""
        if entry.get("error_message"):
            notes = entry["error_message"][:50]
        if entry.get("rollback_version"):
            notes = f"\u2192 v{entry['rollback_version']}"

        table.add_row(version, channel, date_str, status, notes)

    console.print(table)


def run_update_channels(verbose: bool = False):
    """List available release channels."""
    try:
        service = _get_update_service()
    except ImportError:
        console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
        console.print("  pip install -e backend/")
        sys.exit(1)

    channels = service.get_channels()
    current_channel = service.get_settings().get("channel", "stable")

    table = Table(title="Release Channels")
    table.add_column("Channel", style="bold")
    table.add_column("Description")
    table.add_column("Status")

    for ch in channels:
        is_active = ch["id"] == current_channel
        status = "[green]Active[/green]" if is_active else ""
        name = ch["name"]
        if ch.get("recommended"):
            name += " [blue](Recommended)[/blue]"
        table.add_row(f"[cyan]{ch['id']}[/cyan]", ch.get("description", ""), status)

    console.print(table)
    console.print()
    console.print("Change channel: [bold]amf update settings --channel <name>[/bold]")


def run_update_settings(
    channel: str | None = None,
    auto_check: bool | None = None,
    auto_download: bool | None = None,
    auto_install: bool | None = None,
    verbose: bool = False,
):
    """View or modify update settings."""
    try:
        service = _get_update_service()
    except ImportError:
        console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
        console.print("  pip install -e backend/")
        sys.exit(1)

    updates = {}
    if channel:
        updates["channel"] = channel
    if auto_check is not None:
        updates["auto_check"] = auto_check
    if auto_download is not None:
        updates["auto_download"] = auto_download
    if auto_install is not None:
        updates["auto_install"] = auto_install

    if updates:
        service.update_settings(updates)
        console.print("[green]Settings updated.[/green]")

    settings = service.get_settings()

    table = Table(title="Update Settings")
    table.add_column("Setting", style="bold")
    table.add_column("Value")
    table.add_column("Description")

    descriptions = {
        "channel": "Release channel",
        "auto_check": "Auto-check for updates",
        "auto_download": "Auto-download updates",
        "auto_install": "Auto-install updates",
        "auto_restart": "Auto-restart after update",
        "check_frequency_hours": "Check frequency (hours)",
        "notify_on_optional": "Notify for optional updates",
        "notify_on_security": "Notify for security updates",
        "check_at_startup": "Check at startup",
        "background_download": "Background download",
        "proxy_url": "Proxy URL",
        "verify_signature": "Verify signatures",
        "verify_checksum": "Verify checksums",
    }

    for key, desc in descriptions.items():
        value = settings.get(key)
        if isinstance(value, bool):
            value_str = "[green]Enabled[/green]" if value else "[dim]Disabled[/dim]"
        elif value is None:
            value_str = "[dim]Not set[/dim]"
        else:
            value_str = str(value)
        table.add_row(key, value_str, desc)

    console.print(table)
    console.print(f"\n[dim]Config file: {service.settings_file}[/dim]")


def run_update_release_notes(version: str, verbose: bool = False):
    """Show release notes for a specific version."""
    try:
        service = _get_update_service()
    except ImportError:
        console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
        console.print("  pip install -e backend/")
        sys.exit(1)

    with safe_progress() as progress:
        progress.add_task(description="Fetching release notes...")
        result = service.get_release_notes(version)

    if not result.get("found"):
        console.print(f"[red]Release not found:[/red] v{version}")
        sys.exit(1)

    console.print(f"\n[bold]{result.get('name', f'v{version}')}[/bold]")
    console.print(f"  Published: {result.get('published_at', '?')}")
    if result.get("author"):
        console.print(f"  Author: {result['author']}")
    if result.get("prerelease"):
        console.print("  [yellow]Pre-release[/yellow]")
    if result.get("html_url"):
        console.print(f"  URL: {result['html_url']}")

    if result.get("changelog"):
        console.print(f"\n[bold]Changes:[/bold]")
        for line in result["changelog"]:
            console.print(f"  {line}")
    elif result.get("body"):
        console.print(f"\n[bold]Release body:[/bold]")
        console.print(result["body"])
