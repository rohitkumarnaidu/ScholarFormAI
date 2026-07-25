import sys
import tempfile
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()


def run_preview(input_path: str, style: str, output_path: str, open_browser: bool, verbose: bool):
    input_file = Path(input_path)
    if not input_file.exists():
        console.print(f"[red]Error:[/red] Input file not found: {input_path}")
        sys.exit(1)

    try:
        text = input_file.read_text(encoding="utf-8")
    except Exception as e:
        console.print(f"[red]Error reading file:[/red] {e}")
        sys.exit(1)

    console.print(f"[bold]Generating preview for:[/bold] {input_file.name}")
    console.print(f"[bold]Style:[/bold] {style}")

    html = None
    try:
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
        html = formatter.generate_html_preview(manuscript, formatting_style)

    except ImportError:
        console.print("[yellow]Local formatter not available. Trying API...[/yellow]")
        try:
            import requests

            payload = {
                "manuscript": {"title": input_file.stem, "sections": [{"heading": "Content", "level": 1, "content": [{"text": text}]}]},
                "style_id": style,
            }

            response = requests.post(
                "http://localhost:8000/api/v1/preview",
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            html = response.json().get("html", "")

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)

    if not html:
        console.print("[red]Error:[/red] No preview generated")
        sys.exit(1)

    if output_path:
        output_file = Path(output_path)
        output_file.write_text(html, encoding="utf-8")
        console.print(f"[green]Preview saved to:[/green] {output_file}")
    else:
        output_file = Path(tempfile.mktemp(suffix=".html"))
        output_file.write_text(html, encoding="utf-8")

    if open_browser or not output_path:
        import webbrowser
        webbrowser.open(f"file://{output_file.absolute()}")
        console.print(f"[dim]Preview opened in browser: {output_file}[/dim]")
    else:
        console.print(Panel(html[:500] + "...", title="Preview (first 500 chars)"))
