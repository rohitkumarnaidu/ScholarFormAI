import logging

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

logger = logging.getLogger(__name__)


def safe_progress(*, transient: bool = True) -> Progress:
    columns: list = []
    try:
        columns.append(SpinnerColumn())
    except Exception:
        pass  # intentionally ignored
    columns.append(TextColumn("{task.description}"))
    return Progress(*columns, console=Console(stderr=True), transient=transient)


def get_console() -> Console:
    return Console(stderr=True)
