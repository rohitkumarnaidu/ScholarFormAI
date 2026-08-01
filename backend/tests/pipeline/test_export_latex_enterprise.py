# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from app.models import ImageFormat
from __future__ import annotations
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from app.pipeline.export.latex_exporter import (
    LaTeXExporter,
    escape_latex,
    _resolve_pandoc_binary,
    _convert_via_pandoc,
)

def _make_doc(**overrides):
    from app.models import PipelineDocument, Block, BlockType
    from app.models.pipeline_document import DocumentMetadata, TemplateInfo

    defaults = dict(
        document_id="tex1",
        blocks=[
            Block(block_id="b1", index=1, block_type=BlockType.TITLE, text="Paper Title", section_name="title"),
            Block(block_id="b2", index=2, block_type=BlockType.HEADING_1, text="Introduction", section_name="intro"),
            Block(block_id="b3", index=3, block_type=BlockType.BODY, text="Body text.", section_name="body"),
            Block(block_id="b4", index=4, block_type=BlockType.HEADING_2, text="Sub Section", section_name="sub"),
            Block(block_id="b5", index=5, block_type=BlockType.HEADING_3, text="Sub Sub", section_name="subsub"),
        ],
        metadata=DocumentMetadata(
            title="Test Paper",
            authors=["Alice Smith", "Bob Jones"],
            abstract="This is a test.",
            keywords=["test", "paper"],
        ),
        template=TemplateInfo(template_name="default"),
        references=[],
        figures=[],
        tables=[],
        equations=[],
    )
    defaults.update(overrides)
    doc = PipelineDocument(**{k: v for k, v in defaults.items() if k != "template"})
    doc.template = defaults["template"]
    return doc

# ── escape_latex ───────────────────────────────────────────────────────

class TestEscapeLatex:
    def test_ampersand(self):
        assert escape_latex("a&b") == r"a\&b"

    def test_percent(self):
        assert escape_latex("100%") == r"100\%"

    def test_dollar(self):
        assert escape_latex("$10") == r"\$10"

    def test_hash(self):
        assert escape_latex("#1") == r"\#1"

    def test_underscore(self):
        assert escape_latex("a_b") == r"a\_b"

    def test_braces(self):
        assert escape_latex("{hello}") == r"\{hello\}"

    def test_tilde(self):
        assert r"\textasciitilde{}" in escape_latex("~test")

    def test_caret(self):
        assert r"\textasciicircum{}" in escape_latex("^test")

    def test_backslash(self):
        assert r"\textbackslash{}" in escape_latex("\\test")

    def test_all_chars(self):
        result = escape_latex("&%$#_{}~^\\")
        assert "\\&" in result
        assert "\\%" in result
        assert "\\$" in result

    def test_empty_string(self):
        assert escape_latex("") == ""

    def test_no_special_chars(self):
        assert escape_latex("hello world") == "hello world"

    def test_none_input(self):
        with pytest.raises(TypeError):
            escape_latex(None)

# ── _resolve_pandoc_binary ─────────────────────────────────────────────

