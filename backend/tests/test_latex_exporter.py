from unittest.mock import MagicMock, patch


class TestEscapeLatex:
    def test_no_special_chars(self):
        from app.pipeline.export.latex_exporter import escape_latex

        assert escape_latex("Hello World") == "Hello World"

    def test_ampersand(self):
        from app.pipeline.export.latex_exporter import escape_latex

        assert escape_latex("A & B") == "A \\& B"

    def test_percent(self):
        from app.pipeline.export.latex_exporter import escape_latex

        assert escape_latex("100%") == "100\\%"

    def test_dollar(self):
        from app.pipeline.export.latex_exporter import escape_latex

        assert escape_latex("$10") == "\\$10"

    def test_underscore(self):
        from app.pipeline.export.latex_exporter import escape_latex

        assert escape_latex("test_method") == "test\\_method"

    def test_backslash(self):
        from app.pipeline.export.latex_exporter import escape_latex

        assert "textbackslash" in escape_latex("a\\b")

    def test_multiple_chars(self):
        from app.pipeline.export.latex_exporter import escape_latex

        assert escape_latex("&%$#_{}") != "&%$#_{}"


class TestResolvePandocBinary:
    def test_from_env(self):
        from app.pipeline.export.latex_exporter import _resolve_pandoc_binary

        with patch.dict("os.environ", {"PANDOC_PATH": "/custom/pandoc"}, clear=False):
            result = _resolve_pandoc_binary()
        assert result == "/custom/pandoc"

    def test_from_shutil(self):
        from app.pipeline.export.latex_exporter import _resolve_pandoc_binary

        with patch("shutil.which", return_value="/usr/bin/pandoc"):
            result = _resolve_pandoc_binary()
        assert result is not None

    def test_not_found(self):
        from app.pipeline.export.latex_exporter import _resolve_pandoc_binary

        with patch.dict("os.environ", {}, clear=True), patch("shutil.which", return_value=None):
            result = _resolve_pandoc_binary()
        assert result is None


class TestWriteBibtex:
    def test_writes_article_entries(self, tmp_path):
        from app.pipeline.export.latex_exporter import LaTeXExporter

        exporter = LaTeXExporter()
        doc = MagicMock()
        ref = MagicMock()
        ref.formatted_text = "Smith, J. (2020). A paper."
        ref.raw_text = None
        ref.metadata = {
            "authors": "Smith, J.",
            "title": "A paper",
            "year": "2020",
            "journal": "Journal X",
            "doi": "10.1234/abc",
        }
        doc.references = [ref]
        bib_path = tmp_path / "manuscript.bib"
        exporter._write_bibtex(doc, bib_path)
        content = bib_path.read_text(encoding="utf-8")
        assert "@article{ref_1" in content
        assert "Smith, J." in content
        assert "Journal X" in content

    def test_writes_misc_entry_when_no_title(self, tmp_path):
        from app.pipeline.export.latex_exporter import LaTeXExporter

        exporter = LaTeXExporter()
        doc = MagicMock()
        ref = MagicMock()
        ref.formatted_text = "Some raw reference text"
        ref.raw_text = None
        ref.metadata = {}
        doc.references = [ref]
        bib_path = tmp_path / "manuscript.bib"
        exporter._write_bibtex(doc, bib_path)
        content = bib_path.read_text(encoding="utf-8")
        assert "@misc{ref_1" in content

    def test_no_references(self, tmp_path):
        from app.pipeline.export.latex_exporter import LaTeXExporter

        exporter = LaTeXExporter()
        doc = MagicMock()
        doc.references = []
        bib_path = tmp_path / "manuscript.bib"
        exporter._write_bibtex(doc, bib_path)
        assert not bib_path.exists()


class TestWriteTitleAuthors:
    def test_with_authors(self):
        from app.pipeline.export.latex_exporter import LaTeXExporter

        exporter = LaTeXExporter()
        doc = MagicMock()
        doc.metadata.title = "Test Paper"
        doc.metadata.authors = ["Alice Smith", "Bob Jones"]
        doc.metadata.publication_date = None
        lines = []
        exporter._write_title_authors(lines, doc)
        text = "\n".join(lines)
        assert "\\title{Test Paper}" in text
        assert "Alice Smith" in text
        assert "\\date" in text
        assert "\\maketitle" in text

    def test_with_publication_date(self):
        from app.pipeline.export.latex_exporter import LaTeXExporter

        exporter = LaTeXExporter()
        doc = MagicMock()
        doc.metadata.title = "Paper"
        doc.metadata.authors = ["Alice"]
        doc.metadata.publication_date = "2024-06-15"
        lines = []
        exporter._write_title_authors(lines, doc)
        text = "\n".join(lines)
        assert "2024" in text


