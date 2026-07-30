"""Update management CLI commands."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import click
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.progress import BarColumn, DownloadColumn, Progress, TextColumn, TimeRemainingColumn

from amf._console import get_console, safe_progress
from amf.config import AMFConfig

logger = logging.getLogger(__name__)
console = get_console()


def _get_update_service():
    """Get or create an UpdateService instance."""
    try:
        from app.services.update_service import UpdateService
        from app import __version__
        return UpdateService(current_version=__version__)
    except ImportError:
        # Auto-discover backend directory relative to CLI root
        backend_dir = Path(__file__).resolve().parent.parent.parent.parent / "backend"
        if backend_dir.exists() and str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        from app.services.update_service import UpdateService
        from app import __version__
        return UpdateService(current_version=__version__)



def _format_size(size: int) -> str:
    if size >= 1_000_000:
        return f"{size / 1_000_000:.1f} MB"
    if size >= 1_000:
        return f"{size / 1_000:.1f} KB"
    return f"{size} B"


def run_update_check(channel: str | None = None, json_output: bool = False, verbose: bool = False):
    """Check for available updates."""
    try:
        service = _get_update_service()
    except ImportError:
        if json_output:
            console.print(json.dumps({"error": "Backend modules not available"}))
        else:
            console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
            console.print("  pip install -e backend/")
        sys.exit(1)

    with safe_progress() as progress:
        progress.add_task(description="Checking for updates...")
        try:
            result = service.check_for_updates(channel=channel)
        except Exception as e:
            if json_output:
                console.print(json.dumps({"error": f"Update check failed: {e}"}))
            else:
                console.print(f"[red]Error:[/red] Update check failed: {e}")
            sys.exit(1)

    if json_output:
        console.print(json.dumps(result, indent=2))
        return

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


def run_update_channel(channel_name: str | None = None, json_output: bool = False, verbose: bool = False):
    """List or switch release channels."""
    try:
        service = _get_update_service()
    except ImportError:
        if json_output:
            console.print(json.dumps({"error": "Backend modules not available"}))
        else:
            console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
        sys.exit(1)

    if channel_name:
        valid_channels = [c["id"] for c in service.get_channels()]
        if channel_name not in valid_channels:
            if json_output:
                console.print(json.dumps({"error": f"Invalid channel: {channel_name}. Valid: {valid_channels}"}))
            else:
                console.print(f"[red]Error:[/red] Invalid channel '[bold]{channel_name}[/bold]'. Must be one of: {', '.join(valid_channels)}")
            sys.exit(1)

        service.update_settings({"channel": channel_name})
        if not json_output:
            console.print(f"[green]Switched active release channel to:[/green] [bold cyan]{channel_name}[/bold cyan]")

    current_channel = service.get_settings().get("channel", "stable")
    channels = service.get_channels()

    if json_output:
        console.print(json.dumps({"current_channel": current_channel, "channels": channels}, indent=2))
        return

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
    console.print("Switch channel: [bold]amf update channel <name>[/bold]")


def run_update_channels(verbose: bool = False):
    """Alias for run_update_channel."""
    run_update_channel(channel_name=None, json_output=False, verbose=verbose)


def run_update_download(version: str | None = None, retry: int = 3, json_output: bool = False, verbose: bool = False):
    """Download an update payload with retry resilience and verification."""
    try:
        service = _get_update_service()
    except ImportError:
        if json_output:
            console.print(json.dumps({"error": "Backend modules not available"}))
        else:
            console.print("[red]Error:[/red] Backend modules not available. Install the backend package.")
        sys.exit(1)

    check_result = service.check_for_updates()
    if check_result.get("status") != "update-available" and not version:
        if json_output:
            console.print(json.dumps({"status": "no_update", "message": "No updates available."}))
        else:
            console.print("[green]No updates available.[/green]")
        return

    update = check_result.get("update", {})
    target_version = version or update.get("version")

    if not target_version:
        if json_output:
            console.print(json.dumps({"error": "No update version specified or available."}))
        else:
            console.print("[red]Error:[/red] No update version specified or available.")
        sys.exit(1)

    if not json_output:
        console.print(f"[bold]Downloading[/bold] AMF v{target_version} (retries={retry})...")
        console.print(f"  Size: {_format_size(update.get('size', 0))}")

    result = {}
    if not json_output:
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

            result = service.download_update_with_retry(version=target_version, max_retries=retry, progress_callback=_on_progress)
    else:
        result = service.download_update_with_retry(version=target_version, max_retries=retry)

    if json_output:
        console.print(json.dumps(result, indent=2))
        return

    if result.get("success"):
        console.print(f"[green]Downloaded:[/green] {result.get('path')}")
        checksum_ok = result.get("checksum_valid")
        if checksum_ok is False:
            console.print("[red]Warning:[/red] SHA-256 Checksum verification failed!")
        elif checksum_ok is True:
            console.print("[green]SHA-256 Checksum verified.[/green]")

        console.print()
        console.print("Run [bold]amf update install[/bold] to install this update")
    else:
        console.print(f"[red]Download failed:[/red] {result.get('error', 'Unknown error')}")
        sys.exit(1)


def run_update_verify(
    file_path: str | None = None,
    checksum: str | None = None,
    signature: str | None = None,
    public_key: str | None = None,
    json_output: bool = False,
    verbose: bool = False,
):
    """Standalone command to verify local asset checksum and digital signature."""
    try:
        service = _get_update_service()
    except ImportError:
        if json_output:
            console.print(json.dumps({"error": "Backend modules not available"}))
        else:
            console.print("[red]Error:[/red] Backend modules not available. Install backend package.")
        sys.exit(1)

    if not file_path:
        dl_path = getattr(service, "_downloaded_path", None)
        if dl_path and Path(dl_path).exists():
            file_path = str(dl_path)
        else:
            updates_dir = service.update_dir
            if updates_dir.exists():
                files = sorted(updates_dir.glob("amf-*"), key=lambda f: f.stat().st_mtime, reverse=True)
                if files:
                    file_path = str(files[0])

    if not file_path:
        if json_output:
            console.print(json.dumps({"error": "No target file provided for verification."}))
        else:
            console.print("[red]Error:[/red] No file provided for verification. Use --file <path>.")
        sys.exit(1)

    res = service.verify_asset_integrity(
        file_path=file_path,
        expected_checksum=checksum,
        signature=signature,
        public_key=public_key,
    )

    if json_output:
        console.print(json.dumps(res, indent=2))
        return

    table = Table(title=f"Verification Report: {res.get('file_name', 'Asset')}")
    table.add_column("Property", style="bold")
    table.add_column("Details")
    table.add_column("Status")

    table.add_row("File Path", res.get("path", file_path), "[green]Exists[/green]" if res.get("exists") else "[red]Missing[/red]")
    table.add_row("Size", _format_size(res.get("size_bytes", 0)), "[dim]OK[/dim]")
    table.add_row("Calculated SHA-256", res.get("calculated_sha256", "N/A"), "[dim]Digest[/dim]")

    if checksum:
        chk_status = "[green]Passed[/green]" if res.get("checksum_valid") else "[red]Failed[/red]"
        table.add_row("Expected Checksum", checksum, chk_status)

    if signature:
        sig_status = "[green]Verified[/green]" if res.get("signature_valid") else "[red]Invalid Signature[/red]"
        table.add_row("ED25519/RSA Signature", signature[:20] + "..." if len(signature) > 20 else signature, sig_status)

    overall = "[bold green]VERIFIED VALID[/bold green]" if res.get("valid") else "[bold red]VERIFICATION FAILED[/bold red]"
    table.add_row("Overall Result", overall, "")

    console.print(table)
    if not res.get("valid"):
        sys.exit(1)


def run_update_install(version: str | None = None, file_path: str | None = None, json_output: bool = False, verbose: bool = False):
    """Execute atomic installation with automatic snapshot/backup creation."""
    try:
        service = _get_update_service()
    except ImportError:
        if json_output:
            console.print(json.dumps({"error": "Backend modules not available"}))
        else:
            console.print("[red]Error:[/red] Backend modules not available.")
        sys.exit(1)

    if not json_output:
        with safe_progress() as progress:
            progress.add_task(description="Creating backup snapshot and installing update...")
            result = service.install_update(version=version, source_path=file_path)
    else:
        result = service.install_update(version=version, source_path=file_path)

    if json_output:
        console.print(json.dumps(result, indent=2))
        return

    if result.get("success"):
        console.print(f"[green]Installed:[/green] v{result.get('version')}")
        if result.get("previous_version"):
            console.print(f"  Previous version: {result['previous_version']}")
        if result.get("backup_path"):
            console.print(f"  Backup snapshot: [cyan]{result['backup_path']}[/cyan]")
        console.print()
        console.print("[yellow]Please restart the application to apply the update.[/yellow]")
    else:
        console.print(f"[red]Installation failed:[/red] {result.get('error', 'Unknown error')}")
        sys.exit(1)


def run_update_offline(
    archive_path: str,
    signature: str | None = None,
    public_key: str | None = None,
    json_output: bool = False,
    verbose: bool = False,
):
    """Install update from local offline .tar.gz or .zip archive package with signature validation."""
    try:
        service = _get_update_service()
    except ImportError:
        if json_output:
            console.print(json.dumps({"error": "Backend modules not available"}))
        else:
            console.print("[red]Error:[/red] Backend modules not available.")
        sys.exit(1)

    path = Path(archive_path)
    if not path.exists():
        if json_output:
            console.print(json.dumps({"error": f"Offline package not found: {path}"}))
        else:
            console.print(f"[red]Error:[/red] Offline package file not found: [bold]{archive_path}[/bold]")
        sys.exit(1)

    if not json_output:
        console.print(f"[bold]Installing offline update package:[/bold] {path.name}...")

    result = service.install_offline_update(archive_path=path, signature=signature, public_key=public_key)

    if json_output:
        console.print(json.dumps(result, indent=2))
        return

    if result.get("success"):
        console.print(f"[green]Successfully installed offline update:[/green] v{result.get('version')}")
        if result.get("backup_path"):
            console.print(f"  Backup created at: [cyan]{result['backup_path']}[/cyan]")
        console.print("\n[yellow]Please restart the application.[/yellow]")
    else:
        console.print(f"[red]Offline installation failed:[/red] {result.get('error', 'Unknown error')}")
        sys.exit(1)


def run_update_rollback(version: str | None = None, json_output: bool = False, verbose: bool = False):
    """Roll back to previous version or specified version tag using backup snapshot."""
    try:
        service = _get_update_service()
    except ImportError:
        if json_output:
            console.print(json.dumps({"error": "Backend modules not available"}))
        else:
            console.print("[red]Error:[/red] Backend modules not available.")
        sys.exit(1)

    if not json_output:
        with safe_progress() as progress:
            progress.add_task(description="Rolling back to backup snapshot...")
            result = service.rollback(target_version=version)
    else:
        result = service.rollback(target_version=version)

    if json_output:
        console.print(json.dumps(result, indent=2))
        return

    if result.get("success"):
        console.print(f"[green]Rolled back to:[/green] v{result.get('version')}")
        console.print("[yellow]Please restart the application.[/yellow]")
    else:
        console.print(f"[red]Rollback failed:[/red] {result.get('error', 'Unknown error')}")
        sys.exit(1)


def run_update_history(limit: int = 20, json_output: bool = False, verbose: bool = False):
    """Show update history."""
    try:
        service = _get_update_service()
    except ImportError:
        if json_output:
            console.print(json.dumps({"error": "Backend modules not available"}))
        else:
            console.print("[red]Error:[/red] Backend modules not available.")
        sys.exit(1)

    history = service.get_history(limit=limit)

    if json_output:
        console.print(json.dumps({"history": history}, indent=2))
        return

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
        ver = entry.get("version", "?")
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

        table.add_row(ver, channel, date_str, status, notes)

    console.print(table)


def run_update_settings(
    channel: str | None = None,
    auto_check: bool | None = None,
    auto_download: bool | None = None,
    auto_install: bool | None = None,
    verify_signature: bool | None = None,
    verify_checksum: bool | None = None,
    reset: bool = False,
    json_output: bool = False,
    verbose: bool = False,
):
    """View or modify update settings."""
    try:
        service = _get_update_service()
    except ImportError:
        if json_output:
            console.print(json.dumps({"error": "Backend modules not available"}))
        else:
            console.print("[red]Error:[/red] Backend modules not available.")
        sys.exit(1)

    if reset:
        from app.services.update_service import DEFAULT_SETTINGS
        service._settings = dict(DEFAULT_SETTINGS)
        service._save_settings()

    updates = {}
    if channel:
        updates["channel"] = channel
    if auto_check is not None:
        updates["auto_check"] = auto_check
    if auto_download is not None:
        updates["auto_download"] = auto_download
    if auto_install is not None:
        updates["auto_install"] = auto_install
    if verify_signature is not None:
        updates["verify_signature"] = verify_signature
    if verify_checksum is not None:
        updates["verify_checksum"] = verify_checksum

    if updates:
        service.update_settings(updates)
        if not json_output:
            console.print("[green]Settings updated.[/green]")

    settings = service.get_settings()

    if json_output:
        console.print(json.dumps(settings, indent=2))
        return

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


def run_update_release_notes(version: str | None = None, json_output: bool = False, verbose: bool = False):
    """Show release notes for a specific version using Rich Markdown."""
    try:
        service = _get_update_service()
    except ImportError:
        if json_output:
            console.print(json.dumps({"error": "Backend modules not available"}))
        else:
            console.print("[red]Error:[/red] Backend modules not available.")
        sys.exit(1)

    target_ver = version
    if not target_ver:
        chk = service.check_for_updates()
        target_ver = chk.get("latest_version") or service.current_version

    with safe_progress() as progress:
        progress.add_task(description=f"Fetching release notes for v{target_ver}...")
        result = service.get_release_notes(target_ver)

    if json_output:
        console.print(json.dumps(result, indent=2))
        return

    if not result.get("found"):
        console.print(f"[red]Release not found:[/red] v{target_ver}")
        sys.exit(1)

    console.print(f"\n[bold green]{result.get('name', f'v{target_ver}')}[/bold green]")
    console.print(f"  Published: {result.get('published_at', '?')}")
    if result.get("author"):
        console.print(f"  Author: {result['author']}")
    if result.get("prerelease"):
        console.print("  [yellow]Pre-release[/yellow]")
    if result.get("html_url"):
        console.print(f"  URL: {result['html_url']}")

    if result.get("body"):
        console.print("\n[bold]Release Notes:[/bold]")
        console.print(Markdown(result["body"]))
    elif result.get("changelog"):
        console.print("\n[bold]Changes:[/bold]")
        for line in result["changelog"]:
            console.print(f"  {line}")
