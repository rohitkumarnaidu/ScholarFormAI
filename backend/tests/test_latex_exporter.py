# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from app.pipeline.export.latex_exporter import LaTeXExporter, escape_latex, JOURNAL_TEMPLATES
from app.models.pipeline_document import PipelineDocument, DocumentMetadata, TemplateInfo


def test_escape_latex():
    assert escape_latex("A&B") == r"A\&B"
    assert escape_latex("100%") == r"100\%"
    assert escape_latex("$_") == r"\$\_"
    assert escape_latex("plain text") == "plain text"
    assert escape_latex("{braces}") == r"\{braces\}"


def test_convert_to_latex_requires_pandoc(tmp_path: Path):
    docx_path = tmp_path / "input.docx"
    docx_path.write_bytes(b"PK\x03\x04")
    exporter = LaTeXExporter()

    with patch("app.pipeline.export.latex_exporter.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="Pandoc is not installed"):
            exporter.convert_to_latex(str(docx_path), str(tmp_path))


def test_convert_to_latex_invokes_pandoc_and_returns_output(tmp_path: Path):
    docx_path = tmp_path / "paper.docx"
    docx_path.write_bytes(b"PK\x03\x04")
    output_dir = tmp_path / "out"
    output_path = output_dir / "paper.tex"
    exporter = LaTeXExporter(timeout_seconds=10)

    def _fake_run(*args, **kwargs):
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\\section{Intro}", encoding="utf-8")
        return subprocess.CompletedProcess(args=kwargs.get("args", []), returncode=0)

    with (
        patch("app.pipeline.export.latex_exporter.shutil.which", return_value="pandoc"),
        patch("app.pipeline.export.latex_exporter.subprocess.run", side_effect=_fake_run) as run_mock,
    ):
        result = exporter.convert_to_latex(str(docx_path), str(output_dir))

    assert result == str(output_path)
    assert output_path.exists()
    called_command = run_mock.call_args.args[0]
    assert "--to=latex" in called_command
    assert "--standalone" in called_command


def test_convert_to_latex_surfaces_pandoc_failure(tmp_path: Path):
    docx_path = tmp_path / "paper.docx"
    docx_path.write_bytes(b"PK\x03\x04")
    exporter = LaTeXExporter()

    with (
        patch("app.pipeline.export.latex_exporter.shutil.which", return_value="pandoc"),
        patch(
            "app.pipeline.export.latex_exporter.subprocess.run",
            return_value=subprocess.CompletedProcess(args=["pandoc"], returncode=2, stderr="bad input"),
        ),
    ):
        with pytest.raises(RuntimeError, match="Pandoc conversion failed"):
            exporter.convert_to_latex(str(docx_path), str(tmp_path / "out"))


def test_convert_to_latex_missing_source(tmp_path: Path):
    exporter = LaTeXExporter()
    with pytest.raises(RuntimeError, match="DOCX not found"):
        exporter.convert_to_latex(str(tmp_path / "nonexistent.docx"), str(tmp_path))


def test_export_from_document_default_template(tmp_path: Path):
    doc = PipelineDocument(
        document_id="doc-1",
        metadata=DocumentMetadata(title="Test Paper", authors=["Alice"], abstract="An abstract."),
        blocks=[],
    )
    exporter = LaTeXExporter()
    result = exporter.export_from_document(doc, str(tmp_path))
    tex_path = Path(result)
    assert tex_path.exists()
    content = tex_path.read_text(encoding="utf-8")
    assert r"\documentclass" in content
    assert r"\title{Test Paper}" in content
    assert r"\author{Alice}" in content
    assert r"\begin{abstract}" in content
    assert r"An abstract." in content
    assert r"\end{abstract}" in content
    assert r"\end{document}" in content


def test_export_from_document_with_template(tmp_path: Path):
    doc = PipelineDocument(
        document_id="doc-2",
        metadata=DocumentMetadata(title="IEEE Paper", authors=["Bob"]),
        template=TemplateInfo(template_name="ieee"),
        blocks=[],
    )
    exporter = LaTeXExporter()
    result = exporter.export_from_document(doc, str(tmp_path))
    content = Path(result).read_text(encoding="utf-8")
    assert r"\documentclass[conference]{IEEEtran}" in content
    assert r"\title{IEEE Paper}" in content


def test_export_from_document_with_sections(tmp_path: Path):
    from app.models.block import Block

    doc = PipelineDocument(
        document_id="doc-3",
        metadata=DocumentMetadata(title="Structured"),
        blocks=[
            Block(block_id="b1", block_type="heading_1", text="Introduction", index=0),
            Block(block_id="b2", block_type="paragraph", text="Some intro text.", index=1),
            Block(block_id="b3", block_type="heading_2", text="Methods", index=2),
            Block(block_id="b4", block_type="paragraph", text="Details here.", index=3),
        ],
    )
    exporter = LaTeXExporter()
    result = exporter.export_from_document(doc, str(tmp_path))
    content = Path(result).read_text(encoding="utf-8")
    assert r"\section{Introduction}" in content
    assert r"\subsection{Methods}" in content
    assert "Some intro text." in content
    assert "Details here." in content


def test_export_from_document_with_figures(tmp_path: Path):
    from app.models.figure import Figure, ImageFormat

    doc = PipelineDocument(
        document_id="doc-4",
        metadata=DocumentMetadata(title="With Figs"),
        figures=[
            Figure(figure_id="f1", index=0, caption_text="Test figure", image_data=b"PNG", image_format=ImageFormat.PNG),
        ],
    )
    exporter = LaTeXExporter()
    result = exporter.export_from_document(doc, str(tmp_path))
    content = Path(result).read_text(encoding="utf-8")
    assert r"\begin{figure}" in content
    assert r"\includegraphics" in content
    assert r"\caption{Test figure}" in content
    assert r"\end{figure}" in content


def test_export_from_document_with_tables(tmp_path: Path):
    from app.models.table import Table

    doc = PipelineDocument(
        document_id="doc-5",
        metadata=DocumentMetadata(title="With Tables"),
        tables=[
            Table(
                table_id="t1", index=0, num_rows=2, num_cols=2, block_index=0,
                caption_text="Results",
                rows=[["Name", "Value"], ["X", "42"]],
            ),
        ],
    )
    exporter = LaTeXExporter()
    result = exporter.export_from_document(doc, str(tmp_path))
    content = Path(result).read_text(encoding="utf-8")
    assert r"\begin{table}" in content
    assert r"\begin{tabular}" in content
    assert r"\caption{Results}" in content
    assert "Name & Value" in content
    assert "X & 42" in content
    assert r"\end{table}" in content


def test_export_from_document_with_equations(tmp_path: Path):
    from app.models.equation import Equation

    doc = PipelineDocument(
        document_id="doc-6",
        metadata=DocumentMetadata(title="With Eqs"),
        equations=[
            Equation(equation_id="e1", index=0, text=r"E = mc^2"),
        ],
    )
    exporter = LaTeXExporter()
    result = exporter.export_from_document(doc, str(tmp_path))
    content = Path(result).read_text(encoding="utf-8")
    assert r"\begin{equation}" in content
    assert r"E = mc^2" in content
    assert r"\end{equation}" in content


def test_export_from_document_with_bibliography(tmp_path: Path):
    from app.models.reference import Reference

    doc = PipelineDocument(
        document_id="doc-7",
        metadata=DocumentMetadata(title="With Refs"),
        references=[
            Reference(
                reference_id="r1", citation_key="smith2024", index=0,
                raw_text="Smith, J. (2024). A paper.",
                formatted_text="Smith, J. (2024). A paper.",
                metadata={"title": "A paper", "authors": "Smith, J.", "year": "2024"},
            ),
        ],
    )
    exporter = LaTeXExporter()
    result = exporter.export_from_document(doc, str(tmp_path))
    content = Path(result).read_text(encoding="utf-8")
    assert r"\printbibliography" in content or r"\bibliography{" in content
    bib_path = Path(tmp_path) / "manuscript.bib"
    assert bib_path.exists()
    bib_content = bib_path.read_text(encoding="utf-8")
    assert "@article" in bib_content
    assert "A paper" in bib_content


def test_export_from_document_keywords(tmp_path: Path):
    doc = PipelineDocument(
        document_id="doc-8",
        metadata=DocumentMetadata(
            title="Keywords Test",
            keywords=["machine learning", "NLP"],
        ),
        blocks=[],
    )
    exporter = LaTeXExporter()
    result = exporter.export_from_document(doc, str(tmp_path))
    content = Path(result).read_text(encoding="utf-8")
    assert r"\textbf{Keywords:}" in content
    assert "machine learning" in content


def test_export_from_document_empty_document(tmp_path: Path):
    doc = PipelineDocument(document_id="doc-9", metadata=DocumentMetadata())
    exporter = LaTeXExporter()
    result = exporter.export_from_document(doc, str(tmp_path))
    content = Path(result).read_text(encoding="utf-8")
    assert r"\title{Untitled}" in content
    assert r"\end{document}" in content


def test_journal_templates_have_default():
    assert "default" in JOURNAL_TEMPLATES
    assert "ieee" in JOURNAL_TEMPLATES
    assert "acm" in JOURNAL_TEMPLATES
    for key, tpl in JOURNAL_TEMPLATES.items():
        assert "documentclass" in tpl
        assert "packages" in tpl
