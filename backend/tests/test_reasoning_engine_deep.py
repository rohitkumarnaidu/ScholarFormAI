# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.pipeline.intelligence.reasoning_engine import (
    ReasoningEngine,
    _instruction_set_circuit_fallback,
    get_reasoning_engine,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
            with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                return ReasoningEngine()


@pytest.fixture
def sample_blocks():
    return [
        {"block_id": "b1", "text": "Introduction", "index": 0},
        {"block_id": "b2", "text": "This paper presents a novel approach.", "index": 1},
    ]


# ---------------------------------------------------------------------------
# __init__ variations
# ---------------------------------------------------------------------------

class TestInit:
    def test_default_timeout_from_settings(self):
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
                with patch("app.pipeline.intelligence.reasoning_engine.settings") as mock_settings:
                    mock_settings.PIPELINE_REASONING_TIMEOUT_SECONDS = "60"
                    with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                        engine = ReasoningEngine()
        assert engine.timeout == 60

    def test_pytest_mode_disables_nvidia(self):
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
                with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                    engine = ReasoningEngine()
        assert engine.nvidia_api_key == ""
        assert engine.nvidia_available is False


# ---------------------------------------------------------------------------
# _is_cancelled
# ---------------------------------------------------------------------------

class TestIsCancelled:
    def test_none_not_cancelled(self, engine):
        assert engine._is_cancelled(None) is False

    def test_unset_event_not_cancelled(self, engine):
        import threading
        e = threading.Event()
        assert engine._is_cancelled(e) is False

    def test_set_event_is_cancelled(self, engine):
        import threading
        e = threading.Event()
        e.set()
        assert engine._is_cancelled(e) is True

    def test_object_without_is_set(self, engine):
        assert engine._is_cancelled(SimpleNamespace()) is False


# ---------------------------------------------------------------------------
# _normalize_semantic_type
# ---------------------------------------------------------------------------

class TestNormalizeSemanticType:
    def test_none_returns_body(self, engine):
        assert engine._normalize_semantic_type(None) == "BODY"

    def test_known_type(self, engine):
        assert engine._normalize_semantic_type("TITLE") == "TITLE"

    def test_with_hyphens(self, engine):
        assert engine._normalize_semantic_type("heading-1") == "HEADING_1"

    def test_with_spaces(self, engine):
        assert engine._normalize_semantic_type("reference entry") == "REFERENCE_ENTRY"

    def test_alias_body_text(self, engine):
        assert engine._normalize_semantic_type("BODY_TEXT") == "BODY"

    def test_alias_heading(self, engine):
        assert engine._normalize_semantic_type("HEADING") == "HEADING_1"

    def test_abstract_heading(self, engine):
        assert engine._normalize_semantic_type("ABSTRACT_HEADING") == "ABSTRACT_HEADING"

    def test_abstract_in_name_with_heading(self, engine):
        assert engine._normalize_semantic_type("SOME_ABSTRACT_HEADING_STUFF") == "ABSTRACT_HEADING"

    def test_abstract_alone(self, engine):
        assert engine._normalize_semantic_type("ABSTRACT") == "ABSTRACT_BODY"

    def test_reference_fallback(self, engine):
        assert engine._normalize_semantic_type("MY_REFERENCE") == "REFERENCE_ENTRY"

    def test_biblio_fallback(self, engine):
        assert engine._normalize_semantic_type("BIBLIO") == "REFERENCE_ENTRY"

    def test_heading_prefix_fallback(self, engine):
        assert engine._normalize_semantic_type("HEADING_X") == "HEADING_1"

    def test_unknown_falls_to_body(self, engine):
        assert engine._normalize_semantic_type("GARBAGE_TYPE") == "BODY"

    def test_case_insensitive(self, engine):
        assert engine._normalize_semantic_type("title") == "TITLE"


# ---------------------------------------------------------------------------
# _normalize_confidence
# ---------------------------------------------------------------------------

