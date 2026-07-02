# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from app.pipeline.parsing.nougat_parser import (
    NougatParser, _classify_nougat_line, _check_available_ram_gb, _pdf_to_images
)

class TestNougatClassifyLine:
    def test_empty_line(self):

        from app.models import BlockType
        assert _classify_nougat_line("") == BlockType.UNKNOWN

    def test_h1(self):
        from app.models import BlockType
        assert _classify_nougat_line("# Title") == BlockType.HEADING_1

    def test_h2(self):
        from app.models import BlockType
        assert _classify_nougat_line("## Section") == BlockType.HEADING_2

    def test_h3(self):
        from app.models import BlockType
        assert _classify_nougat_line("### Subsection") == BlockType.HEADING_3

    def test_abstract(self):
        from app.models import BlockType
        assert _classify_nougat_line("Abstract") == BlockType.ABSTRACT

    def test_references(self):
        from app.models import BlockType
        assert _classify_nougat_line("References") == BlockType.HEADING_1

    def test_bibliography(self):
        from app.models import BlockType
        assert _classify_nougat_line("Bibliography") == BlockType.HEADING_1

    def test_unordered_list(self):
        from app.models import BlockType
        assert _classify_nougat_line("- item") == BlockType.LIST_ITEM
        assert _classify_nougat_line("* item") == BlockType.LIST_ITEM

    def test_ordered_list(self):
        from app.models import BlockType
        assert _classify_nougat_line("1. item") == BlockType.LIST_ITEM

    def test_body(self):
        from app.models import BlockType
        assert _classify_nougat_line("Normal sentence.") == BlockType.BODY

class TestNougatParserInit:
    def test_init_with_remote_urls(self):
        from app.models import BlockType
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = ["https://nougat.example.com"]
            mock_s.PIPELINE_DOCLING_TIMEOUT_SECONDS = 30
            mock_s.GROBID_MAX_RETRIES = 3
            p = NougatParser()
            assert p.remote_base_urls == ["https://nougat.example.com"]
            assert p._last_good_remote_url == "https://nougat.example.com"

    def test_init_with_single_url(self):
        from app.models import BlockType
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = []
            mock_s.NOUGAT_URL = "https://fallback.example.com"
            mock_s.PIPELINE_DOCLING_TIMEOUT_SECONDS = 25
            mock_s.GROBID_MAX_RETRIES = 3
            p = NougatParser()
            assert "fallback.example.com" in p.remote_base_urls[0]

    def test_init_no_remote_no_local_raises(self):
        from app.models import BlockType
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = []
            mock_s.NOUGAT_URL = None
            mock_s.PIPELINE_DOCLING_TIMEOUT_SECONDS = 25
            mock_s.GROBID_MAX_RETRIES = 3
            with patch("app.pipeline.parsing.nougat_parser.NOUGAT_AVAILABLE", False):
                with pytest.raises(ImportError, match="Nougat dependencies unavailable"):
                    NougatParser()

    def test_supports_format(self):
        from app.models import BlockType
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = ["https://example.com"]
            p = NougatParser()
            assert p.supports_format(".pdf")
            assert not p.supports_format(".docx")

class TestNougatParserHelpers:
    def test_retry_backoff(self):
        from app.models import BlockType
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = ["https://example.com"]
            p = NougatParser()
            assert p._retry_backoff_seconds(1) == 1.0
            assert p._retry_backoff_seconds(2) == 2.0
            assert p._retry_backoff_seconds(3) == 4.0
            assert p._retry_backoff_seconds(5) == 8.0

    def test_ordered_urls_prefers_last_good(self):
        from app.models import BlockType
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = ["https://a.com", "https://b.com"]
            mock_s.PIPELINE_DOCLING_TIMEOUT_SECONDS = 25
            mock_s.GROBID_MAX_RETRIES = 3
            p = NougatParser()
            p._last_good_remote_url = "https://b.com"
            ordered = p._ordered_remote_urls()
            assert ordered[0] == "https://b.com"

    def test_mark_last_good_remote_url(self):
        from app.models import BlockType
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = ["https://a.com"]
            p = NougatParser()
            p._mark_last_good_remote_url("https://a.com", reason="test")
            assert p._last_good_remote_url == "https://a.com"

    def test_extract_remote_text_from_dict(self):
        from app.models import BlockType
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = ["https://example.com"]
            p = NougatParser()
            assert p._extract_remote_text({"markdown": "hello"}) == "hello"
            assert p._extract_remote_text({"text": "world"}) == "world"
            assert p._extract_remote_text({"content": "test"}) == "test"
            assert p._extract_remote_text({"result": "ok"}) == "ok"

    def test_extract_remote_text_from_string(self):
        from app.models import BlockType
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = ["https://example.com"]
            p = NougatParser()
            assert p._extract_remote_text("direct text") == "direct text"

    def test_extract_remote_text_empty(self):
        from app.models import BlockType
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = ["https://example.com"]
            p = NougatParser()
            assert p._extract_remote_text({}) == ""
            assert p._extract_remote_text({"markdown": ""}) == ""

    def test_check_ram(self):
        from app.models import BlockType
        gb = _check_available_ram_gb()
        assert isinstance(gb, float)

    def test_new_document(self):
        from app.models import BlockType
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = ["https://example.com"]
            p = NougatParser()
            doc = p._new_document("/path/file.pdf", "doc1")
            assert doc.document_id == "doc1"
            assert doc.original_filename == "file.pdf"

