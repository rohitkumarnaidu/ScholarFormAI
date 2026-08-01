# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Comprehensive gap-filling tests for ReasoningEngine — covers uncovered branches
in health checking, NVIDIA LiteLLM calls, metrics recording, and edge cases.
"""

from __future__ import annotations

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
# _check_ollama_health — all branches
# ---------------------------------------------------------------------------

class TestCheckOllamaHealth:
    """Cover every branch in _check_ollama_health."""

    def test_non_dict_data_returns_true(self):
        """Response.json() returns non-dict -> server is up."""
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = "string"
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
                with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                    engine = ReasoningEngine()
                    assert engine.ollama_available is True

    def test_models_not_list_returns_true(self):
        """models field is not a list -> server is up."""
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"models": "not_a_list"}
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
                with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                    engine = ReasoningEngine()
                    assert engine.ollama_available is True

    def test_default_model_found(self):
        """Default fallback_model found in model list."""
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "models": [{"name": "deepseek-r1:8b"}]
            }
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
                with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                    engine = ReasoningEngine()
                    assert engine.ollama_available is True

    def test_auto_select_deepseek(self):
        """DeepSeek model auto-selected when default not found."""
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "models": [{"name": "deepseek-r1:7b"}]
            }
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
                with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                    engine = ReasoningEngine(model="mistral:7b")
                    assert engine.ollama_available is True
                    assert "deepseek" in engine.fallback_model

    def test_fallback_to_any_model(self):
        """No deepseek but other models available -> use first."""
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "models": [{"name": "llama3:8b"}]
            }
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
                with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                    engine = ReasoningEngine(model="mistral:7b")
                    assert engine.ollama_available is True
                    assert engine.fallback_model == "llama3:8b"

    def test_no_models_but_200_returns_true(self):
        """200 response with no models list -> still available."""
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"models": []}
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
                with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                    engine = ReasoningEngine()
                    assert engine.ollama_available is True

    def test_json_parse_exception_returns_true(self):
        """Exception in json parsing -> server reachable."""
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.side_effect = ValueError("bad json")
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
                with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                    engine = ReasoningEngine()
                    assert engine.ollama_available is True

    def test_request_exception_returns_false(self):
        """RequestException -> unavailable."""
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.side_effect = ConnectionError("refused")
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
                with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                    engine = ReasoningEngine()
                    assert engine.ollama_available is False

    def test_generic_exception_returns_false(self):
        """Generic Exception -> unavailable."""
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.side_effect = RuntimeError("unexpected")
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
                with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                    engine = ReasoningEngine()
                    assert engine.ollama_available is False

    def test_non_200_response(self):
        """Non-200 status code -> unavailable."""
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.return_value.status_code = 404
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
                with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                    engine = ReasoningEngine()
                    assert engine.ollama_available is False


# ---------------------------------------------------------------------------
# _call_nvidia_litellm — full coverage
# ---------------------------------------------------------------------------

class TestCallNvidiaLiteLLM:
    """Cover _call_nvidia_litellm method."""

    def test_llm_service_not_available(self, engine):
        """_LLM_SERVICE_AVAILABLE is False -> return None."""
        with patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", False):
            result = engine._call_nvidia_litellm([{"role": "user", "content": "hi"}])
            assert result is None

    def test_no_api_key(self, engine):
        """nvidia_api_key is empty -> return None."""
        engine.nvidia_api_key = ""
        with patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", True):
            result = engine._call_nvidia_litellm([{"role": "user", "content": "hi"}])
            assert result is None

    def test_empty_text_returned(self, engine):
        """_llm_generate returns empty -> return None."""
        engine.nvidia_api_key = "test-key"
        with (
            patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine.LITELLM_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine._llm_generate",
                  return_value="") as mock_gen,
        ):
            result = engine._call_nvidia_litellm([{"role": "user", "content": "hi"}])
            assert result is None
            mock_gen.assert_called_once()

    def test_successful_json_parse(self, engine):
        """Returns parsed JSON from _llm_generate."""
        engine.nvidia_api_key = "test-key"
        with (
            patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine.LITELLM_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine._llm_generate",
                  return_value='{"blocks": [{"block_id": "b1"}]}') as mock_gen,
        ):
            result = engine._call_nvidia_litellm([{"role": "user", "content": "hi"}])
            assert result == {"blocks": [{"block_id": "b1"}]}

    def test_json_extraction_from_text(self, engine):
        """Extracts JSON from text response with surrounding text."""
        engine.nvidia_api_key = "test-key"
        with (
            patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine.LITELLM_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine._llm_generate",
                  return_value='text before {"blocks": []} text after') as mock_gen,
        ):
            result = engine._call_nvidia_litellm([{"role": "user", "content": "hi"}])
            assert result == {"blocks": []}

    def test_no_json_found_returns_none(self, engine):
        """No JSON in response -> return None."""
        engine.nvidia_api_key = "test-key"
        with (
            patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine.LITELLM_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine._llm_generate",
                  return_value="plain text") as mock_gen,
        ):
            result = engine._call_nvidia_litellm([{"role": "user", "content": "hi"}])
            assert result is None


# ---------------------------------------------------------------------------
# generate_instruction_set — metrics recording coverage
# ---------------------------------------------------------------------------

class TestGenerateInstructionSetMetrics:
    """Cover the METRICS_AVAILABLE recording paths."""

    def test_nvidia_success_records_metrics(self, engine, sample_blocks):
        """NVIDIA success records metrics."""
        engine.nvidia_available = True
        engine.nvidia_client = MagicMock()
        normalized = {"blocks": [{"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9}]}

        mock_metrics = MagicMock()

        with (
            patch.object(engine, "_generate_with_nvidia", return_value=normalized),
            patch.object(engine, "_validate_json_schema", return_value=True),
            patch("app.pipeline.intelligence.reasoning_engine.METRICS_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine.get_model_metrics",
                  return_value=mock_metrics),
        ):
            result = engine.generate_instruction_set(sample_blocks, "rules")
            assert result["fallback"] is False
            mock_metrics.record_call.assert_called_once()
            args = mock_metrics.record_call.call_args
            assert args[0][0] == "nvidia"
            assert args[0][1] is True

    def test_nvidia_failure_records_metrics(self, engine, sample_blocks):
        """NVIDIA failure records metrics and fallback."""
        engine.nvidia_available = True
        engine.nvidia_client = MagicMock()
        mock_metrics = MagicMock()

        with (
            patch.object(engine, "_generate_with_nvidia", return_value=None),
            patch.object(engine, "_normalize_instruction_payload", return_value={"blocks": []}),
            patch.object(engine, "_validate_json_schema", return_value=False),
            patch.object(engine, "_is_cancelled", return_value=False),
            patch.object(engine, "_rule_based_fallback",
                         return_value={"blocks": [], "fallback": True, "confidence": 0.5}),
            patch("app.pipeline.intelligence.reasoning_engine.METRICS_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine.get_model_metrics",
                  return_value=mock_metrics),
        ):
            result = engine.generate_instruction_set(sample_blocks, "rules")
            assert mock_metrics.record_call.call_count >= 1
            assert mock_metrics.record_fallback.call_count >= 1

    def test_nvidia_exception_records_metrics(self, engine, sample_blocks):
        """NVIDIA exception records metrics and fallback."""
        engine.nvidia_available = True
        engine.nvidia_client = MagicMock()
        mock_metrics = MagicMock()

        with (
            patch.object(engine, "_generate_with_nvidia", side_effect=RuntimeError("failed")),
            patch.object(engine, "_is_cancelled", return_value=False),
            patch.object(engine, "_rule_based_fallback",
                         return_value={"blocks": [], "fallback": True, "confidence": 0.5}),
            patch("app.pipeline.intelligence.reasoning_engine.METRICS_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine.get_model_metrics",
                  return_value=mock_metrics),
        ):
            result = engine.generate_instruction_set(sample_blocks, "rules")
            assert mock_metrics.record_call.call_count >= 1

    def test_deepseek_success_records_metrics(self, engine, sample_blocks):
        """DeepSeek success records metrics."""
        engine.nvidia_available = False
        engine.ollama_available = True
        engine.llm = MagicMock()
        mock_metrics = MagicMock()

        normalized = {"blocks": [{"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9}]}

        with (
            patch.object(engine, "_generate_with_deepseek", return_value=normalized),
            patch.object(engine, "_validate_json_schema", return_value=True),
            patch("app.pipeline.intelligence.reasoning_engine.METRICS_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine.get_model_metrics",
                  return_value=mock_metrics),
        ):
            result = engine.generate_instruction_set(sample_blocks, "rules")
            assert result["fallback"] is False
            mock_metrics.record_call.assert_called_once()
            args = mock_metrics.record_call.call_args
            assert args[0][0] == "deepseek"
            assert args[0][1] is True

    def test_deepseek_fallback_payload_records_metrics(self, engine, sample_blocks):
        """DeepSeek returns fallback payload -> records metrics."""
        engine.nvidia_available = False
        engine.ollama_available = True
        engine.llm = MagicMock()
        mock_metrics = MagicMock()

        fallback_result = {"blocks": [{"block_id": "b0", "semantic_type": "BODY_TEXT", "confidence": 0.5}], "fallback": True, "confidence": 0.5}

        with (
            patch.object(engine, "_generate_with_deepseek", return_value=fallback_result),
            patch("app.pipeline.intelligence.reasoning_engine.METRICS_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine.get_model_metrics",
                  return_value=mock_metrics),
        ):
            result = engine.generate_instruction_set(sample_blocks, "rules")
            assert result["model"] == "rule_based"
            mock_metrics.record_call.assert_called_once()
            mock_metrics.record_fallback.assert_called_once()

    def test_deepseek_invalid_schema_records_metrics(self, engine, sample_blocks):
        """DeepSeek invalid schema -> records fallback metrics."""
        engine.nvidia_available = False
        engine.ollama_available = True
        engine.llm = MagicMock()
        mock_metrics = MagicMock()

        with (
            patch.object(engine, "_generate_with_deepseek", return_value=None),
            patch("app.pipeline.intelligence.reasoning_engine.METRICS_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine.get_model_metrics",
                  return_value=mock_metrics),
            patch("app.pipeline.intelligence.reasoning_engine.logger"),
        ):
            result = engine.generate_instruction_set(sample_blocks, "rules")
            assert result["fallback"] is True
            mock_metrics.record_call.assert_called_once()
            mock_metrics.record_fallback.assert_called_once()

    def test_deepseek_exception_records_metrics(self, engine, sample_blocks):
        """DeepSeek exception -> records fallback metrics."""
        engine.nvidia_available = False
        engine.ollama_available = True
        engine.llm = MagicMock()
        mock_metrics = MagicMock()

        with (
            patch.object(engine, "_generate_with_deepseek", side_effect=RuntimeError("fail")),
            patch("app.pipeline.intelligence.reasoning_engine.METRICS_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine.get_model_metrics",
                  return_value=mock_metrics),
            patch("app.pipeline.intelligence.reasoning_engine.logger"),
        ):
            result = engine.generate_instruction_set(sample_blocks, "rules")
            assert result["fallback"] is True
            mock_metrics.record_call.assert_called_once()
            mock_metrics.record_fallback.assert_called_once()


# ---------------------------------------------------------------------------
# _generate_with_nvidia — extras and edge cases
# ---------------------------------------------------------------------------

class TestGenerateWithNvidiaGaps:
    """Cover remaining branches in _generate_with_nvidia."""

    def _setup_nvidia(self, engine):
        engine.nvidia_available = True
        engine.nvidia_client = MagicMock()

    def test_metadata_hints_code_block(self, engine):
        """Code block metadata generates CODE hint."""
        self._setup_nvidia(engine)
        engine.nvidia_client.chat.return_value = '{"blocks": [{"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9}]}'
        with patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", False):
            result = engine._generate_with_nvidia(
                [{"block_id": "b1", "text": "Code", "metadata": {
                    "is_code_block": True,
                    "code_language": "python",
                }}], ""
            )
        assert result is not None
        assert len(result["blocks"]) == 1

    def test_metadata_hints_table(self, engine):
        """Table metadata generates TABLE hint."""
        self._setup_nvidia(engine)
        engine.nvidia_client.chat.return_value = '{"blocks": [{"block_id": "b1", "semantic_type": "TABLE", "confidence": 0.9}]}'
        with patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", False):
            result = engine._generate_with_nvidia(
                [{"block_id": "b1", "text": "Table data", "metadata": {"is_table": True}}], ""
            )
        assert result is not None

    def test_metadata_hints_list_item(self, engine):
        """List item metadata generates LIST_ITEM hint."""
        self._setup_nvidia(engine)
        engine.nvidia_client.chat.return_value = '{"blocks": [{"block_id": "b1", "semantic_type": "LIST_ITEM", "confidence": 0.9}]}'
        with patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", False):
            result = engine._generate_with_nvidia(
                [{"block_id": "b1", "text": "Item", "metadata": {"is_list_item": True}}], ""
            )
        assert result is not None

    def test_metadata_hints_font_size(self, engine):
        """Font size metadata generates Size hint."""
        self._setup_nvidia(engine)
        engine.nvidia_client.chat.return_value = '{"blocks": [{"block_id": "b1", "semantic_type": "BODY", "confidence": 0.9}]}'
        with patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", False):
            result = engine._generate_with_nvidia(
                [{"block_id": "b1", "text": "Text", "metadata": {"font_size": 14.0}}], ""
            )
        assert result is not None

    def test_metadata_hints_bold_style(self, engine):
        """Bold style generates BOLD hint."""
        self._setup_nvidia(engine)
        engine.nvidia_client.chat.return_value = '{"blocks": [{"block_id": "b1", "semantic_type": "BODY", "confidence": 0.9}]}'
        with patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", False):
            result = engine._generate_with_nvidia(
                [{"block_id": "b1", "text": "Bold", "metadata": {}, "style": {"bold": True}}], ""
            )
        assert result is not None

    def test_llm_service_fails_nvidia_client_succeeds(self, engine):
        """_llm_generate fails, nvidia_client fallback succeeds."""
        engine.nvidia_available = True
        engine.nvidia_client = MagicMock()
        engine.nvidia_client.chat.return_value = '{"blocks": [{"block_id": "b1", "semantic_type": "TITLE", "confidence": 0.9}]}'
        with (
            patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine.LITELLM_AVAILABLE", True),
            patch("app.pipeline.intelligence.reasoning_engine._llm_generate",
                  side_effect=RuntimeError("llm service down")),
        ):
            result = engine._generate_with_nvidia(
                [{"block_id": "b1", "text": "Title", "metadata": {}}], ""
            )
        assert result is not None
        assert len(result["blocks"]) == 1

    def test_parsed_non_dict_returns_none(self, engine):
        """Parsed result is not a dict -> None."""
        engine.nvidia_available = True
        engine.nvidia_client = MagicMock()
        engine.nvidia_client.chat.return_value = '["not", "a", "dict"]'
        with patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", False):
            result = engine._generate_with_nvidia(
                [{"block_id": "b1", "text": "T", "metadata": {}}], ""
            )
        assert result is None

    def test_parsed_no_blocks_returns_none(self, engine):
        """Parsed result has no 'blocks' key -> None."""
        engine.nvidia_available = True
        engine.nvidia_client = MagicMock()
        engine.nvidia_client.chat.return_value = '{"other": "data"}'
        with patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", False):
            result = engine._generate_with_nvidia(
                [{"block_id": "b1", "text": "T", "metadata": {}}], ""
            )
        assert result is None


class TestGenerateWithDeepSeekGaps:
    """Cover remaining branches in _generate_with_deepseek."""

    def test_llm_invoke_and_service_unavailable(self, engine):
        """No llm, no llm_service -> batch_result is None."""
        engine.llm = None
        with (
            patch("app.pipeline.intelligence.reasoning_engine._LLM_SERVICE_AVAILABLE", False),
            patch("app.pipeline.intelligence.reasoning_engine.LITELLM_AVAILABLE", False),
            patch("time.sleep"),
        ):
            result = engine._generate_with_deepseek(
                [{"block_id": "b1", "text": "Title"}], "", max_retries=0,
            )
        assert result["fallback"] is True

    def test_parse_response_json_decode_error(self, engine):
        """_parse_response helper: JSON decode error, no match -> None."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "{invalid json}"
        mock_llm.invoke.return_value = mock_response
        engine.llm = mock_llm
        with patch("app.pipeline.intelligence.reasoning_engine.logger"):
            result = engine._generate_with_deepseek(
                [{"block_id": "b1", "text": "Title"}], "", max_retries=0,
            )
        assert result["fallback"] is True

    def test_cancelled_during_retry_sleep(self, engine):
        """Cancelled during retry sleep -> rule fallback."""
        import threading
        event = threading.Event()

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("fail")
        engine.llm = mock_llm

        def set_event(*_args):
            event.set()

        with (
            patch("time.sleep", side_effect=set_event),
        ):
            result = engine._generate_with_deepseek(
                [{"block_id": "b1", "text": "Title"}], "", max_retries=1,
                cancellation_event=event,
            )
        assert result["fallback"] is True


