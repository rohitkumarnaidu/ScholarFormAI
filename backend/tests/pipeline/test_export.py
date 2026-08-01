# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import pytest
import os
import json
from unittest.mock import MagicMock, patch
from app.pipeline.export.exporter import Exporter
from app.pipeline.export.jats_generator import JATSGenerator
from app.pipeline.export.latex_exporter import LaTeXExporter
from app.pipeline.export.pdf_exporter import PDFExporter


class TestExporter:
    def _make_doc(self, **kw):
        doc = MagicMock()
        doc.document_id = kw.get("document_id", "doc1")
        doc.original_filename = kw.get("original_filename", "test.docx")
        doc.source_path = kw.get("source_path", "/tmp/test.docx")
        doc.output_path = kw.get("output_path", "/tmp/output.docx")
        doc.template = kw.get("template", MagicMock(template_name="ieee"))
        meta = MagicMock()
        meta.title = kw.get("title", "Test")
        meta.authors = kw.get("authors", [])
        meta.affiliations = kw.get("affiliations", [])
        meta.doi = kw.get("doi", None)
        meta.abstract = kw.get("abstract", None)
        meta.keywords = kw.get("keywords", [])
        meta.publication_date = kw.get("publication_date", None)
        meta.volume = kw.get("volume", None)
        meta.issue = kw.get("issue", None)
        doc.metadata = meta
        doc.is_valid = kw.get("is_valid", True)
        doc.validation_errors = kw.get("validation_errors", [])
        doc.validation_warnings = kw.get("validation_warnings", [])
        doc.blocks = kw.get("blocks", [])
        doc.references = kw.get("references", [])
        doc.figures = kw.get("figures", [])
        doc.tables = kw.get("tables", [])
        doc.equations = kw.get("equations", [])
        doc.processing_history = kw.get("processing_history", [])
        doc.get_stats.return_value = kw.get("stats", {})
        doc.formatting_options = kw.get("formatting_options", {})
        return doc

    def test_init(self):
        e = Exporter()
        assert e.pdf_exporter is not None
        assert e.latex_exporter is not None

    def test_get_export_formats_default(self):
        doc = self._make_doc()
        doc.formatting_options = {}
        assert Exporter()._get_export_formats(doc) == ["docx", "json", "markdown"]

    def test_get_export_formats_custom(self):
        doc = self._make_doc()
        doc.formatting_options = {"export_formats": ["pdf", "html"]}
        result = Exporter()._get_export_formats(doc)
        assert "docx" in result
        assert "pdf" in result
        assert "html" in result

    def test_get_export_formats_ensures_docx(self):
        doc = self._make_doc()
        doc.formatting_options = {"export_formats": ["pdf"]}
        result = Exporter()._get_export_formats(doc)
        assert result[0] == "docx"

    def test_get_export_formats_normalizes(self):
        doc = self._make_doc()
        doc.formatting_options = {"export_formats": "PDF"}
        result = Exporter()._get_export_formats(doc)
        assert "pdf" in result

    def test_build_export_payload(self):
        with patch("app.pipeline.export.exporter.safe_model_dump", return_value={"title": "T"}):
            payload = Exporter()._build_export_payload(self._make_doc())
            assert payload["document_id"] == "doc1"
            assert payload["template"] == "ieee"
            assert "exported_at" in payload

    def test_build_export_payload_no_template(self):
        with patch("app.pipeline.export.exporter.safe_model_dump", return_value={}):
            payload = Exporter()._build_export_payload(self._make_doc(template=None))
            assert payload["template"] is None

    def test_build_markdown_with_all_metadata(self):
        block = MagicMock(index=0, block_type="body", text="Hello world")
        doc = self._make_doc(
            title="Test Title", authors=["John Doe", "Jane Smith"],
            affiliations=["MIT"], doi="10.1234/test",
            abstract="An abstract.", keywords=["kw1", "kw2"],
            blocks=[block],
        )
        md = Exporter()._build_markdown(doc)
        assert "# Test Title" in md
        assert "John Doe, Jane Smith" in md
        assert "An abstract." in md
        assert "Hello world" in md

    def test_build_markdown_skips_references_and_headings(self):
        h = MagicMock(index=0, block_type="heading_1", text="Intro")
        b = MagicMock(index=1, block_type="body", text="Some text")
        rh = MagicMock(index=2, block_type="references_heading", text="Refs")
        doc = self._make_doc(title=None, authors=[], blocks=[h, b, rh])
        md = Exporter()._build_markdown(doc)
        assert "## Intro" in md
        assert "Some text" in md
        assert "Refs" not in md

    def test_build_markdown_with_references(self):
        ref = MagicMock(index=0, formatted_text="[1] Smith et al.", raw_text=None)
        doc = self._make_doc(title=None, authors=[], blocks=[], references=[ref])
        md = Exporter()._build_markdown(doc)
        assert "## References" in md
        assert "[1] Smith et al." in md

    def test_export_word_doc_none(self):
        assert Exporter().export(None, "/path/out.docx") is None

    def test_export_word_doc_saves(self, tmp_path):
        wd = MagicMock()
        out = str(tmp_path / "out.docx")
        assert Exporter().export(wd, out) == out
        wd.save.assert_called_once_with(out)

    def test_export_json_success(self, tmp_path):
        with patch("app.pipeline.export.exporter.safe_model_dump", return_value={"title": "T"}):
            doc = self._make_doc()
            out = str(tmp_path / "out.json")
            result = Exporter().export_json(doc, out)
            assert result == out
            data = json.load(open(out, encoding="utf-8"))
            assert data["document_id"] == "doc1"

    def test_export_json_failure(self, tmp_path):
        doc = self._make_doc()
        doc.get_stats.side_effect = Exception("err")
        with patch("app.pipeline.export.exporter.safe_model_dump", return_value={}):
            assert Exporter().export_json(doc, str(tmp_path / "f.json")) is None

    def test_export_markdown_success(self, tmp_path):
        doc = self._make_doc(title=None, authors=[])
        out = str(tmp_path / "out.md")
        assert Exporter().export_markdown(doc, out) == out

    def test_export_markdown_failure(self, tmp_path):
        doc = self._make_doc(title=None, authors=[])
        with patch.object(Exporter, "_build_markdown", side_effect=Exception("fail")):
            assert Exporter().export_markdown(doc, str(tmp_path / "x.md")) is None

    def test_export_jats_success(self, tmp_path):
        with patch("app.pipeline.export.exporter.JATSGenerator") as m:
            m.return_value.to_xml.return_value = "<a/>"
            out = str(tmp_path / "out.xml")
            assert Exporter().export_jats(MagicMock(), out) == out

    def test_export_jats_failure(self, tmp_path):
        with patch("app.pipeline.export.exporter.JATSGenerator") as m:
            m.return_value.to_xml.side_effect = Exception("x")
            assert Exporter().export_jats(MagicMock(), str(tmp_path / "x.xml")) is None

    def test_export_html_with_title(self, tmp_path):
        block = MagicMock(index=0, block_type="body", text="<hello>")
        doc = self._make_doc(title="My Doc", authors=[], blocks=[block], references=[])
        out = str(tmp_path / "out.html")
        result = Exporter().export_html(doc, out)
        with open(out) as f:
            c = f.read()
            assert "<title>My Doc</title>" in c
            assert "&lt;hello&gt;" in c
        assert result == out

    def test_export_html_no_title(self, tmp_path):
        doc = self._make_doc(title=None, authors=[], blocks=[])
        assert Exporter().export_html(doc, str(tmp_path / "out.html")) is not None

    def test_export_html_ordered_list(self, tmp_path):
        block = MagicMock(index=0, block_type="body", text="1. First")
        doc = self._make_doc(title=None, authors=[], blocks=[block])
        out = str(tmp_path / "out.html")
        Exporter().export_html(doc, out)
        with open(out) as f:
            assert "<ol>" in f.read()

    def test_export_html_exception(self, tmp_path):
        doc = self._make_doc()
        with patch.object(Exporter, "_build_markdown", side_effect=Exception("x")):
            assert Exporter().export_html(doc, str(tmp_path / "x.html")) is None

    @patch("app.pipeline.export.exporter.LaTeXExporter")
    def test_export_latex_no_output_path(self, m):
        doc = self._make_doc()
        doc.output_path = None
        assert Exporter().export_latex(doc, "/tmp/out.tex") is None

    @patch("app.pipeline.export.exporter.LaTeXExporter")
    def test_export_latex_success(self, m):
        m.return_value.convert_to_latex.return_value = "/tmp/out.tex"
        doc = self._make_doc(output_path="/tmp/in.docx")
        with patch("os.replace"):
            assert Exporter().export_latex(doc, "/tmp/out.tex") == "/tmp/out.tex"

    @patch("app.pipeline.export.exporter.LaTeXExporter")
    def test_export_latex_exception(self, m):
        m.return_value.convert_to_latex.side_effect = Exception("x")
        doc = self._make_doc(output_path="/tmp/in.docx")
        assert Exporter().export_latex(doc, "/tmp/out.tex") is None

    def test_process_no_output_path(self):
        doc = self._make_doc()
        doc.output_path = None
        result = Exporter().process(doc)
        assert result is doc

    def test_process_calls_export(self):
        e = Exporter()
        doc = self._make_doc(formatting_options={"export_formats": ["docx"]})
        doc.generated_doc = MagicMock()
        with patch.object(e, "export") as me:
            e.process(doc)
            me.assert_called_once_with(doc.generated_doc, doc.output_path)