class TestResolvePandoc:
    def test_env_var_set(self):
        with patch.dict(os.environ, {"PANDOC_PATH": "/custom/pandoc"}, clear=True):
            assert _resolve_pandoc_binary() == "/custom/pandoc"

    def test_env_var_empty(self):
        with patch.dict(os.environ, {"PANDOC_PATH": ""}, clear=True):
            with patch("shutil.which", return_value="/usr/bin/pandoc"):
                assert _resolve_pandoc_binary() == "/usr/bin/pandoc"

    def test_env_not_set_pandoc_not_found(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("shutil.which", return_value=None):
                assert _resolve_pandoc_binary() is None

    def test_env_var_whitespace_only(self):
        with patch.dict(os.environ, {"PANDOC_PATH": "  "}, clear=True):
            with patch("shutil.which", return_value="/usr/bin/pandoc"):
                assert _resolve_pandoc_binary() == "/usr/bin/pandoc"

# ── _convert_via_pandoc ────────────────────────────────────────────────

class TestConvertViaPandoc:
    def test_pandoc_not_found(self):
        with patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value=None):
            assert _convert_via_pandoc("in.docx", "out.tex", 120) is False

    def test_success(self):
        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        with (
            patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/usr/bin/pandoc"),
            patch("subprocess.run", return_value=mock_result),
            patch("os.path.exists", return_value=True),
        ):
            assert _convert_via_pandoc("in.docx", "out.tex", 120) is True

    def test_failure_exit_code(self):
        mock_result = MagicMock(returncode=1, stdout="", stderr="error")
        with (
            patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/usr/bin/pandoc"),
            patch("subprocess.run", return_value=mock_result),
        ):
            assert _convert_via_pandoc("in.docx", "out.tex", 120) is False

    def test_success_but_output_missing(self):
        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        with (
            patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/usr/bin/pandoc"),
            patch("subprocess.run", return_value=mock_result),
            patch("os.path.exists", return_value=False),
        ):
            assert _convert_via_pandoc("in.docx", "out.tex", 120) is False

    def test_timeout(self):
        with (
            patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/usr/bin/pandoc"),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="pandoc", timeout=120)),
        ):
            assert _convert_via_pandoc("in.docx", "out.tex", 120) is False

    def test_os_error(self):
        with (
            patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/usr/bin/pandoc"),
            patch("subprocess.run", side_effect=OSError("not found")),
        ):
            assert _convert_via_pandoc("in.docx", "out.tex", 120) is False

# ── LaTeXExporter.convert_to_latex ─────────────────────────────────────

class TestConvertToLatex:
    def test_file_not_found(self):
        exporter = LaTeXExporter()
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(RuntimeError, match="DOCX not found"):
                exporter.convert_to_latex("/nonexistent/doc.docx", "/tmp/out")

    def test_pandoc_not_found(self):
        exporter = LaTeXExporter()
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value=None),
        ):
            with pytest.raises(RuntimeError, match="Pandoc is not installed"):
                exporter.convert_to_latex("/tmp/doc.docx", "/tmp/out")

    def test_conversion_success(self):
        exporter = LaTeXExporter()
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/usr/bin/pandoc"),
            patch("app.pipeline.export.latex_exporter._convert_via_pandoc", return_value=True),
            patch("pathlib.Path.mkdir"),
        ):
            result = exporter.convert_to_latex("/tmp/doc.docx", "/tmp/out")
            assert result.endswith(".tex")

    def test_conversion_failure(self):
        exporter = LaTeXExporter()
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/usr/bin/pandoc"),
            patch("app.pipeline.export.latex_exporter._convert_via_pandoc", return_value=False),
        ):
            with pytest.raises(RuntimeError, match="Pandoc conversion failed"):
                exporter.convert_to_latex("/tmp/doc.docx", "/tmp/out")

    def test_timeout_configurable(self):
        exporter = LaTeXExporter(timeout_seconds=300)
        assert exporter.timeout == 300

    def test_stem_from_filename(self):
        exporter = LaTeXExporter()
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/usr/bin/pandoc"),
            patch("app.pipeline.export.latex_exporter._convert_via_pandoc", return_value=True),
            patch("pathlib.Path.mkdir"),
        ):
            result = exporter.convert_to_latex("/tmp/my_manuscript.docx", "/tmp/out")
            assert "my_manuscript.tex" in result

# ── LaTeXExporter.export_from_document ─────────────────────────────────

