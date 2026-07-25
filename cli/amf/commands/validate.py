import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()


def run_validate(input_path: str, style: str, output_path: str, verbose: bool):
    input_file = Path(input_path)
    if not input_file.exists():
        console.print(f"[red]Error:[/red] Input file not found: {input_path}")
        sys.exit(1)

    try:
        text = input_file.read_text(encoding="utf-8")
    except Exception as e:
        console.print(f"[red]Error reading file:[/red] {e}")
        sys.exit(1)

    console.print(f"[bold]Validating:[/bold] {input_file.name}")
    console.print(f"[bold]Style:[/bold] {style}")
    console.print()

    try:
        from app.services.validator import ManuscriptValidator
        from app.services.parser import ManuscriptParser

        parser = ManuscriptParser()
        manuscript = parser.parse(text)

        validator = ManuscriptValidator()
        result = validator.validate(manuscript, style)

    except ImportError:
        console.print("[yellow]Warning:[/yellow] Local validator not available. Trying API...")
        try:
            import requests

            payload = {
                "manuscript": {"title": input_file.stem},
                "style_id": style,
            }

            response = requests.post(
                "http://localhost:8000/api/v1/validate",
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)

    if output_path:
        Path(output_path).write_text(json.dumps(result, indent=2))
        console.print(f"[dim]Report saved to: {output_path}[/dim]")

    if result["valid"]:
        console.print(Panel("[green]✓ Manuscript is valid[/green]", title="Validation Result"))
    else:
        console.print(Panel(f"[red]✗ Manuscript has {len(result['errors'])} error(s)[/red]", title="Validation Result"))

    if result["errors"]:
        table = Table(title="Errors", style="red")
        table.add_column("Code", style="bold")
        table.add_column("Message")
        table.add_column("Location")
        for err in result["errors"]:
            table.add_row(err.get("code", ""), err.get("message", ""), err.get("location", ""))
        console.print(table)

    if result["warnings"]:
        table = Table(title="Warnings", style="yellow")
        table.add_column("Code", style="bold")
        table.add_column("Message")
        table.add_column("Location")
        for warn in result["warnings"]:
            table.add_row(warn.get("code", ""), warn.get("message", ""), warn.get("location", ""))
        console.print(table)

    if result.get("suggestions"):
        console.print("[bold]Suggestions:[/bold]")
        for s in result["suggestions"]:
            console.print(f"  • {s}")

    if result["valid"]:
        sys.exit(0)
    else:
        sys.exit(1)
