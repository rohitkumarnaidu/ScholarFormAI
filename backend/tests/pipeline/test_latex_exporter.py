# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
import pytest

class TestLaTeXExporter:
    def _make_doc(self, metadata=None, blocks=None, figures=None, tables=None, equations=None, references=None, template=None):
        from app.models import BlockType
        doc = MagicMock()
        doc.metadata = metadata or MagicMock()
        doc.metadata.title = "Test Manuscript"
        doc.metadata.authors = ["Alice Smith", "Bob Jones"]
        doc.metadata.publication_date = "2024"
        doc.metadata.abstract = "This is the abstract."
        doc.metadata.keywords = ["test"]
        doc.blocks = blocks or []
        doc.figures = figures or []
        doc.tables = tables or []
        doc.equations = equations or []
        doc.references = references or []
        doc.template = template
        return doc

    def test_escape_latex(self):
        from app.models import BlockType
        from app.pipeline.export.latex_exporter import escape_latex
        assert escape_latex("A & B % C") == r"A \& B \% C"
        assert escape_latex("normal text") == "normal text"
        assert escape_latex("$100 #1") == r"\$100 \#1"

    def test_resolve_pandoc_binary_from_env(self):
        from app.models import BlockType
        with patch.dict("os.environ", {"PANDOC_PATH": "/usr/local/bin/pandoc"}, clear=True):
            from app.pipeline.export.latex_exporter import _resolve_pandoc_binary
            assert _resolve_pandoc_binary() == "/usr/local/bin/pandoc"

    def test_resolve_pandoc_binary_from_shutil(self):
        from app.models import BlockType
        with patch.dict("os.environ", {}, clear=True):
            with patch("app.pipeline.export.latex_exporter.shutil.which", return_value="/usr/bin/pandoc"):
                from app.pipeline.export.latex_exporter import _resolve_pandoc_binary
                assert _resolve_pandoc_binary() == "/usr/bin/pandoc"

    def test_resolve_pandoc_not_found(self):
        from app.models import BlockType
        with patch.dict("os.environ", {}, clear=True):
            with patch("app.pipeline.export.latex_exporter.shutil.which", return_value=None):
                from app.pipeline.export.latex_exporter import _resolve_pandoc_binary
                assert _resolve_pandoc_binary() is None

    def test_convert_via_pandoc_success(self):
        from app.models import BlockType
        with patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/usr/bin/pandoc"), \
             patch("app.pipeline.export.latex_exporter.subprocess.run") as mock_run, \
             patch("app.pipeline.export.latex_exporter.os.path.exists", return_value=True):
            mock_run.return_value.returncode = 0
            from app.pipeline.export.latex_exporter import _convert_via_pandoc
            result = _convert_via_pandoc("test.docx", "out.tex", 120)
            assert result is True

    def test_convert_via_pandoc_failure(self):
        from app.models import BlockType
        with patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/usr/bin/pandoc"), \
             patch("app.pipeline.export.latex_exporter.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "error"
            from app.pipeline.export.latex_exporter import _convert_via_pandoc
            result = _convert_via_pandoc("test.docx", "out.tex", 120)
            assert result is False

    def test_convert_via_pandoc_timeout(self):
        from app.models import BlockType
        with patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/usr/bin/pandoc"), \
             patch("app.pipeline.export.latex_exporter.subprocess.run", side_effect=TimeoutError):
            from app.pipeline.export.latex_exporter import _convert_via_pandoc
            result = _convert_via_pandoc("test.docx", "out.tex", 120)
            assert result is False

    def test_convert_to_latex_no_docx(self):
        from app.models import BlockType
        from app.pipeline.export.latex_exporter import LaTeXExporter
        exporter = LaTeXExporter()
        with patch("app.pipeline.export.latex_exporter.Path.exists", return_value=False):
            with pytest.raises(RuntimeError, match="DOCX not found"):
                exporter.convert_to_latex("nonexistent.docx", "/tmp", "default")

    def test_convert_to_latex_no_pandoc(self):
        from app.models import BlockType
        from app.pipeline.export.latex_exporter import LaTeXExporter
        exporter = LaTeXExporter()
        with patch("app.pipeline.export.latex_exporter.Path.exists", return_value=True), \
             patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value=None):
            with pytest.raises(RuntimeError, match="Pandoc is not installed"):
                exporter.convert_to_latex("test.docx", "/tmp", "default")

    def test_convert_to_latex_pandoc_fails(self):
        from app.models import BlockType
        from app.pipeline.export.latex_exporter import LaTeXExporter
        exporter = LaTeXExporter()
        with patch("app.pipeline.export.latex_exporter.Path.exists", return_value=True), \
             patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/usr/bin/pandoc"), \
             patch("app.pipeline.export.latex_exporter._convert_via_pandoc", return_value=False):
            with pytest.raises(RuntimeError, match="Pandoc conversion failed"):
                exporter.convert_to_latex("test.docx", "/tmp", "default")

    def test_export_from_document_default_template(self, tmp_path):
        from app.models import BlockType
        from app.pipeline.export.latex_exporter import LaTeXExporter
        doc = self._make_doc()
        exporter = LaTeXExporter()
        result = exporter.export_from_document(doc, str(tmp_path))
        assert result.endswith(".tex")

    def test_export_from_document_with_template(self, tmp_path):
        from app.models import BlockType
        from app.pipeline.export.latex_exporter import LaTeXExporter
        template = MagicMock()
        template.template_name = "IEEE"
        doc = self._make_doc(template=template)
        exporter = LaTeXExporter()
        result = exporter.export_from_document(doc, str(tmp_path))
        assert result.endswith(".tex")
        content = tmp_path.joinpath("manuscript.tex").read_text(encoding="utf-8")
        assert "IEEEtran" in content

    def test_export_from_document_with_sections(self, tmp_path):
        from app.models import BlockType
        from app.pipeline.export.latex_exporter import LaTeXExporter
        blocks = []
        for btype, text in [("HEADING_1", "Introduction"), ("BODY", "Hello world"), ("HEADING_2", "Methods")]:
            b = MagicMock()
            b.index = len(blocks)
            b.text = text
            b.block_type = btype
            blocks.append(b)
        doc = self._make_doc(blocks=blocks)
        exporter = LaTeXExporter()
        result = exporter.export_from_document(doc, str(tmp_path))
        content = tmp_path.joinpath("manuscript.tex").read_text(encoding="utf-8")
        assert "Introduction" in content
        assert "Hello world" in content

    def test_export_with_figures(self, tmp_path):
        from app.models import BlockType
        from app.pipeline.export.latex_exporter import LaTeXExporter
        fig = MagicMock()
        fig.index = 0
        fig.caption_text = "Test Figure"
        fig.image_data = b"fake_image_data"
        fig.image_format = "png"
        fig.label = "fig:test"
        doc = self._make_doc(figures=[fig])
        exporter = LaTeXExporter()
        exporter.export_from_document(doc, str(tmp_path))
        tex = tmp_path.joinpath("manuscript.tex").read_text(encoding="utf-8")
        assert "figure" in tex.lower()
        assert "fig:test" in tex
        assert tmp_path.joinpath("fig_0.png").exists()

    def test_export_with_tables(self, tmp_path):
        from app.models import BlockType
        from app.pipeline.export.latex_exporter import LaTeXExporter
        tbl = MagicMock()
        tbl.index = 0
        tbl.caption_text = "Test Table"
        tbl.rows = [["Name", "Value"], ["A", "1"]]
        doc = self._make_doc(tables=[tbl])
        exporter = LaTeXExporter()
        exporter.export_from_document(doc, str(tmp_path))
        tex = tmp_path.joinpath("manuscript.tex").read_text(encoding="utf-8")
        assert "tabular" in tex
        assert "Test Table" in tex

    def test_export_with_equations(self, tmp_path):
        from app.models import BlockType
        from app.pipeline.export.latex_exporter import LaTeXExporter
        eq = MagicMock()
        eq.index = 0
        eq.text = "x = y"
        eq.mathml = None
        eq.omml = None
        doc = self._make_doc(equations=[eq])
        exporter = LaTeXExporter()
        exporter.export_from_document(doc, str(tmp_path))
        tex = tmp_path.joinpath("manuscript.tex").read_text(encoding="utf-8")
        assert "equation" in tex

    def test_export_with_references(self, tmp_path):
        from app.models import BlockType
        from app.pipeline.export.latex_exporter import LaTeXExporter
        ref = MagicMock()
        ref.formatted_text = "A reference"
        ref.raw_text = "Raw ref"
        ref.metadata = {"title": "Paper Title", "authors": "Alice", "year": "2024", "journal": "Test Journal", "doi": "10.1234/test"}
        doc = self._make_doc(references=[ref])
        exporter = LaTeXExporter()
        exporter.export_from_document(doc, str(tmp_path))
        bib = tmp_path.joinpath("manuscript.bib")
        assert bib.exists()
        bib_text = bib.read_text(encoding="utf-8")
        assert "@article" in bib_text
        assert "Paper Title" in bib_text

    def test_export_no_title(self, tmp_path):
        from app.models import BlockType
        from app.pipeline.export.latex_exporter import LaTeXExporter
        doc = self._make_doc()
        doc.metadata.title = None
        exporter = LaTeXExporter()
        exporter.export_from_document(doc, str(tmp_path))
        tex = tmp_path.joinpath("manuscript.tex").read_text(encoding="utf-8")
        assert "Untitled" in tex
