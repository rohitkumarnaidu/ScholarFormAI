import json
import logging
import sys
from pathlib import Path

from amf._client import BackendClient
from amf._console import get_console, safe_progress
from amf._output import print_validation_result
from amf.config import AMFConfig

logger = logging.getLogger(__name__)
console = get_console()


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

    client = BackendClient(AMFConfig())

    with safe_progress() as progress:
        progress.add_task(description="Validating manuscript...")
        try:
            result = client.validate(input_file, style)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)

    exit_code = print_validation_result(result, output_path)
    sys.exit(exit_code)
