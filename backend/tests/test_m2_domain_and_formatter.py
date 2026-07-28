import tempfile
import pytest

from app.api.models import Author, Manuscript, Paragraph, Reference, Section
from app.domain.models import (
    DomainAuthor,
    DomainManuscript,
    DomainParagraph,
    DomainReference,
    DomainSection,
    from_pydantic,
    to_pydantic,
)
from app.services.formatter import (
    DocumentLayoutEngine,
    HTMLPreviewRenderer,
    ManuscriptFormatter,
    PageEstimator,
    ReferenceRenderer,
)
from app.services.parser import ManuscriptParser
from app.services.style_registry import StyleRegistry
from app.services.validator import ManuscriptValidator


class TestDomainModels:
    def test_domain_author_initialization_and_pydantic_conversion(self):
        # From name
        a1 = DomainAuthor(name="Jane Doe", email="jane@example.com", affiliation="MIT", orcid="0000-0002-1825-0097")
        assert a1.first_name == "Jane"
        assert a1.last_name == "Doe"
        assert a1.name == "Jane Doe"

        # From first_name / last_name
        a2 = DomainAuthor(first_name="Albert", last_name="Einstein")
        assert a2.name == "Albert Einstein"

        # Pydantic conversion round-trip
        p_author = Author(first_name="Isaac", last_name="Newton", email="isaac@cambridge.ac.uk")
        d_author = DomainAuthor.from_pydantic(p_author)
        assert d_author.first_name == "Isaac"
        assert d_author.last_name == "Newton"
        assert d_author.name == "Isaac Newton"
        assert d_author.email == "isaac@cambridge.ac.uk"

        p_author_back = d_author.to_pydantic()
        assert isinstance(p_author_back, Author)
        assert p_author_back.first_name == "Isaac"
        assert p_author_back.last_name == "Newton"
        assert p_author_back.email == "isaac@cambridge.ac.uk"

    def test_domain_section_and_paragraph_conversion(self):
        p = Paragraph(text="Sample paragraph", style="italic", alignment="center")
        d_p = DomainParagraph.from_pydantic(p)
        assert d_p.text == "Sample paragraph"
        assert d_p.style == "italic"
        assert d_p.alignment == "center"

        p_back = d_p.to_pydantic()
        assert isinstance(p_back, Paragraph)
        assert p_back.text == "Sample paragraph"

        s = Section(heading="Introduction", level=1, content=[p])
        d_s = DomainSection.from_pydantic(s)
        assert d_s.title == "Introduction"
        assert d_s.heading == "Introduction"
        assert d_s.level == 1
        assert len(d_s.content) == 1
        assert d_s.content[0].text == "Sample paragraph"

        s_back = d_s.to_pydantic()
        assert isinstance(s_back, Section)
        assert s_back.heading == "Introduction"
        assert len(s_back.content) == 1

    def test_domain_reference_and_manuscript(self):
        r = Reference(
            title="Quantum Mechanics",
            authors=[Author(first_name="Erwin", last_name="Schrödinger")],
            year="1926",
            journal="Annalen der Physik",
            doi="10.1002/andp.19263840404",
        )
        d_r = DomainReference.from_pydantic(r)
        assert d_r.title == "Quantum Mechanics"
        assert d_r.year == "1926"
        assert d_r.journal == "Annalen der Physik"
        assert len(d_r.authors) == 1
        assert d_r.authors[0].last_name == "Schrödinger"

        m = Manuscript(
            title="A Study of Wave Dynamics",
            authors=[Author(first_name="Erwin", last_name="Schrödinger")],
            abstract="This paper discusses wave mechanics.",
            keywords=["physics", "quantum"],
            sections=[Section(heading="Introduction", level=1, content=[Paragraph(text="Intro text")])],
            references=[r],
            acknowledgments="Thanks to University of Zurich",
        )

        d_m = DomainManuscript.from_pydantic(m)
        assert d_m.title == "A Study of Wave Dynamics"
        assert d_m.abstract == "This paper discusses wave mechanics."
        assert d_m.keywords == ["physics", "quantum"]
        assert len(d_m.sections) == 1
        assert len(d_m.references) == 1
        assert d_m.metadata["acknowledgments"] == "Thanks to University of Zurich"

        m_back = d_m.to_pydantic()
        assert isinstance(m_back, Manuscript)
        assert m_back.title == "A Study of Wave Dynamics"
        assert m_back.acknowledgments == "Thanks to University of Zurich"

    def test_standalone_conversion_helpers(self):
        p_author = Author(first_name="Marie", last_name="Curie")
        d_author = from_pydantic(p_author)
        assert isinstance(d_author, DomainAuthor)
        assert d_author.name == "Marie Curie"

        p_back = to_pydantic(d_author)
        assert isinstance(p_back, Author)
        assert p_back.last_name == "Curie"


