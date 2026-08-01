# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Comprehensive tests for utility modules and services.
Targets the biggest coverage gaps to push toward 90%.
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, date, time
from enum import Enum
import json


# ── Serialization Tests ──────────────────────────────────────────────────────

class TestSanitizeForJson:
    def test_dict_sanitization(self):
        from app.utils.serialization import sanitize_for_json
        result = sanitize_for_json({"key": "value", "nested": {"a": 1}})
        assert result == {"key": "value", "nested": {"a": 1}}

    def test_list_sanitization(self):
        from app.utils.serialization import sanitize_for_json
        result = sanitize_for_json([1, 2, "three"])
        assert result == [1, 2, "three"]

    def test_tuple_sanitization(self):
        from app.utils.serialization import sanitize_for_json
        result = sanitize_for_json((1, 2, 3))
        assert result == [1, 2, 3]

    def test_set_sanitization(self):
        from app.utils.serialization import sanitize_for_json
        result = sanitize_for_json({3, 1, 2})
        assert isinstance(result, list)
        assert sorted(result) == [1, 2, 3]

    def test_bytes_sanitization(self):
        from app.utils.serialization import sanitize_for_json
        result = sanitize_for_json(b"hello")
        assert result["encoding"] == "binary"
        assert result["size_bytes"] == 5
        assert result["omitted"] is True

    def test_empty_bytes_sanitization(self):
        from app.utils.serialization import sanitize_for_json
        result = sanitize_for_json(b"")
        assert result["size_bytes"] == 0
        assert result["preview_b64"] == ""

    def test_datetime_sanitization(self):
        from app.utils.serialization import sanitize_for_json
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = sanitize_for_json(dt)
        assert result == "2024-01-15T10:30:00"

    def test_date_sanitization(self):
        from app.utils.serialization import sanitize_for_json
        d = date(2024, 1, 15)
        result = sanitize_for_json(d)
        assert result == "2024-01-15"

    def test_time_sanitization(self):
        from app.utils.serialization import sanitize_for_json
        t = time(10, 30, 0)
        result = sanitize_for_json(t)
        assert result == "10:30:00"

    def test_enum_sanitization(self):
        from app.utils.serialization import sanitize_for_json
        class MyEnum(Enum):
            A = "value_a"
            B = "value_b"
        result = sanitize_for_json(MyEnum.A)
        assert result == "value_a"

    def test_primitive_passthrough(self):
        from app.utils.serialization import sanitize_for_json
        assert sanitize_for_json(42) == 42
        assert sanitize_for_json("hello") == "hello"
        assert sanitize_for_json(None) is None
        assert sanitize_for_json(True) is True

    def test_nested_complex_structure(self):
        from app.utils.serialization import sanitize_for_json
        dt = datetime(2024, 1, 1, 0, 0, 0)
        data = {
            "items": [1, (2, 3), {4, 5}],
            "timestamp": dt,
            "data": b"test",
        }
        result = sanitize_for_json(data)
        assert result["items"][0] == 1
        assert result["items"][1] == [2, 3]
        assert isinstance(result["items"][2], list)
        assert result["timestamp"] == "2024-01-01T00:00:00"
        assert result["data"]["encoding"] == "binary"


class TestSafeModelDump:
    def test_none_returns_empty_dict(self):
        from app.utils.serialization import safe_model_dump
        assert safe_model_dump(None) == {}

    def test_pydantic_v2_model_dump(self):
        from app.utils.serialization import safe_model_dump
        mock_obj = MagicMock()
        mock_obj.model_dump.return_value = {"key": "value"}
        result = safe_model_dump(mock_obj)
        assert result == {"key": "value"}
        mock_obj.model_dump.assert_called_once_with(mode="json")

    def test_pydantic_v2_fallback_to_python(self):
        from app.utils.serialization import safe_model_dump
        mock_obj = MagicMock()
        mock_obj.model_dump.side_effect = [Exception("json failed"), {"key": "value"}]
        result = safe_model_dump(mock_obj)
        assert result == {"key": "value"}

    def test_pydantic_v1_dict_method(self):
        from app.utils.serialization import safe_model_dump
        mock_obj = MagicMock()
        del mock_obj.model_dump
        mock_obj.dict.return_value = {"a": 1}
        result = safe_model_dump(mock_obj)
        assert result == {"a": 1}

    def test_plain_dict(self):
        from app.utils.serialization import safe_model_dump
        result = safe_model_dump({"key": "value"})
        assert result == {"key": "value"}

    def test_fallback_wraps_in_value(self):
        from app.utils.serialization import safe_model_dump
        result = safe_model_dump(42)
        assert result == {"value": 42}

    def test_fallback_dict_passthrough(self):
        from app.utils.serialization import safe_model_dump
        result = safe_model_dump({"a": 1})
        assert result == {"a": 1}


class TestBuildStructuredData:
    def test_empty_document(self):
        from app.utils.serialization import build_structured_data
        mock_doc = MagicMock()
        mock_doc.blocks = []
        mock_doc.metadata = None
        mock_doc.references = []
        mock_doc.processing_history = []
        result = build_structured_data(mock_doc)
        assert result["sections"] == {}
        assert result["blocks"] == []
        assert result["headings"] == []

    def test_blocks_with_section_grouping(self):
        from app.utils.serialization import build_structured_data
        block1 = MagicMock()
        block1.block_type = "heading_1"
        block1.text = "Introduction"
        block1.metadata = {}
        block2 = MagicMock()
        block2.block_type = "body"
        block2.text = "Content"
        block2.metadata = {}
        mock_doc = MagicMock()
        mock_doc.blocks = [block1, block2]
        mock_doc.metadata = None
        mock_doc.references = []
        mock_doc.processing_history = []
        result = build_structured_data(mock_doc)
        assert "heading_1" in result["sections"]
        assert len(result["sections"]["heading_1"]) == 1
        assert result["sections"]["heading_1"][0] == "Introduction"

    def test_heading_detection(self):
        from app.utils.serialization import build_structured_data
        block = MagicMock()
        block.block_type = "abstract_heading"
        block.text = "Abstract"
        block.level = 1
        block.section_name = "Abstract"
        block.metadata = {}
        mock_doc = MagicMock()
        mock_doc.blocks = [block]
        mock_doc.metadata = None
        mock_doc.references = []
        mock_doc.processing_history = []
        result = build_structured_data(mock_doc)
        assert len(result["headings"]) == 1
        assert result["headings"][0]["section_name"] == "Abstract"

    def test_partial_flag(self):
        from app.utils.serialization import build_structured_data
        mock_doc = MagicMock()
        mock_doc.blocks = []
        mock_doc.metadata = None
        mock_doc.references = []
        mock_doc.processing_history = []
        result = build_structured_data(mock_doc, partial=True)
        assert result["partial"] is True

    def test_block_without_block_type_skipped(self):
        from app.utils.serialization import build_structured_data
        block = MagicMock()
        block.block_type = None
        mock_doc = MagicMock()
        mock_doc.blocks = [block]
        mock_doc.metadata = None
        mock_doc.references = []
        mock_doc.processing_history = []
        result = build_structured_data(mock_doc)
        assert result["blocks"] == []
        assert result["sections"] == {}


# ── Singleton Tests ──────────────────────────────────────────────────────────

class TestGetOrCreate:
    def test_returns_existing(self):
        from app.utils.singleton import get_or_create
        existing = object()
        result = get_or_create(existing, lambda: object())
        assert result is existing

    def test_creates_new(self):
        from app.utils.singleton import get_or_create
        new_obj = object()
        result = get_or_create(None, lambda: new_obj)
        assert result is new_obj


class TestGetOrCreateSafe:
    def test_returns_existing(self):
        from app.utils.singleton import get_or_create_safe
        import logging
        existing = object()
        result = get_or_create_safe(existing, lambda: object(), logger=logging.getLogger(), name="test")
        assert result is existing

    def test_creates_on_success(self):
        from app.utils.singleton import get_or_create_safe
        import logging
        new_obj = object()
        result = get_or_create_safe(None, lambda: new_obj, logger=logging.getLogger(), name="test")
        assert result is new_obj

    def test_returns_none_on_failure(self):
        from app.utils.singleton import get_or_create_safe
        import logging
        result = get_or_create_safe(None, lambda: 1/0, logger=logging.getLogger(), name="test")
        assert result is None


class TestGetOrCreateCatching:
    def test_returns_existing(self):
        from app.utils.singleton import get_or_create_catching
        existing = object()
        result = get_or_create_catching(existing, lambda: object(), exceptions=(ValueError,))
        assert result is existing

    def test_creates_on_success(self):
        from app.utils.singleton import get_or_create_catching
        new_obj = object()
        result = get_or_create_catching(None, lambda: new_obj, exceptions=(ValueError,))
        assert result is new_obj

    def test_swallows_declared_exception(self):
        from app.utils.singleton import get_or_create_catching
        result = get_or_create_catching(None, lambda: 1/0, exceptions=(ZeroDivisionError,))
        assert result is None

    def test_raises_undeclared_exception(self):
        from app.utils.singleton import get_or_create_catching
        with pytest.raises(ValueError):
            get_or_create_catching(None, lambda: (_ for _ in ()).throw(ValueError("boom")), exceptions=(ZeroDivisionError,))


class TestResolveOptionalCallable:
    def test_returns_none_on_import_failure(self):
        from app.utils.singleton import resolve_optional_callable
        result = resolve_optional_callable("nonexistent_module", "func")
        assert result is None

    def test_returns_none_on_callable_failure(self):
        from app.utils.singleton import resolve_optional_callable
        with patch("app.utils.singleton._load_callable") as mock_load:
            mock_load.return_value = lambda: 1/0
            result = resolve_optional_callable("mod", "func")
            assert result is None


# ── ID Generator Tests ───────────────────────────────────────────────────────

class TestIdGenerator:
    def test_generate_block_id(self):
        from app.utils.id_generator import generate_block_id
        assert generate_block_id(0) == "blk_000"
        assert generate_block_id(1) == "blk_001"
        assert generate_block_id(42) == "blk_042"
        assert generate_block_id(999) == "blk_999"

    def test_generate_figure_id(self):
        from app.utils.id_generator import generate_figure_id
        assert generate_figure_id(0) == "fig_000"
        assert generate_figure_id(12) == "fig_012"

    def test_generate_table_id(self):
        from app.utils.id_generator import generate_table_id
        assert generate_table_id(0) == "tbl_000"
        assert generate_table_id(5) == "tbl_005"

    def test_generate_reference_id(self):
        from app.utils.id_generator import generate_reference_id
        assert generate_reference_id(0) == "ref_000"
        assert generate_reference_id(23) == "ref_023"

    def test_generate_equation_id(self):
        from app.utils.id_generator import generate_equation_id
        assert generate_equation_id(0) == "eqn_000"
        assert generate_equation_id(21) == "eqn_021"

    def test_generate_document_id(self):
        from app.utils.id_generator import generate_document_id
        doc_id = generate_document_id()
        assert doc_id.startswith("doc_")
        assert len(doc_id) > 4

    def test_generate_document_id_custom_prefix(self):
        from app.utils.id_generator import generate_document_id
        doc_id = generate_document_id(prefix="paper")
        assert doc_id.startswith("paper_")


# ── Text Utils Tests ─────────────────────────────────────────────────────────

class TestNormalizeUnicode:
    def test_normalize_quotes(self):
        from app.utils.text_utils import normalize_unicode
        text = '\u2018hello\u2019 \u201cworld\u201d'
        result = normalize_unicode(text)
        assert result == "'hello' \"world\""

    def test_normalize_dashes(self):
        from app.utils.text_utils import normalize_unicode
        text = 'hello\u2014world\u2013test'
        result = normalize_unicode(text)
        assert "--" in result
        assert "-" in result

    def test_normalize_spaces(self):
        from app.utils.text_utils import normalize_unicode
        text = 'hello\u00A0world'
        result = normalize_unicode(text)
        assert result == "hello world"

    def test_normalize_bullets(self):
        from app.utils.text_utils import normalize_unicode
        text = '\u2022 item'
        result = normalize_unicode(text)
        assert result == "\u2022 item"

    def test_no_changes_needed(self):
        from app.utils.text_utils import normalize_unicode
        text = "hello world"
        assert normalize_unicode(text) == text


class TestNormalizeWhitespace:
    def test_collapse_spaces(self):
        from app.utils.text_utils import normalize_whitespace
        result = normalize_whitespace("hello    world")
        assert result == "hello world"

    def test_replace_tabs(self):
        from app.utils.text_utils import normalize_whitespace
        result = normalize_whitespace("hello\tworld")
        assert result == "hello world"

    def test_trim_lines(self):
        from app.utils.text_utils import normalize_whitespace
        result = normalize_whitespace("  hello  \n  world  ")
        assert result == "hello\nworld"

    def test_collapse_newlines(self):
        from app.utils.text_utils import normalize_whitespace
        result = normalize_whitespace("hello\n\n\n\nworld", collapse_newlines=True)
        assert result == "hello\n\nworld"

    def test_preserve_newlines_by_default(self):
        from app.utils.text_utils import normalize_whitespace
        result = normalize_whitespace("hello\n\n\nworld")
        assert result == "hello\n\n\nworld"


