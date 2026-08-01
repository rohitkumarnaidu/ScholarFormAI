# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.pipeline.generation.task_parser import _load_templates, _extract_json, _keywords_from_prompt, TaskParser


class TestLoadTemplates:
    def test_returns_dict(self):
        result = _load_templates()
        assert isinstance(result, dict)

    def test_empty_when_no_templates_dir(self, tmp_path):
        with patch("app.pipeline.generation.task_parser.Path") as mock_path:
            mock_path.return_value.resolve.return_value.parents.__getitem__.return_value = tmp_path
            fake_templates = tmp_path / "templates"
            fake_templates.mkdir()
            (fake_templates / "ieee").mkdir()
            result = _load_templates()
            assert "ieee" in result
            assert result["ieee"] == "IEEE"

    def test_skips_files_in_templates_dir(self, tmp_path):
        with patch("app.pipeline.generation.task_parser.Path") as mock_path:
            mock_path.return_value.resolve.return_value.parents.__getitem__.return_value = tmp_path
            fake_templates = tmp_path / "templates"
            fake_templates.mkdir()
            (fake_templates / "ieee").mkdir()
            (fake_templates / "readme.txt").write_text("hello")
            result = _load_templates()
            assert "readme" not in result

    def test_not_a_directory(self, tmp_path):
        with patch("app.pipeline.generation.task_parser.Path") as mock_path:
            mock_path.return_value.resolve.return_value.parents.__getitem__.return_value = tmp_path
            fake_templates = tmp_path / "templates"
            fake_templates.mkdir()
            (fake_templates / "ieee.txt").write_text("hello")
            result = _load_templates()
            assert "ieee" not in result


class TestExtractJson:
    def test_none(self):
        assert _extract_json(None) is None

    def test_empty(self):
        assert _extract_json("") is None

    def test_simple_json(self):
        assert _extract_json('{"a": 1}') == '{"a": 1}'

    def test_json_in_code_fence(self):
        result = _extract_json('```json\n{"a": 1}\n```')
        assert result == '{"a": 1}'

    def test_json_in_code_fence_no_lang(self):
        result = _extract_json('```\n{"a": 1}\n```')
        assert result == '{"a": 1}'

    def test_surrounding_text(self):
        result = _extract_json('text {"a": 1} more')
        assert result == '{"a": 1}'

    def test_no_braces(self):
        assert _extract_json("hello") is None

    def test_unmatched_braces(self):
        assert _extract_json('{"a":') is None

    def test_only_closing_brace(self):
        assert _extract_json("}") is None

    def test_code_fence_multiline(self):
        text = "```json\n{\n\"key\": \"value\"\n}\n```"
        result = _extract_json(text)
        assert json.loads(result)["key"] == "value"


class TestKeywordsFromPrompt:
    def test_basic(self):
        result = _keywords_from_prompt("machine learning for natural language processing")
        assert "machine" in result
        assert "learning" in result
        assert "natural" in result
        assert len(result) <= 6

    def test_short_tokens_skipped(self):
        result = _keywords_from_prompt("a an the cat dog bird fish")
        assert all(len(k) >= 4 for k in result)

    def test_limit(self):
        result = _keywords_from_prompt("machine learning natural language processing computer vision deep learning")
        assert len(result) == 6

    def test_deduplicates(self):
        result = _keywords_from_prompt("machine learning machine learning")
        assert result == ["machine", "learning"]

    def test_empty(self):
        assert _keywords_from_prompt("") == []

    def test_punctuation_stripped(self):
        result = _keywords_from_prompt("machine, learning; nlp!")
        assert "machine" in result
        assert "learning" in result

    def test_none(self):
        assert _keywords_from_prompt(None) == []


class TestTaskParserInit:
    def test_last_turn_none(self):
        tp = TaskParser()
        assert tp.last_turn is None


class TestParse:
    @pytest.mark.asyncio
    async def test_successful_parse(self):
        tp = TaskParser()
        raw_text = json.dumps({
            "doc_type": "research_paper",
            "template": "ieee",
            "sections": ["Intro", "Methods", "Conclusion"],
            "tone": "academic",
            "length": "long",
            "citation_style": "apa",
            "title": "My Paper",
            "keywords": ["ml", "ai"],
        })
        with patch("app.pipeline.generation.task_parser.generate") as mock_gen:
            mock_gen.return_value = raw_text
            result = await tp.parse("write a paper about ML")
        assert result["doc_type"] == "research_paper"
        assert result["title"] == "My Paper"
        assert tp.last_turn is not None

    @pytest.mark.asyncio
    async def test_parse_handles_no_json(self):
        tp = TaskParser()
        with patch("app.pipeline.generation.task_parser.generate") as mock_gen:
            mock_gen.return_value = "not json at all"
            result = await tp.parse("write a paper")
        assert result["doc_type"] == "research_paper"

    @pytest.mark.asyncio
    async def test_parse_exception(self):
        tp = TaskParser()
        with patch("app.pipeline.generation.task_parser.generate", side_effect=Exception("LLM down")):
            result = await tp.parse("write a paper")
        assert result["doc_type"] == "research_paper"

    @pytest.mark.asyncio
    async def test_parse_empty_raw(self):
        tp = TaskParser()
        with patch("app.pipeline.generation.task_parser.generate") as mock_gen:
            mock_gen.return_value = ""
            result = await tp.parse("write a paper")
        assert result["doc_type"] == "research_paper"
        assert result["template"] == "IEEE"


