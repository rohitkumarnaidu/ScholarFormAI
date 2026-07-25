import json
import logging
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from amf.config import AMFConfig

logger = logging.getLogger(__name__)
console = Console()


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

    if watch:
        _format_and_watch(input_file, output_file, style, parsed_options, config)
    else:
        _format_single(input_file, output_file, style, parsed_options, config)


def _format_single(input_file: Path, output_file: Path, style: str, options: dict, config: AMFConfig):
    console.print(f"[bold]Formatting:[/bold] {input_file.name}")
    console.print(f"[bold]Style:[/bold] {style}")
    console.print(f"[bold]Output:[/bold] {output_file}")

    try:
        text = input_file.read_text(encoding="utf-8")
    except Exception as e:
        console.print(f"[red]Error reading file:[/red] {e}")
        sys.exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description="Formatting manuscript...", total=None)
        try:
            import requests
            api_url = config.get("api_endpoint", "http://localhost:8000")

            payload = {
                "manuscript": {
                    "title": input_file.stem,
                    "sections": [{"heading": "Content", "level": 1, "content": [{"text": text}]}],
                },
                "style_id": style,
                "options": options,
            }

            response = requests.post(
                f"{api_url}/api/v1/format",
                json=payload,
                timeout=60,
            )
            response.raise_for_status()

            result = response.json()
            console.print(f"[green]Success![/green] Formatted with {style.upper()} style")
            console.print(f"[dim]Pages: {result.get('pages', 'N/A')}[/dim]")

        except ImportError:
            console.print("[yellow]Warning:[/yellow] requests not installed. Using local formatter.")

            from app.services.formatter import ManuscriptFormatter
            from app.services.style_registry import StyleRegistry
            from app.api.models import Manuscript, Paragraph, Section

            formatter = ManuscriptFormatter()
            registry = StyleRegistry()
            formatting_style = registry.get_style(style)
            if not formatting_style:
                console.print(f"[red]Error:[/red] Style '{style}' not found")
                sys.exit(1)

            manuscript = Manuscript(
                title=input_file.stem,
                sections=[Section(heading="Content", level=1, content=[Paragraph(text=text)])],
            )
            formatter.format(manuscript, formatting_style, str(output_file))
            console.print(f"[green]Success![/green] Saved to {output_file}")

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)


def _format_and_watch(input_file: Path, output_file: Path, style: str, options: dict, config: AMFConfig):
    console.print(f"[yellow]Watch mode enabled. Watching {input_file}...[/yellow]")
    console.print("Press Ctrl+C to stop.")

    last_mtime = input_file.stat().st_mtime

    try:
        while True:
            current_mtime = input_file.stat().st_mtime
            if current_mtime != last_mtime:
                console.print(f"\n[dim]File changed. Reformatting...[/dim]")
                _format_single(input_file, output_file, style, options, config)
                last_mtime = current_mtime
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Watch mode stopped.[/yellow]")
