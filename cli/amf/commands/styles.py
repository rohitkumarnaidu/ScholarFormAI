import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()


def _get_styles():
    try:
        import requests
        response = requests.get("http://localhost:8000/api/v1/styles", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception:
        from app.services.style_registry import StyleRegistry
        registry = StyleRegistry()
        return registry.list_styles()


def list_styles():
    styles = _get_styles()

    table = Table(title="Available Formatting Styles")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Version")
    table.add_column("Citation Format")
    table.add_column("Built-in")

    for s in styles:
        table.add_row(
            s.get("id", ""),
            s.get("name", ""),
            s.get("version", ""),
            s.get("citation_format", "").upper(),
            "✓" if s.get("is_builtin", True) else "",
        )

    console.print(table)


def show_style(name: str):
    styles = _get_styles()
    style = next((s for s in styles if s["id"] == name), None)

    if not style:
        console.print(f"[red]Error:[/red] Style '{name}' not found")
        sys.exit(1)

    console.print(f"\n[bold]{style['name']}[/bold]")
    console.print(f"  ID: {style['id']}")
    console.print(f"  Version: {style['version']}")
    console.print(f"  Description: {style.get('description', 'N/A')}")
    console.print(f"  Citation Format: {style.get('citation_format', '').upper()}")
    console.print(f"  Built-in: {'Yes' if style.get('is_builtin', True) else 'No'}")

    fields = style.get("fields", {})
    if fields:
        console.print("\n  [bold]Configuration:[/bold]")
        for key, value in fields.items():
            console.print(f"    {key}: {value}")


def export_style(name: str, file: str):
    styles = _get_styles()
    style = next((s for s in styles if s["id"] == name), None)

    if not style:
        console.print(f"[red]Error:[/red] Style '{name}' not found")
        sys.exit(1)

    output_file = Path(file)
    output_file.write_text(json.dumps(style, indent=2))
    console.print(f"[green]Style '{name}' exported to {output_file}[/green]")
