# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def section_prompts():
    from app.pipeline.generation.section_prompts import SECTION_PROMPTS, _truncate, get_section_prompt
    return SECTION_PROMPTS, _truncate, get_section_prompt


class TestSectionPromptsDict:
    def test_has_expected_keys(self, section_prompts):
        sp, _, _ = section_prompts
        expected = {"Abstract", "Introduction", "Literature Review", "Methods", "Results", "Discussion", "Conclusion"}
        assert expected.issubset(sp.keys())

    def test_all_values_non_empty(self, section_prompts):
        sp, _, _ = section_prompts
        for key, val in sp.items():
            assert val, f"Empty prompt for {key}"

    def test_abstract_mentions_no_citations(self, section_prompts):
        sp, _, _ = section_prompts
        assert "do not include citations" in sp["Abstract"].lower()

    def test_discussion_mentions_interpretation(self, section_prompts):
        sp, _, _ = section_prompts
        assert "interpret" in sp["Discussion"].lower()


class TestTruncate:
    def test_none(self, section_prompts):
        _, trunc, _ = section_prompts
        assert trunc(None) == ""

    def test_empty(self, section_prompts):
        _, trunc, _ = section_prompts
        assert trunc("") == ""

    def test_short_text(self, section_prompts):
        _, trunc, _ = section_prompts
        assert trunc("Hello world") == "Hello world"

    def test_long_text_truncated(self, section_prompts):
        _, trunc, _ = section_prompts
        long = "word " * 1000
        result = trunc(long, limit=100)
        assert len(result) <= 104
        assert result.endswith("...")

    def test_cleans_whitespace(self, section_prompts):
        _, trunc, _ = section_prompts
        result = trunc("  hello   world  ", limit=100)
        assert result == "hello world"

    def test_exact_limit(self, section_prompts):
        _, trunc, _ = section_prompts
        text = "a" * 200
        result = trunc(text, limit=200)
        assert result == text

    def test_one_over_limit(self, section_prompts):
        _, trunc, _ = section_prompts
        text = "a" * 101
        result = trunc(text, limit=100)
        assert result.endswith("...")

    def test_integer_limit_truncates(self, section_prompts):
        _, trunc, _ = section_prompts
        text = "hello world foo bar"
        result = trunc(text, limit=5)
        assert result.endswith("...")

    def test_non_string(self, section_prompts):
        _, trunc, _ = section_prompts
        assert trunc(12345) == "12345"


class TestGetSectionPrompt:
    def test_known_section(self, section_prompts):
        sp, _, gsp = section_prompts
        context = {"task_spec": {"title": "Test"}, "template_rules": [], "outline": {"sections": []}, "previous_sections": {}}
        result = gsp("Introduction", context)
        assert sp["Introduction"] in result
        assert "Document context" in result
        assert "Template rules" in result

    def test_unknown_section(self, section_prompts):
        _, _, gsp = section_prompts
        context = {"task_spec": {}, "template_rules": [], "outline": {}, "previous_sections": {}}
        result = gsp("Custom Section", context)
        assert "Write a rigorous academic section" in result

    def test_includes_previous_sections(self, section_prompts):
        _, _, gsp = section_prompts
        context = {
            "task_spec": {},
            "template_rules": [],
            "outline": {},
            "previous_sections": {"Intro": "Hello world text here"},
        }
        result = gsp("Methods", context)
        assert "Previous sections" in result

    def test_empty_previous_sections_omitted(self, section_prompts):
        _, _, gsp = section_prompts
        context = {
            "task_spec": {},
            "template_rules": [],
            "outline": {},
            "previous_sections": {},
        }
        result = gsp("Methods", context)
        assert "Previous sections" not in result

    def test_previous_sections_truncated(self, section_prompts):
        _, _, gsp = section_prompts
        long_val = "word " * 5000
        context = {
            "task_spec": {},
            "template_rules": [],
            "outline": {},
            "previous_sections": {"Intro": long_val},
        }
        result = gsp("Methods", context)
        assert len(result) < len(long_val) * 2

    def test_previous_sections_skips_non_string(self, section_prompts):
        _, _, gsp = section_prompts
        context = {
            "task_spec": {},
            "template_rules": [],
            "outline": {},
            "previous_sections": {"Intro": 12345},
        }
        result = gsp("Methods", context)
        assert "Previous sections" not in result

    def test_previous_sections_skips_empty(self, section_prompts):
        _, _, gsp = section_prompts
        context = {
            "task_spec": {},
            "template_rules": [],
            "outline": {},
            "previous_sections": {"Intro": ""},
        }
        result = gsp("Methods", context)
        assert "Previous sections" not in result

    def test_outline_included(self, section_prompts):
        _, _, gsp = section_prompts
        context = {"task_spec": {}, "template_rules": [], "outline": {"sections": [{"title": "Intro"}]}, "previous_sections": {}}
        result = gsp("Results", context)
        assert '"sections"' in result or "Intro" in result

    def test_template_rules_included(self, section_prompts):
        _, _, gsp = section_prompts
        context = {"task_spec": {}, "template_rules": [{"rule": "use IEEE style"}], "outline": {}, "previous_sections": {}}
        result = gsp("Conclusion", context)
        assert "IEEE" in result or "rule" in result

    def test_missing_context_keys(self, section_prompts):
        _, _, gsp = section_prompts
        context = {}
        result = gsp("Introduction", context)
        assert result is not None
