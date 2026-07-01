import pytest


class TestParse:
    def test_plain_json_array(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        result = parser.parse('[{"type":"BODY","content":"Hello"}]', "paper")
        assert len(result) == 1
        assert result[0]["type"] == "BODY"
        assert result[0]["content"] == "Hello"

    def test_json_in_fences(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        response = "```json\n[{\"type\":\"TITLE\",\"content\":\"My Paper\"}]\n```"
        result = parser.parse(response, "paper")
        assert result[0]["type"] == "TITLE"

    def test_fences_without_json_tag(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        response = "```\n[{\"type\":\"BODY\",\"content\":\"text\"}]\n```"
        result = parser.parse(response, "paper")
        assert result[0]["content"] == "text"

    def test_fences_with_language_tag(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        response = "```python\n[{\"type\":\"BODY\",\"content\":\"code\"}]\n```"
        result = parser.parse(response, "paper")
        assert result[0]["content"] == "code"

    def test_bracket_in_text(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        response = "Here is the JSON: [{\"type\":\"BODY\",\"content\":\"ok\"}]"
        result = parser.parse(response, "paper")
        assert result[0]["content"] == "ok"

    def test_no_json_raises(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        with pytest.raises(ValueError, match="JSON array"):
            parser.parse("Just text with no brackets", "paper")

    def test_invalid_json_raises(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        with pytest.raises(ValueError, match="Invalid JSON"):
            parser.parse("[{invalid}]", "paper")

    def test_non_list_json_raises(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        with pytest.raises(ValueError, match="JSON array"):
            parser.parse('{"type":"BODY"}', "paper")

    def test_unknown_block_type_falls_to_body(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        result = parser.parse('[{"type":"CUSTOM","content":"test"}]', "paper")
        assert result[0]["type"] == "BODY"

    def test_type_aliases_resolved(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        result = parser.parse('[{"type":"H1","content":"Heading"}]', "paper")
        assert result[0]["type"] == "HEADING_1"

    def test_non_dict_block_handled(self):
        from app.pipeline.generation.content_parser import ContentParser
        parser = ContentParser()
        result = parser.parse('["raw string"]', "paper")
        assert result[0]["type"] == "BODY"


class TestExtractJson:
    def test_extract_from_fences_json(self):
        from app.pipeline.generation.content_parser import ContentParser
        text = "```json\n[{}]\n```"
        assert ContentParser._extract_json(text) == "[{}]"

    def test_extract_from_plain_fences(self):
        from app.pipeline.generation.content_parser import ContentParser
        text = "```\n[{}]\n```"
        assert ContentParser._extract_json(text) == "[{}]"

    def test_extract_plain_array(self):
        from app.pipeline.generation.content_parser import ContentParser
        assert ContentParser._extract_json("[{}]") == "[{}]"

    def test_extract_bracket_search(self):
        from app.pipeline.generation.content_parser import ContentParser
        result = ContentParser._extract_json("text [{}] end")
        assert result.startswith("[{}]")

    def test_extract_raises_on_no_json(self):
        from app.pipeline.generation.content_parser import ContentParser
        with pytest.raises(ValueError):
            ContentParser._extract_json("no brackets")


class TestNormalise:
    def test_normalise_sets_level_default(self):
        from app.pipeline.generation.content_parser import ContentParser
        result = ContentParser._normalise({"type": "BODY", "content": "x"}, 0)
        assert result["level"] == 0

    def test_normalise_preserves_metadata(self):
        from app.pipeline.generation.content_parser import ContentParser
        result = ContentParser._normalise(
            {"type": "BODY", "content": "x", "metadata": {"key": "val"}}, 0
        )
        assert result["metadata"] == {"key": "val"}

    def test_normalise_fallback_type(self):
        from app.pipeline.generation.content_parser import ContentParser
        result = ContentParser._normalise({}, 0)
        assert result["type"] == "BODY"
