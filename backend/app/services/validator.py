import logging
from typing import Any

from app.api.models import ValidationIssue
from app.domain.models import DomainManuscript
from app.services.style_registry import StyleRegistry

logger = logging.getLogger(__name__)


class ManuscriptValidator:
    def __init__(self):
        self.style_registry = StyleRegistry()

    def validate(self, manuscript: DomainManuscript | Any, style_id: str) -> dict[str, Any]:
        if not isinstance(manuscript, DomainManuscript):
            manuscript = DomainManuscript.from_pydantic(manuscript)

        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        suggestions: list[str] = []

        style = self.style_registry.get_style(style_id)

        self._validate_title(manuscript, errors, warnings)
        self._validate_authors(manuscript, errors, warnings)
        self._validate_abstract(manuscript, style, errors, warnings, suggestions)
        self._validate_keywords(manuscript, style, warnings, suggestions)
        self._validate_sections(manuscript, errors, warnings, suggestions)
        self._validate_references(manuscript, errors, warnings)
        self._validate_metadata(manuscript, warnings)

        valid = len(errors) == 0

        return {
            "valid": valid,
            "errors": [e.model_dump() for e in errors],
            "warnings": [w.model_dump() for w in warnings],
            "suggestions": suggestions,
        }

    def _validate_title(
        self,
        manuscript: DomainManuscript,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
    ):
        if not manuscript.title or not manuscript.title.strip():
            errors.append(
                ValidationIssue(
                    code="MISSING_TITLE", message="Manuscript title is required", severity="error"
                )
            )
        elif len(manuscript.title) < 5:
            warnings.append(
                ValidationIssue(
                    code="SHORT_TITLE",
                    message="Title seems too short (less than 5 characters)",
                    severity="warning",
                )
            )
        elif len(manuscript.title) > 500:
            warnings.append(
                ValidationIssue(
                    code="LONG_TITLE",
                    message="Title is very long (over 500 characters). Consider shortening.",
                    severity="warning",
                )
            )

    def _validate_authors(
        self,
        manuscript: DomainManuscript,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
    ):
        if not manuscript.authors:
            errors.append(
                ValidationIssue(
                    code="MISSING_AUTHORS",
                    message="At least one author is required",
                    severity="error",
                )
            )
            return

        for i, author in enumerate(manuscript.authors):
            if not author.first_name or not author.last_name:
                warnings.append(
                    ValidationIssue(
                        code="INCOMPLETE_AUTHOR",
                        message=f"Author {i + 1} is missing first or last name",
                        location=f"authors[{i}]",
                        severity="warning",
                    )
                )

    def _validate_abstract(
        self,
        manuscript: DomainManuscript,
        style: Any,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
        suggestions: list[str],
    ):
        if style.abstract_required and not manuscript.abstract:
            errors.append(
                ValidationIssue(
                    code="MISSING_ABSTRACT",
                    message=f"Abstract is required for {style.name} style",
                    severity="error",
                )
            )
        elif manuscript.abstract and len(manuscript.abstract) > 500:
            warnings.append(
                ValidationIssue(
                    code="LONG_ABSTRACT",
                    message="Abstract exceeds 500 characters. Consider condensing.",
                    severity="warning",
                )
            )

    def _validate_keywords(
        self,
        manuscript: DomainManuscript,
        style: Any,
        warnings: list[ValidationIssue],
        suggestions: list[str],
    ):
        if style.keywords_required and not manuscript.keywords:
            warnings.append(
                ValidationIssue(
                    code="MISSING_KEYWORDS",
                    message=f"Keywords are recommended for {style.name} style",
                    severity="warning",
                )
            )
        elif len(manuscript.keywords) > 10:
            warnings.append(
                ValidationIssue(
                    code="TOO_MANY_KEYWORDS",
                    message="Too many keywords (max 10 recommended)",
                    severity="warning",
                )
            )

    def _validate_sections(
        self,
        manuscript: DomainManuscript,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
        suggestions: list[str],
    ):
        if not manuscript.sections:
            warnings.append(
                ValidationIssue(
                    code="MISSING_SECTIONS",
                    message="Manuscript has no sections. Consider adding section headings.",
                    severity="warning",
                )
            )
            return

        headings = [(s.heading or s.title).lower() for s in manuscript.sections]
        required_headings = [
            "introduction",
            "method",
            "methodology",
            "results",
            "discussion",
            "conclusion",
        ]

        for req in required_headings:
            if not any(req in h for h in headings):
                suggestions.append(f"Consider adding a '{req.capitalize()}' section")

        for section in manuscript.sections:
            heading_text = section.heading or section.title
            if not heading_text:
                errors.append(
                    ValidationIssue(
                        code="EMPTY_SECTION", message="A section has no heading", severity="error"
                    )
                )

    def _validate_references(
        self,
        manuscript: DomainManuscript,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
    ):
        if not manuscript.references:
            warnings.append(
                ValidationIssue(
                    code="NO_REFERENCES",
                    message="No references found. Academic manuscripts should include references.",
                    severity="warning",
                )
            )
            return

        for i, ref in enumerate(manuscript.references):
            if not ref.title:
                errors.append(
                    ValidationIssue(
                        code="MISSING_REFERENCE_TITLE",
                        message=f"Reference {i + 1} is missing a title",
                        location=f"references[{i}]",
                        severity="error",
                    )
                )

            if not ref.authors and not ref.doi and not ref.url:
                warnings.append(
                    ValidationIssue(
                        code="INCOMPLETE_REFERENCE",
                        message=f"Reference {i + 1} is missing author information, DOI, or URL",
                        location=f"references[{i}]",
                        severity="warning",
                    )
                )

    def _validate_metadata(
        self, manuscript: DomainManuscript, warnings: list[ValidationIssue]
    ):
        ack = manuscript.acknowledgments or manuscript.metadata.get("acknowledgments")
        if ack and len(ack) > 1000:
            warnings.append(
                ValidationIssue(
                    code="LONG_ACKNOWLEDGMENTS",
                    message="Acknowledgments section is very long",
                    severity="warning",
                )
            )
