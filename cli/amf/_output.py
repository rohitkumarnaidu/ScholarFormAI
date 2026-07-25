import json
from pathlib import Path

from rich.panel import Panel
from rich.table import Table

from amf._console import get_console

console = get_console()


def print_validation_result(result: dict, output_path: str | None = None):
    if output_path:
        path = Path(output_path)
        path.write_text(json.dumps(result, indent=2))
        console.print(f"[dim]Report saved to: {path}[/dim]")

    if result.get("valid"):
        console.print(Panel("[green]Manuscript is valid[/green]", title="Validation Result"))
    else:
        err_count = len(result.get("errors", []))
        console.print(Panel(f"[red]Manuscript has {err_count} error(s)[/red]", title="Validation Result"))

    if result.get("errors"):
        table = Table(title="Errors", style="red")
        table.add_column("Code", style="bold")
        table.add_column("Message")
        table.add_column("Location")
        for err in result["errors"]:
            table.add_row(err.get("code", ""), err.get("message", ""), err.get("location", ""))
        console.print(table)

    if result.get("warnings"):
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
            console.print(f"  {s}")

    sys_exit = 0 if result.get("valid") else 1
    return sys_exit


def print_styles_table(styles: list[dict]):
    table = Table(title="Available Formatting Styles")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="green")
    table.add_column("Version")
    table.add_column("Citation Format")
    table.add_column("Description")
    for s in styles:
        table.add_row(
            s.get("id", ""),
            s.get("name", ""),
            s.get("version", ""),
            s.get("citation_format", ""),
            s.get("description", ""),
        )
    console.print(table)
