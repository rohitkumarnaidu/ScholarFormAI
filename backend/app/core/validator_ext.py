import logging
import re
from typing import Any

from app.api.models import Manuscript

logger = logging.getLogger(__name__)

DANGEROUS_PATTERN = re.compile(r"[<>\{\}\\]")
SCRIPT_TAG_PATTERN = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
HTML_TAG_PATTERN = re.compile(r"<[^>]*>")
CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
DOI_PATTERN = re.compile(r"^10\.\d{4,}/[-._;()/:A-Za-z0-9]+$")


MAX_TITLE_LENGTH = 1000
MAX_ABSTRACT_LENGTH = 5000
MAX_SECTIONS = 100
MAX_SECTION_DEPTH = 10
MAX_PARAGRAPHS_PER_SECTION = 500
MAX_AUTHORS = 50
MAX_REFERENCES = 500
MAX_KEYWORDS = 20
MAX_KEYWORD_LENGTH = 100


ALLOWED_ALIGNMENTS = {"left", "center", "right", "justify"}
VALID_FILE_EXTENSIONS = {".docx", ".doc", ".txt", ".md", ".tex", ".pdf"}
ALLOWED_PARAGRAPH_STYLES = {"normal", "bold", "italic", "heading", "quote", "code"}


def sanitize_string(value: str, max_length: int | None = None) -> str:
    if not isinstance(value, str):
        return ""
    value = CONTROL_CHARS_PATTERN.sub("", value)
    value = SCRIPT_TAG_PATTERN.sub("", value)
    value = HTML_TAG_PATTERN.sub("", value)
    value = value.strip()
    if max_length and len(value) > max_length:
        value = value[:max_length]
    return value


def sanitize_manuscript(manuscript: Manuscript) -> Manuscript:
    manuscript.title = sanitize_string(manuscript.title, max_length=MAX_TITLE_LENGTH)

    if manuscript.abstract:
        manuscript.abstract = sanitize_string(manuscript.abstract, max_length=MAX_ABSTRACT_LENGTH)

    sanitized_keywords = []
    for kw in manuscript.keywords:
        sanitized = sanitize_string(kw, max_length=MAX_KEYWORD_LENGTH)
        if sanitized:
            sanitized_keywords.append(sanitized)
    manuscript.keywords = sanitized_keywords

    for author in manuscript.authors:
        author.first_name = sanitize_string(author.first_name, max_length=100)
        author.last_name = sanitize_string(author.last_name, max_length=100)
        if author.email:
            author.email = sanitize_string(author.email, max_length=254)
        if author.affiliation:
            author.affiliation = sanitize_string(author.affiliation, max_length=500)
        if author.orcid:
            author.orcid = sanitize_string(author.orcid, max_length=50)

    for section in manuscript.sections:
        _sanitize_section(section)

    for ref in manuscript.references:
        ref.title = sanitize_string(ref.title, max_length=1000)
        if ref.journal:
            ref.journal = sanitize_string(ref.journal, max_length=500)
        if ref.publisher:
            ref.publisher = sanitize_string(ref.publisher, max_length=500)
        if ref.doi:
            ref.doi = sanitize_string(ref.doi, max_length=500)
        if ref.url:
            ref.url = sanitize_string(ref.url, max_length=2000)

    if manuscript.acknowledgments:
        manuscript.acknowledgments = sanitize_string(manuscript.acknowledgments, max_length=5000)
    if manuscript.funding_statement:
        manuscript.funding_statement = sanitize_string(manuscript.funding_statement, max_length=2000)
    if manuscript.conflict_of_interest:
        manuscript.conflict_of_interest = sanitize_string(manuscript.conflict_of_interest, max_length=2000)
    if manuscript.corresponding_author:
        ca = manuscript.corresponding_author
        ca.first_name = sanitize_string(ca.first_name, max_length=100)
        ca.last_name = sanitize_string(ca.last_name, max_length=100)
        if ca.email:
            ca.email = sanitize_string(ca.email, max_length=254)
        if ca.affiliation:
            ca.affiliation = sanitize_string(ca.affiliation, max_length=500)

    return manuscript