class TestExportFromDocument:
    def test_default_template(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        with (
            patch("pathlib.Path.mkdir"),
            patch.object(Path, "write_text"),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "write_bytes"),
            patch("app.pipeline.export.latex_exporter.LaTeXExporter._write_bibtex"),
        ):
            result = exporter.export_from_document(doc, "/tmp/out")
            assert result.endswith("manuscript.tex")

    def test_all_templates(self):
        for template_name in ["ieee", "acm", "apa", "springer", "nature", "elsevier", "mla", "chicago", "vancouver", "harvard", "default"]:
            exporter = LaTeXExporter()
            doc = _make_doc()
            doc.template.template_name = template_name
            with (
                patch("pathlib.Path.mkdir"),
                patch.object(Path, "write_text"),
                patch.object(Path, "exists", return_value=True),
                patch.object(Path, "write_bytes"),
                patch("app.pipeline.export.latex_exporter.LaTeXExporter._write_bibtex"),
            ):
                result = exporter.export_from_document(doc, "/tmp/out")
                assert result.endswith(".tex")

    def test_template_name_none(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        doc.template.template_name = None
        with (
            patch("pathlib.Path.mkdir"),
            patch.object(Path, "write_text"),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "write_bytes"),
            patch("app.pipeline.export.latex_exporter.LaTeXExporter._write_bibtex"),
        ):
            result = exporter.export_from_document(doc, "/tmp/out")
            assert result.endswith(".tex")

    def test_template_missing(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        doc.template = None
        with (
            patch("pathlib.Path.mkdir"),
            patch.object(Path, "write_text"),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "write_bytes"),
            patch("app.pipeline.export.latex_exporter.LaTeXExporter._write_bibtex"),
        ):
            result = exporter.export_from_document(doc, "/tmp/out")
            assert result.endswith(".tex")

    def test_with_references(self):
        from app.models import Reference
        exporter = LaTeXExporter()
        doc = _make_doc(references=[
            Reference(reference_id="r1", index=1, block_id="r1", block_index=1,
                      citation_key="ref1", year="2024", authors=["A"],
                      title="Paper", raw_text="[1] Ref", metadata={"title": "Paper", "authors": "A", "year": "2024"}),
        ])
        with (
            patch("pathlib.Path.mkdir"),
            patch.object(Path, "write_text"),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "write_bytes"),
            patch("app.pipeline.export.latex_exporter.LaTeXExporter._write_bibtex"),
        ):
            result = exporter.export_from_document(doc, "/tmp/out")
            assert result.endswith(".tex")

# ── _write_title_authors ───────────────────────────────────────────────

