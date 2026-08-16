from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DomainAuthor:
    name: str = ""
    email: str | None = None
    affiliation: str | None = None
    orcid: str | None = None
    first_name: str = ""
    last_name: str = ""

    def __post_init__(self):
        if not self.name and (self.first_name or self.last_name):
            self.name = f"{self.first_name} {self.last_name}".strip()
        elif self.name and not (self.first_name or self.last_name):
            parts = self.name.rsplit(" ", 1)
            if len(parts) == 2:
                self.first_name, self.last_name = parts[0], parts[1]
            else:
                self.first_name, self.last_name = self.name, ""

    @classmethod
    def from_pydantic(cls, author: Any) -> DomainAuthor:
        if isinstance(author, cls):
            return author
        fn = getattr(author, "first_name", "") or ""
        ln = getattr(author, "last_name", "") or ""
        return cls(
            first_name=fn,
            last_name=ln,
            name=f"{fn} {ln}".strip(),
            email=getattr(author, "email", None),
            affiliation=getattr(author, "affiliation", None),
            orcid=getattr(author, "orcid", None),
        )

    def to_pydantic(self) -> Any:
        from app.schemas.models import Author

        fn = self.first_name
        ln = self.last_name
        if not fn and not ln and self.name:
            parts = self.name.rsplit(" ", 1)
            if len(parts) == 2:
                fn, ln = parts[0], parts[1]
            else:
                fn, ln = self.name, ""

        return Author(
            first_name=fn or "",
            last_name=ln or "",
            affiliation=self.affiliation,
            email=self.email,
            orcid=self.orcid,
        )


@dataclass
class DomainParagraph:
    text: str = ""
    style: str | None = None
    alignment: str | None = None
    indent: float | None = None
    bullet: bool | None = False

    @classmethod
    def from_pydantic(cls, paragraph: Any) -> DomainParagraph:
        if isinstance(paragraph, cls):
            return paragraph
        if isinstance(paragraph, str):
            return cls(text=paragraph)
        return cls(
            text=getattr(paragraph, "text", ""),
            style=getattr(paragraph, "style", None),
            alignment=getattr(paragraph, "alignment", None),
            indent=getattr(paragraph, "indent", None),
            bullet=getattr(paragraph, "bullet", False),
        )

    def to_pydantic(self) -> Any:
        from app.schemas.models import Paragraph

        return Paragraph(
            text=self.text,
            style=self.style,
            alignment=self.alignment,
            indent=self.indent,
            bullet=self.bullet,
        )


@dataclass
class DomainSection:
    title: str = ""
    content: list[DomainParagraph | str | Any] = field(default_factory=list)
    level: int = 1
    subsections: list[DomainSection] = field(default_factory=list)
    heading: str = ""

    def __post_init__(self):
        if not self.title and self.heading:
            self.title = self.heading
        elif not self.heading and self.title:
            self.heading = self.title

        normalized_content = []
        for item in self.content:
            if isinstance(item, str):
                normalized_content.append(DomainParagraph(text=item))
            elif isinstance(item, DomainParagraph):
                normalized_content.append(item)
            elif hasattr(item, "text"):
                normalized_content.append(DomainParagraph.from_pydantic(item))
            else:
                normalized_content.append(item)
        self.content = normalized_content

        normalized_sub = []
        for sub in self.subsections:
            if isinstance(sub, DomainSection):
                normalized_sub.append(sub)
            elif hasattr(sub, "heading") or hasattr(sub, "title"):
                normalized_sub.append(DomainSection.from_pydantic(sub))
            else:
                normalized_sub.append(sub)
        self.subsections = normalized_sub

    @classmethod
    def from_pydantic(cls, section: Any) -> DomainSection:
        if isinstance(section, cls):
            return section
        heading = getattr(section, "heading", "") or getattr(section, "title", "")
        level = getattr(section, "level", 1)
        raw_content = getattr(section, "content", [])
        content = [
            DomainParagraph.from_pydantic(p) if hasattr(p, "text") or isinstance(p, str) else p for p in raw_content
        ]
        raw_sub = getattr(section, "subsections", [])
        subsections = [cls.from_pydantic(s) for s in raw_sub]
        return cls(
            title=heading,
            heading=heading,
            level=level,
            content=content,
            subsections=subsections,
        )

    def to_pydantic(self) -> Any:
        from app.schemas.models import Paragraph, Section

        pydantic_content = []
        for p in self.content:
            if isinstance(p, DomainParagraph):
                pydantic_content.append(p.to_pydantic())
            elif isinstance(p, Paragraph):
                pydantic_content.append(p)
            elif isinstance(p, str):
                pydantic_content.append(Paragraph(text=p))
            else:
                pydantic_content.append(p)

        pydantic_sub = [s.to_pydantic() if isinstance(s, DomainSection) else s for s in self.subsections]
        return Section(
            heading=self.heading or self.title,
            level=self.level,
            content=pydantic_content,
            subsections=pydantic_sub,
        )


