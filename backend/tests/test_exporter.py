import pytest
from unittest.mock import MagicMock, patch, mock_open, PropertyMock


@pytest.fixture
def mkblock():
    from app.models.block import Block, BlockType
    def _block(text="Test", btype=BlockType.BODY, idx=0):
        return Block(block_id=f"b{idx}", text=text, block_type=btype, index=idx)
    return _block


def _make_doc(mkblock):
    doc = MagicMock()
    doc.metadata.title = "Test Paper"
    doc.metadata.authors = ["Alice"]
    doc.metadata.affiliations = ["MIT"]
    doc.metadata.doi = "10.1234/test"
    doc.metadata.abstract = "This is an abstract."
    doc.metadata.keywords = ["ML", "AI"]
    doc.original_filename = "paper.docx"
    doc.source_path = "/tmp/paper.docx"
    doc.output_path = "/tmp/output/paper.docx"
    doc.document_id = "doc-123"
    doc.template.template_name = "ieee"
    doc.is_valid = True
    doc.validation_errors = []
    doc.validation_warnings = []
    doc.blocks = [mkblock("Introduction", idx=0), mkblock("Body text here", idx=1)]
    doc.references = []
    doc.figures = []
    doc.tables = []
    doc.equations = []
    doc.processing_history = []
    doc.formatting_options = {}
    doc.get_stats.return_value = {"block_count": 2}
    return doc


class TestGetExportFormats:
    def test_default_formats(self):
        from app.pipeline.export.exporter import Exporter
        exporter = Exporter()
        doc = MagicMock()
        doc.formatting_options = {}
        result = exporter._get_export_formats(doc)
        assert "docx" in result
        assert "json" in result
        assert "markdown" in result

    def test_docx_always_present(self):
        from app.pipeline.export.exporter import Exporter
        exporter = Exporter()
        doc = MagicMock()
        doc.formatting_options = {"export_formats": ["json"]}
        result = exporter._get_export_formats(doc)
        assert result[0] == "docx"

    def test_custom_formats(self):
        from app.pipeline.export.exporter import Exporter
        exporter = Exporter()
        doc = MagicMock()
        doc.formatting_options = {"export_formats": ["pdf", "html"]}
        result = exporter._get_export_formats(doc)
        assert "pdf" in result
        assert "html" in result

    def test_non_list_formats(self):
        from app.pipeline.export.exporter import Exporter
        exporter = Exporter()
        doc = MagicMock()
        doc.formatting_options = {"export_formats": "pdf"}
        result = exporter._get_export_formats(doc)
        assert "pdf" in result


class TestBuildExportPayload:
    def test_basic_payload(self, mkblock):
        from app.pipeline.export.exporter import Exporter
        with patch("app.pipeline.export.exporter.safe_model_dump",
                   side_effect=lambda x: {"title": "Test Paper"} if hasattr(x, "title") else {}):
            exporter = Exporter()
            doc = _make_doc(mkblock)
            payload = exporter._build_export_payload(doc)
        assert payload["document_id"] == "doc-123"
        assert payload["template"] == "ieee"
        assert payload["stats"]["block_count"] == 2

    def test_exported_at_exists(self, mkblock):
        from app.pipeline.export.exporter import Exporter
        with patch("app.pipeline.export.exporter.safe_model_dump",
                   side_effect=lambda x: {"title": "Test"} if hasattr(x, "title") else {}):
            exporter = Exporter()
            doc = _make_doc(mkblock)
            payload = exporter._build_export_payload(doc)
        assert "exported_at" in payload


class TestBuildMarkdown:
    def test_basic_markdown(self, mkblock):
        from app.pipeline.export.exporter import Exporter
        exporter = Exporter()
        doc = _make_doc(mkblock)
        md = exporter._build_markdown(doc)
        assert "# Test Paper" in md
        assert "Alice" in md
        assert "MIT" in md
        assert "Body text here" in md
        assert "Keywords:" in md

    def test_no_metadata_title(self, mkblock):
        from app.pipeline.export.exporter import Exporter
        exporter = Exporter()
        doc = _make_doc(mkblock)
        doc.metadata.title = None
        md = exporter._build_markdown(doc)
        assert "paper.docx" in md

    def test_skips_reference_blocks(self, mkblock):
        from app.pipeline.export.exporter import Exporter
        from app.models.block import BlockType
        exporter = Exporter()
        doc = _make_doc(mkblock)
        doc.blocks.append(mkblock("References", BlockType.REFERENCES_HEADING, idx=3))
        doc.blocks.append(mkblock("[1] Ref", BlockType.REFERENCE_ENTRY, idx=4))
        md = exporter._build_markdown(doc)
        assert "[1] Ref" not in md

    def test_heading_blocks(self, mkblock):
        from app.pipeline.export.exporter import Exporter
        from app.models.block import BlockType
        exporter = Exporter()
        doc = _make_doc(mkblock)
        doc.blocks = [
            mkblock("Introduction", BlockType.HEADING_1, idx=0),
            mkblock("Body text", BlockType.BODY, idx=1),
        ]
        md = exporter._build_markdown(doc)
        assert "## Introduction" in md

    def test_references_section(self, mkblock):
        from app.pipeline.export.exporter import Exporter
        exporter = Exporter()
        doc = _make_doc(mkblock)
        ref = MagicMock()
        ref.formatted_text = "Smith, J. (2020). A paper."
        ref.raw_text = None
        ref.index = 0
        doc.references = [ref]
        md = exporter._build_markdown(doc)
        assert "## References" in md
        assert "Smith" in md

    def test_empty_blocks_skipped(self, mkblock):
        from app.pipeline.export.exporter import Exporter
        exporter = Exporter()
        doc = _make_doc(mkblock)
        doc.blocks = [mkblock("", idx=0)]
        md = exporter._build_markdown(doc)
        assert md.strip() != ""


