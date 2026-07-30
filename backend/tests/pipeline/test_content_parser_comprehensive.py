# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
from __future__ import annotations

import pytest


@pytest.fixture
def parser():
    from app.pipeline.generation.content_parser import ContentParser
    return ContentParser()


@pytest.fixture
def constants():
    from app.pipeline.generation.content_parser import VALID_BLOCK_TYPES, TYPE_ALIASES
    return VALID_BLOCK_TYPES, TYPE_ALIASES


class TestValidBlockTypes:
    def test_contains_expected(self, constants):
        valid_block_types, _ = constants
        assert "TITLE" in valid_block_types
        assert "BODY" in valid_block_types
        assert "HEADING_1" in valid_block_types
        assert "REFERENCE_ENTRY" in valid_block_types


class TestTypeAliases:
    def test_h1_maps_to_heading1(self, constants):
        _, type_aliases = constants
        assert type_aliases["H1"] == "HEADING_1"

    def test_paragraph_maps_to_body(self, constants):
        _, type_aliases = constants
        assert type_aliases["PARAGRAPH"] == "BODY"

    def test_ref_maps_to_reference_entry(self, constants):
        _, type_aliases = constants
        assert type_aliases["REF"] == "REFERENCE_ENTRY"

    def test_author_maps_to_author_info(self, constants):
        _, type_aliases = constants
        assert type_aliases["AUTHOR"] == "AUTHOR_INFO"

    def test_affiliation_info(self, constants):
        _, type_aliases = constants
        assert type_aliases["AFFILIATION_INFO"] == "AFFILIATION"


class TestExtractJson:
    def test_json_code_fence(self, parser):
        result = parser._extract_json('```json\n[{"type": "BODY", "content": "Hello"}]\n```')
        assert '"type": "BODY"' in result

    def test_code_fence_no_lang(self, parser):
        result = parser._extract_json('```\n[{"type": "BODY"}]\n```')
        assert '"type": "BODY"' in result

    def test_plain_json_array(self, parser):
        result = parser._extract_json('[{"type": "TITLE"}]')
        assert result == '[{"type": "TITLE"}]'

    def test_find_bracket_anywhere(self, parser):
        result = parser._extract_json('text before\n[{"type": "BODY"}]\ntext after')
        assert '"type": "BODY"' in result

    def test_no_json_raises(self, parser):
        with pytest.raises(ValueError, match="does not contain a JSON array"):
            parser._extract_json("just plain text")

    def test_empty_raises(self, parser):
        with pytest.raises(ValueError):
            parser._extract_json("")

    def test_code_fence_with_newlines(self, parser):
        text = '```json\n[\n  {"type": "BODY", "content": "Line1"},\n  {"type": "TITLE", "content": "Title"}\n]\n```'
        result = parser._extract_json(text)
        assert "Line1" in result


class TestLoadJson:
    def test_valid_array(self, parser):
        result = parser._load_json('[{"type": "BODY"}]')
        assert result == [{"type": "BODY"}]

    def test_invalid_json_raises(self, parser):
        with pytest.raises(ValueError, match="Invalid JSON"):
            parser._load_json("{broken}")

    def test_not_a_list_raises(self, parser):
        with pytest.raises(ValueError, match="Expected a JSON array"):
            parser._load_json('{"type": "BODY"}')


class TestNormalise:
    def test_known_type(self, parser):
        result = parser._normalise({"type": "TITLE", "content": "My Title", "level": 0}, 0)
        assert result["type"] == "TITLE"
        assert result["content"] == "My Title"

    def test_aliased_type(self, parser):
        result = parser._normalise({"type": "H1", "content": "Intro"}, 0)
        assert result["type"] == "HEADING_1"

    def test_unknown_type_falls_back_to_body(self, parser):
        result = parser._normalise({"type": "WEIRD_TYPE", "content": "text"}, 0)
        assert result["type"] == "BODY"

    def test_non_dict_input(self, parser):
        result = parser._normalise("just a string", 0)
        assert result["type"] == "BODY"
        assert result["content"] == "just a string"

    def test_non_dict_with_type_field(self, parser):
        result = parser._normalise(42, 5)
        assert result["content"] == "42"
        assert result["type"] == "BODY"

    def test_missing_type_defaults_to_body(self, parser):
        result = parser._normalise({"content": "text"}, 0)
        assert result["type"] == "BODY"

    def test_preserves_metadata(self, parser):
        result = parser._normalise({"type": "BODY", "content": "text", "metadata": {"key": "val"}}, 0)
        assert result["metadata"] == {"key": "val"}

    def test_strips_content(self, parser):
        result = parser._normalise({"type": "BODY", "content": "  text  "}, 0)
        assert result["content"] == "text"

    def test_default_level_zero(self, parser):
        result = parser._normalise({"type": "BODY", "content": "text"}, 0)
        assert result["level"] == 0

    def test_empty_type_stripped_unknown(self, parser):
        result = parser._normalise({"type": "  ", "content": "text"}, 0)
        assert result["type"] == "BODY"

    def test_empty_content(self, parser):
        result = parser._normalise({"type": "BODY", "content": ""}, 0)
        assert result["content"] == ""

    def test_type_case_insensitive(self, parser):
        result = parser._normalise({"type": "body", "content": "text"}, 0)
        assert result["type"] == "BODY"

    def test_type_with_spaces(self, parser):
        result = parser._normalise({"type": "  ABSTRACT  ", "content": "text"}, 0)
        assert result["type"] == "ABSTRACT"

    def test_unknown_type_logs_warning(self, parser):
        result = parser._normalise({"type": "CUSTOM_SECTION", "content": "text"}, 0)
        assert result["type"] == "BODY"

    def test_figure_caption_type(self, parser):
        result = parser._normalise({"type": "FIGURE_CAPTION", "content": "Fig 1"}, 0)
        assert result["type"] == "FIGURE_CAPTION"


class TestParse:
    def test_successful_parse(self, parser):
        response = '[{"type": "TITLE", "content": "Paper"}, {"type": "BODY", "content": "Text"}]'
        result = parser.parse(response, "research_paper")
        assert len(result) == 2
        assert result[0]["type"] == "TITLE"
        assert result[1]["type"] == "BODY"

    def test_parse_with_code_fence(self, parser):
        response = '```json\n[{"type": "ABSTRACT", "content": "Summary"}]\n```'
        result = parser.parse(response, "thesis")
        assert result[0]["type"] == "ABSTRACT"

    def test_parse_no_json_array_raises(self, parser):
        with pytest.raises(ValueError, match="does not contain a JSON array"):
            parser.parse("{invalid}", "paper")

    def test_parse_no_array_raises(self, parser):
        with pytest.raises(ValueError, match="does not contain a JSON array"):
            parser.parse("text without brackets", "paper")

    def test_parse_logs_count(self, parser, caplog):
        import logging
        caplog.set_level(logging.INFO)
        response = '[{"type": "BODY", "content": "Text"}]'
        parser.parse(response, "report")
        assert any("parsed 1 blocks" in r.message for r in caplog.records)
