__version__ = "1.0.0"

from .client import AMFClient
from .models import (
    Author,
    FormattingOptions,
    FormattingStyle,
    Manuscript,
    ManuscriptResult,
    Reference,
    Section,
    ValidationResult,
)

__all__ = [
    "AMFClient",
    "Manuscript",
    "ManuscriptResult",
    "ValidationResult",
    "FormattingStyle",
    "FormattingOptions",
    "Author",
    "Section",
    "Reference",
]