def _sanitize_section(section: Any) -> None:
    section.heading = sanitize_string(section.heading, max_length=500)
    for para in section.content:
        para.text = sanitize_string(para.text, max_length=50000)
        if para.style and para.style not in ALLOWED_PARAGRAPH_STYLES:
            para.style = None
        if para.alignment and para.alignment not in ALLOWED_ALIGNMENTS:
            para.alignment = None
    for sub in section.subsections:
        _sanitize_section(sub)


def validate_manuscript_size(manuscript: Manuscript) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if len(manuscript.title) > MAX_TITLE_LENGTH:
        errors.append(
            {
                "code": "TITLE_TOO_LONG",
                "message": f"Title exceeds {MAX_TITLE_LENGTH} characters",
                "location": "title",
            }
        )

    if manuscript.abstract and len(manuscript.abstract) > MAX_ABSTRACT_LENGTH:
        warnings.append(
            {
                "code": "ABSTRACT_TOO_LONG",
                "message": f"Abstract exceeds {MAX_ABSTRACT_LENGTH} characters",
                "location": "abstract",
            }
        )

    if len(manuscript.authors) > MAX_AUTHORS:
        errors.append(
            {
                "code": "TOO_MANY_AUTHORS",
                "message": f"Too many authors (max {MAX_AUTHORS})",
                "location": "authors",
            }
        )

    if len(manuscript.sections) > MAX_SECTIONS:
        errors.append(
            {
                "code": "TOO_MANY_SECTIONS",
                "message": f"Too many sections (max {MAX_SECTIONS})",
                "location": "sections",
            }
        )

    if len(manuscript.references) > MAX_REFERENCES:
        warnings.append(
            {
                "code": "TOO_MANY_REFERENCES",
                "message": f"Too many references (max {MAX_REFERENCES})",
                "location": "references",
            }
        )

    if len(manuscript.keywords) > MAX_KEYWORDS:
        warnings.append(
            {
                "code": "TOO_MANY_KEYWORDS",
                "message": f"Too many keywords (max {MAX_KEYWORDS})",
                "location": "keywords",
            }
        )

    max_depth = _check_section_depth(manuscript.sections)
    if max_depth > MAX_SECTION_DEPTH:
        errors.append(
            {
                "code": "SECTION_DEPTH_EXCEEDED",
                "message": (f"Section nesting depth ({max_depth}) exceeds maximum ({MAX_SECTION_DEPTH})"),
                "location": "sections",
            }
        )

    total_paragraphs = _count_total_paragraphs(manuscript.sections)
    if total_paragraphs > 10000:
        warnings.append(
            {
                "code": "TOO_MANY_PARAGRAPHS",
                "message": f"Document has {total_paragraphs} paragraphs, consider splitting",
                "location": "sections",
            }
        )

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def _check_section_depth(sections: list[Any], depth: int = 1) -> int:
    max_depth = depth
    for section in sections:
        if section.subsections:
            child_depth = _check_section_depth(section.subsections, depth + 1)
            max_depth = max(max_depth, child_depth)
    return max_depth


def _count_total_paragraphs(sections: list[Any]) -> int:
    count = 0
    for section in sections:
        count += len(section.content)
        count += _count_total_paragraphs(section.subsections)
    return count


def validate_file_type(filename: str) -> bool:
    ext = Path(filename).suffix.lower() if "." in filename else ""
    return ext in VALID_FILE_EXTENSIONS


from pathlib import Path  # noqa: E402


def validate_email(email: str) -> bool:
    if not email:
        return False
    return bool(EMAIL_PATTERN.match(email))


def validate_doi(doi: str) -> bool:
    if not doi:
        return False
    return bool(DOI_PATTERN.match(doi))