class TestWriteTitleAuthors:
    def test_title_and_authors(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        lines = []
        exporter._write_title_authors(lines, doc)
        content = "\n".join(lines)
        assert r"\title{Test Paper}" in content
        assert r"Alice Smith" in content
        assert r"Bob Jones" in content

    def test_title_missing(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        doc.metadata.title = None
        lines = []
        exporter._write_title_authors(lines, doc)
        assert r"\title{Untitled}" in "\n".join(lines)

    def test_authors_empty(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        doc.metadata.authors = []
        lines = []
        exporter._write_title_authors(lines, doc)
        assert r"\date" in "\n".join(lines)
        assert r"\maketitle" in "\n".join(lines)

    def test_authors_single(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        doc.metadata.authors = ["Single Author"]
        lines = []
        exporter._write_title_authors(lines, doc)
        assert "Single Author" in "\n".join(lines)

    def test_date_present(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        doc.metadata.publication_date = None
        lines = []
        exporter._write_title_authors(lines, doc)
        assert r"\date{\today}" in "\n".join(lines)

    def test_date_absent_uses_today(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        doc.metadata.publication_date = None
        lines = []
        exporter._write_title_authors(lines, doc)
        assert r"\date{\today}" in "\n".join(lines)

    def test_date_datetime_formatted(self):
        from datetime import datetime
        exporter = LaTeXExporter()
        doc = _make_doc()
        doc.metadata.publication_date = datetime(2024, 6, 15)
        lines = []
        exporter._write_title_authors(lines, doc)
        assert "2024" in "\n".join(lines)

    def test_special_chars_in_title(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        doc.metadata.title = "Title with & and %"
        lines = []
        exporter._write_title_authors(lines, doc)
        content = "\n".join(lines)
        assert r"\&" in content
        assert r"\%" in content

# ── _write_abstract ────────────────────────────────────────────────────

class TestWriteAbstract:
    def test_abstract_present(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        lines = []
        exporter._write_abstract(lines, doc)
        content = "\n".join(lines)
        assert r"\begin{abstract}" in content
        assert "This is a test." in content

    def test_abstract_absent(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        doc.metadata.abstract = None
        lines = []
        exporter._write_abstract(lines, doc)
        assert r"\begin{abstract}" not in "\n".join(lines)

    def test_keywords_present(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        lines = []
        exporter._write_abstract(lines, doc)
        assert "Keywords:" in "\n".join(lines)

    def test_keywords_absent(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        doc.metadata.keywords = []
        lines = []
        exporter._write_abstract(lines, doc)
        assert "Keywords:" not in "\n".join(lines)

    def test_special_chars_in_abstract(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        doc.metadata.abstract = "Abstract with & and %"
        lines = []
        exporter._write_abstract(lines, doc)
        content = "\n".join(lines)
        assert r"\&" in content
        assert r"\%" in content

# ── _write_sections ────────────────────────────────────────────────────

class TestWriteSections:
    def _make_section_doc(self, blocks_data):
        """Helper to build doc with custom blocks using real Block instances."""
        from app.models import PipelineDocument, Block
        from app.models.pipeline_document import DocumentMetadata, TemplateInfo
        doc = PipelineDocument(
            document_id="t1",
            blocks=[Block(**b) for b in blocks_data],
            metadata=DocumentMetadata(),
            template=TemplateInfo(template_name="default"),
        )
        return doc

    def test_heading_1(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        lines = []
        exporter._write_sections(lines, doc)
        assert r"\section{Introduction}" in "\n".join(lines)

    def test_heading_2(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        lines = []
        exporter._write_sections(lines, doc)
        assert r"\subsection{Sub Section}" in "\n".join(lines)

    def test_heading_3(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        lines = []
        exporter._write_sections(lines, doc)
        assert r"\subsubsection{Sub Sub}" in "\n".join(lines)

    def test_body_text(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        lines = []
        exporter._write_sections(lines, doc)
        assert "Body text." in "\n".join(lines)

    def test_reference_types_skipped(self):
        doc = self._make_section_doc([
            dict(block_id="r1", index=1, text="Ref text", block_type="reference_entry"),
        ])
        exporter = LaTeXExporter()
        lines = []
        exporter._write_sections(lines, doc)
        assert "Ref text" not in "\n".join(lines)

    def test_empty_text_skipped(self):
        doc = self._make_section_doc([
            dict(block_id="b1", index=1, text="", block_type="body"),
        ])
        exporter = LaTeXExporter()
        lines = []
        exporter._write_sections(lines, doc)

    def test_figure_type_skipped(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        doc.blocks = [MagicMock(block_id="b1", index=1, text="Fig text", block_type="figure")]
        lines = []
        exporter._write_sections(lines, doc)
        content = "\n".join(lines)
        assert "Fig text" not in content

    def test_table_type_skipped(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        doc.blocks = [MagicMock(block_id="b1", index=1, text="Tbl text", block_type="table")]
        lines = []
        exporter._write_sections(lines, doc)
        assert "Tbl text" not in "\n".join(lines)

    def test_unknown_type_as_plain_text(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        doc.blocks = [MagicMock(block_id="b1", index=1, text="Plain", block_type="unknown_type")]
        lines = []
        exporter._write_sections(lines, doc)
        assert "Plain" in "\n".join(lines)

    def test_blocks_sorted_by_index(self):
        from app.models import Block, BlockType
        exporter = LaTeXExporter()
        doc = _make_doc(blocks=[
            Block(block_id="b2", index=2, block_type=BlockType.BODY, text="Second"),
            Block(block_id="b1", index=1, block_type=BlockType.BODY, text="First"),
        ])
        lines = []
        exporter._write_sections(lines, doc)
        content = "\n".join(lines)
        assert content.index("First") < content.index("Second")

# ── _write_figures ─────────────────────────────────────────────────────

class TestWriteFigures:
    def test_no_figures(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        lines = []
        exporter._write_figures(lines, doc)
        assert len(lines) == 0

    def test_figure_with_caption_and_label(self):
        from app.models import Figure
        exporter = LaTeXExporter()
        doc = _make_doc(figures=[
            Figure(figure_id="fig1", index=0, caption_text="A figure", label="fig:1"),
        ])
        lines = []
        exporter._write_figures(lines, doc)
        content = "\n".join(lines)
        assert r"\begin{figure}" in content
        assert r"\caption{A figure}" in content
        assert r"\label{fig:1}" in content

    def test_figure_with_image_data(self):
        from app.models import Figure
        exporter = LaTeXExporter()
        doc = _make_doc(figures=[
            Figure(figure_id="fig1", index=0, caption_text="Fig",
                   image_data=b"imgdata", image_format=ImageFormat.PNG),
        ])
        lines = []
        with patch.object(Path, "write_bytes"), patch.object(Path, "exists", return_value=False):
            exporter._write_figures(lines, doc, out_dir=Path("/tmp/out"))
        assert r"\includegraphics" in "\n".join(lines)

    def test_figure_no_image_data(self):
        from app.models import Figure
        exporter = LaTeXExporter()
        doc = _make_doc(figures=[
            Figure(figure_id="fig1", index=0, caption_text="Only caption"),
        ])
        lines = []
        exporter._write_figures(lines, doc)
        assert r"\includegraphics" not in "\n".join(lines)

    def test_figure_without_label(self):
        from app.models import Figure
        exporter = LaTeXExporter()
        doc = _make_doc(figures=[
            Figure(figure_id="fig1", index=0, caption_text="No label"),
        ])
        lines = []
        exporter._write_figures(lines, doc)
        assert r"\label" not in "\n".join(lines)

    def test_figure_caption_empty(self):
        from app.models import Figure
        exporter = LaTeXExporter()
        doc = _make_doc(figures=[
            Figure(figure_id="fig1", index=0, caption_text=None),
        ])
        lines = []
        exporter._write_figures(lines, doc)
        assert r"\caption{Figure}" in "\n".join(lines)

# ── _write_tables ──────────────────────────────────────────────────────

class TestWriteTables:
    def _make_table_mock(self, index=0, caption_text="Table", rows=None, rows_data=None):
        """Table model uses cells not rows; exporter accesses tbl.rows so use MagicMock."""
        tbl = MagicMock()
        tbl.index = index
        tbl.caption_text = caption_text
        tbl.rows = rows or rows_data or []
        return tbl

    def test_no_tables(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        lines = []
        exporter._write_tables(lines, doc)
        assert len(lines) == 0

    def test_table_with_rows(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        doc.tables = [self._make_table_mock(rows=[["H1", "H2"], ["A", "B"]])]
        lines = []
        exporter._write_tables(lines, doc)
        content = "\n".join(lines)
        assert r"\begin{table}" in content
        assert r"\begin{tabular}" in content
        assert "H1 & H2" in content
        assert r"\caption{Table}" in content

    def test_table_without_rows(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        doc.tables = [self._make_table_mock(rows=[])]
        lines = []
        exporter._write_tables(lines, doc)
        assert r"\begin{tabular}" not in "\n".join(lines)

    def test_table_with_hline(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        doc.tables = [self._make_table_mock(rows=[["A", "B"], ["C", "D"]])]
        lines = []
        exporter._write_tables(lines, doc)
        hlines = [l for l in lines if r"\hline" in l]
        assert len(hlines) >= 2

# ── _write_equations ───────────────────────────────────────────────────

class TestWriteEquations:
    def test_no_equations(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        lines = []
        exporter._write_equations(lines, doc)
        assert len(lines) == 0

    def test_equation_with_text(self):
        from app.models import Equation
        exporter = LaTeXExporter()
        doc = _make_doc(equations=[
            Equation(equation_id="eq1", index=1, block_id="b1",
                     text="x = y"),
        ])
        lines = []
        exporter._write_equations(lines, doc)
        content = "\n".join(lines)
        assert r"\begin{equation}" in content
        assert "x = y" in content

    def test_equation_with_align(self):
        from app.models import Equation
        exporter = LaTeXExporter()
        doc = _make_doc(equations=[
            Equation(equation_id="eq2", index=2, block_id="b2",
                     text=r"\begin{align}x &= y\end{align}"),
        ])
        lines = []
        exporter._write_equations(lines, doc)
        content = "\n".join(lines)
        assert r"\begin{align}" in content
        assert r"\begin{equation}" not in content

    def test_equation_empty_text(self):
        from app.models import Equation
        exporter = LaTeXExporter()
        doc = _make_doc(equations=[
            Equation(equation_id="eq3", index=3, block_id="b3", text=""),
        ])
        lines = []
        exporter._write_equations(lines, doc)
        assert len(lines) == 0

    def test_equation_whitespace_only(self):
        from app.models import Equation
        exporter = LaTeXExporter()
        doc = _make_doc(equations=[
            Equation(equation_id="eq4", index=4, block_id="b4", text="   "),
        ])
        lines = []
        exporter._write_equations(lines, doc)
        assert len(lines) == 0

# ── _write_bibtex ──────────────────────────────────────────────────────

class TestWriteBibtex:
    def test_no_references(self):
        exporter = LaTeXExporter()
        doc = _make_doc()
        bib = MagicMock(spec=Path)
        exporter._write_bibtex(doc, bib)
        bib.write_text.assert_not_called()

    def test_with_metadata_article(self):
        from app.models import Reference
        exporter = LaTeXExporter()
        doc = _make_doc(references=[
            Reference(reference_id="r1", index=1, block_id="r1", block_index=1,
                      citation_key="ref1", year="2024", authors=["A"],
                      title="Paper", raw_text="[1] Ref",
                      metadata={"title": "Paper", "authors": "A Author", "year": "2024", "journal": "J", "doi": "10.1234/test"}),
        ])
        bib = MagicMock(spec=Path)
        exporter._write_bibtex(doc, bib)
        bib.write_text.assert_called_once()
        content = bib.write_text.call_args[0][0]
        assert "@article" in content
        assert "Paper" in content
        assert "A Author" in content
        assert "10.1234/test" in content

    def test_without_metadata_misc(self):
        from app.models import Reference
        exporter = LaTeXExporter()
        doc = _make_doc(references=[
            Reference(reference_id="r1", index=1, block_id="r1", block_index=1,
                      citation_key="ref1", year="2024", authors=["A"],
                      title="Paper", raw_text="[1] Some text", metadata={}),
        ])
        bib = MagicMock(spec=Path)
        exporter._write_bibtex(doc, bib)
        bib.write_text.assert_called_once()
        content = bib.write_text.call_args[0][0]
        assert "@misc" in content

    def test_no_formatted_or_raw_text(self):
        from app.models import Reference
        exporter = LaTeXExporter()
        doc = _make_doc(references=[
            Reference(reference_id="r1", index=1, block_id="r1", block_index=1,
                      citation_key="ref1", year="2024", authors=["A"],
                      title="", raw_text="", metadata={}),
        ])
        bib = MagicMock(spec=Path)
        exporter._write_bibtex(doc, bib)
        bib.write_text.assert_not_called()

    def test_multiple_references(self):
        from app.models import Reference
        exporter = LaTeXExporter()
        doc = _make_doc(references=[
            Reference(reference_id="r1", index=1, block_id="r1", block_index=1,
                      citation_key="r1", year="2024", authors=["A"],
                      title="P1", raw_text="[1]", metadata={"title": "P1", "authors": "A"}),
            Reference(reference_id="r2", index=2, block_id="r2", block_index=2,
                      citation_key="r2", year="2024", authors=["B"],
                      title="P2", raw_text="[2]", metadata={"title": "P2", "authors": "B"}),
        ])
        bib = MagicMock(spec=Path)
        exporter._write_bibtex(doc, bib)
        bib.write_text.assert_called_once()
        content = bib.write_text.call_args[0][0]
        assert "@article{ref_1" in content
        assert "@article{ref_2" in content
