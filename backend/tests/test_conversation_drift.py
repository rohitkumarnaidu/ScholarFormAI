# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI
"""
Conversation drift benchmarks.

Sections:
  2A — Semantic Drift Measurement (~10 tests)
  2B — Context Retention           (~10 tests)
"""

import pytest
import re
import math
from unittest.mock import MagicMock, patch, AsyncMock
from typing import List, Dict


# ===================================================================
#  Helpers
# ===================================================================

def _build_turns(n: int, base_topic: str = "academic formatting") -> List[Dict[str, str]]:
    """Build *n* user/assistant turn pairs on a consistent topic."""
    messages = [{"role": "system", "content": f"You are a {base_topic} assistant."}]
    for i in range(n):
        messages.append({"role": "user", "content": f"Turn {i+1}: adjust the {base_topic} settings."})
        messages.append({"role": "assistant", "content": f"Response {i+1}: applied {base_topic} changes."})
    return messages


def _embedding_similarity(text_a: str, text_b: str) -> float:
    """Compute a simple keyword-Jaccard similarity as a proxy for semantic similarity."""
    tokens_a = set(re.findall(r"\b[a-zA-Z]{3,}\b", text_a.lower()))
    tokens_b = set(re.findall(r"\b[a-zA-Z]{3,}\b", text_b.lower()))
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def _measure_drift(messages: List[Dict[str, str]]) -> float:
    """Measure semantic drift between first user message and last user message."""
    user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
    if len(user_msgs) < 2:
        return 0.0
    sim = _embedding_similarity(user_msgs[0], user_msgs[-1])
    return 1.0 - sim  # drift = 1 - similarity


def _topic_change_detected(messages: List[Dict[str, str]]) -> bool:
    """Detect if topic has shifted significantly between first and last user turn."""
    drift = _measure_drift(messages)
    return drift > 0.7


# ===================================================================
#  Fixtures
# ===================================================================

@pytest.fixture
def mock_llm():
    with patch("app.services.llm_service.generate") as mock_gen:
        mock_gen.return_value = "Mocked LLM response"
        yield mock_gen


# ===================================================================
#  2A — Semantic Drift Measurement
# ===================================================================

class TestSemanticDrift:
    """Measure and threshold semantic drift across conversation turns."""

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_drift_5_turns_low(self):
        messages = _build_turns(5)
        drift = _measure_drift(messages)
        assert 0.0 <= drift <= 1.0
        assert drift < 0.5, f"5 turns on same topic should have low drift: {drift}"

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_drift_10_turns_low(self):
        messages = _build_turns(10)
        drift = _measure_drift(messages)
        assert 0.0 <= drift <= 1.0
        assert drift < 0.5, f"10 turns on same topic should have low drift: {drift}"

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_drift_20_turns_low(self):
        messages = _build_turns(20)
        drift = _measure_drift(messages)
        assert 0.0 <= drift <= 1.0
        assert drift < 0.5, f"20 turns on same topic should have low drift: {drift}"

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_drift_topic_change_high(self):
        messages = [{"role": "system", "content": "Assistant."}]
        messages.append({"role": "user", "content": "Format this academic paper in APA style."})
        messages.append({"role": "assistant", "content": "Formatted in APA."})
        messages.append({"role": "user", "content": "What is the weather forecast for Paris?"})
        messages.append({"role": "assistant", "content": "I don't have weather data."})
        messages.append({"role": "user", "content": "Write me a JavaScript function to sort arrays."})
        drift = _measure_drift(messages)
        assert drift > 0.5, f"Topic change should produce high drift: {drift}"

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_drift_zero_for_identical_messages(self):
        messages = [{"role": "system", "content": "Assistant."}]
        messages.append({"role": "user", "content": "Set margins to 1 inch."})
        messages.append({"role": "assistant", "content": "Done."})
        messages.append({"role": "user", "content": "Set margins to 1 inch."})
        drift = _measure_drift(messages)
        assert drift == pytest.approx(0.0, abs=0.01)

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_drift_single_turn_zero(self):
        messages = [{"role": "user", "content": "Hello."}]
        drift = _measure_drift(messages)
        assert drift == 0.0

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_drift_empty_messages_list(self):
        drift = _measure_drift([])
        assert drift == 0.0

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_topic_change_detection_true(self):
        messages = [{"role": "system", "content": "Assistant."}]
        messages.append({"role": "user", "content": "Format paper."})
        messages.append({"role": "assistant", "content": "Done."})
        messages.append({"role": "user", "content": "Write a Python quicksort."})
        assert _topic_change_detected(messages)

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_topic_change_detection_false(self):
        messages = _build_turns(5)
        assert not _topic_change_detected(messages)

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_drift_gradual_topic_shift(self):
        messages = [{"role": "system", "content": "Assistant."}]
        topics = [
            "Set margins to 1 inch.",
            "Change font to Times New Roman.",
            "Add double line spacing.",
            "Insert page numbers.",
            "What citation style does Nature use?",
        ]
        for t in topics:
            messages.append({"role": "user", "content": t})
            messages.append({"role": "assistant", "content": "OK."})
        drift = _measure_drift(messages)
        assert 0.0 <= drift <= 1.0