class TestValidateSpec:
    def test_defaults(self):
        tp = TaskParser()
        result = tp._validate_spec({}, "write a paper")
        assert result["doc_type"] == "research_paper"
        assert result["template"] == "IEEE"
        assert result["tone"] == "academic"
        assert result["length"] == "medium"
        assert result["citation_style"] == "ieee"
        assert "Abstract" in result["sections"]
        assert "References" in result["sections"]

    def test_custom_doc_type(self):
        tp = TaskParser()
        result = tp._validate_spec({"doc_type": "thesis"}, "prompt")
        assert result["doc_type"] == "thesis"

    def test_invalid_doc_type(self):
        tp = TaskParser()
        result = tp._validate_spec({"doc_type": "poem"}, "prompt")
        assert result["doc_type"] == "research_paper"

    def test_template_with_mapping(self):
        tp = TaskParser()
        result = tp._validate_spec({"template": "ieee"}, "prompt")
        assert result["template"] == "IEEE"

    def test_template_none(self):
        tp = TaskParser()
        result = tp._validate_spec({"template": None}, "prompt")
        assert result["template"] == "IEEE"

    def test_template_empty(self):
        tp = TaskParser()
        result = tp._validate_spec({"template": ""}, "prompt")
        assert result["template"] == "IEEE"

    def test_template_unknown(self):
        tp = TaskParser()
        result = tp._validate_spec({"template": "madeupstyle"}, "prompt")
        assert result["template"] == "IEEE"

    def test_tone_valid(self):
        tp = TaskParser()
        result = tp._validate_spec({"tone": "technical"}, "prompt")
        assert result["tone"] == "technical"

    def test_tone_invalid(self):
        tp = TaskParser()
        result = tp._validate_spec({"tone": "casual"}, "prompt")
        assert result["tone"] == "academic"

    def test_length_valid(self):
        tp = TaskParser()
        result = tp._validate_spec({"length": "short"}, "prompt")
        assert result["length"] == "short"

    def test_length_invalid(self):
        tp = TaskParser()
        result = tp._validate_spec({"length": "extreme"}, "prompt")
        assert result["length"] == "medium"

    def test_citation_style_valid(self):
        tp = TaskParser()
        result = tp._validate_spec({"citation_style": "apa"}, "prompt")
        assert result["citation_style"] == "apa"

    def test_citation_style_invalid(self):
        tp = TaskParser()
        result = tp._validate_spec({"citation_style": "weird"}, "prompt")
        assert result["citation_style"] == "ieee"

    def test_citation_style_empty_falls_to_template(self):
        tp = TaskParser()
        result = tp._validate_spec({"citation_style": "", "template": "apa"}, "prompt")
        assert result["citation_style"] == "apa"

    def test_title_missing(self):
        tp = TaskParser()
        result = tp._validate_spec({}, "prompt")
        assert result["title"] == "Untitled Research Paper"

    def test_title_custom(self):
        tp = TaskParser()
        result = tp._validate_spec({"title": "My Study"}, "prompt")
        assert result["title"] == "My Study"

    def test_sections_include_references(self):
        tp = TaskParser()
        result = tp._validate_spec({"sections": ["Intro", "Methods"]}, "prompt")
        assert "References" in result["sections"]
        assert result["sections"][-1] == "References"

    def test_sections_duplicates_removed(self):
        tp = TaskParser()
        result = tp._validate_spec({"sections": ["Intro", "Intro", "Methods"]}, "prompt")
        assert result["sections"].count("Intro") == 1

    def test_keywords_from_prompt(self):
        tp = TaskParser()
        result = tp._validate_spec({}, "machine learning natural language processing")
        assert len(result["keywords"]) > 0

    def test_keywords_capped_at_10(self):
        tp = TaskParser()
        kw = [f"keyword{i}" for i in range(20)]
        result = tp._validate_spec({"keywords": kw}, "prompt")
        assert len(result["keywords"]) <= 10

    def test_keywords_empty_stripped(self):
        tp = TaskParser()
        result = tp._validate_spec({"keywords": ["ml", "", "  ", "ai"]}, "prompt")
        assert result["keywords"] == ["ml", "ai"]

    def test_none_values_removed(self):
        tp = TaskParser()
        result = tp._validate_spec({"tone": None, "length": None, "title": None, "sections": None}, "prompt")
        assert result["tone"] == "academic"
        assert result["length"] == "medium"
