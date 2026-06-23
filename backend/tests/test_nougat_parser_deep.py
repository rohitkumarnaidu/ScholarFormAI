# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Deep tests for NougatParser (nougat_parser.py) — 80+ tests covering all internal
methods, remote parsing, local inference, model loading, retry logic, and output
parsing.

NOUGAT_AVAILABLE is a module-level flag set at import time; it MUST be patched
via patch.object before NougatParser.__init__ runs.
"""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch, ANY, call
import pytest

pytestmark = pytest.mark.llm

from app.models.block import BlockType
from app.pipeline.parsing.nougat_parser import (
    _check_available_ram_gb,
    _classify_nougat_line,
    _pdf_to_images,
    PRIMARY_MODEL,
    FALLBACK_MODEL,
    MIN_RAM_GB,
)


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _make_parser(
    nougat_available=True,
    remote_urls=None,
    legacy_url=None,
    model_store_cached=False,
    ram_gb=8.0,
):
    """Build a NougatParser with all external dependencies mocked.

    Parameters control the most common mocking scenarios.  The caller is
    responsible for patching method-level dependencies (requests, torch,
    NougatProcessor, fitz, etc.) in individual tests.
    """
    patch_settings = patch("app.pipeline.parsing.nougat_parser.settings")
    patch_nougat_flag = patch(
        "app.pipeline.parsing.nougat_parser.NOUGAT_AVAILABLE", nougat_available
    )

    with patch_settings as ms, patch_nougat_flag:
        urls_fn = MagicMock(name="get_nougat_urls", return_value=remote_urls or [])
        ms.get_nougat_urls = urls_fn
        ms.NOUGAT_URL = legacy_url
        ms.PIPELINE_DOCLING_TIMEOUT_SECONDS = 25
        ms.GROBID_MAX_RETRIES = 3

        from app.pipeline.parsing.nougat_parser import NougatParser

        parser = NougatParser()

    parser._mock_settings = ms
    return parser




def _patch_processor_and_model(parser, processor=None, model=None, device="cpu"):
    """Attach mock processor & model to a parser instance."""
    parser.processor = processor or MagicMock(name="processor")
    parser.model = model or MagicMock(name="model")
    parser.device = device
    parser._model_loaded = True
    parser.active_model_name = "facebook/nougat-base"
    return parser


# ===================================================================
#  _check_available_ram_gb  (module-level)
# ===================================================================

class TestCheckAvailableRamGb:
    def test_returns_float(self):
        ram = _check_available_ram_gb()
        assert isinstance(ram, float)

    def test_psutil_exception_returns_zero(self):
        # psutil is imported inside _check_available_ram_gb; make it raise
        mock_psutil = MagicMock()
        mock_psutil.virtual_memory.side_effect = Exception("boom")
        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            assert _check_available_ram_gb() == 0.0

    def test_psutil_import_error_returns_zero(self):
        import builtins
        orig_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "psutil":
                raise ImportError("no psutil")
            return orig_import(name, *args, **kwargs)

        with patch("builtins.__import__", fake_import):
            assert _check_available_ram_gb() == 0.0


# ===================================================================
#  _classify_nougat_line
# ===================================================================

class TestClassifyNougatLine:
    def test_empty_line(self):
        assert _classify_nougat_line("") == BlockType.UNKNOWN
        assert _classify_nougat_line("   ") == BlockType.UNKNOWN
        assert _classify_nougat_line("\t") == BlockType.UNKNOWN

    def test_heading_1(self):
        assert _classify_nougat_line("# Introduction") == BlockType.HEADING_1
        assert _classify_nougat_line("#  Introduction") == BlockType.HEADING_1

    def test_heading_2(self):
        assert _classify_nougat_line("## Background") == BlockType.HEADING_2

    def test_heading_3(self):
        assert _classify_nougat_line("### Methods") == BlockType.HEADING_3

    def test_abstract(self):
        assert _classify_nougat_line("Abstract") == BlockType.ABSTRACT
        assert _classify_nougat_line("ABSTRACT") == BlockType.ABSTRACT
        assert _classify_nougat_line("abstract") == BlockType.ABSTRACT

    def test_references_and_bibliography(self):
        assert _classify_nougat_line("References") == BlockType.HEADING_1
        assert _classify_nougat_line("references") == BlockType.HEADING_1
        assert _classify_nougat_line("Bibliography") == BlockType.HEADING_1
        assert _classify_nougat_line("BIBLIOGRAPHY") == BlockType.HEADING_1

    def test_list_item_dash(self):
        assert _classify_nougat_line("- first item") == BlockType.LIST_ITEM
        assert _classify_nougat_line("-  indented") == BlockType.LIST_ITEM

    def test_list_item_star(self):
        assert _classify_nougat_line("* bullet") == BlockType.LIST_ITEM

    def test_list_item_numbered(self):
        assert _classify_nougat_line("1. first") == BlockType.LIST_ITEM
        assert _classify_nougat_line("10. tenth") == BlockType.LIST_ITEM

    def test_table_like_lines(self):
        assert _classify_nougat_line("a | b | c") == BlockType.UNKNOWN
        assert _classify_nougat_line("| a | b |") == BlockType.UNKNOWN

    def test_table_single_pipe_is_body(self):
        assert _classify_nougat_line("not a | table") == BlockType.BODY

    def test_body_paragraph(self):
        assert _classify_nougat_line("This is a normal paragraph.") == BlockType.BODY
        assert _classify_nougat_line("We present a novel method...") == BlockType.BODY


# ===================================================================
#  _pdf_to_images
# ===================================================================

class TestPdfToImages:
    def test_with_fitz(self):
        mock_image = MagicMock(name="Image")
        mock_pix = MagicMock(name="pix")
        mock_pix.width = 400
        mock_pix.height = 300
        mock_pix.samples = b"pixel_data"
        mock_page = MagicMock(name="page")
        mock_page.get_pixmap.return_value = mock_pix
        mock_doc = MagicMock(name="doc")
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page, mock_page]))
        mock_fitz = MagicMock(name="fitz")
        mock_fitz.open.return_value = mock_doc

        import builtins
        orig = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "fitz":
                return mock_fitz
            return orig(name, *args, **kwargs)

        with patch("builtins.__import__", fake_import):
            with patch("app.pipeline.parsing.nougat_parser.Image.frombytes", return_value=mock_image):
                result = _pdf_to_images("test.pdf")

        assert len(result) == 2
        mock_fitz.open.assert_called_once_with("test.pdf")

    def test_fallback_pdf2image(self):
        mock_image_1 = MagicMock(name="img1")
        mock_image_2 = MagicMock(name="img2")
        mock_pdf2image = MagicMock()
        mock_pdf2image.convert_from_path.return_value = [mock_image_1, mock_image_2]

        import builtins
        orig = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "fitz":
                raise ImportError("no fitz")
            return orig(name, *args, **kwargs)

        with patch("builtins.__import__", fake_import):
            with patch.dict("sys.modules", {"pdf2image": mock_pdf2image}):
                result = _pdf_to_images("test.pdf")

        assert len(result) == 2

    def test_no_library_raises(self):
        import builtins
        orig = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name in ("fitz", "pdf2image"):
                raise ImportError(f"no {name}")
            return orig(name, *args, **kwargs)

        with patch("builtins.__import__", fake_import):
            with pytest.raises(RuntimeError, match="Cannot convert PDF to images"):
                _pdf_to_images("test.pdf")


# ===================================================================
#  NougatParser.__init__
# ===================================================================

class TestInit:
    def test_with_remote_urls(self):
        parser = _make_parser(nougat_available=False, remote_urls=["http://nougat:8000"])
        assert parser.remote_base_urls == ["http://nougat:8000"]
        assert parser._last_good_remote_url == "http://nougat:8000"
        assert parser.remote_max_retries == 3
        assert parser.remote_timeout >= 10
        assert parser._model_loaded is False
        assert parser.model is None

    def test_with_legacy_nougat_url(self):
        parser = _make_parser(nougat_available=False, legacy_url="http://legacy:8080")
        assert parser.remote_base_urls == ["http://legacy:8080"]
        assert parser._last_good_remote_url == "http://legacy:8080"

    def test_no_urls_nougat_available(self):
        parser = _make_parser(nougat_available=True, remote_urls=None)
        assert parser.remote_base_urls == []
        assert parser._last_good_remote_url is None

    def test_no_urls_no_nougat_raises(self):
        with pytest.raises(ImportError, match="Nougat dependencies unavailable"):
            _make_parser(nougat_available=False, remote_urls=None)

    def test_remote_and_local_available(self):
        parser = _make_parser(
            nougat_available=True,
            remote_urls=["http://nougat:8000", "http://backup:8000"],
        )
        assert parser.remote_base_urls == ["http://nougat:8000", "http://backup:8000"]
        assert parser._last_good_remote_url == "http://nougat:8000"
        assert parser._model_loaded is False

    def test_urls_stripped_trailing_slash(self):
        parser = _make_parser(nougat_available=False, remote_urls=["http://n/", "http://m/"])
        assert parser.remote_base_urls == ["http://n", "http://m"]

    def test_remote_timeout_from_settings(self):
        patch_settings = patch("app.pipeline.parsing.nougat_parser.settings")
        patch_flag = patch("app.pipeline.parsing.nougat_parser.NOUGAT_AVAILABLE", True)

        with patch_settings as ms, patch_flag:
            ms.get_nougat_urls = MagicMock(return_value=["http://n:8000"])
            ms.NOUGAT_URL = None
            ms.PIPELINE_DOCLING_TIMEOUT_SECONDS = 120
            ms.GROBID_MAX_RETRIES = 5

            from app.pipeline.parsing.nougat_parser import NougatParser

            parser = NougatParser()
            assert parser.remote_timeout == 120
            assert parser.remote_max_retries == 5


# ===================================================================
#  supports_format
# ===================================================================

class TestSupportsFormat:
    def test_pdf_returns_true(self):
        parser = _make_parser(nougat_available=True)
        assert parser.supports_format(".pdf") is True
        assert parser.supports_format(".PDF") is True

    def test_non_pdf_returns_false(self):
        parser = _make_parser(nougat_available=True)
        assert parser.supports_format(".docx") is False
        assert parser.supports_format(".txt") is False
        assert parser.supports_format("") is False


# ===================================================================
#  _ordered_remote_urls
# ===================================================================

class TestOrderedRemoteUrls:
    def test_within_ttl_moves_last_good_to_front(self):
        parser = _make_parser(nougat_available=True, remote_urls=["http://a", "http://b", "http://c"])
        parser._last_good_remote_url = "http://b"
        parser._last_good_remote_at = time.monotonic()  # fresh
        ordered = parser._ordered_remote_urls()
        assert ordered[0] == "http://b"

    def test_expired_ttl_does_not_reorder(self):
        parser = _make_parser(nougat_available=True, remote_urls=["http://a", "http://b"])
        parser._last_good_remote_url = "http://b"
        parser._last_good_remote_at = time.monotonic() - 1000  # well past TTL
        ordered = parser._ordered_remote_urls()
        assert ordered == ["http://a", "http://b"]

    def test_no_last_good_returns_original(self):
        parser = _make_parser(nougat_available=True, remote_urls=["http://a", "http://b"])
        parser._last_good_remote_url = None
        ordered = parser._ordered_remote_urls()
        assert ordered == ["http://a", "http://b"]

    def test_empty_urls(self):
        parser = _make_parser(nougat_available=True, remote_urls=[])
        assert parser._ordered_remote_urls() == []

    def test_last_good_not_in_list(self):
        parser = _make_parser(nougat_available=True, remote_urls=["http://a"])
        parser._last_good_remote_url = "http://unknown"
        parser._last_good_remote_at = time.monotonic()
        assert parser._ordered_remote_urls() == ["http://a"]


# ===================================================================
#  _mark_last_good_remote_url
# ===================================================================

class TestMarkLastGoodRemoteUrl:
    def test_sets_last_good_url_and_timestamp(self):
        parser = _make_parser(nougat_available=True, remote_urls=["http://a"])
        before = parser._last_good_remote_at
        parser._mark_last_good_remote_url("http://b", reason="test")
        assert parser._last_good_remote_url == "http://b"
        assert parser._last_good_remote_at >= before

    def test_switch_logs_warning(self):
        parser = _make_parser(nougat_available=True, remote_urls=["http://a"])
        parser._last_good_remote_url = "http://old"
        with patch("app.pipeline.parsing.nougat_parser.logger") as m_log:
            parser._mark_last_good_remote_url("http://new", reason="failover")
            m_log.warning.assert_called_once()
            args, _ = m_log.warning.call_args
            assert "failover" in args[0]


# ===================================================================
#  _retry_backoff_seconds
# ===================================================================

class TestRetryBackoffSeconds:
    def test_exponential(self):
        parser = _make_parser(nougat_available=True)
        assert parser._retry_backoff_seconds(1) == 1.0
        assert parser._retry_backoff_seconds(2) == 2.0
        assert parser._retry_backoff_seconds(3) == 4.0

    def test_capped_at_eight(self):
        parser = _make_parser(nougat_available=True)
        assert parser._retry_backoff_seconds(4) == 8.0
        assert parser._retry_backoff_seconds(5) == 8.0
        assert parser._retry_backoff_seconds(10) == 8.0

    def test_attempt_zero(self):
        parser = _make_parser(nougat_available=True)
        assert parser._retry_backoff_seconds(0) == 1.0  # 2^(max(0,-1)) = 2^0 = 1.0


# ===================================================================
#  _new_document
# ===================================================================

class TestNewDocument:
    def test_creates_document_with_metadata(self):
        parser = _make_parser(nougat_available=True)
        doc = parser._new_document("/path/to/paper.pdf", "doc_001")
        assert doc.document_id == "doc_001"
        assert doc.original_filename == "paper.pdf"
        assert doc.source_path == "/path/to/paper.pdf"
        assert doc.metadata is not None
        assert doc.blocks == []

    def test_filename_from_path(self):
        parser = _make_parser(nougat_available=True)
        doc = parser._new_document("/a/b/c/MyPaper.PDF", "x")
        assert doc.original_filename == "MyPaper.PDF"


# ===================================================================
#  _extract_remote_text
# ===================================================================

class TestExtractRemoteText:
    def test_from_dict_markdown_key(self):
        parser = _make_parser(nougat_available=True)
        result = parser._extract_remote_text({"markdown": "# Hello\nWorld"})
        assert result == "# Hello\nWorld"

    def test_from_dict_text_key(self):
        parser = _make_parser(nougat_available=True)
        result = parser._extract_remote_text({"text": "some text", "markdown": ""})
        assert result == "some text"

    def test_from_dict_content_key(self):
        parser = _make_parser(nougat_available=True)
        result = parser._extract_remote_text({"content": "body", "text": ""})
        assert result == "body"

    def test_from_dict_result_key(self):
        parser = _make_parser(nougat_available=True)
        result = parser._extract_remote_text({"result": "parsed", "content": ""})
        assert result == "parsed"

    def test_from_string(self):
        parser = _make_parser(nougat_available=True)
        result = parser._extract_remote_text("raw string output")
        assert result == "raw string output"

    def test_from_empty_string(self):
        parser = _make_parser(nougat_available=True)
        result = parser._extract_remote_text("")
        assert result == ""

    def test_empty_dict_returns_empty_string(self):
        parser = _make_parser(nougat_available=True)
        result = parser._extract_remote_text({})
        assert result == ""

    def test_dict_with_only_whitespace_values(self):
        parser = _make_parser(nougat_available=True)
        result = parser._extract_remote_text({"markdown": "   ", "text": ""})
        assert result == ""

    def test_none_payload(self):
        parser = _make_parser(nougat_available=True)
        result = parser._extract_remote_text(None)
        assert result == ""

    def test_int_payload(self):
        parser = _make_parser(nougat_available=True)
        result = parser._extract_remote_text(42)
        assert result == ""


# ===================================================================
#  _parse_via_remote
# ===================================================================

class TestParseViaRemote:
    def test_no_urls_configured_returns_none(self):
        parser = _make_parser(nougat_available=True, remote_urls=[])
        result = parser._parse_via_remote("test.pdf", "doc_001")
        assert result is None

    @patch("app.pipeline.parsing.nougat_parser.requests.post")
    @patch("app.pipeline.parsing.nougat_parser.time.sleep", return_value=None)
    @patch("builtins.open")
    def test_success(self, mock_open, mock_sleep, mock_post):
        mock_fh = MagicMock(name="fh")
        mock_open.return_value.__enter__.return_value = mock_fh

        mock_resp = MagicMock(name="resp")
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"markdown": "# Hello\n\nWorld"}
        mock_post.return_value = mock_resp

        parser = _make_parser(nougat_available=True, remote_urls=["http://n:8000"])
        doc = parser._parse_via_remote("test.pdf", "doc_001")

        assert doc is not None
        assert doc.document_id == "doc_001"
        assert len(doc.blocks) >= 1
        assert doc.metadata.ai_hints["parser"] == "nougat_remote"
        assert doc.metadata.ai_hints["nougat_endpoint"] == "http://n:8000/parse"
        mock_post.assert_called_once()

    @patch("app.pipeline.parsing.nougat_parser.requests.post")
    @patch("app.pipeline.parsing.nougat_parser.time.sleep", return_value=None)
    @patch("builtins.open")
    def test_retry_on_transient_429(self, mock_open, mock_sleep, mock_post):
        mock_open.return_value.__enter__.return_value = MagicMock()
        resp_429 = MagicMock(status_code=429)
        resp_200 = MagicMock(status_code=200)
        resp_200.json.return_value = {"markdown": "ok"}
        mock_post.side_effect = [resp_429, resp_200]

        parser = _make_parser(nougat_available=True, remote_urls=["http://n:8000"])
        doc = parser._parse_via_remote("test.pdf", "doc_001")

        assert doc is not None
        assert mock_post.call_count == 2

    @patch("app.pipeline.parsing.nougat_parser.requests.post")
    @patch("app.pipeline.parsing.nougat_parser.time.sleep", return_value=None)
    @patch("builtins.open")
    def test_retry_on_transient_503(self, mock_open, mock_sleep, mock_post):
        mock_open.return_value.__enter__.return_value = MagicMock()
        resp_503 = MagicMock(status_code=503)
        resp_200 = MagicMock(status_code=200)
        resp_200.json.return_value = {"markdown": "ok"}
        mock_post.side_effect = [resp_503, resp_200]

        parser = _make_parser(nougat_available=True, remote_urls=["http://n:8000"])
        doc = parser._parse_via_remote("test.pdf", "doc_001")
        assert doc is not None

    @patch("app.pipeline.parsing.nougat_parser.requests.post")
    @patch("app.pipeline.parsing.nougat_parser.time.sleep", return_value=None)
    @patch("builtins.open")
    def test_non_transient_status_does_not_retry(self, mock_open, mock_sleep, mock_post):
        mock_open.return_value.__enter__.return_value = MagicMock()
        resp_400 = MagicMock(status_code=400)
        mock_post.return_value = resp_400

        parser = _make_parser(nougat_available=True, remote_urls=["http://n:8000"])
        doc = parser._parse_via_remote("test.pdf", "doc_001")
        # 400 is not transient, so it breaks out per path — 2 paths tried, 0 retries
        assert doc is None
        assert mock_post.call_count == 2  # 1 per path (no retries on non-transient)

    @patch("app.pipeline.parsing.nougat_parser.requests.post")
    @patch("app.pipeline.parsing.nougat_parser.time.sleep", return_value=None)
    @patch("builtins.open")
    def test_all_retries_exhausted(self, mock_open, mock_sleep, mock_post):
        mock_open.return_value.__enter__.return_value = MagicMock()
        resp = MagicMock(status_code=503)
        mock_post.return_value = resp

        parser = _make_parser(nougat_available=True, remote_urls=["http://n:8000"])
        doc = parser._parse_via_remote("test.pdf", "doc_001")
        assert doc is None
        # 2 paths × 3 retries each = 6 total calls
        assert mock_post.call_count == 6

    @patch("app.pipeline.parsing.nougat_parser.requests.post")
    @patch("app.pipeline.parsing.nougat_parser.time.sleep", return_value=None)
    @patch("builtins.open")
    def test_empty_response_retries(self, mock_open, mock_sleep, mock_post):
        mock_open.return_value.__enter__.return_value = MagicMock()
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"markdown": ""}
        mock_post.return_value = mock_resp

        parser = _make_parser(nougat_available=True, remote_urls=["http://n:8000"])
        doc = parser._parse_via_remote("test.pdf", "doc_001")
        assert doc is None
        # 2 paths × 3 retries each = 6
        assert mock_post.call_count == 6

    @patch("app.pipeline.parsing.nougat_parser.requests.post")
    @patch("app.pipeline.parsing.nougat_parser.time.sleep", return_value=None)
    @patch("builtins.open")
    def test_request_exception_retry(self, mock_open, mock_sleep, mock_post):
        mock_open.return_value.__enter__.return_value = MagicMock()
        mock_post.side_effect = [
            Exception("connection error"),
            MagicMock(status_code=200, json=lambda: {"markdown": "ok"}),
        ]

        parser = _make_parser(nougat_available=True, remote_urls=["http://n:8000"])
        doc = parser._parse_via_remote("test.pdf", "doc_001")
        assert doc is not None
        assert mock_post.call_count == 2

    @patch("app.pipeline.parsing.nougat_parser.requests.post")
    @patch("app.pipeline.parsing.nougat_parser.time.sleep", return_value=None)
    @patch("builtins.open")
    def test_failover_endpoints(self, mock_open, mock_sleep, mock_post):
        mock_open.return_value.__enter__.return_value = MagicMock()

        def side_effect(*args, **kwargs):
            url = args[0] if args else kwargs.get("url", "")
            if "first" in url:
                return MagicMock(status_code=503)
            return MagicMock(status_code=200, json=lambda: {"markdown": "ok"})

        mock_post.side_effect = side_effect

        parser = _make_parser(
            nougat_available=True,
            remote_urls=["http://first:8000", "http://second:8000"],
        )
        doc = parser._parse_via_remote("test.pdf", "doc_001")
        assert doc is not None
        assert doc.metadata.ai_hints["nougat_endpoint"].startswith("http://second:8000")

    @patch("app.pipeline.parsing.nougat_parser.requests.post")
    @patch("app.pipeline.parsing.nougat_parser.time.sleep", return_value=None)
    @patch("builtins.open")
    def test_updates_last_good_url(self, mock_open, mock_sleep, mock_post):
        mock_open.return_value.__enter__.return_value = MagicMock()
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"markdown": "ok"}
        mock_post.return_value = mock_resp

        parser = _make_parser(nougat_available=True, remote_urls=["http://n:8000"])
        assert parser._last_good_remote_url == "http://n:8000"
        doc = parser._parse_via_remote("test.pdf", "doc_001")
        assert doc is not None
        assert parser._last_good_remote_url == "http://n:8000"

    @patch("app.pipeline.parsing.nougat_parser.requests.post")
    @patch("app.pipeline.parsing.nougat_parser.time.sleep", return_value=None)
    @patch("builtins.open")
    def test_multiple_paths_tried(self, mock_open, mock_sleep, mock_post):
        mock_open.return_value.__enter__.return_value = MagicMock()
        resp_200 = MagicMock(status_code=200)
        resp_200.json.return_value = {"markdown": "ok"}

        def side_effect(*args, **kwargs):
            url = kwargs.get("url", "") or args[0]
            if url.endswith("/api/parse"):
                return resp_200
            return MagicMock(status_code=404)

        mock_post.side_effect = side_effect

        parser = _make_parser(nougat_available=True, remote_urls=["http://n:8000"])
        doc = parser._parse_via_remote("test.pdf", "doc_001")
        assert doc is not None
        assert doc.metadata.ai_hints["nougat_endpoint"].endswith("/api/parse")

    @patch("app.pipeline.parsing.nougat_parser.requests.post")
    @patch("app.pipeline.parsing.nougat_parser.time.sleep", return_value=None)
    @patch("builtins.open")
    def test_response_json_fallback_to_text(self, mock_open, mock_sleep, mock_post):
        mock_open.return_value.__enter__.return_value = MagicMock()
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.side_effect = ValueError("not json")
        mock_resp.text = "# Hello\n\nWorld"
        mock_post.return_value = mock_resp

        parser = _make_parser(nougat_available=True, remote_urls=["http://n:8000"])
        doc = parser._parse_via_remote("test.pdf", "doc_001")
        assert doc is not None
        assert len(doc.blocks) >= 1


# ===================================================================
#  _ensure_model_loaded
# ===================================================================

class TestEnsureModelLoaded:
    def test_already_loaded_returns_immediately(self):
        parser = _make_parser(nougat_available=True)
        parser._model_loaded = True
        parser._ensure_model_loaded()
        # Should not raise

    @patch("app.pipeline.parsing.nougat_parser.NOUGAT_AVAILABLE", False)
    def test_not_available_raises(self):
        parser = _make_parser(nougat_available=True, remote_urls=["http://n:8000"])
        with pytest.raises(RuntimeError, match="Local Nougat dependencies unavailable"):
            parser._ensure_model_loaded()

    @patch("app.pipeline.parsing.nougat_parser.torch")
    def test_loaded_from_model_store_cache(self, mock_torch):
        mock_torch.device = lambda x: x
        mock_torch.cuda.is_available.return_value = False
        mock_torch.no_grad = MagicMock(
            return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())
        )

        parser = _make_parser(nougat_available=True)
        with patch("app.services.model_store.model_store") as mock_store:
            mock_store.is_loaded.return_value = True
            mock_model = MagicMock(name="cached_model")
            param_mock = MagicMock(name="param")
            param_mock.device = "cpu"
            mock_model.parameters.return_value = iter([param_mock])
            mock_store.get_model.side_effect = lambda k: {
                "nougat_model": mock_model,
                "nougat_processor": MagicMock(name="cached_processor"),
            }.get(k)
            parser._ensure_model_loaded()

        assert parser._model_loaded is True
        assert parser.active_model_name == "cached"

    @patch("app.pipeline.parsing.nougat_parser.NougatProcessor")
    @patch("app.pipeline.parsing.nougat_parser.VisionEncoderDecoderModel")
    @patch("app.pipeline.parsing.nougat_parser.torch")
    @patch("app.pipeline.parsing.nougat_parser._check_available_ram_gb")
    def test_loads_preferred_model(
        self, mock_ram, mock_torch, mock_model_class, mock_processor_class
    ):
        mock_ram.return_value = 64.0
        mock_torch.device = lambda x: x
        mock_torch.cuda.is_available.return_value = False
        mock_torch.no_grad.return_value = MagicMock(
            __enter__=MagicMock(), __exit__=MagicMock()
        )

        mock_processor = MagicMock(name="processor")
        mock_model = MagicMock(name="model")
        param_mock = MagicMock(name="param")
        param_mock.device = "cpu"
        mock_model.parameters.return_value = iter([param_mock])
        mock_processor_class.from_pretrained.return_value = mock_processor
        mock_model_class.from_pretrained.return_value = mock_model

        parser = _make_parser(nougat_available=True)
        with patch("app.services.model_store.model_store") as mock_store:
            mock_store.is_loaded.return_value = False
            parser._ensure_model_loaded()

        assert parser._model_loaded is True
        assert parser.active_model_name == PRIMARY_MODEL
        mock_processor_class.from_pretrained.assert_called_once_with(PRIMARY_MODEL)
        mock_model_class.from_pretrained.assert_called_once_with(PRIMARY_MODEL)

    @patch("app.pipeline.parsing.nougat_parser.NougatProcessor")
    @patch("app.pipeline.parsing.nougat_parser.VisionEncoderDecoderModel")
    @patch("app.pipeline.parsing.nougat_parser.torch")
    @patch("app.pipeline.parsing.nougat_parser._check_available_ram_gb")
    def test_fallback_on_low_ram(
        self, mock_ram, mock_torch, mock_model_class, mock_processor_class
    ):
        mock_ram.return_value = 2.0  # below MIN_RAM_GB
        mock_torch.device = lambda x: x
        mock_torch.cuda.is_available.return_value = False
        mock_torch.no_grad.return_value = MagicMock(
            __enter__=MagicMock(), __exit__=MagicMock()
        )

        mock_processor = MagicMock(name="processor")
        mock_model = MagicMock(name="model")
        param_mock = MagicMock(name="param")
        param_mock.device = "cpu"
        mock_model.parameters.return_value = iter([param_mock])
        mock_processor_class.from_pretrained.return_value = mock_processor
        mock_model_class.from_pretrained.return_value = mock_model

        parser = _make_parser(nougat_available=True)
        with patch("app.services.model_store.model_store") as mock_store:
            mock_store.is_loaded.return_value = False
            parser._ensure_model_loaded()

        assert parser._model_loaded is True
        assert parser.active_model_name == FALLBACK_MODEL
        mock_processor_class.from_pretrained.assert_called_once_with(FALLBACK_MODEL)

    @patch("app.pipeline.parsing.nougat_parser.NougatProcessor")
    @patch("app.pipeline.parsing.nougat_parser.VisionEncoderDecoderModel")
    @patch("app.pipeline.parsing.nougat_parser.torch")
    def test_both_models_fail_raises(
        self, mock_torch, mock_model_class, mock_processor_class
    ):
        mock_torch.device = lambda x: x
        mock_torch.cuda.is_available.return_value = False
        mock_torch.no_grad.return_value = MagicMock(
            __enter__=MagicMock(), __exit__=MagicMock()
        )

        mock_processor_class.from_pretrained.side_effect = Exception("OOM")

        parser = _make_parser(nougat_available=True)
        with patch("app.services.model_store.model_store") as mock_store:
            mock_store.is_loaded.return_value = False
            with pytest.raises(RuntimeError, match="unable to load local Nougat model"):
                parser._ensure_model_loaded()

    @patch("app.pipeline.parsing.nougat_parser.NougatProcessor")
    @patch("app.pipeline.parsing.nougat_parser.VisionEncoderDecoderModel")
    @patch("app.pipeline.parsing.nougat_parser.torch")
    @patch("app.pipeline.parsing.nougat_parser._check_available_ram_gb")
    def test_preferred_fails_fallback_succeeds(
        self, mock_ram, mock_torch, mock_model_class, mock_processor_class
    ):
        mock_ram.return_value = 64.0  # enough RAM for preferred model
        mock_torch.device = lambda x: x
        mock_torch.cuda.is_available.return_value = False
        mock_torch.no_grad.return_value = MagicMock(
            __enter__=MagicMock(), __exit__=MagicMock()
        )

        mock_processor = MagicMock(name="processor")
        mock_model = MagicMock(name="model")
        param_mock = MagicMock(name="param")
        param_mock.device = "cpu"
        mock_model.parameters.return_value = iter([param_mock])

        # PRIMARY fails at processor, FALLBACK succeeds for both
        mock_processor_class.from_pretrained.side_effect = [
            Exception("OOM on primary"),
            mock_processor,
        ]
        mock_model_class.from_pretrained.return_value = mock_model

        parser = _make_parser(nougat_available=True)
        with patch("app.services.model_store.model_store") as mock_store:
            mock_store.is_loaded.return_value = False
            parser._ensure_model_loaded()
        assert parser._model_loaded is True
        assert parser.active_model_name == FALLBACK_MODEL


# ===================================================================
#  _process_page
# ===================================================================

class TestProcessPage:
    def test_success(self):
        parser = _make_parser(nougat_available=True)
        mock_processor = MagicMock(name="processor")
        mock_processor.tokenizer.unk_token_id = 3
        mock_processor.return_value = MagicMock(pixel_values=MagicMock())
        mock_processor.batch_decode.return_value = ["## Result\n\nText"]
        mock_processor.post_process_generation.return_value = "## Result\n\nText"

        mock_model = MagicMock(name="model")
        mock_model.generate.return_value = MagicMock()

        _patch_processor_and_model(parser, processor=mock_processor, model=mock_model)

        with patch("app.pipeline.parsing.nougat_parser.torch") as m_torch:
            m_torch.no_grad.return_value = MagicMock(
                __enter__=MagicMock(), __exit__=MagicMock()
            )

            mock_image = MagicMock(name="image")
            result = parser._process_page(mock_image)

        assert result == "## Result\n\nText"
        mock_processor.assert_called_once_with(mock_image, return_tensors="pt")
        mock_model.generate.assert_called_once()
        kwargs = mock_model.generate.call_args[1]
        assert "bad_words_ids" in kwargs
        assert kwargs["bad_words_ids"] == [[3]]

    def test_with_torch_cuda(self):
        parser = _make_parser(nougat_available=True)
        mock_processor = MagicMock(name="processor")
        mock_processor.tokenizer.unk_token_id = 3
        mock_processor.return_value = MagicMock(pixel_values=MagicMock())
        mock_processor.batch_decode.return_value = ["cuda output"]
        mock_processor.post_process_generation.return_value = "cuda output"

        mock_model = MagicMock(name="model")
        mock_model.generate.return_value = MagicMock()

        _patch_processor_and_model(parser, processor=mock_processor, model=mock_model, device="cuda")

        with patch("app.pipeline.parsing.nougat_parser.torch") as m_torch:
            m_torch.no_grad.return_value = MagicMock(
                __enter__=MagicMock(), __exit__=MagicMock()
            )
            mock_image = MagicMock(name="image")
            result = parser._process_page(mock_image)

        assert result == "cuda output"


# ===================================================================
#  _parse_local
# ===================================================================

class TestParseLocal:
    @patch("app.pipeline.parsing.nougat_parser._pdf_to_images")
    @patch("app.pipeline.parsing.nougat_parser.torch")
    def test_success(self, mock_torch, mock_pdf_to_images):
        mock_img_1 = MagicMock(name="img1")
        mock_img_2 = MagicMock(name="img2")
        mock_pdf_to_images.return_value = [mock_img_1, mock_img_2]

        parser = _make_parser(nougat_available=True)

        mock_processor = MagicMock(name="processor")
        mock_processor.tokenizer.unk_token_id = 3
        mock_processor.return_value = MagicMock(pixel_values=MagicMock())
        mock_processor.batch_decode.side_effect = [
            ["Page 1 content"],
            ["Page 2 content"],
        ]
        mock_processor.post_process_generation.side_effect = [
            "Page 1 content",
            "Page 2 content",
        ]

        mock_model = MagicMock(name="model")
        mock_model.generate.return_value = MagicMock()

        _patch_processor_and_model(parser, processor=mock_processor, model=mock_model)

        mock_torch.no_grad.return_value = MagicMock(
            __enter__=MagicMock(), __exit__=MagicMock()
        )

        doc = parser._parse_local("test.pdf", "doc_001")

        assert doc.document_id == "doc_001"
        assert len(doc.blocks) > 0
        assert doc.metadata.ai_hints["parser"] == "nougat_local"
        assert doc.metadata.ai_hints["nougat_model"] == "facebook/nougat-base"
        assert mock_pdf_to_images.call_count == 1

    @patch("app.pipeline.parsing.nougat_parser._pdf_to_images")
    @patch("app.pipeline.parsing.nougat_parser.torch")
    def test_empty_images(self, mock_torch, mock_pdf_to_images):
        mock_pdf_to_images.return_value = []

        parser = _make_parser(nougat_available=True)
        _patch_processor_and_model(parser)

        mock_torch.no_grad.return_value = MagicMock(
            __enter__=MagicMock(), __exit__=MagicMock()
        )

        doc = parser._parse_local("test.pdf", "doc_001")
        assert doc.blocks == []
        assert doc.metadata.ai_hints["parser"] == "nougat_local"

    @patch("app.pipeline.parsing.nougat_parser._pdf_to_images")
    @patch("app.pipeline.parsing.nougat_parser.torch")
    def test_page_failure_continues(self, mock_torch, mock_pdf_to_images):
        mock_img_1 = MagicMock(name="img1")
        mock_img_2 = MagicMock(name="img2")
        mock_pdf_to_images.return_value = [mock_img_1, mock_img_2]

        parser = _make_parser(nougat_available=True)

        mock_processor = MagicMock(name="processor")
        mock_processor.tokenizer.unk_token_id = 3
        mock_processor.return_value = MagicMock(pixel_values=MagicMock())
        mock_processor.batch_decode.side_effect = [
            Exception("page 1 crash"),
            ["Page 2 ok"],
        ]
        mock_processor.post_process_generation.return_value = "Page 2 ok"

        mock_model = MagicMock(name="model")
        _patch_processor_and_model(parser, processor=mock_processor, model=mock_model)

        mock_torch.no_grad.return_value = MagicMock(
            __enter__=MagicMock(), __exit__=MagicMock()
        )

        doc = parser._parse_local("test.pdf", "doc_001")
        # Should still have page 2 content
        assert len(doc.blocks) > 0


# ===================================================================
#  parse  (main entry)
# ===================================================================

class TestParse:
    def test_file_not_found(self):
        parser = _make_parser(nougat_available=True)
        with patch("os.path.exists", return_value=False):
            with pytest.raises(FileNotFoundError, match="PDF file not found"):
                parser.parse("/nonexistent/paper.pdf", "doc_001")

    @patch("app.pipeline.parsing.nougat_parser.requests.post")
    @patch("app.pipeline.parsing.nougat_parser.time.sleep", return_value=None)
    @patch("builtins.open")
    @patch("os.path.exists", return_value=True)
    def test_remote_success(self, mock_exists, mock_open, mock_sleep, mock_post):
        mock_open.return_value.__enter__.return_value = MagicMock()
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"markdown": "# Intro\n\nBody text"}
        mock_post.return_value = mock_resp

        parser = _make_parser(nougat_available=True, remote_urls=["http://n:8000"])
        doc = parser.parse("test.pdf", "doc_001")

        assert doc.document_id == "doc_001"
        assert doc.metadata.ai_hints["parser"] == "nougat_remote"

    @patch("app.pipeline.parsing.nougat_parser.requests.post")
    @patch("app.pipeline.parsing.nougat_parser.time.sleep", return_value=None)
    @patch("builtins.open")
    @patch("app.pipeline.parsing.nougat_parser._pdf_to_images")
    @patch("app.pipeline.parsing.nougat_parser.torch")
    @patch("os.path.exists", return_value=True)
    def test_remote_fallback_to_local(
        self, mock_exists, mock_torch, mock_pdf_to_images, mock_open, mock_sleep, mock_post
    ):
        mock_open.return_value.__enter__.return_value = MagicMock()
        # Remote returns None (no URLs configured that work)
        mock_pdf_to_images.return_value = []
        mock_torch.no_grad.return_value = MagicMock(
            __enter__=MagicMock(), __exit__=MagicMock()
        )

        parser = _make_parser(nougat_available=True, remote_urls=[])
        _patch_processor_and_model(parser)

        doc = parser.parse("test.pdf", "doc_001")
        assert doc.metadata.ai_hints["parser"] == "nougat_local"

    @patch("app.pipeline.parsing.nougat_parser.NOUGAT_AVAILABLE", False)
    @patch("app.pipeline.parsing.nougat_parser.requests.post")
    @patch("app.pipeline.parsing.nougat_parser.time.sleep", return_value=None)
    @patch("builtins.open")
    @patch("os.path.exists", return_value=True)
    def test_remote_fails_local_not_available(self, mock_exists, mock_open, mock_sleep, mock_post):
        mock_open.return_value.__enter__.return_value = MagicMock()
        mock_resp = MagicMock(status_code=503)
        mock_post.return_value = mock_resp

        parser = _make_parser(nougat_available=False, remote_urls=["http://n:8000"])
        doc = parser.parse("test.pdf", "doc_001")

        assert doc.metadata.ai_hints["parser"] == "nougat_unavailable"
        assert len(doc.processing_history) > 0
        assert doc.processing_history[0].status == "error"

    @patch("app.pipeline.parsing.nougat_parser.NOUGAT_AVAILABLE", False)
    @patch("app.pipeline.parsing.nougat_parser.requests.post")
    @patch("app.pipeline.parsing.nougat_parser.time.sleep", return_value=None)
    @patch("builtins.open")
    @patch("os.path.exists", return_value=True)
    def test_all_fail_empty_document(self, mock_exists, mock_open, mock_sleep, mock_post):
        mock_open.return_value.__enter__.return_value = MagicMock()
        mock_resp = MagicMock(status_code=503)
        mock_post.return_value = mock_resp

        parser = _make_parser(nougat_available=False, remote_urls=["http://n:8000"])
        doc = parser.parse("test.pdf", "doc_001")

        assert doc.blocks == []
        assert doc.metadata.ai_hints["parser"] == "nougat_unavailable"


# ===================================================================
#  _parse_nougat_output
# ===================================================================

class TestParseNougatOutput:
    def test_empty_string(self):
        parser = _make_parser(nougat_available=True)
        blocks = parser._parse_nougat_output("")
        assert blocks == []

    def test_only_whitespace(self):
        parser = _make_parser(nougat_available=True)
        blocks = parser._parse_nougat_output("   \n\n  \n")
        assert blocks == []

    def test_basic_paragraphs(self):
        parser = _make_parser(nougat_available=True)
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        blocks = parser._parse_nougat_output(text)
        assert len(blocks) == 3
        assert blocks[0].text == "First paragraph."
        assert blocks[0].block_type == BlockType.BODY
        assert blocks[0].style.bold is False

    def test_headings(self):
        parser = _make_parser(nougat_available=True)
        text = "# Title\n\n## Section\n\n### Subsection\n\nBody."
        blocks = parser._parse_nougat_output(text)
        assert len(blocks) == 4
        assert blocks[0].text == "Title"
        assert blocks[0].block_type == BlockType.HEADING_1
        assert blocks[0].style.bold is True
        assert blocks[0].metadata["heading_level"] == 1
        assert blocks[1].text == "Section"
        assert blocks[1].block_type == BlockType.HEADING_2
        assert blocks[1].metadata["heading_level"] == 2
        assert blocks[2].text == "Subsection"
        assert blocks[2].block_type == BlockType.HEADING_3
        assert blocks[2].metadata["heading_level"] == 3
        assert blocks[3].block_type == BlockType.BODY

    def test_with_equations(self):
        parser = _make_parser(nougat_available=True)
        text = "Equation inline \\[E=mc^2\\] here.\n\n$$\\int f(x) dx$$"
        blocks = parser._parse_nougat_output(text)
        assert len(blocks) == 2
        assert blocks[0].metadata.get("has_equation") is True
        assert blocks[1].metadata.get("has_equation") is True

    def test_with_tables(self):
        parser = _make_parser(nougat_available=True)
        text = "Normal paragraph.\n\n| Col1 | Col2 | Col3 |"
        blocks = parser._parse_nougat_output(text)
        assert len(blocks) == 2
        assert blocks[1].block_type == BlockType.UNKNOWN
        assert blocks[1].metadata.get("is_table") is True

    def test_heading_metadata(self):
        parser = _make_parser(nougat_available=True)
        text = "# Introduction"
        blocks = parser._parse_nougat_output(text)
        assert len(blocks) == 1
        assert blocks[0].metadata["heading_level"] == 1
        assert blocks[0].metadata["potential_heading"] is True
        assert blocks[0].metadata["parser"] == "nougat"

    def test_begin_equation(self):
        parser = _make_parser(nougat_available=True)
        text = "\\begin{equation} E=mc^2 \\end{equation}"
        blocks = parser._parse_nougat_output(text)
        assert len(blocks) == 1
        assert blocks[0].metadata.get("has_equation") is True

    def test_block_ids_sequential(self):
        parser = _make_parser(nougat_available=True)
        text = "Block A\n\nBlock B\n\nBlock C"
        blocks = parser._parse_nougat_output(text)
        assert len(blocks) == 3
        assert blocks[0].block_id == "blk_000"
        assert blocks[1].block_id == "blk_001"
        assert blocks[2].block_id == "blk_002"

    def test_block_indices(self):
        parser = _make_parser(nougat_available=True)
        text = "One\n\nTwo\n\nThree"
        blocks = parser._parse_nougat_output(text)
        assert blocks[0].index == 100
        assert blocks[1].index == 200
        assert blocks[2].index == 300

    def test_references_and_bibliography_classified_as_heading1(self):
        parser = _make_parser(nougat_available=True)
        text = "References\n\n[1] Author. Title. Journal.\n\nBibliography\n\n[2] Another."
        blocks = parser._parse_nougat_output(text)
        # "References" and "Bibliography" are classified as HEADING_1
        assert blocks[0].block_type == BlockType.HEADING_1
        assert blocks[0].text == "References"
        assert blocks[2].block_type == BlockType.HEADING_1
        assert blocks[2].text == "Bibliography"

    def test_abstract_classification(self):
        parser = _make_parser(nougat_available=True)
        text = "Abstract\n\nThis paper presents..."
        blocks = parser._parse_nougat_output(text)
        assert blocks[0].block_type == BlockType.ABSTRACT
        assert blocks[1].block_type == BlockType.BODY
        assert blocks[1].text == "This paper presents..."

    def test_list_items(self):
        parser = _make_parser(nougat_available=True)
        text = "- item one\n\n- item two\n\n1. numbered item"
        blocks = parser._parse_nougat_output(text)
        assert len(blocks) == 3
        for b in blocks:
            assert b.block_type == BlockType.LIST_ITEM

    def test_bold_on_non_heading_is_false(self):
        parser = _make_parser(nougat_available=True)
        text = "Regular paragraph."
        blocks = parser._parse_nougat_output(text)
        assert blocks[0].style.bold is False

    def test_heading_block_type_without_hash(self):
        # "References" and "Bibliography" become HEADING_1 without # prefix
        parser = _make_parser(nougat_available=True)
        text = "References"
        blocks = parser._parse_nougat_output(text)
        assert blocks[0].block_type == BlockType.HEADING_1
        assert blocks[0].text == "References"
        assert "potential_heading" not in blocks[0].metadata  # no # prefix
        assert "heading_level" not in blocks[0].metadata
        assert blocks[0].style.bold is False  # heading_level is 0

    def test_heading_bold_only_when_heading_level_gt_zero(self):
        parser = _make_parser(nougat_available=True)
        text = "# Real Heading\n\nReferences"
        blocks = parser._parse_nougat_output(text)
        assert blocks[0].style.bold is True  # heading_level == 1
        assert blocks[0].metadata["heading_level"] == 1
        assert blocks[1].style.bold is False  # heading_level == 0
        assert "heading_level" not in blocks[1].metadata


# ===================================================================
#  Integration-style edge cases
# ===================================================================

class TestEdgeCases:
    @patch("app.pipeline.parsing.nougat_parser.requests.post")
    @patch("app.pipeline.parsing.nougat_parser.time.sleep", return_value=None)
    @patch("builtins.open")
    def test_remote_sets_ai_hints_parser_field(self, mock_open, mock_sleep, mock_post):
        mock_open.return_value.__enter__.return_value = MagicMock()
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"markdown": "Hello world"}
        mock_post.return_value = mock_resp

        parser = _make_parser(nougat_available=True, remote_urls=["http://n:8000"])
        doc = parser._parse_via_remote("test.pdf", "doc_001")
        assert doc.metadata.ai_hints["parser"] == "nougat_remote"

    @patch("app.pipeline.parsing.nougat_parser.requests.post")
    @patch("app.pipeline.parsing.nougat_parser.time.sleep", return_value=None)
    @patch("builtins.open")
    def test_remote_sets_processing_stage(self, mock_open, mock_sleep, mock_post):
        mock_open.return_value.__enter__.return_value = MagicMock()
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"markdown": "Hello world"}
        mock_post.return_value = mock_resp

        parser = _make_parser(nougat_available=True, remote_urls=["http://n:8000"])
        doc = parser._parse_via_remote("test.pdf", "doc_001")
        assert len(doc.processing_history) == 1
        assert doc.processing_history[0].stage_name == "parsing"
        assert doc.processing_history[0].status == "success"

    @patch("app.pipeline.parsing.nougat_parser.requests.post")
    @patch("app.pipeline.parsing.nougat_parser.time.sleep", return_value=None)
    @patch("builtins.open")
    def test_remote_retries_backoff_respected(self, mock_open, mock_sleep, mock_post):
        mock_open.return_value.__enter__.return_value = MagicMock()
        resp = MagicMock(status_code=503)
        mock_post.return_value = resp

        parser = _make_parser(nougat_available=True, remote_urls=["http://n:8000"])
        result = parser._parse_via_remote("test.pdf", "doc_001")
        assert result is None
        # Should have called sleep between retries
        assert mock_sleep.call_count >= 2

    def test_parser_str_representation(self):
        parser = _make_parser(nougat_available=True)
        assert isinstance(parser.supports_format(".pdf"), bool)

    def test_transient_status_codes_defined(self):
        parser = _make_parser(nougat_available=True)
        assert 429 in parser.TRANSIENT_HTTP_STATUSES
        assert 503 in parser.TRANSIENT_HTTP_STATUSES
        assert 504 in parser.TRANSIENT_HTTP_STATUSES
        assert 408 in parser.TRANSIENT_HTTP_STATUSES
        assert 400 not in parser.TRANSIENT_HTTP_STATUSES

    def test_remote_parse_paths_default(self):
        parser = _make_parser(nougat_available=True, remote_urls=["http://n:8000"])
        assert "/parse" in parser.remote_parse_paths
        assert "/api/parse" in parser.remote_parse_paths

    @patch("app.pipeline.parsing.nougat_parser._pdf_to_images")
    @patch("app.pipeline.parsing.nougat_parser.torch")
    def test_local_sets_processing_stage(self, mock_torch, mock_pdf_to_images):
        mock_pdf_to_images.return_value = []
        mock_torch.no_grad.return_value = MagicMock(
            __enter__=MagicMock(), __exit__=MagicMock()
        )

        parser = _make_parser(nougat_available=True)
        _patch_processor_and_model(parser)

        doc = parser._parse_local("test.pdf", "doc_001")
        assert len(doc.processing_history) == 1
        assert doc.processing_history[0].status == "success"
        assert "local Nougat" in doc.processing_history[0].message
