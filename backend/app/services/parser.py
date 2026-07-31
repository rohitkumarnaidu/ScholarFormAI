import logging
import re

from app.domain.models import (
    DomainAuthor,
    DomainManuscript,
    DomainParagraph,
    DomainReference,
    DomainSection,
)

logger = logging.getLogger(__name__)


class ManuscriptParser:
    def parse(self, text: str, fmt: str = "auto") -> DomainManuscript:
        fmt = self.detect_format(text) if fmt == "auto" else fmt

        parsers = {
            "markdown": self._parse_markdown,
            "latex": self._parse_latex,
            "plain": self._parse_plain_text,
        }

        parser = parsers.get(fmt)
        if not parser:
            raise ValueError(f"Unsupported format: {fmt}")

        return parser(text)

    def detect_format(self, text: str) -> str:
        if re.search(r"\\documentclass|\\begin\{|\\section\{", text):
            return "latex"
        if re.search(r"^#{1,6}\s", text, re.MULTILINE):
            return "markdown"
        return "plain"

    def _parse_markdown(self, text: str) -> DomainManuscript:
        lines = text.strip().split("\n")
        title = ""
        authors = []
        abstract = ""
        keywords = []
        sections = []
        references = []
        current_section = None
        in_abstract = False
        in_references = False

        for line in lines:
            stripped = line.strip()

            if not stripped:
                continue

            if stripped.lower().startswith("# abstract") or stripped.lower().startswith("## abstract"):
                in_abstract = True
                in_references = False
                continue

            if stripped.lower().startswith("# references") or stripped.lower().startswith("## references"):
                in_abstract = False
                in_references = True
                continue

            kw_match = re.match(r"^Keywords?\s*:?\s*(.+)$", stripped, re.IGNORECASE)
            if kw_match:
                in_abstract = False
                keywords = [k.strip() for k in kw_match.group(1).split(",")]
                continue

            if in_abstract and not stripped.startswith("#"):
                if not abstract:
                    abstract = stripped
                else:
                    abstract += " " + stripped
                continue

            if in_references:
                references.append(DomainReference(title=stripped))
                continue

            heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
            if heading_match:
                in_abstract = False
                in_references = False
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2)

                if not title and level == 1:
                    title = heading_text
                    continue

                new_section = DomainSection(title=heading_text, heading=heading_text, level=level)
                sections.append(new_section)
                current_section = new_section
                continue

            if not title:
                title = stripped
                continue

            author_match = re.match(r"^By\s+(.+)$", stripped, re.IGNORECASE)
            if author_match and not authors:
                author_names = author_match.group(1).split(",")
                for name in author_names:
                    name = name.strip()
                    if " " in name:
                        parts = name.rsplit(" ", 1)
                        authors.append(
                            DomainAuthor(
                                first_name=parts[0],
                                last_name=parts[1],
                                name=f"{parts[0]} {parts[1]}",
                            )
                        )
                    else:
                        authors.append(DomainAuthor(name=name))
                continue

            kw_match = re.match(r"^Keywords?\s*:?\s*(.+)$", stripped, re.IGNORECASE)
            if kw_match:
                keywords = [k.strip() for k in kw_match.group(1).split(",")]
                continue

            para = DomainParagraph(text=stripped)

            if current_section:
                current_section.content.append(para)

        return DomainManuscript(
            title=title,
            authors=authors,
            abstract=abstract,
            keywords=keywords,
            sections=sections,
            references=references,
        )

    def _parse_latex(self, text: str) -> DomainManuscript:
        title = ""
        authors = []
        abstract = ""
        sections = []

        title_match = re.search(r"\\title\{([^}]+)\}", text)
        if title_match:
            title = title_match.group(1)

        author_matches = re.findall(r"\\author\{([^}]+)\}", text)
        if author_matches:
            for auth_text in author_matches:
                for name in auth_text.split(r"\and"):
                    name = name.strip()
                    if " " in name:
                        parts = name.rsplit(" ", 1)
                        authors.append(
                            DomainAuthor(
                                first_name=parts[0],
                                last_name=parts[1],
                                name=f"{parts[0]} {parts[1]}",
                            )
                        )
                    else:
                        authors.append(DomainAuthor(name=name))

        abstract_match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.DOTALL)
        if abstract_match:
            abstract = abstract_match.group(1).strip()

        section_matches = re.findall(
            r"\\(section|subsection)\{([^}]+)\}(.*?)(?=\\(?:section|subsection|bibliography)|$)",
            text,
            re.DOTALL,
        )
        for sec_type, heading, content in section_matches:
            level = 1 if sec_type == "section" else 2
            paragraphs = [DomainParagraph(text=p.strip()) for p in re.split(r"\n\s*\n", content.strip()) if p.strip()]
            sections.append(DomainSection(title=heading, heading=heading, level=level, content=paragraphs))

        return DomainManuscript(
            title=title,
            authors=authors,
            abstract=abstract,
            sections=sections,
        )

    def _parse_plain_text(self, text: str) -> DomainManuscript:
        lines = text.strip().split("\n")
        sections = []

        title = lines[0] if lines else ""
        current_section = None

        for line in lines[1:]:
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.isupper() and 3 < len(stripped) < 100:
                current_section = DomainSection(title=stripped, heading=stripped, level=1)
                sections.append(current_section)
            else:
                para = DomainParagraph(text=stripped)
                if current_section:
                    current_section.content.append(para)

        return DomainManuscript(title=title, sections=sections)