@dataclass
class DomainReference:
    id: str | None = None
    title: str = ""
    authors: list[DomainAuthor] = field(default_factory=list)
    journal: str | None = None
    year: str | None = None
    doi: str | None = None
    raw_text: str | None = None
    book_title: str | None = None
    publisher: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    url: str | None = None
    isbn: str | None = None

    def __post_init__(self):
        normalized_authors = []
        for a in self.authors:
            if isinstance(a, DomainAuthor):
                normalized_authors.append(a)
            elif hasattr(a, "first_name") or hasattr(a, "last_name"):
                normalized_authors.append(DomainAuthor.from_pydantic(a))
            else:
                normalized_authors.append(a)
        self.authors = normalized_authors

    @classmethod
    def from_pydantic(cls, ref: Any) -> DomainReference:
        if isinstance(ref, cls):
            return ref
        raw_authors = getattr(ref, "authors", [])
        authors = [DomainAuthor.from_pydantic(a) if not isinstance(a, DomainAuthor) else a for a in raw_authors]
        year_val = getattr(ref, "year", None)
        return cls(
            id=getattr(ref, "id", None),
            title=getattr(ref, "title", ""),
            authors=authors,
            journal=getattr(ref, "journal", None),
            year=str(year_val) if year_val is not None else None,
            doi=getattr(ref, "doi", None),
            raw_text=getattr(ref, "raw_text", None),
            book_title=getattr(ref, "book_title", None),
            publisher=getattr(ref, "publisher", None),
            volume=getattr(ref, "volume", None),
            issue=getattr(ref, "issue", None),
            pages=getattr(ref, "pages", None),
            url=getattr(ref, "url", None),
            isbn=getattr(ref, "isbn", None),
        )

    def to_pydantic(self) -> Any:
        from app.schemas.models import Reference

        pydantic_authors = [a.to_pydantic() if isinstance(a, DomainAuthor) else a for a in self.authors]
        return Reference(
            title=self.title,
            authors=pydantic_authors,
            year=self.year,
            journal=self.journal,
            book_title=self.book_title,
            publisher=self.publisher,
            volume=self.volume,
            issue=self.issue,
            pages=self.pages,
            doi=self.doi,
            url=self.url,
            isbn=self.isbn,
        )


@dataclass
class DomainManuscript:
    title: str = ""
    authors: list[DomainAuthor] = field(default_factory=list)
    abstract: str | None = None
    keywords: list[str] = field(default_factory=list)
    sections: list[DomainSection] = field(default_factory=list)
    references: list[DomainReference] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    acknowledgments: str | None = None
    funding_statement: str | None = None
    conflict_of_interest: str | None = None
    corresponding_author: DomainAuthor | None = None

    def __post_init__(self):
        self.authors = [DomainAuthor.from_pydantic(a) if not isinstance(a, DomainAuthor) else a for a in self.authors]
        self.sections = [
            DomainSection.from_pydantic(s) if not isinstance(s, DomainSection) else s for s in self.sections
        ]
        self.references = [
            DomainReference.from_pydantic(r) if not isinstance(r, DomainReference) else r for r in self.references
        ]
        if self.corresponding_author and not isinstance(self.corresponding_author, DomainAuthor):
            self.corresponding_author = DomainAuthor.from_pydantic(self.corresponding_author)

    @classmethod
    def from_pydantic(cls, manuscript: Any) -> DomainManuscript:
        if isinstance(manuscript, cls):
            return manuscript
        title = getattr(manuscript, "title", "")
        abstract = getattr(manuscript, "abstract", None)
        keywords = list(getattr(manuscript, "keywords", []))
        ack = getattr(manuscript, "acknowledgments", None)
        funding = getattr(manuscript, "funding_statement", None)
        coi = getattr(manuscript, "conflict_of_interest", None)
        corr = getattr(manuscript, "corresponding_author", None)
        corr_domain = DomainAuthor.from_pydantic(corr) if corr else None

        authors = [DomainAuthor.from_pydantic(a) for a in getattr(manuscript, "authors", [])]
        sections = [DomainSection.from_pydantic(s) for s in getattr(manuscript, "sections", [])]
        references = [DomainReference.from_pydantic(r) for r in getattr(manuscript, "references", [])]

        metadata = {
            "acknowledgments": ack,
            "funding_statement": funding,
            "conflict_of_interest": coi,
        }

        return cls(
            title=title,
            authors=authors,
            abstract=abstract,
            keywords=keywords,
            sections=sections,
            references=references,
            metadata=metadata,
            acknowledgments=ack,
            funding_statement=funding,
            conflict_of_interest=coi,
            corresponding_author=corr_domain,
        )

    def to_pydantic(self) -> Any:
        from app.schemas.models import Manuscript

        return Manuscript(
            title=self.title,
            authors=[a.to_pydantic() for a in self.authors],
            abstract=self.abstract,
            keywords=list(self.keywords),
            sections=[s.to_pydantic() for s in self.sections],
            references=[r.to_pydantic() for r in self.references],
            acknowledgments=self.acknowledgments or self.metadata.get("acknowledgments"),
            funding_statement=self.funding_statement or self.metadata.get("funding_statement"),
            conflict_of_interest=self.conflict_of_interest or self.metadata.get("conflict_of_interest"),
            corresponding_author=self.corresponding_author.to_pydantic() if self.corresponding_author else None,
        )


def from_pydantic(obj: Any) -> Any:
    """Seamlessly convert an API model to its corresponding domain dataclass."""
    if isinstance(obj, (DomainManuscript, DomainAuthor, DomainSection, DomainReference, DomainParagraph)):
        return obj

    cls_name = type(obj).__name__
    if cls_name == "Manuscript" or hasattr(obj, "sections"):
        return DomainManuscript.from_pydantic(obj)
    if cls_name == "Author" or (hasattr(obj, "first_name") and hasattr(obj, "last_name")):
        return DomainAuthor.from_pydantic(obj)
    if cls_name == "Section" or hasattr(obj, "heading"):
        return DomainSection.from_pydantic(obj)
    if cls_name == "Reference" or (hasattr(obj, "title") and hasattr(obj, "journal")):
        return DomainReference.from_pydantic(obj)
    if cls_name == "Paragraph" or hasattr(obj, "text"):
        return DomainParagraph.from_pydantic(obj)
    return obj


def to_pydantic(obj: Any) -> Any:
    """Seamlessly convert a domain dataclass to its corresponding API Pydantic model."""
    if hasattr(obj, "to_pydantic"):
        return obj.to_pydantic()
    return obj
