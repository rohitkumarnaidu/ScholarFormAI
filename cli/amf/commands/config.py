from rich.table import Table

from amf._console import get_console
from amf.config import AMFConfig

console = get_console()


def show_config():
    config = AMFConfig()

    table = Table(title="AMF Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="bold")

    for key, value in config.get_all().items():
        table.add_row(key, str(value))

    console.print(table)
    console.print(f"\n[dim]Config file: {config.config_path}[/dim]")