class TestNougatParserParseNougatOutput:
    def test_empty_text(self):
        from app.models import BlockType
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = ["https://example.com"]
            p = NougatParser()
            assert p._parse_nougat_output("") == []
            assert p._parse_nougat_output("  ") == []

    def test_body_paragraph(self):
        from app.models import BlockType
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = ["https://example.com"]
            p = NougatParser()
            blocks = p._parse_nougat_output("Hello world")
            assert len(blocks) == 1
            assert blocks[0].block_type == BlockType.BODY

    def test_heading(self):
        from app.models import BlockType
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = ["https://example.com"]
            p = NougatParser()
            blocks = p._parse_nougat_output("# Title")
            assert blocks[0].text == "Title"
            assert blocks[0].metadata["heading_level"] == 1

    def test_equation_detection(self):
        from app.models import BlockType
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = ["https://example.com"]
            p = NougatParser()
            blocks = p._parse_nougat_output("Equation with \\[E=mc^2\\]")
            assert blocks[0].metadata.get("has_equation") is True

    def test_table_detection(self):
        from app.models import BlockType
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = ["https://example.com"]
            p = NougatParser()
            blocks = p._parse_nougat_output("| A | B |")
            assert blocks[0].metadata.get("is_table") is True

    def test_parser_metadata(self):
        from app.models import BlockType
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = ["https://example.com"]
            p = NougatParser()
            blocks = p._parse_nougat_output("Text")
            assert blocks[0].metadata["parser"] == "nougat"

class TestNougatParserParse:
    def test_parse_file_not_found(self):
        from app.models import BlockType
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = ["https://example.com"]
            p = NougatParser()
            with pytest.raises(FileNotFoundError):
                p.parse("/nonexistent.pdf", "doc1")

    def test_parse_remote_success(self, tmp_path):
        from app.models import BlockType
        f = tmp_path / "test.pdf"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = ["https://example.com"]
            p = NougatParser()
            with patch.object(p, "_parse_via_remote", return_value=MagicMock(document_id="doc1")):
                doc = p.parse(str(f), "doc1")
                assert doc.document_id == "doc1"

    def test_parse_remote_none_local_available(self, tmp_path):
        from app.models import BlockType
        f = tmp_path / "test.pdf"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = ["https://example.com"]
            with patch("app.pipeline.parsing.nougat_parser.NOUGAT_AVAILABLE", True):
                p = NougatParser()
                with patch.object(p, "_parse_via_remote", return_value=None):
                    with patch.object(p, "_parse_local", return_value=MagicMock(document_id="doc1_local")):
                        doc = p.parse(str(f), "doc1")
                        assert doc is not None

    def test_parse_remote_none_local_unavailable(self, tmp_path):
        from app.models import BlockType
        f = tmp_path / "test.pdf"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.nougat_parser.settings") as mock_s:
            mock_s.get_nougat_urls.return_value = ["https://example.com"]
            with patch("app.pipeline.parsing.nougat_parser.NOUGAT_AVAILABLE", False):
                p = NougatParser()
                with patch.object(p, "_parse_via_remote", return_value=None):
                    doc = p.parse(str(f), "doc1")
                    assert doc.metadata.ai_hints["parser"] == "nougat_unavailable"
