from unittest.mock import MagicMock, patch

import pytest


class TestExtractJson:
    def test_simple_json(self):
        from app.pipeline.generation.task_parser import _extract_json
        assert _extract_json('{"a": 1}') == '{"a": 1}'

    def test_empty(self):
        from app.pipeline.generation.task_parser import _extract_json
        assert _extract_json("") is None

    def test_with_code_fence(self):
        from app.pipeline.generation.task_parser import _extract_json
        result = _extract_json("```json\n{\"a\": 1}\n```")
        assert result == '{"a": 1}'

    def test_no_braces(self):
        from app.pipeline.generation.task_parser import _extract_json
        assert _extract_json("just text") is None

    def test_nested_json(self):
        from app.pipeline.generation.task_parser import _extract_json
        result = _extract_json('Here is: {"outer": {"inner": 1}} and more')
        assert result == '{"outer": {"inner": 1}}'

    def test_text_after_json(self):
        from app.pipeline.generation.task_parser import _extract_json
        result = _extract_json('{"a": 1}\nsome trailing text')
        assert result == '{"a": 1}'


class TestKeywordsFromPrompt:
    def test_basic(self):
        from app.pipeline.generation.task_parser import _keywords_from_prompt
        result = _keywords_from_prompt("machine learning for medical image analysis")
        assert "machine" in result
        assert "learning" in result
        assert "medical" in result

    def test_short_tokens_skipped(self):
        from app.pipeline.generation.task_parser import _keywords_from_prompt
        result = _keywords_from_prompt("a an the for cat")
        assert all(len(k) >= 4 for k in result)

    def test_limit(self):
        from app.pipeline.generation.task_parser import _keywords_from_prompt
        prompt = "one two three four five six seven eight"
        result = _keywords_from_prompt(prompt, limit=3)
        assert len(result) == 3

    def test_empty(self):
        from app.pipeline.generation.task_parser import _keywords_from_prompt
        assert _keywords_from_prompt("") == []

    def test_dedupes(self):
        from app.pipeline.generation.task_parser import _keywords_from_prompt
        result = _keywords_from_prompt("machine learning machine learning")
        assert len(result) == 2


class TestValidateSpec:
    def test_defaults(self):
        from app.pipeline.generation.task_parser import TaskParser
        parser = TaskParser()
        spec = parser._validate_spec({}, "machine learning paper")
        assert spec["doc_type"] == "research_paper"
        assert "Abstract" in spec["sections"]
        assert len(spec["keywords"]) > 0

    def test_custom_doc_type(self):
        from app.pipeline.generation.task_parser import TaskParser
        parser = TaskParser()
        spec = parser._validate_spec({"doc_type": "thesis"}, "test")
        assert spec["doc_type"] == "thesis"

    def test_invalid_doc_type_falls_back(self):
        from app.pipeline.generation.task_parser import TaskParser
        parser = TaskParser()
        spec = parser._validate_spec({"doc_type": "invalid"}, "test")
        assert spec["doc_type"] == "research_paper"

    def test_custom_sections(self):
        from app.pipeline.generation.task_parser import TaskParser
        parser = TaskParser()
        spec = parser._validate_spec({"sections": ["Intro", "Conclusion"]}, "test")
        assert "Intro" in spec["sections"]
        assert "Conclusion" in spec["sections"]
        assert "References" in spec["sections"]

    def test_references_always_appended(self):
        from app.pipeline.generation.task_parser import TaskParser
        parser = TaskParser()
        spec = parser._validate_spec({"sections": ["Intro"]}, "test")
        assert spec["sections"] == ["Intro", "References"]

    def test_invalid_tone_falls_back(self):
        from app.pipeline.generation.task_parser import TaskParser
        parser = TaskParser()
        spec = parser._validate_spec({"tone": "casual"}, "test")
        assert spec["tone"] == "academic"

    def test_invalid_length_falls_back(self):
        from app.pipeline.generation.task_parser import TaskParser
        parser = TaskParser()
        spec = parser._validate_spec({"length": "xlarge"}, "test")
        assert spec["length"] == "medium"

    def test_keywords_from_prompt_when_empty(self):
        from app.pipeline.generation.task_parser import TaskParser
        parser = TaskParser()
        spec = parser._validate_spec({}, "deep learning for NLP analysis")
        assert len(spec["keywords"]) > 0
        assert "learning" in spec["keywords"]

    def test_custom_title(self):
        from app.pipeline.generation.task_parser import TaskParser
        parser = TaskParser()
        spec = parser._validate_spec({"title": "My Paper"}, "test")
        assert spec["title"] == "My Paper"

    def test_missing_title_generated(self):
        from app.pipeline.generation.task_parser import TaskParser
        parser = TaskParser()
        spec = parser._validate_spec({"doc_type": "thesis", "title": ""}, "test")
        assert "Thesis" in spec["title"]


class TestTaskParser:
    @pytest.mark.asyncio
    async def test_parse_success(self):
        from app.pipeline.generation.task_parser import TaskParser
        parser = TaskParser()

        mock_generate = MagicMock(return_value='{"doc_type":"thesis","template":"ieee","sections":["Intro"]}')

        with patch("app.pipeline.generation.task_parser.generate", mock_generate):
            result = await parser.parse("write a thesis on ML")

        assert result["doc_type"] == "thesis"
        assert "Intro" in result["sections"]
        assert parser.last_turn is not None

    @pytest.mark.asyncio
    async def test_parse_fallback_on_exception(self):
        from app.pipeline.generation.task_parser import TaskParser
        parser = TaskParser()

        mock_generate = MagicMock(side_effect=Exception("LLM down"))

        with patch("app.pipeline.generation.task_parser.generate", mock_generate):
            result = await parser.parse("write a thesis on ML")

        assert result["doc_type"] == "research_paper"

    @pytest.mark.asyncio
    async def test_parse_invalid_json_falls_back(self):
        from app.pipeline.generation.task_parser import TaskParser
        parser = TaskParser()

        mock_generate = MagicMock(return_value="```\nnot json\n```")

        with patch("app.pipeline.generation.task_parser.generate", mock_generate):
            result = await parser.parse("test")

        assert result["doc_type"] == "research_paper"

    @pytest.mark.asyncio
    async def test_parse_partial_json_merged_with_defaults(self):
        from app.pipeline.generation.task_parser import TaskParser
        parser = TaskParser()

        mock_generate = MagicMock(return_value='{"title":"Custom Title"}')

        with patch("app.pipeline.generation.task_parser.generate", mock_generate):
            result = await parser.parse("test")

        assert result["title"] == "Custom Title"
        assert result["doc_type"] == "research_paper"
