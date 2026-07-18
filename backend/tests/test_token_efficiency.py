# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI
"""
Token efficiency and cost tracking tests.

Sections:
  3A — Token Usage Tracking  (~8 tests)
  3B — Cost Tracking         (~4 tests)
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict


# ===================================================================
#  Mock Token Counter & Cost Models
# ===================================================================

_PROVIDER_RATES: Dict[str, Dict[str, float]] = {
    "nvidia":  {"input_per_1k": 0.0005, "output_per_1k": 0.0015},
    "groq":    {"input_per_1k": 0.0002, "output_per_1k": 0.0006},
    "openai":  {"input_per_1k": 0.01,   "output_per_1k": 0.03},
    "ollama":  {"input_per_1k": 0.0,    "output_per_1k": 0.0},
}


class MockTokenCounter:
    """Simple mock token counter approximating ~4 chars per token."""

    CHARS_PER_TOKEN = 4.0

    @staticmethod
    def count(text: str) -> int:
        if not text:
            return 0
        return max(1, int(len(text) / MockTokenCounter.CHARS_PER_TOKEN))

    @staticmethod
    def count_messages(messages) -> int:
        total = 0
        for m in messages:
            total += MockTokenCounter.count(m.get("content", ""))
        return total


def _calculate_cost(input_tokens: int, output_tokens: int, provider: str) -> float:
    rates = _PROVIDER_RATES.get(provider, _PROVIDER_RATES["ollama"])
    input_cost = (input_tokens / 1000) * rates["input_per_1k"]
    output_cost = (output_tokens / 1000) * rates["output_per_1k"]
    return round(input_cost + output_cost, 6)


def _simulate_conversation_cost(turns: int, provider: str, tokens_per_turn: int = 200) -> float:
    input_tokens = tokens_per_turn * turns
    output_tokens = tokens_per_turn * turns
    return _calculate_cost(input_tokens, output_tokens, provider)


# ===================================================================
#  3A — Token Usage Tracking
# ===================================================================

class TestTokenCounting:
    """Mock token counting and budget enforcement."""

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_token_counter_empty(self):
        assert MockTokenCounter.count("") == 0
        assert MockTokenCounter.count(None) == 0

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_token_counter_short_text(self):
        assert MockTokenCounter.count("hello") >= 1

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_token_counter_long_text(self):
        tokens = MockTokenCounter.count("word " * 1000)
        assert 1000 <= tokens <= 1500

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_prompt_budget_not_exceeded(self):
        from app.services.llm_service import MAX_LLM_INPUT_LENGTH
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        prompt = builder.build("academic_paper", {"title": "Test", "authors": ["A"]}, {})
        estimated_tokens = MockTokenCounter.count(prompt)
        max_tokens = int(MAX_LLM_INPUT_LENGTH / MockTokenCounter.CHARS_PER_TOKEN)
        assert estimated_tokens <= max_tokens

    @pytest.mark.unit
    @pytest.mark.ai_quality
    @pytest.mark.parametrize("doc_type,metadata", [
        ("academic_paper", {"title": "Budget", "authors": ["A"],
                            "sections": [{"name": "Intro", "include": True}]}),
        ("resume", {"name": "N", "skills": ["Python"],
                    "education": [{"degree": "PhD", "institution": "U", "year": "2024"}]}),
        ("report", {"title": "R", "authors": ["A"],
                    "sections": [{"name": "Exec Summary", "include": True}]}),
        ("thesis", {"title": "T", "candidate_name": "C", "university": "U",
                    "chapter_number": 1, "abstract": "A",
                    "sections": [{"name": "Intro", "include": True}]}),
        ("portfolio", {"name": "N", "projects": [{"title": "P", "year": "2024", "description": "D"}]}),
    ])
    def test_all_prompt_types_under_token_budget(self, doc_type, metadata):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        prompt = builder.build(doc_type, metadata, {})
        tokens = MockTokenCounter.count(prompt)
        assert tokens <= 2500, f"{doc_type} uses {tokens} tokens (limit 2500)"

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_system_plus_user_under_budget(self):
        from app.services.llm_service import MAX_LLM_INPUT_LENGTH
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        system_prompt = "You are an academic formatting assistant. Follow all instructions precisely."
        user_prompt = builder.build("academic_paper", {"title": "Test", "authors": ["A"]}, {})
        total_chars = len(system_prompt) + len(user_prompt)
        assert total_chars <= MAX_LLM_INPUT_LENGTH

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_response_truncation_at_limit(self):
        from app.services.llm_service import sanitize_for_llm, MAX_LLM_INPUT_LENGTH
        text = "A" * (MAX_LLM_INPUT_LENGTH * 3)
        result = sanitize_for_llm(text)
        assert len(result) <= MAX_LLM_INPUT_LENGTH + 100


# ===================================================================
#  3B — Cost Tracking
# ===================================================================

class TestCostTracking:
    """Per-provider cost simulation and fallback chain costing."""

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_cost_nvidia(self):
        cost = _calculate_cost(1000, 500, "nvidia")
        expected = (1000 / 1000 * 0.0005) + (500 / 1000 * 0.0015)
        assert cost == pytest.approx(expected, abs=1e-6)
        assert cost > 0

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_cost_ollama_free(self):
        cost = _calculate_cost(10000, 5000, "ollama")
        assert cost == 0.0

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_cost_fallback_chain(self):
        chain = ["nvidia", "groq", "ollama"]
        total_cost = 0.0
        for provider in chain:
            cost = _simulate_conversation_cost(turns=5, provider=provider, tokens_per_turn=200)
            total_cost += cost
        assert total_cost >= 0
        nvidia_only = _simulate_conversation_cost(turns=5, provider="nvidia", tokens_per_turn=200)
        assert total_cost <= nvidia_only * 3

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_cost_conversation_scales_with_turns(self):
        cost_5 = _simulate_conversation_cost(5, "nvidia", 200)
        cost_20 = _simulate_conversation_cost(20, "nvidia", 200)
        assert cost_5 > 0
        assert cost_20 > cost_5
