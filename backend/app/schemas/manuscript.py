from pydantic import BaseModel, Field


class Author(BaseModel):
    first_name: str
    last_name: str
    affiliation: str | None = None
    email: str | None = None
    orcid: str | None = None
    corresponding: bool = False


class Paragraph(BaseModel):
    text: str
    style: str | None = None
    alignment: str | None = None
    indent: float | None = None
    bullet: bool = False


class Section(BaseModel):
    heading: str
    level: int = Field(default=1, ge=1, le=6)
    content: list[Paragraph] = []
    subsections: list["Section"] = []


class Reference(BaseModel):
    authors: list[Author] = []
    year: str | None = None
    title: str
    journal: str | None = None
    book_title: str | None = None
    publisher: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None
    url: str | None = None
    isbn: str | None = None


class Manuscript(BaseModel):
    title: str
    authors: list[Author] = []
    abstract: str | None = None
    keywords: list[str] = []
    sections: list[Section] = []
    references: list[Reference] = []
    acknowledgments: str | None = None
    funding_statement: str | None = None
    conflict_of_interest: str | None = None
    corresponding_author: Author | None = None
