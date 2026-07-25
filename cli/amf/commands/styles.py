import json
import logging
import sys
from pathlib import Path

from amf._client import BackendClient
from amf._output import print_styles_table
from amf._console import get_console
from amf.config import AMFConfig

logger = logging.getLogger(__name__)
console = get_console()


def _get_client() -> BackendClient:
    return BackendClient(AMFConfig())


def list_styles():
    client = _get_client()
    try:
        styles = client.list_styles()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    table_rows = []
    for s in styles:
        table_rows.append({
            "id": s.get("id", ""),
            "name": s.get("name", ""),
            "version": s.get("version", ""),
            "citation_format": s.get("citation_format", "").upper(),
        })
    print_styles_table(styles)


def show_style(name: str):
    client = _get_client()
    try:
        styles = client.list_styles()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    style = next((s for s in styles if s["id"] == name), None)
    if not style:
        console.print(f"[red]Error:[/red] Style '{name}' not found")
        sys.exit(1)

    console.print(f"\n[bold]{style['name']}[/bold]")
    console.print(f"  ID: {style['id']}")
    console.print(f"  Version: {style['version']}")
    console.print(f"  Description: {style.get('description', 'N/A')}")
    console.print(f"  Citation Format: {style.get('citation_format', '').upper()}")

    fields = style.get("fields", {})
    if fields:
        console.print("\n  [bold]Configuration:[/bold]")
        for key, value in fields.items():
            console.print(f"    {key}: {value}")


def export_style(name: str, file: str):
    client = _get_client()
    try:
        styles = client.list_styles()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    style = next((s for s in styles if s["id"] == name), None)
    if not style:
        console.print(f"[red]Error:[/red] Style '{name}' not found")
        sys.exit(1)

    output_file = Path(file)
    output_file.write_text(json.dumps(style, indent=2))
    console.print(f"[green]Style '{name}' exported to {output_file}[/green]")