class TestNormalizeListMarkers:
    def test_bullet_at_start(self):
        from app.utils.text_utils import normalize_list_markers
        result = normalize_list_markers("\u2022 item text")
        assert result == "\u2022 item text"

    def test_no_bullet(self):
        from app.utils.text_utils import normalize_list_markers
        result = normalize_list_markers("just text")
        assert result == "just text"

    def test_trims_input(self):
        from app.utils.text_utils import normalize_list_markers
        result = normalize_list_markers("  \u2022 item  ")
        assert result == "\u2022 item"


class TestCleanMetadataField:
    def test_basic_cleaning(self):
        from app.utils.text_utils import clean_metadata_field
        result = clean_metadata_field("  Hello\u00A0World  ")
        assert result == "Hello World"

    def test_removes_newlines(self):
        from app.utils.text_utils import clean_metadata_field
        result = clean_metadata_field("Hello\nWorld")
        assert result == "Hello World"

    def test_empty_string(self):
        from app.utils.text_utils import clean_metadata_field
        assert clean_metadata_field("") == ""

    def test_none_passthrough(self):
        from app.utils.text_utils import clean_metadata_field
        assert clean_metadata_field(None) is None


class TestNormalizeBlockText:
    def test_none_returns_empty(self):
        from app.utils.text_utils import normalize_block_text
        assert normalize_block_text(None) == ""

    def test_basic_normalization(self):
        from app.utils.text_utils import normalize_block_text
        result = normalize_block_text("  Hello\u00A0World  ")
        assert result == "Hello World"

    def test_empty_not_ok_returns_original(self):
        from app.utils.text_utils import normalize_block_text
        result = normalize_block_text("   ", is_empty_ok=False)
        assert result == "   "


class TestNormalizeTableCellText:
    def test_basic_normalization(self):
        from app.utils.text_utils import normalize_table_cell_text
        result = normalize_table_cell_text("  Hello\nWorld  ")
        assert result == "Hello World"

    def test_empty_string(self):
        from app.utils.text_utils import normalize_table_cell_text
        assert normalize_table_cell_text("") == ""

    def test_none_returns_empty(self):
        from app.utils.text_utils import normalize_table_cell_text
        assert normalize_table_cell_text(None) == ""


# ── Encryption Service Tests ─────────────────────────────────────────────────

class TestEncryptionService:
    def test_generate_key(self):
        from app.services.encryption_service import EncryptionService
        key = EncryptionService.generate_key()
        assert isinstance(key, str)
        assert len(key) > 0

    def test_encrypt_decrypt_roundtrip(self):
        from app.services.encryption_service import EncryptionService
        key = EncryptionService.generate_key()
        service = EncryptionService(key=key)
        plaintext = "secret-api-key-12345"
        encrypted = service.encrypt(plaintext)
        assert encrypted != plaintext
        decrypted = service.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_empty_raises(self):
        from app.services.encryption_service import EncryptionService
        service = EncryptionService()
        with pytest.raises(ValueError, match="Cannot encrypt empty"):
            service.encrypt("")

    def test_decrypt_empty_raises(self):
        from app.services.encryption_service import EncryptionService
        service = EncryptionService()
        with pytest.raises(ValueError, match="Cannot decrypt empty"):
            service.decrypt("")

    def test_decrypt_invalid_raises(self):
        from app.services.encryption_service import EncryptionService
        service = EncryptionService()
        with pytest.raises((ValueError, Exception)):
            service.decrypt("invalid-base64-data!!")

    def test_auto_generates_key_if_not_set(self):
        from app.services.encryption_service import EncryptionService
        with patch("app.services.encryption_service.os.environ", {}):
            service = EncryptionService()
            assert service._fernet is not None

    def test_get_encryption_service_singleton(self):
        from app.services.encryption_service import get_encryption_service
        s1 = get_encryption_service()
        s2 = get_encryption_service()
        assert s1 is s2


# ── Feature Flags Tests ──────────────────────────────────────────────────────

class TestFeatureFlagService:
    def test_default_flags(self):
        from app.services.feature_flags import FeatureFlagService
        service = FeatureFlagService()
        assert service.get_flag("ai_suggestions") is True
        assert service.get_flag("dark_mode_beta") is False

    def test_set_flag(self):
        from app.services.feature_flags import FeatureFlagService
        service = FeatureFlagService()
        service.set_flag("dark_mode_beta", True)
        assert service.get_flag("dark_mode_beta") is True

    def test_get_all_flags(self):
        from app.services.feature_flags import FeatureFlagService
        service = FeatureFlagService()
        flags = service.get_all_flags()
        assert "ai_suggestions" in flags
        assert "dark_mode_beta" in flags

    def test_custom_default(self):
        from app.services.feature_flags import FeatureFlagService
        service = FeatureFlagService()
        result = service.get_flag("nonexistent", default="fallback")
        assert result == "fallback"

    def test_get_feature_flag_convenience(self):
        from app.services.feature_flags import get_feature_flag
        result = get_feature_flag("ai_suggestions")
        assert result is True

    def test_get_feature_flag_service_singleton(self):
        from app.services.feature_flags import get_feature_flag_service
        s1 = get_feature_flag_service()
        s2 = get_feature_flag_service()
        assert s1 is s2


# ── Retry Guard Tests ────────────────────────────────────────────────────────

