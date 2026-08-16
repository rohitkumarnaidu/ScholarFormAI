# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Comprehensive tests targeting uncovered utility, middleware, and service files.
Covers exceptions, deprecation, id_generator, singleton, cleanup, serialization,
text_utils, security_headers, request_id, and logging_config.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from datetime import time as time_type
from enum import Enum
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID

import pytest

from app.exceptions import (
    AuthenticationError,
    DatabaseUnavailableError,
    DocumentNotFoundError,
    ExternalServiceError,
    FileStorageError,
    RateLimitExceededError,
)


class TestExceptions:
    def test_database_unavailable_default(self):
        e = DatabaseUnavailableError()
        assert str(e) == "Database is currently unavailable."

    def test_database_unavailable_custom(self):
        e = DatabaseUnavailableError("Custom DB error")
        assert str(e) == "Custom DB error"

    def test_document_not_found_with_id(self):
        e = DocumentNotFoundError("doc-123")
        assert e.doc_id == "doc-123"
        assert "doc-123" in str(e)

    def test_document_not_found_without_id(self):
        e = DocumentNotFoundError()
        assert e.doc_id is None

    def test_authentication_error(self):
        e = AuthenticationError("Invalid token")
        assert str(e) == "Invalid token"

    def test_rate_limit_exceeded(self):
        e = RateLimitExceededError("Too fast")
        assert "Too fast" in str(e)

    def test_file_storage_error(self):
        e = FileStorageError("Disk full")
        assert "Disk full" in str(e)

    def test_external_service_error_default(self):
        e = ExternalServiceError()
        assert "External service call failed." in str(e)

    def test_external_service_error_with_service(self):
        e = ExternalServiceError(service="GROBID")
        assert "GROBID" in str(e)
        assert e.service == "GROBID"


from app.routers.deprecation import (
    DEPRECATION_DATE,
    DeprecatedRoute,
    build_deprecation_headers,
    normalize_path,
)


class TestDeprecation:
    def test_build_deprecation_headers_without_successor(self):
        headers = build_deprecation_headers(None)
        assert headers["Deprecation"] == "true"
        assert headers["Sunset"] == DEPRECATION_DATE
        assert "Link" not in headers

    def test_build_deprecation_headers_with_successor(self):
        headers = build_deprecation_headers("/api/v2/endpoint")
        assert headers["Deprecation"] == "true"
        assert headers["Link"] == '</api/v2/endpoint>; rel="successor-version"'

    def test_normalize_path_removes_trailing_slash(self):
        assert normalize_path("/api/v1/") == "/api/v1"

    def test_normalize_path_root_unchanged(self):
        assert normalize_path("/") == "/"

    def test_normalize_path_no_slash(self):
        assert normalize_path("/api/v1") == "/api/v1"

    def test_deprecated_route_methods(self):
        route = DeprecatedRoute(
            path="/test",
            endpoint=lambda: None,
            methods={"GET"},
        )
        headers = build_deprecation_headers(route._successor_path())
        assert headers["Deprecation"] == "true"


from app.utils.id_generator import (
    generate_block_id,
    generate_document_id,
    generate_equation_id,
    generate_figure_id,
    generate_reference_id,
    generate_table_id,
)


class TestIdGenerator:
    def test_generate_block_id(self):
        assert generate_block_id(0) == "blk_000"
        assert generate_block_id(1) == "blk_001"
        assert generate_block_id(42) == "blk_042"
        assert generate_block_id(999) == "blk_999"

    def test_generate_figure_id(self):
        assert generate_figure_id(0) == "fig_000"
        assert generate_figure_id(12) == "fig_012"

    def test_generate_table_id(self):
        assert generate_table_id(0) == "tbl_000"
        assert generate_table_id(5) == "tbl_005"

    def test_generate_reference_id(self):
        assert generate_reference_id(0) == "ref_000"
        assert generate_reference_id(23) == "ref_023"

    def test_generate_equation_id(self):
        assert generate_equation_id(0) == "eqn_000"
        assert generate_equation_id(21) == "eqn_021"

    def test_generate_document_id_format(self):
        doc_id = generate_document_id()
        assert doc_id.startswith("doc_")

    def test_generate_document_id_custom_prefix(self):
        doc_id = generate_document_id(prefix="manuscript")
        assert doc_id.startswith("manuscript_")

    def test_generate_document_id_timestamp(self):
        doc_id = generate_document_id()
        parts = doc_id.split("_")
        assert len(parts) == 3


from app.utils.singleton import get_or_create, get_or_create_catching, get_or_create_safe, resolve_optional_callable