def deep_validate_manuscript(manuscript: Manuscript) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if not manuscript.title.strip():
        issues.append(
            {
                "code": "EMPTY_TITLE",
                "message": "Title is empty after sanitization",
                "location": "title",
                "severity": "error",
            }
        )

    for i, author in enumerate(manuscript.authors):
        if not author.first_name.strip() or not author.last_name.strip():
            issues.append(
                {
                    "code": "INCOMPLETE_AUTHOR",
                    "message": f"Author {i + 1} has empty name fields",
                    "location": f"authors[{i}]",
                    "severity": "warning",
                }
            )
        if author.email and not validate_email(author.email):
            warnings.append(
                {
                    "code": "INVALID_EMAIL",
                    "message": f"Author {i + 1} email appears invalid",
                    "location": f"authors[{i}].email",
                    "severity": "warning",
                }
            )

    for i, ref in enumerate(manuscript.references):
        if ref.doi and not validate_doi(ref.doi):
            warnings.append(
                {
                    "code": "INVALID_DOI",
                    "message": f"Reference {i + 1} DOI appears invalid",
                    "location": f"references[{i}].doi",
                    "severity": "warning",
                }
            )

    issue_headings = _check_duplicate_headings(manuscript.sections)
    for heading, count in issue_headings:
        warnings.append(
            {
                "code": "DUPLICATE_HEADING",
                "message": f"Heading '{heading}' appears {count} times",
                "location": "sections",
                "severity": "warning",
            }
        )

    return {
        "issues": issues,
        "warnings": warnings,
        "valid": len([i for i in issues if i.get("severity") == "error"]) == 0,
    }


def _check_duplicate_headings(sections: list[Any]) -> list[tuple]:
    from collections import Counter

    headings = []
    for section in sections:
        headings.append(section.heading.lower().strip())
        headings.extend(h for h, _ in _check_duplicate_headings(section.subsections))
    counter = Counter(headings)
    return [(h, c) for h, c in counter.items() if c > 1]


def cross_field_validate(manuscript: Manuscript) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []

    if manuscript.corresponding_author:
        found = False
        for author in manuscript.authors:
            if (
                author.first_name == manuscript.corresponding_author.first_name
                and author.last_name == manuscript.corresponding_author.last_name
            ):
                found = True
                break
        if not found:
            issues.append(
                {
                    "code": "CORRESPONDING_AUTHOR_NOT_IN_AUTHORS",
                    "message": "Corresponding author is not listed in the authors list",
                    "location": "corresponding_author",
                    "severity": "warning",
                }
            )

    if manuscript.acknowledgments and not manuscript.funding_statement and not manuscript.conflict_of_interest:
        issues.append(
            {
                "code": "MISSING_DECLARATIONS",
                "message": ("Acknowledgments present but no funding statement or conflict of interest"),
                "location": "metadata",
                "severity": "info",
            }
        )

    if manuscript.keywords:
        unique_kw = set(k.lower().strip() for k in manuscript.keywords if k.strip())
        if len(unique_kw) != len([k for k in manuscript.keywords if k.strip()]):
            issues.append(
                {
                    "code": "DUPLICATE_KEYWORDS",
                    "message": "Keywords contain duplicates",
                    "location": "keywords",
                    "severity": "warning",
                }
            )

    return {"issues": issues, "valid": all(i.get("severity") != "error" for i in issues)}


def get_validator_checks() -> dict[str, str]:
    return {
        "sanitize_string": "Strip control chars, HTML tags, and script tags",
        "sanitize_manuscript": "Sanitize all manuscript fields",
        "validate_manuscript_size": "Check manuscript size constraints",
        "validate_file_type": "Check file extension is allowed",
        "validate_email": "Validate email format",
        "validate_doi": "Validate DOI format",
        "deep_validate_manuscript": "Deep structural validation",
        "cross_field_validate": "Cross-field consistency checks",
    }