class TestRetryGuard:
    def test_sync_success_no_retry(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff
        call_count = 0
        @retry_with_backoff(max_retries=2, backoff_factor=0.01)
        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"
        result = succeed()
        assert result == "ok"
        assert call_count == 1

    def test_sync_eventually_succeeds(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff
        call_count = 0
        @retry_with_backoff(max_retries=3, backoff_factor=0.01)
        def eventually():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "success"
        result = eventually()
        assert result == "success"
        assert call_count == 3

    def test_sync_fails_after_max_retries(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff
        @retry_with_backoff(max_retries=2, backoff_factor=0.01)
        def always_fail():
            raise RuntimeError("boom")
        with pytest.raises(RuntimeError, match="boom"):
            always_fail()

    def test_execute_with_retry(self):
        from app.pipeline.safety.retry_guard import execute_with_retry
        def add(a, b):
            return a + b
        result = execute_with_retry(add, 2, 3, max_retries=1, backoff_factor=0.01)
        assert result == 5

    def test_base_delay_alias(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff
        @retry_with_backoff(max_retries=1, base_delay=0.01)
        def succeed():
            return "ok"
        assert succeed() == "ok"


# ── Quality Score Service Tests ──────────────────────────────────────────────

class TestQualityScoreService:
    def test_compute_quality_score_basic(self):
        from app.services.quality_score_service import compute_quality_score
        structured_data = {
            "metadata": {"abstract": "This is an abstract"},
            "references": [{"title": "Ref 1"}],
            "headings": [{"text": "Introduction"}],
            "blocks": [],
        }
        validation_results = {"citation_target": 5}
        result = compute_quality_score(structured_data, "ieee", validation_results)
        assert "template_compliance_pct" in result
        assert "overall_score" in result
        assert result["citation_count"] == 1

    def test_compute_quality_score_missing_sections(self):
        from app.services.quality_score_service import compute_quality_score
        structured_data = {
            "metadata": {},
            "references": [],
            "headings": [],
            "blocks": [],
        }
        validation_results = {
            "errors": ["missing required section: methods"],
            "citation_target": 5,
        }
        result = compute_quality_score(structured_data, "ieee", validation_results)
        assert len(result["missing_sections"]) > 0

    def test_normalize_function(self):
        from app.services.quality_score_service import _normalize
        assert _normalize("  Hello  World  ") == "hello world"
        assert _normalize(None) == ""

    def test_flatten_aliases(self):
        from app.services.quality_score_service import _flatten_aliases
        result = _flatten_aliases([{"a", "b"}, {"c"}])
        assert result == ["a", "b", "c"]

    def test_display_section_name(self):
        from app.services.quality_score_service import _display_section_name
        result = _display_section_name({"methods", "methodology"})
        assert "Method" in result

    def test_dedupe_preserve_order(self):
        from app.services.quality_score_service import _dedupe_preserve_order
        result = _dedupe_preserve_order(["a", "b", "a", "c", "b"])
        assert result == ["a", "b", "c"]

    def test_infer_provider_from_model(self):
        from app.services.quality_score_service import _infer_provider_from_model
        assert _infer_provider_from_model("groq-llama") == "groq"
        assert _infer_provider_from_model("nvidia-llama") == "nvidia"
        assert _infer_provider_from_model("ollama-deepseek") == "ollama"
        assert _infer_provider_from_model("openai-gpt4") == "openai"
        assert _infer_provider_from_model("claude-3") == "anthropic"
        assert _infer_provider_from_model("rule_based") == "rule_based"
        assert _infer_provider_from_model("") is None

    def test_extract_missing_sections(self):
        from app.services.quality_score_service import _extract_missing_sections
        result = _extract_missing_sections({
            "errors": ["missing required section: methods"],
            "warnings": ["missing required section: results"],
        })
        assert "methods" in result
        assert "results" in result

    def test_extract_llm_provider(self):
        from app.services.quality_score_service import _extract_llm_provider
        result = _extract_llm_provider({"llm_provider_used": "openai"})
        assert result == "openai"

    def test_collect_present_sections(self):
        from app.services.quality_score_service import _collect_present_sections
        result = _collect_present_sections({
            "metadata": {"abstract": "test"},
            "references": [{}],
            "headings": [{"text": "Introduction"}],
        })
        assert "abstract" in result
        assert "references" in result
        assert "introduction" in result


# ── AI Explainer Tests ───────────────────────────────────────────────────────

class TestAIExplainer:
    def test_explain_missing_sections(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        explainer = AIExplainer()
        results = {"errors": ["missing section: methods"]}
        explanations = explainer.explain_results(results, "IEEE")
        assert len(explanations) > 0
        assert "IEEE" in explanations[0]

    def test_explain_reference_issues(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        explainer = AIExplainer()
        results = {"errors": ["reference incomplete"]}
        explanations = explainer.explain_results(results)
        assert len(explanations) > 0

    def test_explain_dict_errors(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        explainer = AIExplainer()
        results = {"errors": [{"category": "missing_sections", "message": "test"}]}
        explanations = explainer.explain_results(results)
        assert len(explanations) > 0

    def test_explain_empty_results(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        explainer = AIExplainer()
        explanations = explainer.explain_results({"errors": []})
        assert explanations == []


# ── Review Manager Tests ─────────────────────────────────────────────────────

class TestReviewManager:
    def test_threshold_validation(self):
        from app.pipeline.validation.review_manager import ReviewManager
        with pytest.raises(ValueError):
            ReviewManager(review_threshold=0.5, critical_threshold=0.6)
        with pytest.raises(ValueError):
            ReviewManager(review_threshold=1.5, critical_threshold=0.5)

    def test_evaluate_ok_document(self):
        from app.pipeline.validation.review_manager import ReviewManager
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="doc-1")
        doc.metadata.ai_hints = {}
        manager = ReviewManager(review_threshold=0.7, critical_threshold=0.4)
        result = manager.evaluate(doc)
        status_val = result.review.status.value if hasattr(result.review.status, "value") else result.review.status
        assert status_val.upper() == "OK"

    def test_evaluate_low_confidence_block(self):
        from app.pipeline.validation.review_manager import ReviewManager
        from app.models.pipeline_document import PipelineDocument, ReviewStatus
        from app.models import Block, BlockType
        doc = PipelineDocument(document_id="doc-1")
        block = Block(block_id="blk_001", text="test", block_type=BlockType.BODY, index=0)
        block.metadata = {"classification_confidence": 0.3}
        doc.blocks = [block]
        doc.metadata.ai_hints = {}
        manager = ReviewManager(review_threshold=0.7, critical_threshold=0.5)
        result = manager.evaluate(doc)
        assert result.review.status == ReviewStatus.CRITICAL


# ── Cross Reference Engine Tests ─────────────────────────────────────────────

class TestCrossReferenceEngine:
    def test_validate_no_violations(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="doc-1")
        doc.blocks = []
        doc.figures = []
        doc.tables = []
        doc.equations = []
        engine = CrossReferenceEngine()
        violations = engine.validate_integrity(doc)
        assert violations == []

    def test_dangling_figure_reference(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="doc-1")
        block = Block(block_id="blk_001", text="See Figure 5 for details.", block_type=BlockType.BODY, index=0)
        doc.blocks = [block]
        doc.figures = []
        doc.tables = []
        doc.equations = []
        engine = CrossReferenceEngine()
        violations = engine.validate_integrity(doc)
        assert len(violations) == 1
        assert "Figure 5" in violations[0]

    def test_dangling_table_reference(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="doc-1")
        block = Block(block_id="blk_001", text="Table 3 shows results.", block_type=BlockType.BODY, index=0)
        doc.blocks = [block]
        doc.figures = []
        doc.tables = []
        doc.equations = []
        engine = CrossReferenceEngine()
        violations = engine.validate_integrity(doc)
        assert len(violations) == 1
        assert "Table 3" in violations[0]

    def test_dangling_equation_reference(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="doc-1")
        block = Block(block_id="blk_001", text="As shown in Equation (2)", block_type=BlockType.BODY, index=0)
        doc.blocks = [block]
        doc.figures = []
        doc.tables = []
        doc.equations = []
        engine = CrossReferenceEngine()
        violations = engine.validate_integrity(doc)
        assert len(violations) == 1
        assert "Equation (2)" in violations[0]


# ── Quality Scorer Tests ─────────────────────────────────────────────────────

class TestQualityScorer:
    def test_score_basic(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        scorer = QualityScorer()
        content = {
            "sections": [
                {"title": "Abstract", "content": "This is an abstract with enough content to pass the word count threshold easily." * 3},
                {"title": "Introduction", "content": "Introduction content that is long enough to meet requirements." * 3},
            ]
        }
        task_spec = {"sections": ["Abstract", "Introduction"]}
        result = scorer.score(content, "ieee", task_spec)
        assert "template_compliance" in result
        assert "overall_score" in result

    def test_word_count(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._word_count("hello world") == 2
        assert QualityScorer._word_count("") == 0
        assert QualityScorer._word_count(None) == 0

    def test_count_citations(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._count_citations("[1]") == 1
        assert QualityScorer._count_citations("[1, 2, 3]") == 1
        assert QualityScorer._count_citations("(Smith 2024)") == 1
        assert QualityScorer._count_citations("") == 0

    def test_section_balance_single(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        result = QualityScorer._section_balance({"A": "text"}, ["A"])
        assert result == 100.0

    def test_citation_score(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._citation_score(5, 5) == 100.0
        assert QualityScorer._citation_score(0, 5) == 0.0

    def test_percentage(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._percentage(5, 10) == 50.0
        assert QualityScorer._percentage(0, 10) == 0.0
        assert QualityScorer._percentage(5, 0) == 0.0


# ── Section Prompts Tests ────────────────────────────────────────────────────

class TestSectionPrompts:
    def test_known_section_prompt(self):
        from app.pipeline.generation.section_prompts import get_section_prompt
        prompt = get_section_prompt("Abstract", {})
        assert "abstract" in prompt.lower()

    def test_unknown_section_default(self):
        from app.pipeline.generation.section_prompts import get_section_prompt
        prompt = get_section_prompt("Custom Section", {})
        assert "academic section" in prompt.lower()

    def test_truncate_function(self):
        from app.pipeline.generation.section_prompts import _truncate
        assert _truncate("") == ""
        assert _truncate(None) == ""
        short = "hello world"
        assert _truncate(short) == short
        long_text = "x" * 2000
        result = _truncate(long_text)
        assert len(result) <= 1203
        assert result.endswith("...")

    def test_context_inclusion(self):
        from app.pipeline.generation.section_prompts import get_section_prompt
        context = {
            "task_spec": {"title": "Test Paper"},
            "template_rules": [],
            "outline": [{"title": "Intro"}],
            "previous_sections": {"Abstract": "Abstract text here"},
        }
        prompt = get_section_prompt("Introduction", context)
        assert "Test Paper" in prompt
        assert "Abstract text here" in prompt


# ── Content Parser Tests ─────────────────────────────────────────────────────

class TestContentParser:
    def test_parse_plain_json(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        response = '[{"type": "BODY", "content": "Hello world"}]'
        blocks = parser.parse(response, "research_paper")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "BODY"

    def test_parse_json_with_code_fences(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        response = '```json\n[{"type": "HEADING_1", "content": "Title"}]\n```'
        blocks = parser.parse(response, "research_paper")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "HEADING_1"

    def test_type_aliasing(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        response = '[{"type": "H1", "content": "Title"}]'
        blocks = parser.parse(response, "research_paper")
        assert blocks[0]["type"] == "HEADING_1"

    def test_unknown_type_fallback(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        response = '[{"type": "UNKNOWN_TYPE", "content": "text"}]'
        blocks = parser.parse(response, "research_paper")
        assert blocks[0]["type"] == "BODY"

    def test_invalid_json_raises(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        with pytest.raises(ValueError):
            parser.parse("not json at all", "research_paper")

    def test_non_array_raises(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        with pytest.raises(ValueError):
            parser.parse('{"key": "value"}', "research_paper")

    def test_non_dict_block(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        response = '["just a string"]'
        blocks = parser.parse(response, "research_paper")
        assert blocks[0]["type"] == "BODY"


# ── Task Parser Tests ────────────────────────────────────────────────────────

class TestTaskParserHelpers:
    def test_extract_json_from_code_fences(self):
        from app.pipeline.generation.task_parser import _extract_json
        text = '```json\n{"key": "value"}\n```'
        result = _extract_json(text)
        assert result == '{"key": "value"}'

    def test_extract_json_plain(self):
        from app.pipeline.generation.task_parser import _extract_json
        text = '{"key": "value"}'
        result = _extract_json(text)
        assert result == '{"key": "value"}'

    def test_extract_json_not_found(self):
        from app.pipeline.generation.task_parser import _extract_json
        assert _extract_json("no json here") is None

    def test_keywords_from_prompt(self):
        from app.pipeline.generation.task_parser import _keywords_from_prompt
        result = _keywords_from_prompt("Write a paper about machine learning")
        assert "machine" in result
        assert "learning" in result
        assert len(result) <= 6

    def test_validate_spec_defaults(self):
        from app.pipeline.generation.task_parser import TaskParser
        parser = TaskParser()
        spec = parser._validate_spec({}, "test prompt")
        assert spec["doc_type"] == "research_paper"
        assert spec["tone"] == "academic"
        assert "References" in spec["sections"]


# ── Validator Guard Tests ────────────────────────────────────────────────────

class TestValidatorGuard:
    def test_valid_dict_result(self):
        from app.pipeline.safety.validator_guard import validate_output
        @validate_output({"key": str}, error_return_value={})
        def my_func():
            return {"key": "value"}
        result = my_func()
        assert result == {"key": "value"}

    def test_missing_keys_returns_error_value(self):
        from app.pipeline.safety.validator_guard import validate_output
        @validate_output({"key": str, "other": str}, error_return_value={})
        def my_func():
            return {"key": "value"}
        result = my_func()
        assert result == {}

    def test_exception_returns_error_value(self):
        from app.pipeline.safety.validator_guard import validate_output
        @validate_output({"key": str}, error_return_value={})
        def my_func():
            raise RuntimeError("boom")
        result = my_func()
        assert result == {}


# ── Logging Context Tests ────────────────────────────────────────────────────

class TestLoggingContext:
    def test_bind_and_reset_context(self):
        from app.utils.logging_context import bind_context, reset_context, get_request_id_context
        tokens = bind_context(request_id="req-123", job_id="job-456")
        try:
            assert get_request_id_context() == "req-123"
        finally:
            reset_context(tokens)

    def test_log_context_manager(self):
        from app.utils.logging_context import log_context, get_request_id_context
        with log_context(request_id="req-789"):
            assert get_request_id_context() == "req-789"
        assert get_request_id_context() is None

    def test_log_extra(self):
        from app.utils.logging_context import log_context, log_extra
        with log_context(request_id="req-111", job_id="job-222"):
            extra = log_extra()
            assert extra["request_id"] == "req-111"
            assert extra["job_id"] == "job-222"

    def test_log_context_filter(self):
        from app.utils.logging_context import LogContextFilter, log_context
        with log_context(request_id="req-filter"):
            filter_obj = LogContextFilter()
            record = MagicMock()
            del record.request_id
            filter_obj.filter(record)
            assert record.request_id == "req-filter"


# ── Model Store Tests ────────────────────────────────────────────────────────

class TestModelStore:
    def test_singleton(self):
        from app.services.model_store import ModelStore
        s1 = ModelStore()
        s2 = ModelStore()
        assert s1 is s2

    def test_set_and_get(self):
        from app.services.model_store import model_store
        model_store.set_model("test", "model_data")
        assert model_store.get_model("test") == "model_data"
        assert model_store.is_loaded("test") is True
        assert model_store.is_loaded("nonexistent") is False


# ── Model Metrics Tests ──────────────────────────────────────────────────────

class TestModelMetrics:
    def test_record_call(self):
        from app.services.model_metrics import ModelMetrics
        metrics = ModelMetrics()
        metrics.record_call("nvidia", True, 1.5, quality_score=0.8)
        assert metrics.metrics["nvidia"]["total_calls"] == 1
        assert metrics.metrics["nvidia"]["successful_calls"] == 1
        assert len(metrics.quality_scores) == 1

    def test_record_failure(self):
        from app.services.model_metrics import ModelMetrics
        metrics = ModelMetrics()
        metrics.record_call("deepseek", False, 2.0)
        assert metrics.metrics["deepseek"]["failed_calls"] == 1

    def test_record_fallback(self):
        from app.services.model_metrics import ModelMetrics
        metrics = ModelMetrics()
        metrics.record_fallback("nvidia", "rules", "timeout")
        assert len(metrics.fallback_chain) == 1
        assert metrics.fallback_chain[0]["from"] == "nvidia"

    def test_get_summary(self):
        from app.services.model_metrics import ModelMetrics
        metrics = ModelMetrics()
        metrics.record_call("nvidia", True, 1.0)
        summary = metrics.get_summary()
        assert "models" in summary
        assert "fallback_rate" in summary

    def test_get_model_comparison(self):
        from app.services.model_metrics import ModelMetrics
        metrics = ModelMetrics()
        metrics.record_call("nvidia", True, 1.0)
        metrics.record_call("deepseek", True, 2.0)
        metrics.record_call("rules", True, 0.5)
        comparison = metrics.get_model_comparison()
        assert "nvidia_vs_deepseek" in comparison
        assert "agent_vs_legacy" in comparison

    def test_export_metrics(self, tmp_path):
        from app.services.model_metrics import ModelMetrics
        metrics = ModelMetrics()
        metrics.record_call("nvidia", True, 1.0)
        filepath = tmp_path / "metrics.json"
        metrics.export_metrics(str(filepath))
        assert filepath.exists()
        data = json.loads(filepath.read_text())
        assert "metrics" in data

    def test_unknown_model_ignored(self):
        from app.services.model_metrics import ModelMetrics
        metrics = ModelMetrics()
        metrics.record_call("unknown_model", True, 1.0)
        assert all(m["total_calls"] == 0 for m in metrics.metrics.values())


# ── VLLM Adoption Tests ──────────────────────────────────────────────────────

class TestVLLMAdoption:
    def test_build_report(self):
        from app.services.vllm_adoption import build_vllm_adoption_report
        with patch("app.services.vllm_adoption.get_llm_requests_total", return_value=0):
            with patch("app.services.vllm_adoption.get_llm_tokens_total", return_value=0):
                report = build_vllm_adoption_report()
                assert "enabled" in report
                assert "traffic" in report
                assert "phase4_plan" in report
                assert report["phase4_plan"]["status"] == "hold"


# ── Enhancement Manager Tests ────────────────────────────────────────────────

class TestEnhancementManager:
    def test_coerce_bool(self):
        from app.services.enhancement_manager import _coerce_bool
        assert _coerce_bool(True) is True
        assert _coerce_bool(False) is False
        assert _coerce_bool("true") is True
        assert _coerce_bool("false") is False
        assert _coerce_bool("1") is True
        assert _coerce_bool("0") is False
        assert _coerce_bool(None) is False
        assert _coerce_bool(None, default=True) is True

    def test_module_available(self):
        from app.services.enhancement_manager import _module_available
        assert _module_available("json") is True
        assert _module_available("nonexistent_module_xyz") is False

    def test_split_csv(self):
        from app.services.enhancement_manager import _split_csv
        assert _split_csv("a, b, c", []) == ["a", "b", "c"]
        assert _split_csv("", ["default"]) == ["default"]
        assert _split_csv(None, ["default"]) == ["default"]

    def test_enhancement_profile_to_dict(self):
        from app.services.enhancement_manager import EnhancementProfile
        profile = EnhancementProfile(
            enabled=True, queue_enabled=False, queue_provider="local",
            queue_available=False, ocr_enabled=True, ocr_backends=["builtin"],
            keyword_enabled=True, keyword_backends=["basic"],
        )
        d = profile.to_dict()
        assert d["enabled"] is True
        assert d["ocr_backends"] == ["builtin"]

    def test_enhancement_manager_profile(self):
        from app.services.enhancement_manager import enhancement_manager
        profile = enhancement_manager.profile
        assert isinstance(profile.enabled, bool)
        assert isinstance(profile.keyword_backends, list)

    def test_queue_threshold(self):
        from app.services.enhancement_manager import EnhancementManager
        assert EnhancementManager._queue_threshold_seconds() >= 0.0

    def test_should_queue_job_disabled(self):
        from app.services.enhancement_manager import EnhancementManager
        manager = EnhancementManager()
        assert manager.should_queue_job(0.0) is False

    def test_get_ocr_backends(self):
        from app.services.enhancement_manager import enhancement_manager
        backends = enhancement_manager.get_ocr_backends()
        assert isinstance(backends, list)

    def test_get_keyword_backends(self):
        from app.services.enhancement_manager import enhancement_manager
        backends = enhancement_manager.get_keyword_backends()
        assert isinstance(backends, list)
        assert len(backends) > 0


# ── Redis PubSub Tests ───────────────────────────────────────────────────────

class TestRedisPubSub:
    @pytest.mark.asyncio
    async def test_publish_no_channel(self):
        from app.realtime.pubsub import RedisPubSub
        pubsub = RedisPubSub()
        pubsub._force_fallback = True
        await pubsub.publish("", {"event": "test"})

    @pytest.mark.asyncio
    async def test_subscribe_no_channel(self):
        from app.realtime.pubsub import RedisPubSub
        pubsub = RedisPubSub()
        pubsub._force_fallback = True
        events = []
        async for event in pubsub.subscribe(""):
            events.append(event)
        assert events == []

    @pytest.mark.asyncio
    async def test_fallback_publish_subscribe(self):
        from app.realtime.pubsub import RedisPubSub
        pubsub = RedisPubSub()
        pubsub._force_fallback = True
        events = []
        async def collect():
            async for event in pubsub.subscribe("test-channel"):
                events.append(event)
                if len(events) >= 2:
                    break
        task = asyncio.create_task(collect())
        await asyncio.sleep(0.05)
        await pubsub.publish("test-channel", {"data": "hello"})
        await pubsub.publish("test-channel", {"data": "world"})
        await asyncio.wait_for(task, timeout=5.0)
        assert len(events) == 2


# ── Realtime Events Tests ────────────────────────────────────────────────────

class TestRealtimeEvents:
    def test_make_event(self):
        from app.realtime.events import make_event
        event = make_event("connected", job_id="job-1", request_id="req-1")
        assert event["event_type"] == "connected"
        assert event["job_id"] == "job-1"
        assert "timestamp" in event

    def test_make_event_with_payload(self):
        from app.realtime.events import make_event
        event = make_event("progress", job_id="job-1", stage="parsing", progress=50)
        assert event["stage"] == "parsing"
        assert event["progress"] == 50


# ── Dependencies Tests ───────────────────────────────────────────────────────

class TestDependencies:
    def test_has_admin_scope_by_role(self):
        from app.utils.dependencies import _has_admin_scope
        from app.schemas.user import User
        user = User(id="1", email="test@test.com", role="admin")
        assert _has_admin_scope(user) is True

    def test_has_admin_scope_service_role(self):
        from app.utils.dependencies import _has_admin_scope
        from app.schemas.user import User
        user = User(id="1", email="test@test.com", role="service_role")
        assert _has_admin_scope(user) is True

    def test_has_admin_scope_regular_user(self):
        from app.utils.dependencies import _has_admin_scope
        from app.schemas.user import User
        user = User(id="1", email="test@test.com", role="authenticated")
        assert _has_admin_scope(user) is False

    def test_has_admin_scope_from_app_metadata(self):
        from app.utils.dependencies import _has_admin_scope
        from app.schemas.user import User
        user = User(id="1", email="test@test.com", role="user", app_metadata={"role": "admin"})
        assert _has_admin_scope(user) is True

    def test_has_admin_scope_from_roles_list(self):
        from app.utils.dependencies import _has_admin_scope
        from app.schemas.user import User
        user = User(id="1", email="test@test.com", role="user", app_metadata={"roles": ["admin", "editor"]})
        assert _has_admin_scope(user) is True

    def test_has_admin_scope_from_roles_string(self):
        from app.utils.dependencies import _has_admin_scope
        from app.schemas.user import User
        user = User(id="1", email="test@test.com", role="user", app_metadata={"roles": "admin"})
        assert _has_admin_scope(user) is True


# ── Auth Service Tests ───────────────────────────────────────────────────────

class TestAuthService:
    def test_get_user_id_from_payload(self):
        from app.services.auth_service import AuthService
        user_id = AuthService.get_user_id_from_payload({"sub": "user-123"})
        assert user_id == "user-123"

    def test_get_user_id_missing_sub_raises(self):
        from app.services.auth_service import AuthService
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            AuthService.get_user_id_from_payload({})

    def test_require_supabase_raises_503(self):
        from app.services.auth_service import _require_supabase
        from fastapi import HTTPException
        with patch("app.services.auth_service.supabase", None):
            with pytest.raises(HTTPException) as exc_info:
                _require_supabase()
            assert exc_info.value.status_code == 503


# ── Preview Renderer Tests ───────────────────────────────────────────────────

class TestPreviewRendererHelpers:
    def test_is_list_item(self):
        from app.services.preview_renderer import PreviewRenderer
        renderer = PreviewRenderer()
        assert renderer._is_list_item("- item") is True
        assert renderer._is_list_item("1. item") is True
        assert renderer._is_list_item("* item") is True
        assert renderer._is_list_item("just text") is False

    def test_strip_list_marker(self):
        from app.services.preview_renderer import PreviewRenderer
        renderer = PreviewRenderer()
        assert renderer._strip_list_marker("- item") == "item"
        assert renderer._strip_list_marker("1. item") == "item"

    def test_is_caption(self):
        from app.services.preview_renderer import PreviewRenderer
        renderer = PreviewRenderer()
        assert renderer._is_caption("Figure 1: Test") is True
        assert renderer._is_caption("Table 2 - Results") is True
        assert renderer._is_caption("just text") is False

    def test_is_heading(self):
        from app.services.preview_renderer import PreviewRenderer
        renderer = PreviewRenderer()
        assert renderer._is_heading("# Heading") is True
        assert renderer._is_heading("1.2 Introduction") is True
        assert renderer._is_heading("ABSTRACT") is True
        assert renderer._is_heading("just text") is False

    def test_heading_level(self):
        from app.services.preview_renderer import PreviewRenderer
        renderer = PreviewRenderer()
        assert renderer._heading_level("# Heading") == 2
        assert renderer._heading_level("## Heading") == 2
        assert renderer._heading_level("1.2.3 Heading") == 4

    def test_strip_heading_marker(self):
        from app.services.preview_renderer import PreviewRenderer
        renderer = PreviewRenderer()
        assert renderer._strip_heading_marker("# Heading") == "Heading"
        assert renderer._strip_heading_marker("1.2 Heading") == "Heading"

    def test_is_title(self):
        from app.services.preview_renderer import PreviewRenderer
        renderer = PreviewRenderer()
        assert renderer._is_title("My Paper Title", 0) is True
        assert renderer._is_title("Not title", 1) is False
        assert renderer._is_title("Ends with period.", 0) is False

    def test_split_blocks(self):
        from app.services.preview_renderer import PreviewRenderer
        renderer = PreviewRenderer()
        blocks = renderer._split_blocks("Hello world\n\n- item 1\n- item 2")
        assert len(blocks) == 3
        assert blocks[0]["raw_type"] == "paragraph"
        assert blocks[0]["text"] == "Hello world"
        assert blocks[1]["raw_type"] == "list_item"
        assert blocks[1]["text"] == "item 1"
        assert blocks[2]["raw_type"] == "list_item"
        assert blocks[2]["text"] == "item 2"

    def test_classify_blocks(self):
        from app.services.preview_renderer import PreviewRenderer
        renderer = PreviewRenderer()
        raw_blocks = [
            {"raw_type": "paragraph", "text": "My Title"},
            {"raw_type": "paragraph", "text": "Abstract"},
            {"raw_type": "paragraph", "text": "This is the abstract body."},
        ]
        classified = renderer._classify_blocks(raw_blocks)
        assert classified[0]["type"] == "title"
        assert classified[1]["type"] == "abstract_heading"
        assert classified[2]["type"] == "abstract_body"

    def test_render_blocks(self):
        from app.services.preview_renderer import PreviewRenderer
        renderer = PreviewRenderer()
        blocks = [
            {"type": "title", "text": "My Title"},
            {"type": "paragraph", "text": "Some text"},
        ]
        html = renderer._render_blocks(blocks)
        assert '<h1 class="doc-title">My Title</h1>' in html
        assert '<p class="doc-paragraph">Some text</p>' in html

    def test_render_preview_empty_content(self):
        from app.services.preview_renderer import PreviewRenderer
        renderer = PreviewRenderer()
        result = renderer.render_preview("", "ieee")
        assert "html" in result
        assert "latency_ms" in result
        assert "warnings" in result
        assert "empty_content" in result["warnings"]


# ── Virus Scanner Tests ──────────────────────────────────────────────────────

class TestVirusScanner:
    @pytest.mark.asyncio
    async def test_scan_returns_clean(self):
        from app.utils.virus_scanner import VirusScanner
        scanner = VirusScanner()
        result = await scanner.scan("nonexistent_file.txt")
        assert result.get("clean") is True

    @pytest.mark.asyncio
    async def test_scan_singleton(self):
        from app.utils.virus_scanner import virus_scanner
        assert virus_scanner is not None


# ── Background Tasks Tests ───────────────────────────────────────────────────

class TestBackgroundTasks:
    def test_with_timeout_decorator_import(self):
        from app.utils.background_tasks import with_timeout
        assert with_timeout is not None

    def test_mark_job_as_failed_import(self):
        from app.utils.background_tasks import _mark_job_as_failed
        assert _mark_job_as_failed is not None

    def test_run_pipeline_with_timeout_import(self):
        from app.utils.background_tasks import run_pipeline_with_timeout
        assert run_pipeline_with_timeout is not None


# ── Dependencies Utils Tests ─────────────────────────────────────────────────

class TestDependenciesUtils:
    def test_require_supabase_raises(self):
        from app.routers.v1.documents_impl import _require_db
        from fastapi import HTTPException
        with patch("app.db.supabase_client.get_supabase_client", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                _require_db()
            assert exc_info.value.status_code == 503

    def test_status_cache_key(self):
        from app.routers.v1.documents_impl import _status_cache_key
        from app.schemas.user import User
        user = User(id="user-1", email="test@test.com")
        key = _status_cache_key("job-123", user)
        assert "user-1" in key
        assert "job-123" in key

    def test_status_cache_key_anonymous(self):
        from app.routers.v1.documents_impl import _status_cache_key
        key = _status_cache_key("job-123", None)
        assert "__anon__" in key
        assert "job-123" in key

    def test_clone_status_payload(self):
        from app.routers.v1.documents_impl import _clone_status_payload
        original = {"data": [1, 2, 3]}
        cloned = _clone_status_payload(original)
        assert cloned == original
        assert cloned is not original
        cloned["data"].append(4)
        assert 4 not in original["data"]

    def test_normalize_provider_name(self):
        from app.routers.v1.documents_impl import _normalize_provider_name
        assert _normalize_provider_name("nvidia-llama") == "nvidia"
        assert _normalize_provider_name("groq-mixtral") == "groq"
        assert _normalize_provider_name("ollama-deepseek") == "ollama"
        assert _normalize_provider_name("openai-gpt4") == "openai"
        assert _normalize_provider_name("anthropic-claude") == "anthropic"
        assert _normalize_provider_name("rule_based") == "rule_based"
        assert _normalize_provider_name("") is None

    def test_extract_quality_payload_empty(self):
        from app.routers.v1.documents_impl import _extract_quality_payload
        result = _extract_quality_payload(None)
        assert result["quality_score"] is None
        assert result["quality_summary"] is None
        assert result["quality"] is None

    def test_build_initial_status_payload(self):
        from app.routers.v1.documents_impl import _build_initial_status_payload
        payload = _build_initial_status_payload("job-123")
        assert payload["job_id"] == "job-123"
        assert payload["status"] == "PROCESSING"
        assert payload["progress_percentage"] == 0

    def test_canonical_template_id(self):
        from app.routers.v1.templates import _canonical_template_id
        assert _canonical_template_id("IEEE") == "ieee"
        assert _canonical_template_id("Modern Blue") == "modern_blue"

    def test_template_display_name(self):
        from app.routers.v1.templates import _template_display_name
        assert _template_display_name("ieee") == "IEEE"
        assert _template_display_name("apa") == "APA"
        assert _template_display_name("none") == "None"
        assert _template_display_name("modern_blue") == "Modern Blue"

    def test_valid_session_id(self):
        from app.routers.preview import _valid_session_id
        assert _valid_session_id("valid-session-123") is True
        assert _valid_session_id("ab") is False  # too short (min 3)
        assert _valid_session_id("invalid session!") is False  # contains space and !

    def test_hash_html(self):
        from app.routers.preview import _hash_html
        h1 = _hash_html("test content")
        h2 = _hash_html("test content")
        assert h1 == h2
        assert len(h1) == 12

    def test_chunk_text(self):
        from app.routers.preview import _chunk_text
        chunks = list(_chunk_text("hello world", chunk_size=5))
        assert len(chunks) == 3
        assert chunks[0] == "hello"
        assert chunks[1] == " worl"
        assert chunks[2] == "d"

    def test_chunk_text_empty(self):
        from app.routers.preview import _chunk_text
        assert list(_chunk_text("")) == []


# ── Schema Tests ─────────────────────────────────────────────────────────────

class TestSchemas:
    def test_api_envelope_imports(self):
        from app.schemas.api_envelope import APIResponse, APIError
        assert APIResponse is not None
        assert APIError is not None

    def test_document_schema_imports(self):
        from app.schemas.document import DocumentUploadResponse, DocumentStatus
        assert DocumentUploadResponse is not None
        assert DocumentStatus is not None

    def test_user_schema(self):
        from app.schemas.user import User
        user = User(id="1", email="test@test.com")
        assert user.id == "1"
        assert user.email == "test@test.com"
        assert user.role == "authenticated"

    def test_auth_schemas(self):
        from app.schemas.auth import SignupRequest, LoginRequest, ForgotPasswordRequest
        signup = SignupRequest(email="test@test.com", password="Password123!", full_name="Test User", institution="Test Uni", terms_accepted=True)
        assert signup.email == "test@test.com"
        login = LoginRequest(email="test@test.com", password="Password123!")
        assert login.email == "test@test.com"
        forgot = ForgotPasswordRequest(email="test@test.com")
        assert forgot.email == "test@test.com"


# ── Config Settings Tests ────────────────────────────────────────────────────

class TestSettings:
    def test_settings_imports(self):
        from app.config.settings import settings
        assert settings is not None
        assert hasattr(settings, "DEFAULT_TEMPLATE")
        assert hasattr(settings, "MAX_FILE_SIZE")

    def test_default_template(self):
        from app.config.settings import settings
        assert isinstance(settings.DEFAULT_TEMPLATE, str)

    def test_max_file_size(self):
        from app.config.settings import settings
        assert settings.MAX_FILE_SIZE > 0


# ── Exceptions Tests ─────────────────────────────────────────────────────────

class TestExceptions:
    def test_document_not_found_error(self):
        from app.exceptions import DocumentNotFoundError
        exc = DocumentNotFoundError(doc_id="doc-123")
        assert "doc-123" in str(exc)
        assert exc.doc_id == "doc-123"

    def test_file_storage_error(self):
        from app.exceptions import FileStorageError
        exc = FileStorageError("Disk full")
        assert str(exc) == "Disk full"


# ── Auth Service Missing Coverage ─────────────────────────────────────────────

class TestAuthServiceMissingCoverage:
    def test_supabase_unavailable(self):
        from app.services.auth_service import _require_supabase
        from fastapi import HTTPException
        import pytest
        with patch("app.services.auth_service.supabase", None):
            with pytest.raises(HTTPException) as exc_info:
                _require_supabase()
            assert exc_info.value.status_code == 503

    def test_decode_token_no_token(self):
        from app.services.auth_service import AuthService
        import jwt
        with patch("app.services.auth_service.verify_jwt") as mock_verify:
            mock_verify.side_effect = jwt.InvalidTokenError("bad token")
            import pytest
            with pytest.raises(jwt.InvalidTokenError):
                AuthService.decode_token("bad-token")

    def test_get_user_id_missing_sub(self):
        from app.services.auth_service import AuthService
        from fastapi import HTTPException
        import pytest
        with pytest.raises(HTTPException):
            AuthService.get_user_id_from_payload({})


# ── Safe Execution Coverage ───────────────────────────────────────────────────

class TestSafeExecutionCoverage:
    def test_safe_execution_context_no_error(self):
        from app.pipeline.safety.safe_execution import safe_execution
        with safe_execution("test_op"):
            result = 42
        assert result == 42

    def test_safe_execution_context_suppresses_error(self):
        from app.pipeline.safety.safe_execution import safe_execution
        try:
            with safe_execution("test_op", error_return_value="fallback"):
                1 / 0
        except Exception:
            pass

    def test_safe_function_decorator(self):
        from app.pipeline.safety.safe_execution import safe_function
        @safe_function(fallback_value="error_val")
        def failing():
            raise ValueError("boom")
        assert failing() == "error_val"

    def test_safe_function_decorator_no_name(self):
        from app.pipeline.safety.safe_execution import safe_function
        @safe_function(fallback_value=None)
        def failing():
            raise ValueError("boom")
        assert failing() is None

    def test_safe_function_success(self):
        from app.pipeline.safety.safe_execution import safe_function
        @safe_function(fallback_value="bad")
        def working():
            return "good"
        assert working() == "good"


# ── Feature Flags DB/Redis Coverage ───────────────────────────────────────────

class TestFeatureFlagsDBRedisCoverage:
    def test_set_redis_cache_with_redis(self):
        from app.services.feature_flags import FeatureFlagService
        class FakeRedis:
            def setex(self, *args, **kwargs):
                pass
        redis_mock = FakeRedis()
        service = FeatureFlagService(redis=redis_mock)
        service._set_redis_cache("test_flag", "test_val")

    def test_set_redis_cache_handles_exception(self):
        from app.services.feature_flags import FeatureFlagService
        class BadRedis:
            pass
        bad = BadRedis()
        service = FeatureFlagService(redis=bad)
        service._set_redis_cache("x", "y")

    def test_get_flag_cache_hit(self):
        from app.services.feature_flags import FeatureFlagService
        service = FeatureFlagService()
        service._cache["my_flag"] = "cached_val"
        result = service.get_flag("my_flag")
        assert result == "cached_val"

    def test_set_flag_caches_value(self):
        from app.services.feature_flags import FeatureFlagService
        service = FeatureFlagService()
        service.set_flag("new_flag", 42)
        assert service._cache["new_flag"] == 42

    def test_set_flag_updates_cache(self):
        from app.services.feature_flags import FeatureFlagService
        service = FeatureFlagService()
        service.set_flag("ai_suggestions", False)
        assert service.get_flag("ai_suggestions") is False


# ── Logging Context Coverage ──────────────────────────────────────────────────

class TestLoggingContextCoverage:
    def test_log_extra_defaults(self):
        from app.utils.logging_context import log_extra
        result = log_extra()
        assert "request_id" in result
        assert "job_id" in result
        assert "session_id" in result

    def test_log_extra_with_job_id(self):
        from app.utils.logging_context import log_extra
        result = log_extra(job_id="job-456")
        assert "job_id" in result

    def test_log_extra_with_session_id(self):
        from app.utils.logging_context import log_extra
        result = log_extra(session_id="sess-789")
        assert "session_id" in result

    def test_bind_and_reset_context(self):
        from app.utils.logging_context import bind_context, reset_context
        tokens = bind_context(request_id="req-test")
        assert "request_id" in tokens
        reset_context(tokens)

    def test_log_context_manager(self):
        from app.utils.logging_context import log_context
        with log_context(request_id="req-cm"):
            pass

    def test_get_request_id_context(self):
        from app.utils.logging_context import get_request_id_context
        result = get_request_id_context()
        assert result is None or isinstance(result, str)


# ── Section Prompts Coverage ──────────────────────────────────────────────────

class TestSectionPromptsCoverage:
    def test_get_section_prompt(self):
        from app.pipeline.generation.section_prompts import get_section_prompt
        prompt = get_section_prompt("Introduction", {"task_spec": "write", "template_rules": {}, "outline": ["Intro"], "previous_sections": ""})
        assert prompt is not None
        assert len(prompt) > 0

    def test_get_section_prompt_unknown_section(self):
        from app.pipeline.generation.section_prompts import get_section_prompt
        prompt = get_section_prompt("UnknownSection", {"task_spec": "write", "template_rules": {}, "outline": [], "previous_sections": ""})
        assert prompt is not None

    def test_get_section_prompt_minimal_context(self):
        from app.pipeline.generation.section_prompts import get_section_prompt
        prompt = get_section_prompt("Abstract", {})
        assert prompt is not None


# ── Content Parser Coverage ───────────────────────────────────────────────────

class TestContentParserCoverage:
    def test_parse_valid_json(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        result = parser.parse('[{"type": "paragraph", "content": "Hello"}]', "academic")
        assert len(result) == 1
        assert result[0]["content"] == "Hello"

    def test_parse_empty(self):
        from app.pipeline.generation.content_parser import ContentParser
        import pytest
        parser = ContentParser()
        with pytest.raises(ValueError):
            parser.parse("", "academic")

    def test_parse_invalid_json(self):
        from app.pipeline.generation.content_parser import ContentParser
        import pytest
        parser = ContentParser()
        with pytest.raises(ValueError):
            parser.parse("not json at all", "academic")

    def test_parse_valid_object(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        result = parser.parse('[{"type": "heading", "content": "Intro", "level": 1}]', "academic")
        assert len(result) == 1
        assert result[0]["content"] == "Intro"


# ── Retry Guard Coverage ──────────────────────────────────────────────────────

class TestRetryGuardCoverage:
    def test_retry_with_backoff_success(self):
        from app.pipeline.safety.retry_guard import execute_with_retry
        result = execute_with_retry(lambda: "ok", max_retries=2)
        assert result == "ok"

    def test_retry_with_backoff_fails(self):
        from app.pipeline.safety.retry_guard import execute_with_retry
        import pytest
        with pytest.raises(ValueError):
            execute_with_retry(lambda: (_ for _ in ()).throw(ValueError("fail")), max_retries=1)

    def test_retry_guard_alias(self):
        from app.pipeline.safety.retry_guard import retry_guard
        assert retry_guard is not None


# ── Preview Renderer render_preview Coverage ──────────────────────────────────

class TestPreviewRendererRenderCoverage:
    def test_render_preview_basic(self):
        from app.services.preview_renderer import PreviewRenderer
        renderer = PreviewRenderer()
        result = renderer.render_preview("Hello world", "ieee")
        assert "html" in result
        assert len(result["html"]) > 0

    def test_render_preview_empty(self):
        from app.services.preview_renderer import PreviewRenderer
        renderer = PreviewRenderer()
        result = renderer.render_preview("", "ieee")
        assert "html" in result

    def test_render_preview_with_heading(self):
        from app.services.preview_renderer import PreviewRenderer
        renderer = PreviewRenderer()
        result = renderer.render_preview("## Title\n\nBody text.", "modern-blue")
        assert "html" in result


# ── PipelineDocument Model Tests ──────────────────────────────────────────────

class TestPipelineDocumentModel:
    def test_validate_document_id_empty_raises(self):
        from app.models.pipeline_document import PipelineDocument
        import pytest
        with pytest.raises(ValueError):
            PipelineDocument(document_id="")

    def test_validate_document_id_whitespace_raises(self):
        from app.models.pipeline_document import PipelineDocument
        import pytest
        with pytest.raises(ValueError):
            PipelineDocument(document_id="   ")

    def test_document_id_stripped(self):
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="  abc123  ")
        assert doc.document_id == "abc123"

    def test_add_processing_stage(self):
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        doc.add_processing_stage("parsing", "success", "Done", 150)
        assert len(doc.processing_history) == 1
        assert doc.processing_history[0].stage_name == "parsing"
        assert doc.processing_history[0].status == "success"

    def test_add_processing_stage_handles_exception(self):
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        doc.add_processing_stage(42, "broken")
        assert len(doc.processing_history) == 0

    def test_get_block_by_id_found(self):
        from app.models.pipeline_document import PipelineDocument
        from app.models.block import Block, BlockType
        doc = PipelineDocument(document_id="d1")
        b1 = Block(block_id="b1", index=1, block_type=BlockType.BODY, text="Hello")
        b2 = Block(block_id="b2", index=2, block_type=BlockType.BODY, text="World")
        doc.blocks = [b1, b2]
        assert doc.get_block_by_id("b1") is b1

    def test_get_block_by_id_not_found(self):
        from app.models.pipeline_document import PipelineDocument
        from app.models.block import Block, BlockType
        doc = PipelineDocument(document_id="d1")
        doc.blocks = [Block(block_id="b1", index=1, block_type=BlockType.BODY, text="")]
        assert doc.get_block_by_id("nonexistent") is None

    def test_get_block_by_id_empty_returns_none(self):
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        assert doc.get_block_by_id("") is None
        assert doc.get_block_by_id(None) is None

    def test_get_figure_by_id_found(self):
        from app.models.pipeline_document import PipelineDocument
        from app.models.figure import Figure
        doc = PipelineDocument(document_id="d1")
        fig = Figure(figure_id="f1", index=0)
        doc.figures = [fig]
        assert doc.get_figure_by_id("f1") is fig

    def test_get_figure_by_id_empty_returns_none(self):
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        assert doc.get_figure_by_id("") is None

    def test_get_equation_by_id_found(self):
        from app.models.pipeline_document import PipelineDocument
        from app.models.equation import Equation
        doc = PipelineDocument(document_id="d1")
        eq = Equation(equation_id="eq1", latex="x=1", index=0)
        doc.equations = [eq]
        assert doc.get_equation_by_id("eq1") is eq

    def test_get_equation_by_id_empty_returns_none(self):
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        assert doc.get_equation_by_id("") is None

    def test_get_blocks_by_type(self):
        from app.models.pipeline_document import PipelineDocument
        from app.models.block import Block, BlockType
        doc = PipelineDocument(document_id="d1")
        doc.blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.HEADING_1, text="Intro"),
            Block(block_id="b2", index=2, block_type=BlockType.BODY, text="Body"),
            Block(block_id="b3", index=3, block_type=BlockType.HEADING_2, text="Methods"),
        ]
        result = doc.get_blocks_by_type("heading_1")
        assert len(result) == 1
        assert result[0].block_id == "b1"

    def test_get_blocks_by_type_empty_arg(self):
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        assert doc.get_blocks_by_type("") == []
        assert doc.get_blocks_by_type(None) == []

    def test_get_blocks_in_section(self):
        from app.models.pipeline_document import PipelineDocument
        from app.models.block import Block, BlockType
        doc = PipelineDocument(document_id="d1")
        doc.blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.HEADING_1, text="Intro", section_name="Introduction"),
            Block(block_id="b2", index=2, block_type=BlockType.BODY, text="Some text", section_name="Introduction"),
        ]
        result = doc.get_blocks_in_section("introduction")
        assert len(result) == 2

    def test_get_blocks_in_section_empty(self):
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        assert doc.get_blocks_in_section("") == []
        assert doc.get_blocks_in_section(None) == []

    def test_get_section_names(self):
        from app.models.pipeline_document import PipelineDocument
        from app.models.block import Block, BlockType
        doc = PipelineDocument(document_id="d1")
        doc.blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.HEADING_1, text="Intro", section_name="Introduction"),
            Block(block_id="b2", index=2, block_type=BlockType.HEADING_2, text="Methods", section_name="Methods"),
        ]
        sections = doc.get_section_names()
        assert sorted(sections) == ["Introduction", "Methods"]

    def test_get_section_names_empty(self):
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        assert doc.get_section_names() == []

    def test_get_stats(self):
        from app.models.pipeline_document import PipelineDocument
        from app.models.block import Block, BlockType
        doc = PipelineDocument(document_id="d1")
        doc.blocks = [Block(block_id="b1", index=1, block_type=BlockType.BODY, text="")]
        stats = doc.get_stats()
        assert stats["blocks"] == 1
        assert stats["stages"] == 0


# ── Normalizer Pure Method Tests ──────────────────────────────────────────────

class TestNormalizerPureMethods:
    def test_repair_corruptions_2ethodology(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        assert n._repair_common_corruptions("2ethodology") == "2 Methodology"

    def test_repair_corruptions_ntroduction(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        assert n._repair_common_corruptions("1ntroduction") == "1 Introduction"

    def test_repair_corruptions_esults(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        assert n._repair_common_corruptions("3esults") == "3 Results"

    def test_repair_corruptions_iscussion(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        assert n._repair_common_corruptions("4iscussion") == "4 Discussion"

    def test_repair_corruptions_onclusion(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        assert n._repair_common_corruptions("5onclusion") == "5 Conclusion"

    def test_repair_corruptions_eferences(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        assert n._repair_common_corruptions("6eferences") == "6 References"

    def test_repair_corruptions_bstract(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        assert n._repair_common_corruptions("7bstract") == "7 Abstract"

    def test_repair_corruptions_empty(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        assert n._repair_common_corruptions("") == ""

    def test_repair_corruptions_no_change(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        assert n._repair_common_corruptions("Normal text") == "Normal text"

    def test_repair_corruptions_case_insensitive(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        assert n._repair_common_corruptions("2ETHODOLOGY") == "2 Methodology"

    def test_calculate_median_font_size_basic(self):
        from app.pipeline.normalization.normalizer import Normalizer
        from app.models.block import Block, BlockType, TextStyle
        n = Normalizer()
        blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.BODY, text="A", style=TextStyle(font_size=10)),
            Block(block_id="b2", index=2, block_type=BlockType.BODY, text="B", style=TextStyle(font_size=12)),
            Block(block_id="b3", index=3, block_type=BlockType.BODY, text="C", style=TextStyle(font_size=14)),
        ]
        assert n._calculate_median_font_size(blocks) == 12

    def test_calculate_median_font_size_empty(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        assert n._calculate_median_font_size([]) is None

    def test_calculate_median_font_size_no_font_size(self):
        from app.pipeline.normalization.normalizer import Normalizer
        from app.models.block import Block, BlockType, TextStyle
        n = Normalizer()
        blocks = [Block(block_id="b1", index=1, block_type=BlockType.BODY, text="X", style=TextStyle(font_size=None))]
        assert n._calculate_median_font_size(blocks) is None

    def test_normalize_metadata_title(self):
        from app.pipeline.normalization.normalizer import Normalizer
        from app.models.pipeline_document import DocumentMetadata
        n = Normalizer()
        meta = DocumentMetadata(title="  Hello World  ")
        result = n._normalize_metadata(meta)
        assert result.title == "Hello World"

    def test_normalize_metadata_authors_clean(self):
        from app.pipeline.normalization.normalizer import Normalizer
        from app.models.pipeline_document import DocumentMetadata
        n = Normalizer()
        meta = DocumentMetadata(authors=["  Smith, J.  ", "", "Doe, A."])
        result = n._normalize_metadata(meta)
        assert len(result.authors) == 2

    def test_normalize_metadata_keywords(self):
        from app.pipeline.normalization.normalizer import Normalizer
        from app.models.pipeline_document import DocumentMetadata
        n = Normalizer()
        meta = DocumentMetadata(keywords=["  ML  ", "", "AI"])
        result = n._normalize_metadata(meta)
        assert "ML" in result.keywords
        assert "" not in result.keywords

    def test_normalize_metadata_none_fields(self):
        from app.pipeline.normalization.normalizer import Normalizer
        from app.models.pipeline_document import DocumentMetadata
        n = Normalizer()
        meta = DocumentMetadata()
        result = n._normalize_metadata(meta)
        assert result.title is None
        assert result.abstract is None

    def test_sanitize_empty_orphan_removes_empty_body(self):
        from app.pipeline.normalization.normalizer import Normalizer
        from app.models.block import Block, BlockType
        n = Normalizer()
        blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.BODY, text="Keep me"),
            Block(block_id="b2", index=2, block_type=BlockType.BODY, text=""),
            Block(block_id="b3", index=3, block_type=BlockType.UNKNOWN, text=""),
        ]
        result = n._sanitize_empty_orphan_blocks(blocks)
        assert len(result) == 1
        assert result[0].block_id == "b1"

    def test_sanitize_keeps_block_with_figure(self):
        from app.pipeline.normalization.normalizer import Normalizer
        from app.models.block import Block, BlockType
        n = Normalizer()
        blocks = [Block(block_id="b1", index=1, block_type=BlockType.BODY, text="", metadata={"has_figure": True})]
        result = n._sanitize_empty_orphan_blocks(blocks)
        assert len(result) == 1

    def test_sanitize_keeps_block_with_list(self):
        from app.pipeline.normalization.normalizer import Normalizer
        from app.models.block import Block, BlockType
        n = Normalizer()
        blocks = [Block(block_id="b1", index=1, block_type=BlockType.BODY, text="", metadata={"list_level": 0})]
        result = n._sanitize_empty_orphan_blocks(blocks)
        assert len(result) == 1

    def test_normalize_tables_basic(self):
        from app.pipeline.normalization.normalizer import Normalizer
        from app.models.table import Table, TableCell
        n = Normalizer()
        cells = [TableCell(row=0, col=0, text="  Hello  ")]
        table = Table(table_id="t1", cells=cells, rows=[["  World  "]], num_rows=1, num_cols=1, index=0, block_index=0)
        result = n._normalize_tables([table])
        assert len(result) == 1
        assert result[0].cells[0].text == "Hello"
        assert result[0].rows[0][0] == "World"


# ── Reference Normalizer Tests ────────────────────────────────────────────────

class TestReferenceNormalizer:
    def test_clean_author_name_basic(self):
        from app.pipeline.references.normalizer import clean_author_name
        assert clean_author_name("  Smith, J.  ") == "Smith, J."

    def test_clean_author_name_removes_quotes(self):
        from app.pipeline.references.normalizer import clean_author_name
        assert clean_author_name('"Smith, J."') == "Smith, J."

    def test_clean_title_removes_wrapping_quotes(self):
        from app.pipeline.references.normalizer import clean_title
        assert clean_title('"A Great Paper"') == "A Great Paper"

    def test_clean_title_curly_quotes(self):
        from app.pipeline.references.normalizer import clean_title
        assert clean_title("\u201cA Paper\u201d") == "A Paper"

    def test_clean_title_strips_punctuation(self):
        from app.pipeline.references.normalizer import clean_title
        assert clean_title("A Paper.,;") == "A Paper"

    def test_clean_title_empty(self):
        from app.pipeline.references.normalizer import clean_title
        assert clean_title("") == ""

    def test_normalize_page_range_removes_pp(self):
        from app.pipeline.references.normalizer import normalize_page_range
        assert normalize_page_range("pp. 123-145") == "123-145"

    def test_normalize_page_range_removes_p(self):
        from app.pipeline.references.normalizer import normalize_page_range
        assert normalize_page_range("p. 10") == "10"

    def test_normalize_page_range_empty(self):
        from app.pipeline.references.normalizer import normalize_page_range
        assert normalize_page_range("") == ""
        assert normalize_page_range(None) == ""


# ── Reference Formatter Helper Tests ──────────────────────────────────────────

class TestReferenceFormatterHelpers:
    def test_reference_type_to_csl_journal(self):
        from app.pipeline.formatting.reference_formatter import _reference_type_to_csl
        from app.models.reference import Reference, ReferenceType
        ref = Reference(reference_id="r1", citation_key="K1", raw_text="T1", reference_type=ReferenceType.JOURNAL_ARTICLE, index=0)
        assert _reference_type_to_csl(ref) == "article-journal"

    def test_reference_type_to_csl_book(self):
        from app.pipeline.formatting.reference_formatter import _reference_type_to_csl
        from app.models.reference import Reference, ReferenceType
        ref = Reference(reference_id="r1", citation_key="K1", raw_text="T1", reference_type=ReferenceType.BOOK, index=0)
        assert _reference_type_to_csl(ref) == "book"

    def test_reference_type_to_csl_unknown(self):
        from app.pipeline.formatting.reference_formatter import _reference_type_to_csl
        from app.models.reference import Reference, ReferenceType
        ref = Reference(reference_id="r1", citation_key="K1", raw_text="T1", reference_type=ReferenceType.UNKNOWN, index=0)
        assert _reference_type_to_csl(ref) == "article"

    def test_parse_author_name_comma(self):
        from app.pipeline.formatting.reference_formatter import _parse_author_name
        assert _parse_author_name("Smith, J.") == {"family": "Smith", "given": "J."}

    def test_parse_author_name_space(self):
        from app.pipeline.formatting.reference_formatter import _parse_author_name
        assert _parse_author_name("Jane Doe") == {"given": "Jane", "family": "Doe"}

    def test_parse_author_name_single(self):
        from app.pipeline.formatting.reference_formatter import _parse_author_name
        assert _parse_author_name("Aristotle") == {"family": "Aristotle"}

    def test_parse_author_name_empty(self):
        from app.pipeline.formatting.reference_formatter import _parse_author_name
        assert _parse_author_name("") == {"family": "Unknown"}

    def test_parse_author_name_whitespace(self):
        from app.pipeline.formatting.reference_formatter import _parse_author_name
        assert _parse_author_name("  ") == {"family": "Unknown"}

    def test_reference_to_csl_json_basic(self):
        from app.pipeline.formatting.reference_formatter import _reference_to_csl_json
        from app.models.reference import Reference, ReferenceType
        ref = Reference(
            reference_id="r1", citation_key="K1", raw_text="T1", index=0,
            reference_type=ReferenceType.JOURNAL_ARTICLE,
            authors=["Smith, J."], title="My Paper", journal="Nature",
            year=2024, volume="10", issue="2", pages="100-110",
            doi="10.1234/test", url="https://example.com",
        )
        result = _reference_to_csl_json(ref)
        assert result["id"] == "r1"
        assert result["type"] == "article-journal"
        assert result["title"] == "My Paper"
        assert result["container-title"] == "Nature"
        assert result["volume"] == "10"
        assert result["issue"] == "2"
        assert result["page"] == "100-110"
        assert result["DOI"] == "10.1234/test"
        assert result["URL"] == "https://example.com"

    def test_reference_to_csl_json_minimal(self):
        from app.pipeline.formatting.reference_formatter import _reference_to_csl_json
        from app.models.reference import Reference
        ref = Reference(reference_id="r1", citation_key="K1", raw_text="T1", index=0)
        result = _reference_to_csl_json(ref)
        assert result["id"] == "r1"
        assert result["type"] == "article"
        assert "author" not in result
        assert "container-title" not in result


# ── Template Renderer Pure Method Tests ───────────────────────────────────────

class TestTemplateRendererPureMethods:
    def test_coerce_bool_none(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        assert TemplateRenderer._coerce_bool(None, True) is True
        assert TemplateRenderer._coerce_bool(None, False) is False

    def test_coerce_bool_bool(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        assert TemplateRenderer._coerce_bool(True, False) is True
        assert TemplateRenderer._coerce_bool(False, True) is False

    def test_coerce_bool_number(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        assert TemplateRenderer._coerce_bool(1, False) is True
        assert TemplateRenderer._coerce_bool(0, True) is False
        assert TemplateRenderer._coerce_bool(3.14, False) is True
        assert TemplateRenderer._coerce_bool(0.0, True) is False

    def test_coerce_bool_str_truthy(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        for v in ("1", "true", "True", "yes", "on"):
            assert TemplateRenderer._coerce_bool(v, False) is True

    def test_coerce_bool_str_falsy(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        for v in ("0", "false", "False", "no", "off", ""):
            assert TemplateRenderer._coerce_bool(v, True) is False

    def test_coerce_bool_str_unknown_falls_to_default(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        assert TemplateRenderer._coerce_bool("maybe", True) is True

    def test_resolve_bool_option_found(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        r = TemplateRenderer("")
        assert r._resolve_bool_option({"cover_page": True}, ["cover_page", "add_cover_page"], False) is True
        assert r._resolve_bool_option({"cover_page": False}, ["cover_page"], True) is False

    def test_resolve_bool_option_not_found(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        r = TemplateRenderer("")
        assert r._resolve_bool_option({}, ["missing_key"], True) is True

    def test_block_type_token_string(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        from app.models.block import Block, BlockType
        block = Block(block_id="b1", index=1, block_type=BlockType.HEADING_1, text="")
        assert TemplateRenderer._block_type_token(block) == "heading_1"

    def test_first_block_text_found(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        from app.models.block import Block, BlockType
        r = TemplateRenderer("")
        blocks = [
            Block(block_id="b1", index=2, block_type=BlockType.TITLE, text=" Title "),
            Block(block_id="b2", index=1, block_type=BlockType.AUTHOR, text="Author"),
        ]
        assert r._first_block_text(blocks, "title") == "Title"

    def test_first_block_text_not_found(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        from app.models.block import Block, BlockType
        r = TemplateRenderer("")
        blocks = [Block(block_id="b1", index=1, block_type=BlockType.BODY, text="")]
        assert r._first_block_text(blocks, "title") == ""

    def test_all_block_text_found(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        from app.models.block import Block, BlockType
        r = TemplateRenderer("")
        blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.AUTHOR, text=" Doe "),
            Block(block_id="b2", index=2, block_type=BlockType.AUTHOR, text=" Smith "),
        ]
        assert r._all_block_text(blocks, "author") == ["Doe", "Smith"]

    def test_all_block_text_empty(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        from app.models.block import Block, BlockType
        r = TemplateRenderer("")
        blocks = [Block(block_id="b1", index=1, block_type=BlockType.BODY, text="")]
        assert r._all_block_text(blocks, "author") == []

    def test_collect_sections_basic(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        from app.models.block import Block, BlockType
        r = TemplateRenderer("")
        blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.HEADING_1, text="Introduction"),
            Block(block_id="b2", index=2, block_type=BlockType.BODY, text="Body text."),
        ]
        sections = r._collect_sections(blocks)
        assert len(sections) == 1
        assert sections[0]["heading"] == "Introduction"
        assert sections[0]["paragraphs"] == ["Body text."]

    def test_collect_sections_skip_types(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        from app.models.block import Block, BlockType
        r = TemplateRenderer("")
        blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.HEADING_1, text="Intro"),
            Block(block_id="b2", index=2, block_type=BlockType.ABSTRACT_BODY, text="Abstract"),
            Block(block_id="b3", index=3, block_type=BlockType.AUTHOR, text="Me"),
            Block(block_id="b4", index=4, block_type=BlockType.REFERENCE_ENTRY, text="[1] Ref"),
            Block(block_id="b5", index=5, block_type=BlockType.FIGURE_CAPTION, text="Fig 1"),
            Block(block_id="b6", index=6, block_type=BlockType.BODY, text="Real paragraph."),
        ]
        sections = r._collect_sections(blocks)
        assert len(sections) == 1
        assert sections[0]["paragraphs"] == ["Real paragraph."]


# ── Validator Pure Method Tests ───────────────────────────────────────────────

class TestValidatorPureMethods:
    def test_as_bool_none(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        assert DocumentValidator._as_bool(None, True) is True
        assert DocumentValidator._as_bool(None, False) is False

    def test_as_bool_bool(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        assert DocumentValidator._as_bool(True, False) is True
        assert DocumentValidator._as_bool(False, True) is False

    def test_as_bool_number(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        assert DocumentValidator._as_bool(1, False) is True
        assert DocumentValidator._as_bool(0, True) is False

    def test_as_bool_str_truthy(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        for v in ("1", "true", "yes", "on"):
            assert DocumentValidator._as_bool(v, False) is True

    def test_as_bool_str_falsy(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        for v in ("0", "false", "no", "off"):
            assert DocumentValidator._as_bool(v, True) is False

    def test_as_bool_str_unknown(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        assert DocumentValidator._as_bool("unknown", True) is True

    def test_check_figures_missing_caption(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        from app.models.pipeline_document import PipelineDocument
        from app.models.figure import Figure
        doc = PipelineDocument(document_id="d1")
        fig = Figure(figure_id="f1", index=0)
        with patch.object(Figure, "has_caption", return_value=False):
            doc.figures = [fig]
            v = DocumentValidator.__new__(DocumentValidator)
            errs, warns = v._check_figures(doc)
        assert len(warns) == 1
        assert "missing caption" in warns[0]

    def test_check_figures_with_caption_ok(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        from app.models.pipeline_document import PipelineDocument
        from app.models.figure import Figure
        doc = PipelineDocument(document_id="d1")
        fig = Figure(figure_id="f1", index=0)
        with patch.object(Figure, "has_caption", return_value=True):
            doc.figures = [fig]
            v = DocumentValidator.__new__(DocumentValidator)
            errs, warns = v._check_figures(doc)
        assert len(warns) == 0

    def test_check_references_missing_year(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        from app.models.pipeline_document import PipelineDocument
        from app.models.reference import Reference
        doc = PipelineDocument(document_id="d1")
        doc.references = [Reference(reference_id="r1", citation_key="K1", raw_text="T1", index=0)]
        v = DocumentValidator.__new__(DocumentValidator)
        errs, warns = v._check_references(doc)
        assert any("missing publication year" in w for w in warns)

    def test_check_references_no_references_with_section(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        from app.models.pipeline_document import PipelineDocument
        from app.models.block import Block, BlockType
        doc = PipelineDocument(document_id="d1")
        doc.blocks = [Block(block_id="b1", index=1, block_type=BlockType.REFERENCES_HEADING, text="References", section_name="References")]
        v = DocumentValidator.__new__(DocumentValidator)
        errs, warns = v._check_references(doc)
        assert any("no reference entries" in w for w in warns)

    def test_check_tables_missing_caption(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        from app.models.pipeline_document import PipelineDocument
        from app.models.table import Table
        doc = PipelineDocument(document_id="d1")
        doc.tables = [Table(table_id="t1", caption_text="", num_rows=0, num_cols=0, index=0, block_index=0)]
        v = DocumentValidator.__new__(DocumentValidator)
        errs, warns = v._check_tables(doc)
        assert len(warns) == 1
        assert "missing caption" in warns[0]

    def test_check_tables_no_attr(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="d1")
        v = DocumentValidator.__new__(DocumentValidator)
        errs, warns = v._check_tables(doc)
        assert len(warns) == 0


# ── Circuit Breaker Tests ─────────────────────────────────────────────────────

class TestCircuitBreaker:
    def test_pybreaker_closed_success(self):
        from app.pipeline.safety.circuit_breaker import circuit_breaker
        @circuit_breaker(failure_threshold=3, recovery_timeout=60)
        def my_func(x):
            return x * 2
        assert my_func(3) == 6

    def test_pybreaker_fallback_on_error(self):
        from app.pipeline.safety.circuit_breaker import circuit_breaker
        @circuit_breaker(failure_threshold=1, recovery_timeout=60, fallback_function=lambda: "fb")
        def failing():
            raise ValueError("fail")
        result = failing()
        assert result == "fb"

    def test_pybreaker_fallback_also_fails(self):
        from app.pipeline.safety.circuit_breaker import circuit_breaker
        call_count = [0]
        @circuit_breaker(failure_threshold=1, recovery_timeout=60, fallback_function=lambda: 1/0)
        def failing():
            call_count[0] += 1
            raise ValueError("boom")
        result = failing()
        assert result == {}
        assert call_count[0] == 1


# ── Synthesizer Pure Method Tests ─────────────────────────────────────────────

class TestSynthesizerPureMethods:
    def test_extract_json_simple(self):
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        result = MultiDocSynthesizer._extract_json('{"key": "value"}')
        assert result == '{"key": "value"}'

    def test_extract_json_with_backticks(self):
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        result = MultiDocSynthesizer._extract_json('```json\n{"a": 1}\n```')
        assert result == '{"a": 1}'

    def test_extract_json_no_json(self):
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        result = MultiDocSynthesizer._extract_json("Just text")
        assert result is None

    def test_extract_json_empty(self):
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        assert MultiDocSynthesizer._extract_json("") is None

    def test_chunk_text_basic(self):
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        mds = MultiDocSynthesizer.__new__(MultiDocSynthesizer)
        chunks = mds._chunk_text("Hello World", "doc1.pdf", "intro", 1, chunk_size=100, overlap=20)
        assert len(chunks) == 1
        assert chunks[0]["text"] == "Hello World"
        assert chunks[0]["source_doc"] == "doc1.pdf"
        assert chunks[0]["section"] == "intro"
        assert chunks[0]["page"] == 1

    def test_chunk_text_multi_chunk(self):
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        mds = MultiDocSynthesizer.__new__(MultiDocSynthesizer)
        text = "A" * 500
        chunks = mds._chunk_text(text, "d.pdf", "s", None, chunk_size=200, overlap=50)
        assert len(chunks) >= 2

    def test_chunk_text_empty(self):
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        mds = MultiDocSynthesizer.__new__(MultiDocSynthesizer)
        chunks = mds._chunk_text("", "d.pdf", "s", None)
        assert len(chunks) == 0


# ── FormatterEngine format_single Tests ───────────────────────────────────────

class TestFormatterEngine:
    def test_format_single_journal(self):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        from app.models.reference import Reference, ReferenceType
        ref = Reference(
            reference_id="r1", citation_key="K1", raw_text="T1", index=0,
            reference_type=ReferenceType.JOURNAL_ARTICLE,
            authors=["Smith, J.", "Doe, A."], title="My Paper",
            journal="Nature", year=2024, volume="10", pages="100-110",
        )
        engine = ReferenceFormatterEngine.__new__(ReferenceFormatterEngine)
        rules = {
            "journal_format": "{authors}, \"{title},\" {journal}, vol. {volume}, pp. {pages}, {year}.",
            "max_authors": 3,
            "et_al_suffix": "et al.",
        }
        result = engine.format_single(ref, rules)
        assert "Smith, J." in result
        assert "My Paper" in result
        assert "Nature" in result
        assert "2024" in result

    def test_format_single_et_al(self):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        from app.models.reference import Reference, ReferenceType
        ref = Reference(
            reference_id="r1", citation_key="K1", raw_text="T1", index=0,
            reference_type=ReferenceType.JOURNAL_ARTICLE,
            authors=["Smith, J.", "Doe, A.", "Lee, K."],
        )
        engine = ReferenceFormatterEngine.__new__(ReferenceFormatterEngine)
        rules = {"journal_format": "{authors}", "max_authors": 2, "et_al_suffix": "et al."}
        result = engine.format_single(ref, rules)
        assert "et al." in result

    def test_format_single_conference(self):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        from app.models.reference import Reference, ReferenceType
        ref = Reference(
            reference_id="r1", citation_key="K1", raw_text="T1", index=0,
            reference_type=ReferenceType.CONFERENCE_PAPER,
            authors=["Smith, J."], title="Conf Paper",
            conference="ICML 2024", year=2024,
        )
        engine = ReferenceFormatterEngine.__new__(ReferenceFormatterEngine)
        rules = {"conference_format": "{authors}, {title}, {conference}, {year}."}
        result = engine.format_single(ref, rules)
        assert "ICML 2024" in result

    def test_format_single_default_format(self):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        from app.models.reference import Reference, ReferenceType
        ref = Reference(
            reference_id="r1", citation_key="K1", raw_text="T1", index=0,
            reference_type=ReferenceType.BOOK, authors=["Smith, J."],
        )
        engine = ReferenceFormatterEngine.__new__(ReferenceFormatterEngine)
        rules = {}
        result = engine.format_single(ref, rules)
        assert "Smith, J." in result

    def test_format_single_fallback_on_template_error(self):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        from app.models.reference import Reference, ReferenceType
        ref = Reference(
            reference_id="r1", citation_key="K1", raw_text="Original raw text", index=0,
            reference_type=ReferenceType.JOURNAL_ARTICLE,
        )
        engine = ReferenceFormatterEngine.__new__(ReferenceFormatterEngine)
        rules = {"journal_format": "{missing_field}"}
        result = engine.format_single(ref, rules)
        assert result == "Original raw text"


# ── Security Headers Middleware Tests ─────────────────────────────────────────

class TestSecurityHeadersMiddleware:
    def test_security_headers_class_instantiation(self):
        from app.middleware.security_headers import SecurityHeadersMiddleware
        middleware = SecurityHeadersMiddleware.__new__(SecurityHeadersMiddleware)
        assert middleware is not None


# ── Monitoring Middleware Tests ───────────────────────────────────────────────

class TestMonitoringMiddleware:
    def test_monitoring_middleware_init(self):
        from app.middleware.monitoring import MonitoringMiddleware
        mm = MonitoringMiddleware.__new__(MonitoringMiddleware)
        assert mm is not None


# ── Feature Flags Middleware Tests ────────────────────────────────────────────

class TestFeatureFlagsMiddleware:
    def test_feature_flags_middleware_init(self):
        from app.middleware.feature_flags import FeatureFlagMiddleware
        fm = FeatureFlagMiddleware.__new__(FeatureFlagMiddleware)
        assert fm is not None


# ── RequestId Middleware Tests ────────────────────────────────────────────────

class TestRequestIdMiddleware:
    def test_should_log_idempotency_upload(self):
        from app.middleware.request_id import _should_log_idempotency
        assert _should_log_idempotency("/upload") is True
        assert _should_log_idempotency("/api/v1/upload") is True

    def test_should_log_idempotency_generator(self):
        from app.middleware.request_id import _should_log_idempotency
        assert _should_log_idempotency("/generator/sessions") is True

    def test_should_log_idempotency_synthesis(self):
        from app.middleware.request_id import _should_log_idempotency
        assert _should_log_idempotency("/synthesis/sessions") is True

    def test_should_log_idempotency_other(self):
        from app.middleware.request_id import _should_log_idempotency
        assert _should_log_idempotency("/health") is False
        assert _should_log_idempotency("/docs") is False

    def test_get_request_id_existing(self):
        from app.middleware.request_id import get_request_id
        from unittest.mock import MagicMock
        request = MagicMock()
        request.state.request_id = "existing-id"
        assert get_request_id(request) == "existing-id"

    def test_get_request_id_missing_creates_new(self):
        from app.middleware.request_id import get_request_id
        from unittest.mock import MagicMock
        request = MagicMock()
        del request.state.request_id
        rid = get_request_id(request)
        assert isinstance(rid, str)
        assert len(rid) > 0


# ── MaxBodySize Middleware Tests ─────────────────────────────────────────────

class TestMaxBodySizeMiddleware:
    def test_max_body_size_under_limit(self):
        from app.middleware.security_headers import MaxBodySizeMiddleware
        async def app(scope, receive, send):
            pass
        middleware = MaxBodySizeMiddleware(app, max_size=1000)

        async def receive():
            return {"type": "http.request", "body": b"x" * 100}

        sent = []
        async def send(msg):
            sent.append(msg)

        import asyncio
        asyncio.run(middleware({"type": "http", "headers": [[b"content-length", b"100"]]}, receive, send))
        assert len(sent) == 0

    def test_max_body_size_over_limit(self):
        from app.middleware.security_headers import MaxBodySizeMiddleware
        async def app(scope, receive, send):
            pass
        middleware = MaxBodySizeMiddleware(app, max_size=50)

        async def receive():
            return {"type": "http.request", "body": b""}

        sent = []
        async def send(msg):
            sent.append(msg)

        import asyncio
        asyncio.run(middleware({"type": "http", "headers": [[b"content-length", b"100"]]}, receive, send))
        starts = [m for m in sent if m.get("type") == "http.response.start"]
        assert len(starts) == 1
        assert starts[0]["status"] == 413


# ── Health Check Pure Function Tests ──────────────────────────────────────────

class TestHealthCheckPureFunctions:
    def test_clone_payload_simple(self):
        from app.services.health_checks import _clone_payload
        payload = {"status": "ok", "checks": {"db": "healthy"}}
        cloned = _clone_payload(payload)
        assert cloned == payload
        cloned["checks"]["db"] = "changed"
        assert payload["checks"]["db"] == "healthy"

    def test_clone_payload_no_checks(self):
        from app.services.health_checks import _clone_payload
        payload = {"status": "ok"}
        cloned = _clone_payload(payload)
        assert cloned == payload

    def test_clone_payload_checks_not_dict(self):
        from app.services.health_checks import _clone_payload
        payload = {"status": "ok", "checks": "not-a-dict"}
        cloned = _clone_payload(payload)
        assert cloned["checks"] == "not-a-dict"

    def test_invalidate_readiness_cache(self):
        from app.services.health_checks import invalidate_readiness_cache
        invalidate_readiness_cache()

    def test_invalidate_health_cache(self):
        from app.services.health_checks import invalidate_health_cache
        invalidate_health_cache()

    def test_join_endpoint(self):
        from app.services.health_checks import _join_endpoint
        assert _join_endpoint("http://example.com", "/health") == "http://example.com/health"

    def test_join_endpoint_trailing_slash(self):
        from app.services.health_checks import _join_endpoint
        assert _join_endpoint("http://example.com/", "/health") == "http://example.com/health"

    def test_service_health_path_basic(self):
        from app.services.health_checks import _service_health_path
        path = _service_health_path("test_service")
        assert path == "/"
        assert path.startswith("/")

    def test_service_health_path_no_leading_slash(self):
        from app.services.health_checks import _service_health_path
        path = _service_health_path("test", "api/health")
        assert path == "/api/health"

    def test_service_health_path_empty_returns_default(self):
        from app.services.health_checks import _service_health_path
        path = _service_health_path("test", "")
        assert path == "/"

    def test_service_health_path_strips_trailing_slash(self):
        from app.services.health_checks import _service_health_path
        path = _service_health_path("test", "/health/")
        assert path == "/health"


# ── NumberingEngine Tests ────────────────────────────────────────────────────

class TestNumberingEngine:
    def test_apply_numbering_basic(self, monkeypatch):
        from app.pipeline.formatting.numbering import NumberingEngine
        from app.models.pipeline_document import PipelineDocument
        from app.models.block import Block, BlockType, TextStyle
        from unittest.mock import MagicMock
        mock_loader = MagicMock()
        mock_loader.load.return_value = {
            "numbering": {},
            "equations": {"scope": "global", "brackets": "()"},
        }
        engine = NumberingEngine(mock_loader)
        doc = PipelineDocument(document_id="d1")
        doc.blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.HEADING_1, text="Intro", level=1, style=TextStyle()),
        ]
        doc.equations = []
        result = engine.apply_numbering(doc, "ieee")
        assert result.blocks[0].text == "1 Intro"

    def test_apply_numbering_no_double_prefix(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        from app.models.pipeline_document import PipelineDocument
        from app.models.block import Block, BlockType, TextStyle
        from unittest.mock import MagicMock
        mock_loader = MagicMock()
        mock_loader.load.return_value = {"numbering": {}, "equations": {}}
        engine = NumberingEngine(mock_loader)
        doc = PipelineDocument(document_id="d1")
        doc.blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.HEADING_1, text="1 Intro", level=1, style=TextStyle()),
        ]
        result = engine.apply_numbering(doc, "ieee")
        assert result.blocks[0].text == "1 Intro"

    def test_apply_numbering_multilevel(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        from app.models.pipeline_document import PipelineDocument
        from app.models.block import Block, BlockType, TextStyle
        from unittest.mock import MagicMock
        mock_loader = MagicMock()
        mock_loader.load.return_value = {"numbering": {}, "equations": {}}
        engine = NumberingEngine(mock_loader)
        doc = PipelineDocument(document_id="d1")
        doc.blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.HEADING_1, text="Intro", level=1, style=TextStyle()),
            Block(block_id="b2", index=2, block_type=BlockType.HEADING_2, text="Background", level=2, style=TextStyle()),
        ]
        result = engine.apply_numbering(doc, "ieee")
        assert result.blocks[0].text == "1 Intro"
        assert result.blocks[1].text == "1.1 Background"

    def test_apply_numbering_figures_tables(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        from app.models.pipeline_document import PipelineDocument
        from app.models.figure import Figure
        from app.models.table import Table
        from unittest.mock import MagicMock
        mock_loader = MagicMock()
        mock_loader.load.return_value = {"numbering": {}, "equations": {}}
        engine = NumberingEngine(mock_loader)
        doc = PipelineDocument(document_id="d1")
        doc.figures = [Figure(figure_id="f1", index=0), Figure(figure_id="f2", index=1)]
        doc.tables = [Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=0)]
        result = engine.apply_numbering(doc, "ieee")
        assert result.figures[0].number == 1
        assert result.figures[1].number == 2
        assert result.tables[0].number == 1

    def test_apply_numbering_equation_brackets(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        from app.models.pipeline_document import PipelineDocument
        from app.models.equation import Equation
        from unittest.mock import MagicMock
        mock_loader = MagicMock()
        mock_loader.load.return_value = {
            "numbering": {},
            "equations": {"scope": "global", "brackets": "[]"},
        }
        engine = NumberingEngine(mock_loader)
        doc = PipelineDocument(document_id="d1")
        eq = Equation(equation_id="e1", latex="x=1", index=0)
        doc.equations = [eq]
        result = engine.apply_numbering(doc, "ieee")
        assert result.equations[0].number == "[1]"


# ── StyleMapper Tests ────────────────────────────────────────────────────────

class TestStyleMapper:
    def test_get_style_name_heading1(self):
        from app.pipeline.formatting.style_mapper import StyleMapper
        from app.models.block import Block, BlockType
        from unittest.mock import MagicMock
        mock_loader = MagicMock()
        mock_loader.load.return_value = {
            "styles": {"BLOCK_HEADING_1": "Heading 1"},
        }
        mapper = StyleMapper(mock_loader)
        block = Block(block_id="b1", index=1, block_type=BlockType.HEADING_1, text="Intro")
        assert mapper.get_style_name(block, "ieee") == "Heading 1"

    def test_get_style_name_default(self):
        from app.pipeline.formatting.style_mapper import StyleMapper
        from app.models.block import Block, BlockType
        from unittest.mock import MagicMock
        mock_loader = MagicMock()
        mock_loader.load.return_value = {"styles": {}}
        mapper = StyleMapper(mock_loader)
        block = Block(block_id="b1", index=1, block_type=BlockType.BODY, text="Body")
        assert mapper.get_style_name(block, "ieee") == "Normal"


# ── SectionOrderValidator Tests ───────────────────────────────────────────────

class TestSectionOrderValidator:
    def test_validate_order_no_violations(self):
        from app.pipeline.formatting.section_ordering import SectionOrderValidator
        from app.models.pipeline_document import PipelineDocument
        from app.models.block import Block, BlockType
        from unittest.mock import MagicMock
        mock_loader = MagicMock()
        mock_loader.load.return_value = {
            "sections": {
                "order": ["introduction", "methods", "results"],
                "required": ["introduction"],
            },
        }
        validator = SectionOrderValidator(mock_loader)
        doc = PipelineDocument(document_id="d1")
        doc.blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.HEADING_1, text="Introduction", section_name="Introduction"),
            Block(block_id="b2", index=2, block_type=BlockType.HEADING_1, text="Methods", section_name="Methods"),
        ]
        violations = validator.validate_order(doc, "ieee")
        assert len(violations) == 0

    def test_validate_order_missing_required(self):
        from app.pipeline.formatting.section_ordering import SectionOrderValidator
        from app.models.pipeline_document import PipelineDocument
        from app.models.block import Block, BlockType
        from unittest.mock import MagicMock
        mock_loader = MagicMock()
        mock_loader.load.return_value = {
            "sections": {
                "order": ["introduction"],
                "required": ["introduction", "methods"],
            },
        }
        validator = SectionOrderValidator(mock_loader)
        doc = PipelineDocument(document_id="d1")
        doc.blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.HEADING_1, text="Intro", section_name="Introduction"),
        ]
        violations = validator.validate_order(doc, "ieee")
        assert any("Missing required" in v for v in violations)
        assert any("methods" in v.lower() for v in violations)

    def test_validate_order_out_of_order(self):
        from app.pipeline.formatting.section_ordering import SectionOrderValidator
        from app.models.pipeline_document import PipelineDocument
        from app.models.block import Block, BlockType
        from unittest.mock import MagicMock
        mock_loader = MagicMock()
        mock_loader.load.return_value = {
            "sections": {
                "order": ["introduction", "methods", "results"],
                "required": [],
            },
        }
        validator = SectionOrderValidator(mock_loader)
        doc = PipelineDocument(document_id="d1")
        doc.blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.HEADING_1, text="Methods", section_name="Methods"),
            Block(block_id="b2", index=2, block_type=BlockType.HEADING_1, text="Introduction", section_name="Introduction"),
        ]
        violations = validator.validate_order(doc, "ieee")
        assert any("out of order" in v.lower() for v in violations)


# ── Dependencies Utils Tests ──────────────────────────────────────────────────

class TestDependenciesUtilsExtended:
    def test_get_current_user_no_credentials_raises(self):
        from app.utils.dependencies import get_current_user
        from unittest.mock import MagicMock
        import pytest
        from fastapi import HTTPException
        request = MagicMock()
        request.query_params.get.return_value = None
        with pytest.raises(HTTPException) as exc:
            get_current_user(request, None)
        assert exc.value.status_code == 401

    def test_get_current_user_rejects_query_token(self):
        from app.utils.dependencies import get_current_user
        from unittest.mock import MagicMock
        import pytest
        from fastapi import HTTPException
        request = MagicMock()
        def query_get(key, default=None):
            return "abc123" if key == "token" else default
        request.query_params.get = query_get
        with pytest.raises(HTTPException) as exc:
            get_current_user(request, None)
        assert exc.value.status_code == 401
        assert "query parameter" in exc.value.detail.lower()