class TestSingleton:
    def test_get_or_create_creates_new(self):
        factory = Mock(return_value="new_instance")
        result = get_or_create(None, factory)
        assert result == "new_instance"
        factory.assert_called_once()

    def test_get_or_create_returns_existing(self):
        factory = Mock()
        result = get_or_create("existing", factory)
        assert result == "existing"
        factory.assert_not_called()

    def test_get_or_create_safe_creates_new(self):
        factory = Mock(return_value="created")
        result = get_or_create_safe(None, factory, logger=logging.getLogger("test"), name="test")
        assert result == "created"

    def test_get_or_create_safe_handles_exception(self):
        factory = Mock(side_effect=ValueError("fail"))
        result = get_or_create_safe(None, factory, logger=logging.getLogger("test"), name="test")
        assert result is None

    def test_get_or_create_safe_returns_existing(self):
        result = get_or_create_safe("existing", Mock(), logger=Mock(), name="test")
        assert result == "existing"

    def test_get_or_create_catching_creates_new(self):
        factory = Mock(return_value="ok")
        result = get_or_create_catching(None, factory, exceptions=(ValueError,))
        assert result == "ok"

    def test_get_or_create_catching_swallows_exception(self):
        factory = Mock(side_effect=ValueError("bad"))
        result = get_or_create_catching(None, factory, exceptions=(ValueError,))
        assert result is None

    def test_get_or_create_catching_returns_existing(self):
        result = get_or_create_catching("existing", Mock(), exceptions=(ValueError,))
        assert result == "existing"

    def test_resolve_optional_callable_success(self):
        result = resolve_optional_callable("os", "getcwd")
        assert result is not None

    def test_resolve_optional_callable_failure(self):
        result = resolve_optional_callable("nonexistent_module", "nope")
        assert result is None


from app.utils.cleanup import cleanup_old_uploads


class TestCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_uploads_directory_not_found(self):
        async def break_sleep(_duration):
            raise KeyboardInterrupt()

        with patch("app.utils.cleanup.os.path.exists", return_value=False):
            with patch("app.utils.cleanup.asyncio.sleep", break_sleep):
                with pytest.raises(KeyboardInterrupt):
                    await cleanup_old_uploads()

    @pytest.mark.asyncio
    async def test_cleanup_uploads_exception_handling(self):
        async def break_sleep(_duration):
            raise KeyboardInterrupt()

        with patch("app.utils.cleanup.os.path.exists", side_effect=OSError("permission")):
            with patch("app.utils.cleanup.asyncio.sleep", break_sleep):
                with pytest.raises(KeyboardInterrupt):
                    await cleanup_old_uploads()


from app.utils.serialization import build_structured_data, safe_model_dump, sanitize_for_json


class MockEnum(Enum):
    VALUE_A = "a"
    VALUE_B = "b"


class MockModel:
    def __init__(self, data=None):
        self._data = data or {}
        self.blocks = []
        self.metadata = None
        self.references = []
        self.processing_history = []

    def model_dump(self, mode="python"):
        return self._data


class MockBlock:
    def __init__(self, block_type="text", text="hello", level=1, section_name="test"):
        self.block_type = block_type
        self.text = text
        self.level = level
        self.section_name = section_name
        self.metadata = {"heading_level": level}


class TestSerialization:
    def test_sanitize_dict(self):
        result = sanitize_for_json({"key": "value"})
        assert result == {"key": "value"}

    def test_sanitize_list(self):
        result = sanitize_for_json([1, 2, 3])
        assert result == [1, 2, 3]

    def test_sanitize_tuple(self):
        result = sanitize_for_json((1, 2, 3))
        assert result == [1, 2, 3]

    def test_sanitize_set(self):
        result = sanitize_for_json({3, 1, 2})
        assert sorted(result) == [1, 2, 3]

    def test_sanitize_bytes(self):
        result = sanitize_for_json(b"hello")
        assert result["encoding"] == "binary"
        assert result["size_bytes"] == 5
        assert result["omitted"] is True

    def test_sanitize_bytes_empty(self):
        result = sanitize_for_json(b"")
        assert result["preview_b64"] == ""

    def test_sanitize_datetime(self):
        dt = datetime(2026, 6, 15, 10, 30, 0, tzinfo=UTC)
        result = sanitize_for_json(dt)
        assert "2026-06-15T10:30:00" in result

    def test_sanitize_date(self):
        result = sanitize_for_json(date(2026, 6, 15))
        assert result == "2026-06-15"

    def test_sanitize_time(self):
        result = sanitize_for_json(time_type(10, 30, 0))
        assert "10:30:00" in result

    def test_sanitize_enum(self):
        result = sanitize_for_json(MockEnum.VALUE_A)
        assert result == "a"

    def test_sanitize_plain_value(self):
        assert sanitize_for_json(42) == 42
        assert sanitize_for_json("hello") == "hello"
        assert sanitize_for_json(None) is None

    def test_safe_model_dump_none(self):
        assert safe_model_dump(None) == {}

    def test_safe_model_dump_model(self):
        model = MockModel({"key": "val"})
        result = safe_model_dump(model)
        assert result == {"key": "val"}

    def test_safe_model_dump_dict(self):
        result = safe_model_dump({"a": 1})
        assert result == {"a": 1}

    def test_safe_model_dump_plain_value(self):
        result = safe_model_dump("hello")
        assert result == {"value": "hello"}

    def test_build_structured_data_basic(self):
        block = MockBlock()
        doc = MockModel()
        doc.blocks = [block]
        result = build_structured_data(doc)
        assert "sections" in result
        assert "blocks" in result
        assert "headings" in result
        assert result["sections"]["text"] == ["hello"]

    def test_build_structured_data_heading_block(self):
        block = MockBlock(block_type="heading_1", text="Title")
        doc = MockModel()
        doc.blocks = [block]
        result = build_structured_data(doc)
        assert len(result["headings"]) == 1
        assert result["headings"][0]["text"] == "Title"
        assert result["headings"][0]["level"] == 1

    def test_build_structured_data_partial(self):
        doc = MockModel()
        result = build_structured_data(doc, partial=True)
        assert result["partial"] is True

    def test_build_structured_data_empty_blocks(self):
        doc = MockModel()
        doc.blocks = [MockBlock(block_type=None)]
        result = build_structured_data(doc)
        assert result["sections"] == {}

    def test_normalize_block_type_via_structured(self):
        block = MockBlock(block_type="abstract_heading", text="Abstract")
        doc = MockModel()
        doc.blocks = [block]
        result = build_structured_data(doc)
        assert len(result["headings"]) == 1
        assert result["headings"][0]["section_name"] == "test"