class TestFormatterDecomposition:
    @pytest.fixture
    def sample_domain_manuscript(self):
        return DomainManuscript(
            title="Decomposition of Formatter Engine",
            authors=[DomainAuthor(first_name="Ada", last_name="Lovelace", email="ada@analytical.org")],
            abstract="Abstract on single-responsibility principles.",
            keywords=["architecture", "refactoring", "clean-code"],
            sections=[
                DomainSection(
                    title="Introduction",
                    heading="Introduction",
                    level=1,
                    content=[DomainParagraph(text="This section presents clean architecture.")],
                )
            ],
            references=[
                DomainReference(
                    title="Design Patterns",
                    authors=[DomainAuthor(first_name="Erich", last_name="Gamma")],
                    year="1994",
                    journal="Addison-Wesley",
                )
            ],
            corresponding_author=DomainAuthor(first_name="Ada", last_name="Lovelace", email="ada@analytical.org"),
        )

    def test_reference_renderer(self, sample_domain_manuscript):
        style_reg = StyleRegistry()
        apa_style = style_reg.get_style("apa")
        ieee_style = style_reg.get_style("ieee")

        renderer = ReferenceRenderer()
        prefix_apa, body_apa = renderer.format_reference_string(
            sample_domain_manuscript.references[0], apa_style, index=1
        )
        assert "Gamma, E." in prefix_apa
        assert "Design Patterns. Addison-Wesley" in body_apa

        prefix_ieee, body_ieee = renderer.format_reference_string(
            sample_domain_manuscript.references[0], ieee_style, index=1
        )
        assert prefix_ieee == "[1] "

    def test_document_layout_engine(self, sample_domain_manuscript):
        style_reg = StyleRegistry()
        apa_style = style_reg.get_style("apa")

        engine = DocumentLayoutEngine()
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            output_path = tmp.name

        doc_path = engine.render_document(
            manuscript=sample_domain_manuscript,
            style=apa_style,
            output_path=output_path,
        )
        assert doc_path == output_path

    def test_page_estimator_in_memory(self, sample_domain_manuscript):
        estimator = PageEstimator()
        pages = estimator.estimate_pages(sample_domain_manuscript)
        assert isinstance(pages, int)
        assert pages >= 1

    def test_html_preview_renderer(self, sample_domain_manuscript):
        style_reg = StyleRegistry()
        apa_style = style_reg.get_style("apa")

        renderer = HTMLPreviewRenderer()
        html_out = renderer.generate_html_preview(sample_domain_manuscript, apa_style)
        assert "<h1>Decomposition of Formatter Engine</h1>" in html_out
        assert "Ada Lovelace" in html_out
        assert "Abstract on single-responsibility principles." in html_out
        assert "Introduction" in html_out
        assert "Design Patterns" in html_out

    def test_manuscript_formatter_delegator(self, sample_domain_manuscript):
        style_reg = StyleRegistry()
        apa_style = style_reg.get_style("apa")

        formatter = ManuscriptFormatter()
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            output_path = tmp.name

        doc_path = formatter.format(sample_domain_manuscript, apa_style, output_path)
        assert doc_path == output_path

        pages = formatter.estimate_pages(sample_domain_manuscript)
        assert pages >= 1

        html_out = formatter.generate_html_preview(sample_domain_manuscript, apa_style)
        assert "Decomposition of Formatter Engine" in html_out


class TestParserAndValidatorDecoupling:
    def test_parser_returns_domain_manuscript(self):
        parser = ManuscriptParser()
        markdown_text = """# Sample Title
By John Doe

## Abstract
This is an abstract.

Keywords: testing, domain, parser

# Introduction
This is the introduction section.

# References
Sample Reference 1
"""
        doc = parser.parse(markdown_text, fmt="markdown")
        assert isinstance(doc, DomainManuscript)
        assert doc.title == "Sample Title"
        assert len(doc.authors) == 1
        assert doc.authors[0].name == "John Doe"
        assert doc.abstract == "This is an abstract."
        assert doc.keywords == ["testing", "domain", "parser"]
        assert len(doc.sections) == 1
        assert doc.sections[0].title == "Introduction"
        assert len(doc.references) == 1
        assert doc.references[0].title == "Sample Reference 1"

    def test_validator_accepts_domain_manuscript(self):
        validator = ManuscriptValidator()
        d_ms = DomainManuscript(
            title="Comprehensive Validation Test",
            authors=[DomainAuthor(first_name="Alice", last_name="Smith")],
            abstract="A valid abstract for validation.",
            keywords=["validation", "test"],
            sections=[
                DomainSection(title="Introduction", heading="Introduction", level=1),
                DomainSection(title="Methodology", heading="Methodology", level=1),
            ],
            references=[DomainReference(title="Reference 1", authors=[DomainAuthor(name="Bob")])],
        )

        res = validator.validate(d_ms, "apa")
        assert res["valid"] is True
        assert len(res["errors"]) == 0