# ---------------------------------------------------------------------------
# __init__ — remaining variations
# ---------------------------------------------------------------------------

class TestInitGaps:
    """Cover remaining __init__ edge cases."""

    def test_nvidia_enabled_in_non_pytest(self):
        """NVIDIA is enabled when PYTEST_CURRENT_TEST is not set."""
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
                with patch.dict("os.environ", clear=True):
                    with patch("app.pipeline.intelligence.reasoning_engine.settings") as ms:
                        ms.PIPELINE_REASONING_TIMEOUT_SECONDS = "30"
                        ms.NVIDIA_API_KEY = "test-key"
                        ms.ENABLE_NVIDIA_REASONER = True
                        ms.OLLAMA_BASE_URL = "http://localhost:11434"
                        with patch("app.services.nvidia_client.get_nvidia_client") as mock_nv:
                            mock_nv.return_value = MagicMock()
                            engine = ReasoningEngine()
                            assert engine.nvidia_api_key == "test-key"

    def test_ollama_init_failure(self):
        """ChatOllama initialization fails -> ollama_available=False."""
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"models": [{"name": "deepseek-r1:8b"}]}
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama",
                       side_effect=Exception("init failed")):
                with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                    engine = ReasoningEngine()
                    assert engine.ollama_available is False
                    assert engine.llm is None

    def test_timeout_setting_clamped(self):
        """Timeout is clamped to minimum 5."""
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
                with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                    engine = ReasoningEngine(timeout=3)
                    assert engine.timeout == 5

    def test_nvidia_client_none_disabled(self):
        """nvidia_client is None when get_nvidia_client returns None."""
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
                with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                    with patch("app.pipeline.intelligence.reasoning_engine.settings") as ms:
                        ms.PIPELINE_REASONING_TIMEOUT_SECONDS = "30"
                        ms.ENABLE_NVIDIA_REASONER = True
                        ms.NVIDIA_API_KEY = "test"
                        ms.OLLAMA_BASE_URL = "http://localhost:11434"
                        with patch("app.services.nvidia_client.get_nvidia_client",
                                   return_value=None):
                            engine = ReasoningEngine()
                            assert engine.nvidia_available is False

    def test_nvidia_enabled_exception(self):
        """get_nvidia_client raises exception -> nvidia not available."""
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
                with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                    with patch("app.pipeline.intelligence.reasoning_engine.settings") as ms:
                        ms.PIPELINE_REASONING_TIMEOUT_SECONDS = "30"
                        ms.ENABLE_NVIDIA_REASONER = True
                        ms.NVIDIA_API_KEY = "test"
                        ms.OLLAMA_BASE_URL = "http://localhost:11434"
                        with patch("app.services.nvidia_client.get_nvidia_client",
                                   side_effect=Exception("import error")):
                            engine = ReasoningEngine()
                            assert engine.nvidia_available is False


