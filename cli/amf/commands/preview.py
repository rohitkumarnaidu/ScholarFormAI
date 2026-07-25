import logging
import sys
import tempfile
import webbrowser
from pathlib import Path

from amf._client import BackendClient
from amf._console import get_console, safe_progress
from amf.config import AMFConfig

logger = logging.getLogger(__name__)
console = get_console()


def run_preview(input_path: str, style: str, output_path: str, open_browser: bool, verbose: bool):
    input_file = Path(input_path)
    if not input_file.exists():
        console.print(f"[red]Error:[/red] Input file not found: {input_path}")
        sys.exit(1)

    console.print(f"[bold]Generating preview for:[/bold] {input_file.name}")
    console.print(f"[bold]Style:[/bold] {style}")

    client = BackendClient(AMFConfig())

    html = None
    with safe_progress() as progress:
        progress.add_task(description="Generating preview...")
        try:
            html = client.preview(input_file, style)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)

    if not html:
        console.print("[red]Error:[/red] No preview generated")
        sys.exit(1)

    if output_path:
        output_file = Path(output_path)
    else:
        output_file = Path(tempfile.mktemp(suffix=".html"))

    output_file.write_text(html, encoding="utf-8")
    console.print(f"[green]Preview saved to:[/green] {output_file}")

    if open_browser or not output_path:
        webbrowser.open(f"file://{output_file.absolute()}")
        console.print(f"[dim]Preview opened in browser: {output_file}[/dim]")
    else:
        console.print(html[:500] + "...")