class TestLaTeXExporter:
    def test_init(self):
        assert LaTeXExporter(60).timeout == 60

    def test_init_default(self):
        assert LaTeXExporter().timeout == 120

    def test_resolve_pandoc_configured(self):
        import app.pipeline.export.latex_exporter as le
        with patch.dict(os.environ, {"PANDOC_PATH": "/custom/pandoc"}, clear=True):
            assert le._resolve_pandoc_binary() == "/custom/pandoc"

    def test_resolve_pandoc_blank(self):
        import app.pipeline.export.latex_exporter as le
        with patch.dict(os.environ, {"PANDOC_PATH": ""}, clear=True):
            with patch("app.pipeline.export.latex_exporter.shutil.which", return_value=None):
                assert le._resolve_pandoc_binary() is None

    def test_resolve_pandoc_via_shutil(self):
        import app.pipeline.export.latex_exporter as le
        with patch.dict(os.environ, {"PANDOC_PATH": ""}, clear=True):
            with patch("app.pipeline.export.latex_exporter.shutil.which", return_value="/usr/bin/pandoc"):
                assert le._resolve_pandoc_binary() == "/usr/bin/pandoc"

    def test_convert_source_not_found(self, tmp_path):
        with pytest.raises(RuntimeError, match="DOCX not found"):
            LaTeXExporter().convert_to_latex("/nonexistent", str(tmp_path))

    def test_convert_pandoc_not_found(self, tmp_path):
        f = tmp_path / "in.docx"; f.write_text("d")
        with patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value=None):
            with pytest.raises(RuntimeError, match="Pandoc is not installed"):
                LaTeXExporter().convert_to_latex(str(f), str(tmp_path))

    def test_convert_timeout(self, tmp_path):
        f = tmp_path / "in.docx"; f.write_text("d")
        with patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/pandoc"):
            with patch("app.pipeline.export.latex_exporter._convert_via_pandoc", return_value=False):
                with pytest.raises(RuntimeError, match="Pandoc conversion failed"):
                    LaTeXExporter(5).convert_to_latex(str(f), str(tmp_path))

    def test_convert_oserror(self, tmp_path):
        f = tmp_path / "in.docx"; f.write_text("d")
        with patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/pandoc"):
            with patch("app.pipeline.export.latex_exporter._convert_via_pandoc", return_value=False):
                with pytest.raises(RuntimeError, match="Pandoc conversion failed"):
                    LaTeXExporter().convert_to_latex(str(f), str(tmp_path))

    def test_convert_nonzero_return(self, tmp_path):
        f = tmp_path / "in.docx"; f.write_text("d")
        with patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/pandoc"):
            with patch("app.pipeline.export.latex_exporter._convert_via_pandoc", return_value=False):
                with pytest.raises(RuntimeError, match="Pandoc conversion failed"):
                    LaTeXExporter().convert_to_latex(str(f), str(tmp_path))

    def test_convert_output_not_created(self, tmp_path):
        f = tmp_path / "in.docx"; f.write_text("d")
        with patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/pandoc"):
            with patch("app.pipeline.export.latex_exporter._convert_via_pandoc", return_value=False):
                with pytest.raises(RuntimeError, match="Pandoc conversion failed"):
                    LaTeXExporter().convert_to_latex(str(f), str(tmp_path))

    def test_convert_success(self, tmp_path):
        f = tmp_path / "in.docx"; f.write_text("d")
        with patch("app.pipeline.export.latex_exporter._resolve_pandoc_binary", return_value="/pandoc"):
            with patch("app.pipeline.export.latex_exporter._convert_via_pandoc", return_value=True):
                result = LaTeXExporter().convert_to_latex(str(f), str(tmp_path))
                assert result.endswith("in.tex")