# ---------------------------------------------------------------------------
# _instruction_set_circuit_fallback
# ---------------------------------------------------------------------------

class TestInstructionSetCircuitFallback:
    """Circuit breaker fallback function."""

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

    def test_singleton(self):
        import app.pipeline.intelligence.reasoning_engine as re_mod
        re_mod._reasoning_engine = None
        with patch("app.pipeline.intelligence.reasoning_engine.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            with patch("app.pipeline.intelligence.reasoning_engine.ChatOllama"):
                with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}, clear=False):
                    e1 = get_reasoning_engine()
                    e2 = get_reasoning_engine()
        assert e1 is e2


# ---------------------------------------------------------------------------
# Normalize confidence edge
# ---------------------------------------------------------------------------

class TestNormalizeConfidenceGaps:
    """Remaining normalize_confidence edge cases."""

    def test_boolean_value_coerced(self, engine):
        """Boolean True -> 1.0."""
        assert engine._normalize_confidence(True) == 1.0

    def test_boolean_false_coerced(self, engine):
        """Boolean False -> 0.0."""
        assert engine._normalize_confidence(False) == 0.0


class TestNormalizeSemanticTypeGaps:
    """Remaining normalize_semantic_type edge cases."""

    def test_heading_prefix_other(self, engine):
        """HEADING_ prefixed falls to HEADING_1."""
        assert engine._normalize_semantic_type("HEADING_5") == "HEADING_1"

    def test_abstract_and_heading_words(self, engine):
        """ABSTRACT and HEADING both present -> ABSTRACT_HEADING."""
        assert engine._normalize_semantic_type("ABSTRACT_HEADING") == "ABSTRACT_HEADING"

    def test_bibliography_heading_present(self, engine):
        """BIBLIOGRAPHY text -> REFERENCE_ENTRY."""
        assert engine._normalize_semantic_type("BIBLIOGRAPHY") == "REFERENCE_ENTRY"


class TestValidateJsonSchemaGaps:
    """Remaining validate_json_schema edge cases."""

    def test_missing_block_id(self, engine):
        """Block without block_id -> False."""
        data = {"blocks": [{"semantic_type": "BODY", "confidence": 0.5}]}
        assert engine._validate_json_schema(data) is False

    def test_empty_string_block_id(self, engine):
        """Empty string block_id -> False."""
        data = {"blocks": [{"block_id": "", "semantic_type": "BODY", "confidence": 0.5}]}
        assert engine._validate_json_schema(data) is False

    def test_none_block_id(self, engine):
        """None block_id -> False."""
        data = {"blocks": [{"block_id": None, "semantic_type": "BODY", "confidence": 0.5}]}
        assert engine._validate_json_schema(data) is False
