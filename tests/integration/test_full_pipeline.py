"""Full pipeline integration tests: parse -> validate -> format."""


import pytest

from app.api.models import Author, Manuscript, Paragraph, Reference, Section
from app.services.formatter import ManuscriptFormatter
from app.services.parser import ManuscriptParser
from app.services.style_registry import StyleRegistry
from app.services.validator import ManuscriptValidator


class TestFullPipeline:
    """End-to-end integration tests for the full manuscript formatting pipeline."""

    @pytest.fixture
    def components(self):
        return {
            "parser": ManuscriptParser(),
            "validator": ManuscriptValidator(),
            "formatter": ManuscriptFormatter(),
            "registry": StyleRegistry(),
        }

    # ------------------------------------------------------------------ #
    #  Input format -> DOCX smoke tests  (one per style, one per format) #
    # ------------------------------------------------------------------ #

    @pytest.mark.parametrize("style_id", [
        "apa", "mla", "chicago", "ieee", "harvard",
        "vancouver", "turabian", "acs", "ama",
    ])
    def test_markdown_to_docx_all_styles(self, components, tmp_path, style_id):
        md = (
            f"# Test Paper\n"
            f"By Jane Smith\n"
            f"## Abstract\n"
            f"This is a test abstract.\n"
            f"**Keywords:** test, paper\n"
            f"## Introduction\n"
            f"Test content here.\n"
            f"## References\n"
            f"Smith, J. (2024). Test. Journal, 1(1), 1-10.\n"
        )
        manuscript = components["parser"].parse(md, "markdown")
        result = components["validator"].validate(manuscript, style_id)
        style = components["registry"].get_style(style_id)
        output = tmp_path / f"output_{style_id}.docx"
        components["formatter"].format(manuscript, style, str(output))
        assert output.exists(), f"DOCX not created for {style_id}"
        assert output.stat().st_size > 0, f"Empty DOCX for {style_id}"
        if not result["valid"]:
            pytest.fail(f"Validation failed for {style_id}: {result['errors']}")

    def test_markdown_to_docx_apa(self, components, tmp_path):
        md = (
            "# The Impact of AI on Research\n"
            "By Jane Smith\n"
            "## Abstract\n"
            "This study examines AI's role.\n"
            "Keywords: AI, research, methodology\n"
            "## Introduction\n"
            "Artificial intelligence has emerged as a transformative force.\n"
            "## Methodology\n"
            "We conducted a comprehensive review.\n"
            "## Conclusion\n"
            "AI will continue to shape research.\n"
            "## References\n"
            "Turing, A. (1950). Computing Machinery and Intelligence. Mind, 59(236), 433-460.\n"
        )
        manuscript = components["parser"].parse(md, "markdown")
        result = components["validator"].validate(manuscript, "apa")
        assert result["valid"]
        style = components["registry"].get_style("apa")
        output = tmp_path / "apa_output.docx"
        components["formatter"].format(manuscript, style, str(output))
        assert output.exists()
        assert output.stat().st_size > 0

    def test_markdown_to_docx_mla(self, components, tmp_path):
        md = (
            "# Literary Analysis of Modern Poetry\n"
            "By John Doe\n"
            "## Abstract\n"
            "An analysis of contemporary poetic forms.\n"
            "Keywords: poetry, modernism\n"
            "## Introduction\n"
            "Modern poetry represents a departure from traditional forms.\n"
            "## References\n"
            "Doe, John. Modern Poetry. Academic Press, 2021.\n"
        )
        manuscript = components["parser"].parse(md, "markdown")
        result = components["validator"].validate(manuscript, "mla")
        style = components["registry"].get_style("mla")
        output = tmp_path / "mla_output.docx"
        components["formatter"].format(manuscript, style, str(output))
        assert output.exists()
        assert output.stat().st_size > 0

    def test_markdown_to_docx_chicago(self, components, tmp_path):
        md = (
            "# Historical Analysis of Industrial Revolution\n"
            "By Sarah Johnson\n"
            "## Abstract\n"
            "Examining the socioeconomic impacts.\n"
            "Keywords: history, industrial revolution\n"
            "## Introduction\n"
            "The Industrial Revolution transformed society.\n"
            "## References\n"
            "Johnson, Sarah. The Industrial Age. History Press, 2020.\n"
        )
        manuscript = components["parser"].parse(md, "markdown")
        result = components["validator"].validate(manuscript, "chicago")
        style = components["registry"].get_style("chicago")
        output = tmp_path / "chicago_output.docx"
        components["formatter"].format(manuscript, style, str(output))
        assert output.exists()
        assert output.stat().st_size > 0

    def test_markdown_to_docx_ieee(self, components, tmp_path):
        md = (
            "# Machine Learning for Network Security\n"
            "By Alex Chen\n"
            "## Abstract\n"
            "A novel approach to intrusion detection.\n"
            "Keywords: machine learning, security\n"
            "## Introduction\n"
            "Network security is a critical concern.\n"
            "## References\n"
            "A. Chen, 'ML for Security,' IEEE Security, vol. 15, no. 3, pp. 45-52, 2023.\n"
        )
        manuscript = components["parser"].parse(md, "markdown")
        result = components["validator"].validate(manuscript, "ieee")
        style = components["registry"].get_style("ieee")
        output = tmp_path / "ieee_output.docx"
        components["formatter"].format(manuscript, style, str(output))
        assert output.exists()
        assert output.stat().st_size > 0

    def test_latex_to_docx_apa(self, components, tmp_path):
        latex = (
            "\\documentclass{article}\n"
            "\\title{LaTeX Test Manuscript}\n"
            "\\author{Jane Smith\\and John Doe}\n"
            "\\begin{document}\n"
            "\\begin{abstract}\n"
            "This is an abstract from LaTeX.\n"
            "\\end{abstract}\n"
            "\\section{Introduction}\n"
            "This is the introduction section.\n"
            "\\section{Methodology}\n"
            "We used a novel approach.\n"
            "\\end{document}\n"
        )
        manuscript = components["parser"].parse(latex, "latex")
        assert manuscript.title == "LaTeX Test Manuscript"
        assert len(manuscript.authors) >= 1
        style = components["registry"].get_style("apa")
        output = tmp_path / "latex_output.docx"
        components["formatter"].format(manuscript, style, str(output))
        assert output.exists()
        assert output.stat().st_size > 0

    def test_plain_text_to_docx_apa(self, components, tmp_path):
        plain = (
            "Plain Text Manuscript\n"
            "INTRODUCTION\n"
            "This is the introduction of the manuscript.\n"
            "METHODOLOGY\n"
            "We used standard research methods.\n"
            "RESULTS\n"
            "The results were significant.\n"
        )
        manuscript = components["parser"].parse(plain, "plain")
        assert manuscript.title == "Plain Text Manuscript"
        style = components["registry"].get_style("apa")
        output = tmp_path / "plain_output.docx"
        components["formatter"].format(manuscript, style, str(output))
        assert output.exists()
        assert output.stat().st_size > 0

    # ---------------------------------------------------------------- #
    #  Validation edge cases                                            #
    # ---------------------------------------------------------------- #

    def test_validation_passes_with_complete_manuscript(self, components):
        ms = Manuscript(
            title="Complete Manuscript",
            authors=[Author(first_name="Jane", last_name="Smith")],
            abstract="A complete manuscript for testing.",
            keywords=["test"],
            sections=[Section(heading="Introduction", level=1, content=[Paragraph(text="Content.")])],
            references=[Reference(authors=[Author(first_name="A", last_name="Author")], year="2020", title="Ref Title", journal="Journal")],
        )
        result = components["validator"].validate(ms, "apa")
        assert result["valid"]
        assert len(result["errors"]) == 0

    def test_validation_fails_without_title(self, components):
        ms = Manuscript(
            title="",
            authors=[Author(first_name="Jane", last_name="Smith")],
            sections=[Section(heading="Introduction", level=1)],
        )
        result = components["validator"].validate(ms, "apa")
        assert not result["valid"]
        assert any(e["code"] == "MISSING_TITLE" for e in result["errors"])

    def test_validation_passes_with_all_styles(self, components):
        ms = Manuscript(
            title="Multi-Style Validation",
            authors=[Author(first_name="Test", last_name="User")],
            abstract="Testing across all styles.",
            keywords=["test", "validation"],
            sections=[Section(heading="Introduction", level=1, content=[Paragraph(text="Content.")])],
        )
        for style_id in ["apa", "mla", "chicago", "ieee", "harvard", "vancouver", "turabian", "acs", "ama"]:
            result = components["validator"].validate(ms, style_id)
            style = components["registry"].get_style(style_id)
            if style.abstract_required and not ms.abstract:
                assert not result["valid"], f"Expected failure for {style_id}"
            else:
                pass

    def test_validation_fails_without_authors(self, components):
        ms = Manuscript(title="No Authors", sections=[Section(heading="Intro", level=1)])
        result = components["validator"].validate(ms, "apa")
        assert not result["valid"]
        assert any(e["code"] == "MISSING_AUTHORS" for e in result["errors"])

    def test_validation_warns_for_short_title(self, components):
        ms = Manuscript(
            title="Hi",
            authors=[Author(first_name="Jane", last_name="Smith")],
        )
        result = components["validator"].validate(ms, "apa")
        assert any(w["code"] == "SHORT_TITLE" for w in result["warnings"])

    # ---------------------------------------------------------------- #
    #  Formatter edge cases                                             #
    # ---------------------------------------------------------------- #

    def test_formatter_with_empty_sections(self, components, tmp_path):
        ms = Manuscript(
            title="Empty Sections",
            authors=[Author(first_name="Jane", last_name="Smith")],
            abstract="Test abstract.",
            sections=[],
        )
        style = components["registry"].get_style("apa")
        output = tmp_path / "empty_sections.docx"
        components["formatter"].format(ms, style, str(output))
        assert output.exists()
        assert output.stat().st_size > 0

    def test_formatter_with_many_authors(self, components, tmp_path):
        authors = [Author(first_name=f"Author{i}", last_name=f"LastName{i}") for i in range(20)]
        ms = Manuscript(
            title="Many Authors",
            authors=authors,
            abstract="Testing with many authors.",
            keywords=["many", "authors"],
            sections=[Section(heading="Introduction", level=1, content=[Paragraph(text="Content.")])],
        )
        style = components["registry"].get_style("apa")
        output = tmp_path / "many_authors.docx"
        components["formatter"].format(ms, style, str(output))
        assert output.exists()
        assert output.stat().st_size > 0

    def test_formatter_with_complex_references(self, components, tmp_path):
        refs = [
            Reference(
                authors=[Author(first_name="Alan", last_name="Turing")],
                year="1950",
                title="Computing Machinery and Intelligence",
                journal="Mind",
                volume="59",
                issue="236",
                pages="433-460",
                doi="10.1093/mind/LIX.236.433",
            ),
            Reference(
                authors=[Author(first_name="John", last_name="McCarthy")],
                year="1960",
                title="Recursive Functions of Symbolic Expressions",
                journal="Communications of the ACM",
                volume="3",
                issue="4",
                pages="184-195",
            ),
            Reference(
                title="Book Without Authors",
                year="2020",
                publisher="Academic Press",
                isbn="978-0-123-45678-9",
            ),
            Reference(
                authors=[Author(first_name="Marie", last_name="Curie")],
                year="1903",
                title="Radioactive Substances",
                doi="10.1000/xyz123",
            ),
        ]
        ms = Manuscript(
            title="Complex References",
            authors=[Author(first_name="Test", last_name="User")],
            abstract="Testing complex reference formatting.",
            keywords=["references", "complex"],
            sections=[Section(heading="Introduction", level=1, content=[Paragraph(text="Content.")])],
            references=refs,
        )
        style = components["registry"].get_style("apa")
        output = tmp_path / "complex_refs.docx"
        components["formatter"].format(ms, style, str(output))
        assert output.exists()
        assert output.stat().st_size > 0

    def test_formatter_with_nested_sections(self, components, tmp_path):
        ms = Manuscript(
            title="Nested Sections",
            authors=[Author(first_name="Test", last_name="User")],
            abstract="Testing nested sections.",
            sections=[
                Section(
                    heading="Level 1",
                    level=1,
                    content=[Paragraph(text="Level 1 content.")],
                    subsections=[
                        Section(
                            heading="Level 2",
                            level=2,
                            content=[Paragraph(text="Level 2 content.")],
                            subsections=[
                                Section(
                                    heading="Level 3",
                                    level=3,
                                    content=[Paragraph(text="Level 3 content.")],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        style = components["registry"].get_style("apa")
        output = tmp_path / "nested_sections.docx"
        components["formatter"].format(ms, style, str(output))
        assert output.exists()
        assert output.stat().st_size > 0

    def test_formatter_with_custom_options(self, components, tmp_path):
        from app.api.models import FormattingOptions
        ms = Manuscript(
            title="Custom Options",
            authors=[Author(first_name="Jane", last_name="Smith")],
            abstract="Testing custom formatting options.",
            sections=[Section(heading="Introduction", level=1, content=[Paragraph(text="Content.")])],
        )
        style = components["registry"].get_style("apa")
        options = FormattingOptions(
            output_format="docx",
            page_size="Letter",
            font_family="Arial",
            font_size=11,
            line_spacing=1.5,
            margins={"top": 1.0, "bottom": 1.0, "left": 1.0, "right": 1.0},
        )
        output = tmp_path / "custom_options.docx"
        components["formatter"].format(ms, style, str(output), options)
        assert output.exists()
        assert output.stat().st_size > 0

    def test_formatter_html_preview(self, components):
        ms = Manuscript(
            title="Preview Test",
            authors=[Author(first_name="Jane", last_name="Smith")],
            abstract="A preview abstract.",
            keywords=["preview"],
            sections=[Section(heading="Introduction", level=1, content=[Paragraph(text="Content.")])],
            references=[Reference(title="A reference", year="2020")],
        )
        style = components["registry"].get_style("apa")
        html = components["formatter"].generate_html_preview(ms, style)
        assert "<!DOCTYPE html>" in html
        assert "Preview Test" in html
        assert "Abstract" in html
        assert "Keywords" in html
        assert "References" in html

    def test_parser_auto_detect_markdown(self, components):
        text = "# Title\n## Section\nContent."
        fmt = components["parser"].detect_format(text)
        assert fmt == "markdown"

    def test_parser_auto_detect_latex(self, components):
        text = "\\documentclass{article}\n\\section{Intro}\nContent."
        fmt = components["parser"].detect_format(text)
        assert fmt == "latex"

    def test_parser_auto_detect_plain(self, components):
        text = "Just some plain text\nwith no special formatting."
        fmt = components["parser"].detect_format(text)
        assert fmt == "plain"