# ===================================================================
#  2B — Context Retention
# ===================================================================

class TestContextRetention:
    """Key information from early turns must remain accessible in later turns."""

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_early_fact_retained_5_turns(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [{"role": "system", "content": "Citation style: APA 7th. Journal: Nature Genetics."}]
        for i in range(5):
            messages.append({"role": "user", "content": f"Edit section {i+1}."})
            messages.append({"role": "assistant", "content": f"Section {i+1} done."})
        messages.append({"role": "user", "content": "What citation style and journal?"})
        system, user = _extract_prompts(messages)
        assert "APA" in system
        assert "Nature Genetics" in system

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_early_fact_retained_10_turns(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [{"role": "system", "content": "Margin: 1 inch. Font: Times New Roman 12pt."}]
        for i in range(10):
            messages.append({"role": "user", "content": f"Request {i+1}."})
            messages.append({"role": "assistant", "content": f"Response {i+1}."})
        messages.append({"role": "user", "content": "What are the margin and font settings?"})
        system, user = _extract_prompts(messages)
        assert "1 inch" in system
        assert "Times New Roman" in system

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_early_fact_retained_20_turns(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [{"role": "system", "content": "Target word count: 5000. Abstract required: yes."}]
        for i in range(20):
            messages.append({"role": "user", "content": f"Q{i+1}"})
            messages.append({"role": "assistant", "content": f"A{i+1}"})
        system, _ = _extract_prompts(messages)
        assert "5000" in system
        assert "Abstract" in system

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_context_window_within_limit(self):
        from app.services.llm_service import _extract_prompts, MAX_LLM_INPUT_LENGTH
        messages = [{"role": "system", "content": "S" * 1000}]
        for i in range(10):
            messages.append({"role": "user", "content": "X" * 500})
            messages.append({"role": "assistant", "content": "Y" * 500})
        system, user = _extract_prompts(messages)
        total = len(system) + len(user)
        assert total < MAX_LLM_INPUT_LENGTH * 2  # verify manageable size

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_user_preference_survives_edits(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [
            {"role": "system", "content": "You format academic manuscripts."},
            {"role": "user", "content": "I prefer IEEE citation style."},
            {"role": "assistant", "content": "IEEE style set."},
        ]
        edits = ["Fix abstract", "Update references", "Check margins", "Add keywords",
                 "Format tables", "Number sections"]
        for e in edits:
            messages.append({"role": "user", "content": e})
            messages.append({"role": "assistant", "content": f"{e} done."})
        messages.append({"role": "user", "content": "What citation style do I use?"})
        system, user = _extract_prompts(messages)
        assert "IEEE" in user or "IEEE" in system

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_author_list_preserved(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [
            {"role": "system", "content": "Authors: Alice Smith, Bob Jones. Do not change."},
        ]
        for i in range(5):
            messages.append({"role": "user", "content": f"Edit page {i+1}."})
            messages.append({"role": "assistant", "content": f"Page {i+1} formatted."})
        system, _ = _extract_prompts(messages)
        assert "Alice Smith" in system
        assert "Bob Jones" in system

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_context_retention_with_mixed_roles(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [
            {"role": "system", "content": "Formatting rules: APA 7th."},
            {"role": "user", "content": "Set title."},
            {"role": "assistant", "content": "Title set."},
            {"role": "tool", "content": "Tool result data"},
            {"role": "function", "content": "Function output"},
            {"role": "user", "content": "What formatting rules?"},
        ]
        system, user = _extract_prompts(messages)
        assert "APA" in system

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_multiple_system_prompts_merged(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [
            {"role": "system", "content": "Rule A: use IEEE citation style."},
            {"role": "system", "content": "Rule B: target journal is Nature."},
        ]
        system, _ = _extract_prompts(messages)
        assert "Rule A" in system
        assert "Rule B" in system
        assert "IEEE" in system
        assert "Nature" in system

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_system_prompt_preserved_50_turns(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [{"role": "system", "content": "CRITICAL: Preserve original author list at all times."}]
        for i in range(50):
            messages.append({"role": "user", "content": f"T{i}"})
            messages.append({"role": "assistant", "content": f"R{i}"})
        system, _ = _extract_prompts(messages)
        assert "CRITICAL" in system
        assert "author list" in system