from app.utils.text_utils import (
    clean_metadata_field,
    normalize_block_text,
    normalize_list_markers,
    normalize_table_cell_text,
    normalize_unicode,
    normalize_whitespace,
)


class TestTextUtils:
    def test_normalize_unicode_quotes(self):
        assert normalize_unicode("\u201cHello\u201d") == '"Hello"'

    def test_normalize_unicode_dashes(self):
        assert normalize_unicode("\u2014dash") == "--dash"

    def test_normalize_unicode_spaces(self):
        assert normalize_unicode("\u00a0nbsp") == " nbsp"

    def test_normalize_unicode_bullets(self):
        assert "\u2022" in normalize_unicode("\u2022")

    def test_normalize_whitespace_tabs(self):
        result = normalize_whitespace("hello\tworld")
        assert "\t" not in result

    def test_normalize_whitespace_collapse_spaces(self):
        result = normalize_whitespace("hello    world")
        assert "hello world" in result

    def test_normalize_whitespace_collapse_newlines(self):
        result = normalize_whitespace("a\n\n\n\nb", collapse_newlines=True)
        assert result == "a\n\nb"

    def test_normalize_whitespace_preserves_single_newline(self):
        result = normalize_whitespace("a\nb")
        assert "a\nb" in result

    def test_normalize_list_markers_bullet(self):
        result = normalize_list_markers("\u2023 text")
        assert result.startswith("\u2022")

    def test_normalize_list_markers_no_bullet(self):
        result = normalize_list_markers("plain text")
        assert result == "plain text"

    def test_clean_metadata_field_basic(self):
        result = clean_metadata_field("  Hello  World  ")
        assert result == "Hello World"

    def test_clean_metadata_field_empty(self):
        assert clean_metadata_field("") == ""
        assert clean_metadata_field(None) is None

    def test_clean_metadata_field_control_chars(self):
        result = clean_metadata_field("Hello\x00World")
        assert result == "HelloWorld"

    def test_normalize_block_text_none(self):
        assert normalize_block_text(None) == ""

    def test_normalize_block_text_basic(self):
        result = normalize_block_text("  Hello  ")
        assert result.strip() == "Hello"

    def test_normalize_block_text_not_empty_ok(self):
        result = normalize_block_text("", is_empty_ok=False)
        assert result == ""

    def test_normalize_table_cell_text(self):
        result = normalize_table_cell_text("  Hello\nWorld  ")
        assert result == "Hello World"

    def test_normalize_table_cell_text_empty(self):
        assert normalize_table_cell_text("") == ""
        assert normalize_table_cell_text(None) == ""


from app.middleware.security_headers import MaxBodySizeMiddleware, SecurityHeadersMiddleware


