import json
import logging
import sys
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from amf._client import BackendClient
from amf._console import get_console, safe_progress
from amf.config import AMFConfig

logger = logging.getLogger(__name__)
console = get_console()


class ManuscriptChangeHandler(FileSystemEventHandler):
    """Event handler that triggers manuscript reformatting when the watched file changes."""

    def __init__(self, client: BackendClient, input_file: Path, output_file: Path, style: str, options: dict):
        super().__init__()
        self.client = client
        self.input_file = input_file.resolve()
        self.output_file = output_file
        self.style = style
        self.options = options

    def on_modified(self, event):
        if not event.is_directory and Path(event.src_path).resolve() == self.input_file:
            console.print("\n[dim]File changed. Reformatting...[/dim]")
            _format_single(self.client, self.input_file, self.output_file, self.style, self.options)


def run_format(input_path: str, output_path: str, style: str, options_str: str, watch: bool, verbose: bool):
    input_file = Path(input_path)
    if not input_file.exists():
        console.print(f"[red]Error:[/red] Input file not found: {input_path}")
        sys.exit(1)

    config = AMFConfig()
    parsed_options = {}
    if options_str:
        try:
            parsed_options = json.loads(options_str)
        except json.JSONDecodeError:
            console.print("[red]Error:[/red] Invalid JSON in --options")
            sys.exit(1)

    output_file = Path(output_path) if output_path else input_file.with_stem(f"{input_file.stem}_formatted").with_suffix(".docx")

    client = BackendClient(config)

    if watch:
        _format_and_watch(client, input_file, output_file, style, parsed_options)
    else:
        _format_single(client, input_file, output_file, style, parsed_options)


def _format_single(client: BackendClient, input_file: Path, output_file: Path, style: str, options: dict):
    console.print(f"[bold]Formatting:[/bold] {input_file.name}")
    console.print(f"[bold]Style:[/bold] {style}")
    console.print(f"[bold]Output:[/bold] {output_file}")

    try:
        text = input_file.read_text(encoding="utf-8")
    except Exception as e:
        console.print(f"[red]Error reading file:[/red] {e}")
        sys.exit(1)

    with safe_progress() as progress:
        progress.add_task(description="Formatting manuscript...")
        try:
            result = client.format(input_file, output_file, style, options)
            console.print(f"[green]Success![/green] Formatted with {style.upper()} style")
            console.print(f"[dim]Pages: {result.get('pages', 'N/A')}[/dim]")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


def _format_and_watch(client: BackendClient, input_file: Path, output_file: Path, style: str, options: dict):
    console.print(f"[yellow]Watch mode enabled. Watching {input_file}...[/yellow]")
    console.print("Press Ctrl+C to stop.")

    event_handler = ManuscriptChangeHandler(client, input_file, output_file, style, options)
    observer = Observer()
    observer.schedule(event_handler, path=str(input_file.parent.resolve()), recursive=False)
    observer.start()

    try:
        observer.join()
    except KeyboardInterrupt:
        observer.stop()
        console.print("\n[yellow]Watch mode stopped.[/yellow]")
    observer.join()