class TestNormalizeConfidence:
    def test_valid_float(self, engine):
        assert engine._normalize_confidence(0.85) == 0.85

    def test_string_number(self, engine):
        assert engine._normalize_confidence("0.75") == 0.75

    def test_none_uses_default(self, engine):
        assert engine._normalize_confidence(None) == 0.72

    def test_below_zero_clamped(self, engine):
        assert engine._normalize_confidence(-0.5) == 0.0

    def test_above_one_clamped(self, engine):
        assert engine._normalize_confidence(1.5) == 1.0

    def test_unparseable_uses_default(self, engine):
        assert engine._normalize_confidence("abc") == 0.72

    def test_custom_default(self, engine):
        assert engine._normalize_confidence(None, default=0.5) == 0.5


# ---------------------------------------------------------------------------
# _normalize_instruction_payload
# ---------------------------------------------------------------------------

class TestNormalizeInstructionPayload:
    def test_none_data(self, engine):
        assert engine._normalize_instruction_payload(None, []) is None

    def test_not_dict(self, engine):
        assert engine._normalize_instruction_payload("string", []) is None

    def test_no_blocks_key(self, engine):
        assert engine._normalize_instruction_payload({"other": 1}, []) is None

    def test_instructions_alternative_key(self, engine):
        data = {"instructions": [{"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9}]}
        result = engine._normalize_instruction_payload(data, [{"block_id": "b1"}])
        assert result is not None
        assert result["blocks"][0]["semantic_type"] == "TITLE"

    def test_blocks_not_list(self, engine):
        assert engine._normalize_instruction_payload({"blocks": "string"}, []) is None

    def test_complete_normalization(self, engine):
        data = {
            "blocks": [
                {"block_id": "b1", "semantic_type": "BODY_TEXT", "confidence": 0.95},
                {"block_id": "b2", "type": "HEADING", "score": 0.8},
            ]
        }
        source_blocks = [{"block_id": "b1"}, {"block_id": "b2"}]
        result = engine._normalize_instruction_payload(data, source_blocks)
        assert result is not None
        assert len(result["blocks"]) == 2
        assert result["blocks"][0]["semantic_type"] == "BODY"
        assert result["blocks"][1]["semantic_type"] == "HEADING_1"

    def test_block_id_fallbacks(self, engine):
        data = {"blocks": [{"id": "x", "label": "TITLE", "probability": 0.9}]}
        result = engine._normalize_instruction_payload(data, [{}])
        assert result["blocks"][0]["block_id"] == "x"
        assert result["blocks"][0]["semantic_type"] == "TITLE"

    def test_avg_confidence(self, engine):
        data = {"blocks": [
            {"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9},
            {"block_id": "b2", "semantic_type": "BODY", "confidence": 0.7},
        ]}
        result = engine._normalize_instruction_payload(data, [{}, {}])
        assert result["confidence"] == 0.8

    def test_model_and_latency_passed(self, engine):
        data = {
            "blocks": [{"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9}],
            "model": "deepseek-r1",
            "latency": 1.23,
        }
        result = engine._normalize_instruction_payload(data, [{}])
        assert result["model"] == "deepseek-r1"
        assert result["latency"] == 1.23

    def test_canonical_section_name(self, engine):
        data = {
            "blocks": [{
                "block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9,
                "canonical_section_name": "Introduction",
            }]
        }
        result = engine._normalize_instruction_payload(data, [{}])
        assert result["blocks"][0]["canonical_section_name"] == "Introduction"

    def test_skips_non_dict_block(self, engine):
        data = {"blocks": ["string", {"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9}]}
        result = engine._normalize_instruction_payload(data, [{}, {}])
        assert len(result["blocks"]) == 1

    def test_no_normalized_blocks_returns_none(self, engine):
        data = {"blocks": ["string"]}
        assert engine._normalize_instruction_payload(data, []) is None


# ---------------------------------------------------------------------------
# _rule_based_fallback
# ---------------------------------------------------------------------------

class TestRuleBasedFallback:
    def test_heading_with_colon(self, engine):
        blocks = [{"block_id": "b1", "text": "Introduction:", "index": 0}]
        result = engine._rule_based_fallback(blocks)
        assert result["blocks"][0]["semantic_type"] == "HEADING_1"

    def test_abstract_text(self, engine):
        blocks = [{"block_id": "b1", "text": "Abstract: This paper...", "index": 0}]
        result = engine._rule_based_fallback(blocks)
        assert result["blocks"][0]["semantic_type"] == "ABSTRACT_BODY"

    def test_introduction_text(self, engine):
        blocks = [{"block_id": "b1", "text": "Introduction to the topic", "index": 0}]
        result = engine._rule_based_fallback(blocks)
        assert result["blocks"][0]["semantic_type"] == "HEADING_1"

    def test_reference_text(self, engine):
        blocks = [{"block_id": "b1", "text": "References", "index": 0}]
        result = engine._rule_based_fallback(blocks)
        assert result["blocks"][0]["semantic_type"] == "REFERENCE_ENTRY"

    def test_bibliography_text(self, engine):
        blocks = [{"block_id": "b1", "text": "Bibliography", "index": 0}]
        result = engine._rule_based_fallback(blocks)
        assert result["blocks"][0]["semantic_type"] == "REFERENCE_ENTRY"

    def test_body_default(self, engine):
        blocks = [{"block_id": "b1", "text": "Regular paragraph text.", "index": 0}]
        result = engine._rule_based_fallback(blocks)
        assert result["blocks"][0]["semantic_type"] == "BODY_TEXT"

    def test_fallback_flag_true(self, engine):
        blocks = [{"block_id": "b1", "text": "Text", "index": 0}]
        result = engine._rule_based_fallback(blocks)
        assert result["fallback"] is True
        assert result["confidence"] == 0.5


# ---------------------------------------------------------------------------
# _call_ollama (direct HTTP path)
# ---------------------------------------------------------------------------

class TestCallOllama:
    def test_successful_call(self, engine):
        with patch("app.pipeline.intelligence.reasoning_engine.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"response": '{"blocks": []}'}
            result = engine._call_ollama("test prompt")
        assert result == {"blocks": []}

    def test_json_extraction_from_text(self, engine):
        with patch("app.pipeline.intelligence.reasoning_engine.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"response": 'text before {"blocks": []} text after'}
            result = engine._call_ollama("test prompt")
        assert result == {"blocks": []}

    def test_no_json_found(self, engine):
        with patch("app.pipeline.intelligence.reasoning_engine.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"response": "no json here"}
            result = engine._call_ollama("test prompt")
        assert result is None

    def test_request_exception(self, engine):
        with patch("app.pipeline.intelligence.reasoning_engine.requests.post", side_effect=Exception("timeout")):
            result = engine._call_ollama("test prompt")
        assert result is None


# ---------------------------------------------------------------------------
# _validate_json_schema
# ---------------------------------------------------------------------------

class TestValidateJsonSchema:
    def test_not_dict(self, engine):
        assert engine._validate_json_schema("string") is False

    def test_error_key(self, engine):
        assert engine._validate_json_schema({"error": "msg"}) is False

    def test_blocks_not_list(self, engine):
        assert engine._validate_json_schema({"blocks": "not-list"}) is False

    def test_block_not_dict(self, engine):
        assert engine._validate_json_schema({"blocks": ["string"]}) is False

    def test_empty_block_id(self, engine):
        data = {"blocks": [{"block_id": "", "semantic_type": "BODY", "confidence": 0.5}]}
        assert engine._validate_json_schema(data) is False

    def test_missing_semantic_type(self, engine):
        data = {"blocks": [{"block_id": "b1", "confidence": 0.5}]}
        assert engine._validate_json_schema(data) is False

    def test_empty_semantic_type(self, engine):
        data = {"blocks": [{"block_id": "b1", "semantic_type": "", "confidence": 0.5}]}
        assert engine._validate_json_schema(data) is False

    def test_confidence_not_floatable(self, engine):
        data = {"blocks": [{"block_id": "b1", "semantic_type": "BODY", "confidence": "abc"}]}
        assert engine._validate_json_schema(data) is False

    def test_confidence_out_of_range_low(self, engine):
        data = {"blocks": [{"block_id": "b1", "semantic_type": "BODY", "confidence": -0.1}]}
        assert engine._validate_json_schema(data) is False

    def test_confidence_out_of_range_high(self, engine):
        data = {"blocks": [{"block_id": "b1", "semantic_type": "BODY", "confidence": 1.1}]}
        assert engine._validate_json_schema(data) is False


# ---------------------------------------------------------------------------
# generate_instruction_set - cancellation
# ---------------------------------------------------------------------------

class TestGenerateInstructionSetCancellation:
    def test_cancelled_before_start(self, engine, sample_blocks):
        import threading
        event = threading.Event()
        event.set()
        result = engine.generate_instruction_set(sample_blocks, "rules", cancellation_event=event)
        assert result["fallback"] is True

    def test_cancelled_during_nvidia_phase(self, engine, sample_blocks):
        engine.nvidia_available = True
        engine.nvidia_client = MagicMock()
        import threading
        event = threading.Event()

        def set_event(*a, **kw):
            event.set()
            return {"blocks": []}

        with patch.object(engine, "_generate_with_nvidia", side_effect=set_event):
            result = engine.generate_instruction_set(sample_blocks, "rules", cancellation_event=event)
        assert result["fallback"] is True

    def test_cancelled_before_deepseek(self, engine, sample_blocks):
        engine.nvidia_available = False
        import threading
        event = threading.Event()

        with patch.object(engine, "_is_cancelled", side_effect=[False, True]):
            with patch.object(engine, "_generate_with_nvidia", return_value=None):
                result = engine.generate_instruction_set(sample_blocks, "rules", cancellation_event=event)
        assert result["fallback"] is True


# ---------------------------------------------------------------------------
# generate_instruction_set - NVIDIA path
# ---------------------------------------------------------------------------

class TestGenerateInstructionSetNvidia:
    def test_successful_nvidia(self, engine, sample_blocks):
        engine.nvidia_available = True
        engine.nvidia_client = MagicMock()
        normalized = {"blocks": [{"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9}]}
        with patch.object(engine, "_generate_with_nvidia", return_value=normalized):
            with patch.object(engine, "_validate_json_schema", return_value=True):
                with patch("app.pipeline.intelligence.reasoning_engine.METRICS_AVAILABLE", False):
                    result = engine.generate_instruction_set(sample_blocks, "rules")
        assert result["fallback"] is False
        assert result["model"] == "NVIDIA Llama 3.3 70B"

    def test_nvidia_schema_invalid(self, engine, sample_blocks):
        engine.nvidia_available = True
        engine.nvidia_client = MagicMock()
        with patch.object(engine, "_generate_with_nvidia", return_value=None):
            with patch.object(engine, "_normalize_instruction_payload", return_value={"blocks": []}):
                with patch.object(engine, "_validate_json_schema", return_value=False):
                    with patch("app.pipeline.intelligence.reasoning_engine.METRICS_AVAILABLE", False):
                        with patch.object(engine, "_is_cancelled", return_value=False):
                            result = engine.generate_instruction_set(sample_blocks, "rules")
        assert result["fallback"] is True

    def test_nvidia_exception(self, engine, sample_blocks):
        engine.nvidia_available = True
        engine.nvidia_client = MagicMock()
        with patch.object(engine, "_generate_with_nvidia", side_effect=Exception("NVIDIA failed")):
            with patch("app.pipeline.intelligence.reasoning_engine.METRICS_AVAILABLE", False):
                result = engine.generate_instruction_set(sample_blocks, "rules")
        assert result["fallback"] is True
        assert "blocks" in result


# ---------------------------------------------------------------------------
# generate_instruction_set - DeepSeek path
# ---------------------------------------------------------------------------

class TestGenerateInstructionSetDeepSeek:
    def test_deepseek_returns_fallback_payload(self, engine, sample_blocks):
        engine.nvidia_available = False
        engine.ollama_available = True
        engine.llm = MagicMock()
        fallback_result = _instruction_set_circuit_fallback(engine, sample_blocks, "rules")
        with patch.object(engine, "_generate_with_deepseek", return_value=fallback_result):
            with patch("app.pipeline.intelligence.reasoning_engine.METRICS_AVAILABLE", False):
                result = engine.generate_instruction_set(sample_blocks, "rules")
        assert result["model"] == "rule_based"

    def test_deepseek_successful(self, engine, sample_blocks):
        engine.nvidia_available = False
        engine.ollama_available = True
        engine.llm = MagicMock()
        normalized = {"blocks": [{"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9}]}
        with patch.object(engine, "_generate_with_deepseek", return_value=normalized):
            with patch.object(engine, "_validate_json_schema", return_value=True):
                with patch("app.pipeline.intelligence.reasoning_engine.METRICS_AVAILABLE", False):
                    result = engine.generate_instruction_set(sample_blocks, "rules")
        assert result["fallback"] is False
        assert result["model"] == engine.model

    def test_deepseek_invalid_schema(self, engine, sample_blocks):
        engine.nvidia_available = False
        engine.ollama_available = True
        engine.llm = MagicMock()
        with patch.object(engine, "_generate_with_deepseek", return_value=None):
            with patch("app.pipeline.intelligence.reasoning_engine.METRICS_AVAILABLE", False):
                with patch("app.pipeline.intelligence.reasoning_engine.logger"):
                    result = engine.generate_instruction_set(sample_blocks, "rules")
        assert result["fallback"] is True

    def test_deepseek_exception(self, engine, sample_blocks):
        engine.nvidia_available = False
        engine.ollama_available = True
        engine.llm = MagicMock()
        with patch.object(engine, "_generate_with_deepseek", side_effect=Exception("DeepSeek error")):
            with patch("app.pipeline.intelligence.reasoning_engine.METRICS_AVAILABLE", False):
                with patch("app.pipeline.intelligence.reasoning_engine.logger"):
                    result = engine.generate_instruction_set(sample_blocks, "rules")
        assert result["fallback"] is True

    def test_rule_based_final_fallback(self, engine, sample_blocks):
        engine.nvidia_available = False
        engine.ollama_available = False
        result = engine.generate_instruction_set(sample_blocks, "rules")
        assert result["fallback"] is True


# ---------------------------------------------------------------------------
# _generate_with_nvidia
# ---------------------------------------------------------------------------

class TestGenerateWithNvidia:
    def test_cancelled_returns_rule_fallback(self, engine):
        import threading
        event = threading.Event()
        event.set()
        with patch.object(engine, "_rule_based_fallback", return_value={"fallback": True}):
            result = engine._generate_with_nvidia([], "", cancellation_event=event)
        assert result["fallback"] is True

    def test_empty_blocks(self, engine):
        result = engine._generate_with_nvidia([], "")
        assert result == {"blocks": []}

    def test_llm_service_success(self, engine):
        engine.nvidia_client = MagicMock()
        with patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", True):
            with patch("app.pipeline.intelligence.reasoning_engine.LITELLM_AVAILABLE", True):
                with patch("app.pipeline.intelligence.reasoning_engine._llm_generate", return_value='{"blocks": [{"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9}]}'):
                    result = engine._generate_with_nvidia(
                        [{"block_id": "b1", "text": "Title", "metadata": {}}], ""
                    )
        assert result is not None
        assert len(result["blocks"]) == 1

    def test_llm_service_fails_falls_to_nvidia_client(self, engine):
        mock_client = MagicMock()
        mock_client.chat.return_value = '{"blocks": [{"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9}]}'
        engine.nvidia_client = mock_client
        with patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", True):
            with patch("app.pipeline.intelligence.reasoning_engine.LITELLM_AVAILABLE", True):
                with patch("app.pipeline.intelligence.reasoning_engine._llm_generate", return_value=""):
                    result = engine._generate_with_nvidia(
                        [{"block_id": "b1", "text": "Title", "metadata": {}}], ""
                    )
        assert result is not None
        assert len(result["blocks"]) == 1

    def test_no_response_returns_none(self, engine):
        engine.nvidia_client = MagicMock()
        engine.nvidia_client.chat.return_value = ""
        with patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", False):
            result = engine._generate_with_nvidia(
                [{"block_id": "b1", "text": "Title", "metadata": {}}], ""
            )
        assert result is None

    def test_parses_json_from_non_json_response(self, engine):
        engine.nvidia_client = MagicMock()
        engine.nvidia_client.chat.return_value = 'text {"blocks": [{"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9}]} text'
        with patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", False):
            result = engine._generate_with_nvidia(
                [{"block_id": "b1", "text": "T", "metadata": {}}], ""
            )
        assert result is not None
        assert len(result["blocks"]) == 1

    def test_metadata_hints_included(self, engine):
        engine.nvidia_client = MagicMock()
        engine.nvidia_client.chat.return_value = '{"blocks": [{"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9}]}'
        with patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", False):
            result = engine._generate_with_nvidia(
                [{"block_id": "b1", "text": "Title", "metadata": {
                    "heading_level": 1,
                    "is_code_block": True,
                    "code_language": "python",
                    "is_table": True,
                    "is_list_item": True,
                    "font_size": 14.0,
                }, "style": {"bold": True}}], ""
            )
        assert result is not None
        assert len(result["blocks"]) == 1


# ---------------------------------------------------------------------------
# _generate_with_deepseek
# ---------------------------------------------------------------------------

class TestGenerateWithDeepSeek:
    def test_all_retries_fail_falls_to_rules(self, engine):
        engine.ollama_available = True
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("persistent error")
        engine.llm = mock_llm
        with patch("time.sleep"):
            result = engine._generate_with_deepseek(
                [{"block_id": "b1", "text": "Title"}], "", max_retries=1,
            )
        assert result["fallback"] is True

    def test_cancellation_during_loop(self, engine):
        import threading
        event = threading.Event()

        def delayed_set():
            event.set()
            raise Exception("fail")

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = delayed_set
        engine.llm = mock_llm
        with patch("time.sleep"):
            result = engine._generate_with_deepseek(
                [{"block_id": "b1", "text": "Title"}], "", max_retries=1,
                cancellation_event=event,
            )
        assert result["fallback"] is True

    def test_batch_result_not_dict_falls_to_rules(self, engine):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "not-a-dict"
        mock_llm.invoke.return_value = mock_response
        engine.llm = mock_llm
        with patch("app.pipeline.intelligence.reasoning_engine.logger"):
            result = engine._generate_with_deepseek(
                [{"block_id": "b1", "text": "Title"}], "", max_retries=0,
            )
        assert result["fallback"] is True

    def test_empty_merged_blocks_falls_to_rules(self, engine):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '{"other": "data"}'
        mock_llm.invoke.return_value = mock_response
        engine.llm = mock_llm
        result = engine._generate_with_deepseek(
            [{"block_id": "b1", "text": "Title"}], "", max_retries=0,
        )
        assert result["fallback"] is True

    def test_llm_service_fallback(self, engine):
        engine.llm = None
        with patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", True):
            with patch("app.pipeline.intelligence.reasoning_engine.LITELLM_AVAILABLE", True):
                with patch("app.pipeline.intelligence.reasoning_engine._llm_generate", return_value='{"blocks": [{"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9}]}'):
                    result = engine._generate_with_deepseek(
                        [{"block_id": "b1", "text": "Title"}], "", max_retries=0,
                    )
        assert result is not None
        assert len(result.get("blocks", [])) == 1

    def test_parse_json_failure_fallback(self, engine):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "text {blocks: []} text"
        mock_llm.invoke.return_value = mock_response
        engine.llm = mock_llm
        with patch("app.pipeline.intelligence.reasoning_engine.logger"):
            result = engine._generate_with_deepseek(
                [{"block_id": "b1", "text": "Title"}], "", max_retries=0,
            )
        assert result["fallback"] is True


# ---------------------------------------------------------------------------
# _instruction_set_circuit_fallback (module-level function)
# ---------------------------------------------------------------------------

class TestInstructionSetCircuitFallback:
    def test_delegates_to_rule_based(self, engine):
        blocks = [{"block_id": "b1", "text": "Introduction:", "index": 0}]
        result = _instruction_set_circuit_fallback(engine, blocks, "rules")
        assert result["fallback"] is True
        assert result["blocks"][0]["semantic_type"] == "HEADING_1"


# ---------------------------------------------------------------------------
# get_reasoning_engine (singleton)
# ---------------------------------------------------------------------------

class TestGetReasoningEngine:
    def test_returns_engine(self):
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
                with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                    engine = get_reasoning_engine()
        assert isinstance(engine, ReasoningEngine)

    def test_singleton_returns_same_instance(self):
        import app.pipeline.intelligence.reasoning_engine as re_mod
        re_mod._reasoning_engine = None
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
                with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                    e1 = get_reasoning_engine()
                    e2 = get_reasoning_engine()
        assert e1 is e2
