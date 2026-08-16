# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import pytest

from app.pipeline.parsing.tex_parser import TexParser


@pytest.fixture
def parser():
    return TexParser()


class TestTexParserSupportsFormat:
    def test_supports_tex(self, parser):
        assert parser.supports_format(".tex")
        assert parser.supports_format(".latex")

    def test_not_supports_other(self, parser):
        assert not parser.supports_format(".docx")


class TestTexParserParse:
    def test_parse_basic(self, parser, tmp_path):
        f = tmp_path / "test.tex"
        f.write_text(r"\documentclass{article}\begin{document}Hello\end{document}")
        doc = parser.parse(str(f), "doc1")
        assert doc.document_id == "doc1"

    def test_file_not_found(self, parser):
        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent.tex", "doc1")

    def test_utf8_fallback(self, parser, tmp_path):
        f = tmp_path / "test.tex"
        f.write_bytes("café".encode("latin-1"))
        doc = parser.parse(str(f), "doc1")
        assert doc.document_id == "doc1"

    def test_no_document_environment(self, parser, tmp_path):
        f = tmp_path / "raw.tex"
        f.write_text("Just some text")
        doc = parser.parse(str(f), "doc1")
        assert doc is not None


class TestTexParserMetadata:
    def test_extract_title(self, parser):
        meta = parser._extract_metadata(r"\title{My Paper}\author{John}")
        assert meta.title == "My Paper"

    def test_extract_author(self, parser):
        meta = parser._extract_metadata(r"\author{John Doe}")
        assert meta.authors == ["John Doe"]

    def test_extract_multiple_authors(self, parser):
        meta = parser._extract_metadata(r"\author{John Doe \and Jane Smith}")
        assert len(meta.authors) >= 1

    def test_extract_abstract(self, parser):
        meta = parser._extract_metadata(r"\begin{abstract}This is the abstract.\end{abstract}")
        assert "abstract" in meta.abstract.lower()

    def test_metadata_skips_comments(self, parser):
        meta = parser._extract_metadata("%\\title{Hidden}\n\\title{Visible}")
        assert meta.title == "Visible"


class TestTexParserContent:
    def test_section_heading(self, parser):
        blocks = parser._extract_content(r"\section{Introduction}")
        assert len(blocks) >= 1
        assert blocks[0].metadata.get("potential_heading") is True
        assert blocks[0].text == "Introduction"

    def test_subsection_heading(self, parser):
        blocks = parser._extract_content(r"\subsection{Background}")
        assert blocks[0].metadata["heading_level"] == 2

    def test_subsubsection_heading(self, parser):
        blocks = parser._extract_content(r"\subsubsection{Details}")
        assert blocks[0].metadata["heading_level"] == 3

    def test_includegraphics(self, parser):
        blocks = parser._extract_content(r"\includegraphics{figure.png}")
        assert len(blocks) >= 1
        assert blocks[0].metadata.get("is_image_reference") is True
        assert blocks[0].metadata.get("image_source") == "figure.png"

    def test_includegraphics_with_options(self, parser):
        blocks = parser._extract_content(r"\includegraphics[width=0.5\textwidth]{fig.png}")
        assert blocks[0].metadata.get("image_source") == "fig.png"

    def test_display_math(self, parser):
        blocks = parser._extract_content(r"\[E = mc^2\]")
        assert any(b.metadata.get("is_equation") for b in blocks)

    def test_equation_environment(self, parser):
        blocks = parser._extract_content(r"\begin{equation}F=ma\end{equation}")
        assert any(b.metadata.get("is_equation") for b in blocks)

    def test_itemize(self, parser):
        blocks = parser._extract_content(r"\begin{itemize}\item First\item Second\end{itemize}")
        items = [b for b in blocks if b.metadata.get("is_list_item")]
        assert len(items) >= 1

    def test_enumerate(self, parser):
        blocks = parser._extract_content(r"\begin{enumerate}\item One\item Two\end{enumerate}")
        items = [b for b in blocks if b.metadata.get("list_type") == "ordered"]
        assert len(items) >= 1

    def test_table_extraction(self, parser):
        blocks = parser._extract_content(r"\begin{tabular}{cc}a & b\end{tabular}")
        tables = [b for b in blocks if b.metadata.get("is_table")]
        assert len(tables) >= 1

    def test_table_within_table_environment(self, parser):
        blocks = parser._extract_content(r"\begin{table}\centering\begin{tabular}{c}c\end{tabular}\end{table}")
        tables = [b for b in blocks if b.metadata.get("is_table")]
        assert len(tables) >= 1

    def test_paragraphs_extracted_from_body(self, parser):
        import re

        content = r"\begin{document}First para.\n\nSecond para.\end{document}"
        doc_match = re.search(r"\\begin\{document\}(.*?)\\end\{document\}", content, re.DOTALL)
        doc_match.group(1)
        blocks = parser._extract_content(content)
        assert len(blocks) >= 1

    def test_remove_comments(self, parser):
        result = parser._remove_comments("text % comment\nmore text")
        assert "more text" in result
        assert "comment" not in result

    def test_clean_latex_removes_commands(self, parser):
        result = parser._clean_latex(r"\textbf{bold} normal")
        assert "bold" in result
        assert "textbf" not in result

    def test_clean_latex_emph(self, parser):
        result = parser._clean_latex(r"\emph{emphasized}")
        assert "emphasized" in result

    def test_parse_document_body_only(self, parser, tmp_path):
        f = tmp_path / "doc.tex"
        f.write_text(r"\begin{document}Content\end{document}")
        doc = parser.parse(str(f), "doc1")
        assert doc.original_filename == "doc.tex"