class TestExportJson:
    def test_success(self, mkblock):
        from app.pipeline.export.exporter import Exporter
        exporter = Exporter()
        doc = _make_doc(mkblock)

        m = mock_open()
        with patch("builtins.open", m):
            with patch("os.makedirs"):
                with patch("app.pipeline.export.exporter.safe_model_dump",
                           side_effect=lambda x: {}):
                    result = exporter.export_json(doc, "/tmp/out.json")
        assert result == "/tmp/out.json"

    def test_exception_returns_none(self, mkblock):
        from app.pipeline.export.exporter import Exporter
        exporter = Exporter()
        doc = _make_doc(mkblock)

        with patch("os.makedirs", side_effect=Exception("disk full")):
            result = exporter.export_json(doc, "/tmp/out.json")
        assert result is None


class TestExportMarkdown:
    def test_success(self, mkblock):
        from app.pipeline.export.exporter import Exporter
        exporter = Exporter()
        doc = _make_doc(mkblock)

        m = mock_open()
        with patch("builtins.open", m):
            with patch("os.makedirs"):
                result = exporter.export_markdown(doc, "/tmp/out.md")
        assert result == "/tmp/out.md"

    def test_exception_returns_none(self, mkblock):
        from app.pipeline.export.exporter import Exporter
        exporter = Exporter()
        doc = _make_doc(mkblock)

        with patch("os.makedirs", side_effect=Exception("disk full")):
            result = exporter.export_markdown(doc, "/tmp/out.md")
        assert result is None


class TestExportHtml:
    def test_success(self, mkblock):
        from app.pipeline.export.exporter import Exporter
        exporter = Exporter()
        doc = _make_doc(mkblock)

        m = mock_open()
        with patch("builtins.open", m):
            with patch("os.makedirs"):
                result = exporter.export_html(doc, "/tmp/out.html")
        assert result == "/tmp/out.html"

    def test_ol_list_handling(self, mkblock):
        from app.pipeline.export.exporter import Exporter
        exporter = Exporter()
        doc = _make_doc(mkblock)
        doc.blocks = [mkblock("1. First item", idx=0), mkblock("2. Second item", idx=1)]
        with patch("os.makedirs"):
            with patch("builtins.open", mock_open()):
                html_result = exporter.export_html(doc, "/tmp/out.html")
        assert html_result == "/tmp/out.html"


class TestExportJats:
    def test_success(self, mkblock):
        from app.pipeline.export.exporter import Exporter
        exporter = Exporter()
        doc = _make_doc(mkblock)

        with patch("app.pipeline.export.jats_generator.JATSGenerator.to_xml", return_value="<article/>"):
            m = mock_open()
            with patch("builtins.open", m):
                with patch("os.makedirs"):
                    result = exporter.export_jats(doc, "/tmp/out.xml")
        assert result == "/tmp/out.xml"

    def test_exception_returns_none(self, mkblock):
        from app.pipeline.export.exporter import Exporter
        exporter = Exporter()
        doc = _make_doc(mkblock)

        with patch("app.pipeline.export.jats_generator.JATSGenerator.to_xml", side_effect=Exception("fail")):
            result = exporter.export_jats(doc, "/tmp/out.xml")
        assert result is None


class TestProcess:
    def test_process_with_docx_and_output(self, mkblock):
        from app.pipeline.export.exporter import Exporter
        exporter = Exporter()
        doc = _make_doc(mkblock)
        doc.generated_doc = MagicMock()

        with patch("os.makedirs"):
            with patch("builtins.open", mock_open()):
                with patch("app.pipeline.export.jats_generator.JATSGenerator.to_xml", return_value="<article/>"):
                    result = exporter.process(doc)
        assert result is doc

    def test_process_no_output_path(self, mkblock):
        from app.pipeline.export.exporter import Exporter
        exporter = Exporter()
        doc = _make_doc(mkblock)
        doc.output_path = None

        with patch("os.makedirs"):
            with patch("builtins.open", mock_open()):
                with patch("app.pipeline.export.jats_generator.JATSGenerator.to_xml", return_value="<article/>"):
                    result = exporter.process(doc)
        assert result is doc
