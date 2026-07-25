from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from amf.config import AMFConfig

console = Console()


def show_config():
    config = AMFConfig()

    table = Table(title="AMF Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="bold")

    for key, value in config.get_all().items():
        table.add_row(key, str(value))

    console.print(table)
    console.print(f"\n[dim]Config file: {config.config_path}[/dim]")