class TestSecurityHeadersMiddleware:
    @pytest.mark.asyncio
    async def test_security_headers_added(self):
        request = MagicMock()
        request.url.path = "/api/v1/test"
        response = MagicMock()
        response.headers = {}
        call_next = AsyncMock(return_value=response)

        middleware = SecurityHeadersMiddleware.__new__(SecurityHeadersMiddleware)
        middleware.app = MagicMock()

        await middleware.dispatch(request, call_next)
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    @pytest.mark.asyncio
    async def test_security_headers_docs_route(self):
        request = MagicMock()
        request.url.path = "/docs"
        response = MagicMock()
        response.headers = {}
        call_next = AsyncMock(return_value=response)

        middleware = SecurityHeadersMiddleware.__new__(SecurityHeadersMiddleware)
        middleware.app = MagicMock()

        await middleware.dispatch(request, call_next)
        csp = response.headers["Content-Security-Policy"]
        assert "cdn.jsdelivr.net" in csp


class TestMaxBodySizeMiddleware:
    @pytest.mark.asyncio
    async def test_body_within_limit(self):
        send = AsyncMock()
        receive = AsyncMock()
        scope = {
            "type": "http",
            "headers": [(b"content-length", b"1000")],
        }
        app = AsyncMock()
        middleware = MaxBodySizeMiddleware(app, max_size=5000)
        await middleware(scope, receive, send)
        app.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_body_exceeds_limit(self):
        send = AsyncMock()
        receive = AsyncMock()
        scope = {
            "type": "http",
            "headers": [(b"content-length", b"100000000")],
        }
        middleware = MaxBodySizeMiddleware(Mock(), max_size=5000)
        await middleware(scope, receive, send)
        send.assert_awaited()

    @pytest.mark.asyncio
    async def test_non_http_scope_passthrough(self):
        send = AsyncMock()
        receive = AsyncMock()
        scope = {"type": "websocket"}
        app = AsyncMock()
        middleware = MaxBodySizeMiddleware(app)
        await middleware(scope, receive, send)
        app.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalid_content_length_ignored(self):
        send = AsyncMock()
        receive = AsyncMock()
        scope = {
            "type": "http",
            "headers": [(b"content-length", b"not-a-number")],
        }
        app = AsyncMock()
        middleware = MaxBodySizeMiddleware(app)
        await middleware(scope, receive, send)
        app.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_content_length_passthrough(self):
        send = AsyncMock()
        receive = AsyncMock()
        scope = {"type": "http", "headers": []}
        app = AsyncMock()
        middleware = MaxBodySizeMiddleware(app)
        await middleware(scope, receive, send)
        app.assert_awaited_once()


from app.middleware.request_id import RequestIdMiddleware, _should_log_idempotency, get_request_id


class TestRequestIdMiddleware:
    @pytest.mark.asyncio
    async def test_non_http_passthrough(self):
        send = AsyncMock()
        receive = AsyncMock()
        scope = {"type": "websocket"}
        app = AsyncMock()
        middleware = RequestIdMiddleware(app)
        await middleware(scope, receive, send)
        app.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_log_idempotency(self):
        assert _should_log_idempotency("/api/v1/upload") is True
        assert _should_log_idempotency("/api/v1/health") is False

    def test_get_request_id_from_state(self):
        request = MagicMock()
        request.state.request_id = "test-id"
        result = get_request_id(request)
        assert result == "test-id"

    def test_get_request_id_generates_new(self):
        request = MagicMock()
        request.state.request_id = None
        result = get_request_id(request)
        assert UUID(result) is not None


from app.config.logging_config import setup_logging


class TestLoggingConfig:
    def test_setup_logging_idempotent(self):
        logger = setup_logging()
        assert logger is not None

    def test_second_call_returns_same_logger(self):
        logger1 = setup_logging()
        logger2 = setup_logging()
        assert logger1 is logger2


from app.middleware.feature_flags import FeatureFlagMiddleware


class TestFeatureFlagMiddleware:
    @pytest.mark.asyncio
    async def test_non_http_passthrough(self):
        send = AsyncMock()
        receive = AsyncMock()
        scope = {"type": "websocket"}
        app = AsyncMock()
        middleware = FeatureFlagMiddleware.__new__(FeatureFlagMiddleware)
        middleware.app = app
        middleware.enabled = ["flag_a", "flag_b"]
        await middleware(scope, receive, send)
        app.assert_awaited_once()


from app.services.model_store import ModelStore


class TestModelStore:
    def test_model_store_singleton(self):
        s1 = ModelStore()
        s2 = ModelStore()
        assert s1 is s2

    def test_get_model_missing(self):
        store = ModelStore()
        result = store.get_model("nonexistent")
        assert result is None

    def test_set_and_get_model(self):
        store = ModelStore()
        store.set_model("test_model", {"data": 42})
        result = store.get_model("test_model")
        assert result == {"data": 42}

    def test_is_loaded_true(self):
        store = ModelStore()
        store.set_model("loaded_key", "value")
        assert store.is_loaded("loaded_key") is True

    def test_is_loaded_false(self):
        store = ModelStore()
        assert store.is_loaded("missing_key") is False