class TestWriteAbstract:
    def test_with_abstract_and_keywords(self):
        from app.pipeline.export.latex_exporter import LaTeXExporter

        exporter = LaTeXExporter()
        doc = MagicMock()
        doc.metadata.abstract = "This is an abstract."
        doc.metadata.keywords = ["ML", "AI"]
        lines = []
        exporter._write_abstract(lines, doc)
        text = "\n".join(lines)
        assert "abstract" in text.lower()
        assert "ML" in text or "AI" in text


class TestWriteSections:
    def test_headings(self):
        from app.models.block import Block, BlockType
        from app.pipeline.export.latex_exporter import LaTeXExporter

        exporter = LaTeXExporter()
        doc = MagicMock()
        doc.blocks = [
            Block(block_id="b1", text="Introduction", block_type=BlockType.HEADING_1, index=0),
            Block(block_id="b2", text="Background", block_type=BlockType.HEADING_2, index=1),
            Block(block_id="b3", text="Detailed", block_type=BlockType.HEADING_3, index=2),
        ]
        lines = []
        exporter._write_sections(lines, doc)
        text = "\n".join(lines)
        assert "\\section{Introduction}" in text
        assert "\\subsection{Background}" in text
        assert "\\subsubsection{Detailed}" in text

    def test_skips_references_and_figures(self):
        from app.models.block import Block, BlockType
        from app.pipeline.export.latex_exporter import LaTeXExporter

        exporter = LaTeXExporter()
        doc = MagicMock()
        doc.blocks = [
            Block(block_id="b1", text="[1] Ref", block_type=BlockType.REFERENCE_ENTRY, index=0),
        ]
        lines = []
        exporter._write_sections(lines, doc)
        assert "[1] Ref" not in "\n".join(lines)


class TestWriteEquations:
    def test_equation_block(self):
        from app.pipeline.export.latex_exporter import LaTeXExporter

        exporter = LaTeXExporter()
        doc = MagicMock()
        eq = MagicMock()
        eq.text = "x = y"
        eq.mathml = None
        eq.omml = None
        eq.index = 0
        doc.equations = [eq]
        lines = []
        exporter._write_equations(lines, doc)
        text = "\n".join(lines)
        assert "\\begin{equation}" in text
        assert "x = y" in text

    def test_equation_passthrough(self):
        from app.pipeline.export.latex_exporter import LaTeXExporter

        exporter = LaTeXExporter()
        doc = MagicMock()
        eq = MagicMock()
        eq.text = "\\begin{equation}E=mc^2\\end{equation}"
        eq.mathml = None
        eq.omml = None
        eq.index = 0
        doc.equations = [eq]
        lines = []
        exporter._write_equations(lines, doc)
        assert "\\begin{equation}" in "\n".join(lines)


class TestJournalTemplates:
    def test_all_templates_have_required_keys(self):
        from app.pipeline.export.latex_exporter import JOURNAL_TEMPLATES

        for name, tpl in JOURNAL_TEMPLATES.items():
            assert "documentclass" in tpl, f"{name} missing documentclass"
            assert "packages" in tpl, f"{name} missing packages"
            assert "bibliographystyle" in tpl, f"{name} missing bibliographystyle"

    def test_default_exists(self):
        from app.pipeline.export.latex_exporter import JOURNAL_TEMPLATES

        assert "default" in JOURNAL_TEMPLATES


class TestExportFromDocument:
    def test_basic_export(self, tmp_path):
        from app.pipeline.export.latex_exporter import LaTeXExporter

        exporter = LaTeXExporter()
        doc = MagicMock()
        doc.metadata.title = "Test"
        doc.metadata.authors = ["Alice"]
        doc.metadata.abstract = None
        doc.metadata.keywords = []
        doc.metadata.publication_date = None
        doc.blocks = (lambda: [])()

        mock_block = MagicMock()
        mock_block.text = "Introduction"
        mock_block.block_type = "heading_1"
        mock_block.index = 0
        doc.blocks = [mock_block]

        doc.figures = (lambda: [])()
        doc.tables = (lambda: [])()
        doc.equations = (lambda: [])()
        doc.references = (lambda: [])()
        doc.template = MagicMock()
        doc.template.template_name = "ieee"

        exporter.export_from_document(doc, str(tmp_path))
        tex_path = tmp_path / "manuscript.tex"
        assert tex_path.exists()
        content = tex_path.read_text(encoding="utf-8")
        assert "\\documentclass" in content
        assert "\\begin{document}" in content
        assert "\\end{document}" in content