class TestPDFExporter:
    def test_init_with_path(self):
        assert PDFExporter(libreoffice_path="/opt/lo/soffice").libreoffice_path == "/opt/lo/soffice"

    def test_find_libreoffice_windows_found(self):
        with patch("app.pipeline.export.pdf_exporter.settings.LIBREOFFICE_PATH", None):
            with patch("app.pipeline.export.pdf_exporter.platform.system", return_value="Windows"):
                with patch("os.path.exists", return_value=True):
                    p = PDFExporter(libreoffice_path=None)
                    assert "LibreOffice" in p.libreoffice_path

    def test_find_libreoffice_windows_not_found(self):
        with patch("app.pipeline.export.pdf_exporter.settings.LIBREOFFICE_PATH", None):
            with patch("app.pipeline.export.pdf_exporter.platform.system", return_value="Windows"):
                with patch("os.path.exists", return_value=False):
                    assert PDFExporter(libreoffice_path=None).libreoffice_path is None

    def test_find_libreoffice_macos(self):
        with patch("app.pipeline.export.pdf_exporter.settings.LIBREOFFICE_PATH", None):
            with patch("app.pipeline.export.pdf_exporter.platform.system", return_value="Darwin"):
                assert "MacOS" in PDFExporter(libreoffice_path=None).libreoffice_path

    def test_find_libreoffice_linux(self):
        with patch("app.pipeline.export.pdf_exporter.settings.LIBREOFFICE_PATH", None):
            with patch("app.pipeline.export.pdf_exporter.platform.system", return_value="Linux"):
                assert PDFExporter(libreoffice_path=None).libreoffice_path == "libreoffice"

    def test_convert_source_not_exists(self):
        assert PDFExporter(libreoffice_path=None).convert_to_pdf("/nonexistent", "/tmp") is None

    def test_convert_libreoffice_success(self, tmp_path):
        f = tmp_path / "in.docx"; f.write_text("d")
        (tmp_path / "in.pdf").write_text("pdf")
        r = MagicMock(returncode=0, stderr="", stdout="")
        with patch("app.pipeline.export.pdf_exporter.subprocess.run", return_value=r):
            assert PDFExporter("/soffice").convert_to_pdf(str(f), str(tmp_path)) == str(tmp_path / "in.pdf")

    def test_convert_libreoffice_fails_weasyprint_works(self, tmp_path):
        f = tmp_path / "in.docx"; f.write_text("d")
        pdf = str(tmp_path / "in.pdf")
        r = MagicMock(returncode=1, stderr="e", stdout="")
        with patch("app.pipeline.export.pdf_exporter.subprocess.run", return_value=r):
            with patch.object(PDFExporter, "_weasyprint_fallback", return_value=pdf):
                assert PDFExporter("/soffice").convert_to_pdf(str(f), str(tmp_path)) == pdf

    def test_convert_all_fail(self, tmp_path):
        f = tmp_path / "in.docx"; f.write_text("d")
        r = MagicMock(returncode=1, stderr="e", stdout="")
        with patch("app.pipeline.export.pdf_exporter.subprocess.run", return_value=r):
            with patch.object(PDFExporter, "_weasyprint_fallback", return_value=None):
                with pytest.raises(RuntimeError, match="engines failed"):
                    PDFExporter("/soffice").convert_to_pdf(str(f), str(tmp_path))

    def test_weasyprint_unavailable(self, tmp_path):
        assert PDFExporter()._weasyprint_fallback("/in.docx", str(tmp_path / "o.pdf")) is None

    def test_weasyprint_success(self, tmp_path):
        import types
        wp_mod = types.ModuleType("weasyprint")
        wp_mod.HTML = MagicMock()
        docx_mod = types.ModuleType("docx")
        docx_mod.Document = MagicMock()
        docx_mod.Document.return_value.paragraphs = []
        pdf = tmp_path / "o.pdf"; pdf.write_text("pdf")
        with patch.dict("sys.modules", {"weasyprint": wp_mod, "docx": docx_mod}):
            r = PDFExporter()._weasyprint_fallback("/in.docx", str(pdf))
            assert r == str(pdf)

    def test_weasyprint_exception(self, tmp_path):
        import types
        wp_mod = types.ModuleType("weasyprint")
        wp_mod.HTML = MagicMock()
        docx_mod = types.ModuleType("docx")
        docx_mod.Document = MagicMock(side_effect=Exception("x"))
        with patch.dict("sys.modules", {"weasyprint": wp_mod, "docx": docx_mod}):
            assert PDFExporter()._weasyprint_fallback("/in.docx", str(tmp_path / "o.pdf")) is None

    def test_libreoffice_not_found_fallback(self, tmp_path):
        f = tmp_path / "in.docx"; f.write_text("d")
        pdf = str(tmp_path / "in.pdf")
        with patch.object(PDFExporter, "_weasyprint_fallback", return_value=pdf):
            assert PDFExporter(libreoffice_path=None).convert_to_pdf(str(f), str(tmp_path)) == pdf

    def test_docx2pdf_fallback(self, tmp_path):
        f = tmp_path / "in.docx"; f.write_text("d")
        r = MagicMock(returncode=1, stderr="e", stdout="")
        with patch("app.pipeline.export.pdf_exporter.subprocess.run", return_value=r):
            with patch.object(PDFExporter, "_weasyprint_fallback", return_value=None):
                with patch("docx2pdf.convert") as mc:
                    mc.return_value = None
                    with pytest.raises(RuntimeError, match="PDF export engines failed"):
                        PDFExporter("/soffice").convert_to_pdf(str(f), str(tmp_path))


