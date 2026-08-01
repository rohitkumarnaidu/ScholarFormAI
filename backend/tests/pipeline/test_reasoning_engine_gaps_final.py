# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Final gap-filling tests for ReasoningEngine — covers import fallbacks,
validation edge cases, normalization, cancellation paths, and
METRICS_AVAILABLE=False branches.
"""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

# ═══════════════════════════════════════════════════════════════════════════
# _validate_json_schema — edge cases
# ═══════════════════════════════════════════════════════════════════════════

class TestValidateJsonSchema:
    def test_not_dict(self, engine):
        assert engine._validate_json_schema("not_a_dict") is False

    def test_has_error_key(self, engine):
        assert engine._validate_json_schema({"error": "fail", "blocks": []}) is False

    def test_blocks_not_list(self, engine):
        assert engine._validate_json_schema({"blocks": "not_a_list"}) is False

    def test_block_not_dict(self, engine):
        data = {"blocks": [["not_a_dict"]]}
        assert engine._validate_json_schema(data) is False

    def test_semantic_type_not_string(self, engine):
        data = {"blocks": [{"block_id": "b1", "semantic_type": 123, "confidence": 0.5}]}
        assert engine._validate_json_schema(data) is False

    def test_confidence_not_convertible(self, engine):
        data = {"blocks": [{"block_id": "b1", "semantic_type": "BODY", "confidence": "bad"}]}
        assert engine._validate_json_schema(data) is False

    def test_confidence_out_of_range_high(self, engine):
        data = {"blocks": [{"block_id": "b1", "semantic_type": "BODY", "confidence": 1.5}]}
        assert engine._validate_json_schema(data) is False


# ═══════════════════════════════════════════════════════════════════════════
# _normalize_semantic_type — uncovered branches
# ═══════════════════════════════════════════════════════════════════════════

class TestNormalizeSemanticType:
    def test_none_value_returns_body(self, engine):
        assert engine._normalize_semantic_type(None) == "BODY"

    def test_abstract_and_heading_not_in_allowed(self, engine):
        result = engine._normalize_semantic_type("ABSTRACT_AND_HEADING")
        assert result == "ABSTRACT_HEADING"

    def test_abstract_only(self, engine):
        result = engine._normalize_semantic_type("MY_ABSTRACT")
        assert result == "ABSTRACT_BODY"

    def test_final_fallthrough_returns_body(self, engine):
        result = engine._normalize_semantic_type("RANDOM_TEXT_NO_MATCH")
        assert result == "BODY"


# ═══════════════════════════════════════════════════════════════════════════
# _normalize_confidence — edge cases
# ═══════════════════════════════════════════════════════════════════════════

class TestNormalizeConfidence:
    def test_uncastable_value_returns_default(self, engine):
        result = engine._normalize_confidence("not_a_number")
        assert result == 0.72

    def test_negative_value_clamped(self, engine):
        result = engine._normalize_confidence(-0.5)
        assert result == 0.0

    def test_over_one_clamped(self, engine):
        result = engine._normalize_confidence(2.0)
        assert result == 1.0


# ═══════════════════════════════════════════════════════════════════════════
# _normalize_instruction_payload — uncovered branches
# ═══════════════════════════════════════════════════════════════════════════

class TestNormalizeInstructionPayload:
    def test_instructions_fallback_when_blocks_not_list(self, engine):
        data = {"instructions": [{"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9}]}
        result = engine._normalize_instruction_payload(data, [{"block_id": "b1"}])
        assert result is not None
        assert len(result["blocks"]) == 1

    def test_no_blocks_or_instructions_returns_none(self, engine):
        assert engine._normalize_instruction_payload({}, []) is None

    def test_raw_block_not_dict_skipped(self, engine):
        data = {"blocks": [["not_a_dict"]]}
        assert engine._normalize_instruction_payload(data, []) is None

    def test_canonical_section_name_included(self, engine):
        data = {"blocks": [{"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9, "canonical_section_name": "Intro"}]}
        result = engine._normalize_instruction_payload(data, [{"block_id": "b1"}])
        assert result["blocks"][0]["canonical_section_name"] == "Intro"

    def test_model_name_included(self, engine):
        data = {"blocks": [{"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9}], "model": "deepseek-r1"}
        result = engine._normalize_instruction_payload(data, [{"block_id": "b1"}])
        assert result["model"] == "deepseek-r1"

    def test_latency_included(self, engine):
        data = {"blocks": [{"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9}], "latency": 0.45}
        result = engine._normalize_instruction_payload(data, [{"block_id": "b1"}])
        assert result["latency"] == 0.45


# ═══════════════════════════════════════════════════════════════════════════
# _rule_based_fallback — heuristic paths
# ═══════════════════════════════════════════════════════════════════════════

class TestRuleBasedFallback:
    def test_abstract_keyword_in_text(self, engine):
        result = engine._rule_based_fallback([{"block_id": "b1", "text": "Abstract: This paper studies..."}])
        assert result["blocks"][0]["semantic_type"] == "ABSTRACT_BODY"

    def test_reference_keyword_in_text(self, engine):
        result = engine._rule_based_fallback([{"block_id": "b2", "text": "References section"}])
        assert result["blocks"][0]["semantic_type"] == "REFERENCE_ENTRY"


# ═══════════════════════════════════════════════════════════════════════════
# generate_instruction_set — cancellation paths and METRICS_AVAILABLE=False
# ═══════════════════════════════════════════════════════════════════════════

class TestGenerateInstructionSetGaps:
    def test_cancelled_before_start(self, engine, sample_blocks):
        """Cancellation event set before generate_instruction_set."""
        event = threading.Event()
        event.set()
        with patch.object(engine, "_rule_based_fallback") as mock_fb:
            mock_fb.return_value = {"blocks": [], "fallback": True}
            result = engine.generate_instruction_set(sample_blocks, "rules", cancellation_event=event)
            assert result["fallback"] is True

    def test_cancelled_before_nvidia(self, engine, sample_blocks):
        """Cancellation event set before NVIDIA call."""
        engine.nvidia_available = True
        engine.nvidia_client = MagicMock()
        event = threading.Event()
        event.set()
        with patch.object(engine, "_rule_based_fallback") as mock_fb:
            mock_fb.return_value = {"blocks": [], "fallback": True}
            result = engine.generate_instruction_set(sample_blocks, "rules", cancellation_event=event)
            assert result["fallback"] is True

    def test_cancelled_before_deepseek(self, engine, sample_blocks):
        """Cancellation before DeepSeek when NVIDIA unavailable."""
        engine.nvidia_available = False
        engine.ollama_available = True
        engine.llm = MagicMock()
        event = threading.Event()
        event.set()
        with patch.object(engine, "_rule_based_fallback") as mock_fb:
            mock_fb.return_value = {"blocks": [], "fallback": True}
            result = engine.generate_instruction_set(sample_blocks, "rules", cancellation_event=event)
            assert result["fallback"] is True

    def test_nvidia_ollama_unavailable(self, engine, sample_blocks):
        """Both NVIDIA and Ollama unavailable -> rule-based."""
        engine.nvidia_available = False
        engine.ollama_available = False
        result = engine.generate_instruction_set(sample_blocks, "rules")
        assert result["fallback"] is True

    def test_nvidia_success_metrics_false(self, engine, sample_blocks):
        """NVIDIA success with METRICS_AVAILABLE=False."""
        engine.nvidia_available = True
        engine.nvidia_client = MagicMock()
        engine.nvidia_client.chat.return_value = '{"blocks": [{"block_id": "b0", "semantic_type": "TITLE", "confidence": 0.9}]}'
        with (
            patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", False),
            patch("app.pipeline.intelligence.reasoning_engine.METRICS_AVAILABLE", False),
        ):
            result = engine.generate_instruction_set(sample_blocks, "rules")
            assert result["fallback"] is False
            assert "model" in result

    def test_deepseek_success_metrics_false(self, engine, sample_blocks):
        """DeepSeek success with METRICS_AVAILABLE=False."""
        engine.nvidia_available = False
        engine.ollama_available = True
        engine.llm = MagicMock()
        result_data = {"blocks": [{"block_id": "b0", "semantic_type": "TITLE", "confidence": 0.9}]}
        with (
            patch.object(engine, "_generate_with_deepseek", return_value=result_data),
            patch.object(engine, "_validate_json_schema", return_value=True),
            patch("app.pipeline.intelligence.reasoning_engine.METRICS_AVAILABLE", False),
        ):
            result = engine.generate_instruction_set(sample_blocks, "rules")
            assert result["fallback"] is False
            assert "model" in result


# ═══════════════════════════════════════════════════════════════════════════
# _generate_with_nvidia — edge cases
# ═══════════════════════════════════════════════════════════════════════════

class TestGenerateWithNvidiaGaps:
    def test_cancelled_at_start(self, engine):
        engine.nvidia_available = True
        engine.nvidia_client = MagicMock()
        event = threading.Event()
        event.set()
        with patch.object(engine, "_rule_based_fallback") as mock_fb:
            mock_fb.return_value = {"blocks": [], "fallback": True}
            result = engine._generate_with_nvidia([{"block_id": "b1"}], "", cancellation_event=event)
            assert result["fallback"] is True

    def test_empty_blocks(self, engine):
        engine.nvidia_available = True
        engine.nvidia_client = MagicMock()
        result = engine._generate_with_nvidia([], "")
        assert result == {"blocks": []}

    def test_heading_level_hint(self, engine):
        engine.nvidia_available = True
        engine.nvidia_client = MagicMock()
        engine.nvidia_client.chat.return_value = '{"blocks": [{"block_id": "b1", "semantic_type": "HEADING_1", "confidence": 0.9}]}'
        with patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", False):
            result = engine._generate_with_nvidia(
                [{"block_id": "b1", "text": "Intro", "metadata": {"heading_level": 2}}], ""
            )
            assert result is not None

    def test_llm_service_success_skips_nvidia_client(self, engine):
        engine.nvidia_available = True
        engine.nvidia_client = MagicMock()
        with (
            patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine.LITELLM_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine._llm_generate",
                  return_value='{"blocks": [{"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9}]}'),
        ):
            result = engine._generate_with_nvidia(
                [{"block_id": "b1", "text": "Title"}], ""
            )
            assert result is not None
            assert "blocks" in result

    def test_both_sources_fail_returns_none(self, engine):
        engine.nvidia_available = True
        engine.nvidia_client = None
        with patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", False):
            result = engine._generate_with_nvidia(
                [{"block_id": "b1", "text": "Title"}], ""
            )
            assert result is None

    def test_json_regex_recovery(self, engine):
        """JSON with prefix/suffix text recovers via regex."""
        engine.nvidia_available = True
        engine.nvidia_client = MagicMock()
        engine.nvidia_client.chat.return_value = 'prefix {"blocks": []} suffix'
        with patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", False):
            result = engine._generate_with_nvidia(
                [{"block_id": "b1", "text": "Title"}], ""
            )
            assert result is None  # empty merged_blocks


# ═══════════════════════════════════════════════════════════════════════════
# _call_ollama — whole method
# ═══════════════════════════════════════════════════════════════════════════

class TestCallOllama:
    def test_success(self, engine):
        with patch("app.pipeline.intelligence.reasoning_engine.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": '{"blocks": []}'}
            mock_post.return_value = mock_response
            result = engine._call_ollama("test prompt")
            assert result == {"blocks": []}

    def test_request_exception(self, engine):
        with patch("app.pipeline.intelligence.reasoning_engine.requests.post", side_effect=Exception("timeout")):
            result = engine._call_ollama("test prompt")
            assert result is None


# ═══════════════════════════════════════════════════════════════════════════
# _generate_with_deepseek — litsLLM path & edge cases
# ═══════════════════════════════════════════════════════════════════════════

class TestGenerateWithDeepseekGaps:
    def test_litellm_path_success(self, engine):
        engine.llm = None
        engine.ollama_base_url = "http://localhost:11434"
        engine.ollama_available = True
        with (
            patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine.LITELLM_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine._llm_generate",
                  return_value='{"blocks": [{"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9}]}'),
        ):
            result = engine._generate_with_deepseek(
                [{"block_id": "b1", "text": "Title"}], "rules", max_retries=1
            )
            assert result is not None

    def test_no_source_available_returns_fallback(self, engine):
        engine.llm = None
        engine.ollama_base_url = "http://localhost:11434"
        engine.ollama_available = True
        engine.fallback_model = "test-model"
        with (
            patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", False),
            patch("app.pipeline.intelligence.reasoning_engine.LITELLM_AVAILABLE", False),
        ):
            result = engine._generate_with_deepseek(
                [{"block_id": "b1", "text": "Title"}], "rules", max_retries=0
            )
            assert result["fallback"] is True  # rule_based_fallback