class TestJATSGenerator:
    def _doc(self, **kw):
        doc = MagicMock()
        doc.metadata.title = kw.get("title", "Test Article")
        doc.metadata.authors = kw.get("authors", ["John Doe"])
        doc.metadata.publication_date = kw.get("publication_date")
        doc.metadata.volume = kw.get("volume")
        doc.metadata.issue = kw.get("issue")
        doc.metadata.abstract = kw.get("abstract")
        doc.blocks = kw.get("blocks", [])
        doc.references = kw.get("references", [])
        doc.equations = kw.get("equations", [])
        return doc

    def test_to_xml_with_all_metadata(self):
        xml = JATSGenerator().to_xml(self._doc(publication_date="2024-01-15", volume="10", issue="2", abstract="Abs."))
        assert "<article-title>Test Article</article-title>" in xml
        assert "<surname>Doe</surname>" in xml
        assert "<given-names>John</given-names>" in xml
        assert "<year>2024</year>" in xml
        assert "<volume>10</volume>" in xml
        assert "<issue>2</issue>" in xml
        assert "<abstract>" in xml

    def test_no_authors_adds_placeholder(self):
        xml = JATSGenerator().to_xml(self._doc(authors=[]))
        assert "<surname>Author</surname>" in xml
        assert "<given-names>Unknown</given-names>" in xml

    def test_publication_date_datetime(self):
        from datetime import datetime
        xml = JATSGenerator().to_xml(self._doc(publication_date=datetime(2024, 6, 15)))
        assert "<year>2024</year>" in xml
        assert "<month>06</month>" in xml
        assert "<day>15</day>" in xml

    def test_with_blocks(self):
        h = MagicMock(metadata={"semantic_intent": "heading"}, text="Intro")
        b = MagicMock(metadata={"semantic_intent": "body"}, text="Content.")
        xml = JATSGenerator().to_xml(self._doc(blocks=[h, b]))
        assert "<sec>" in xml
        assert "<title>Intro</title>" in xml
        assert "<p>Content.</p>" in xml

    def test_with_block_equation(self):
        eq = MagicMock(mathml="<math><mi>E</mi></math>", equation_id="eq1", is_block=True)
        xml = JATSGenerator().to_xml(self._doc(equations=[eq]))
        assert "disp-formula" in xml
        assert "eq1" in xml

    def test_with_inline_equation(self):
        eq = MagicMock(mathml="<math><mi>E</mi></math>", equation_id="eq2", is_block=False)
        xml = JATSGenerator().to_xml(self._doc(equations=[eq]))
        assert "inline-formula" in xml

    def test_with_references(self):
        ref = MagicMock(reference_id="r1", raw_text="Smith.", metadata={"doi": "10.1234/abc"})
        xml = JATSGenerator().to_xml(self._doc(references=[ref]))
        assert "<ref-list>" in xml
        assert "r1" in xml
        assert "10.1234/abc" in xml

    def test_no_references_skips_ref_list(self):
        xml = JATSGenerator().to_xml(self._doc(references=[]))
        assert "<ref-list>" not in xml

    def test_reference_no_id(self):
        ref = MagicMock(reference_id=None, raw_text="R", metadata=None)
        xml = JATSGenerator().to_xml(self._doc(references=[ref]))
        assert "ref_1" in xml

    def test_missing_abstract(self):
        xml = JATSGenerator().to_xml(self._doc(abstract=None))
        assert "<abstract>" not in xml
