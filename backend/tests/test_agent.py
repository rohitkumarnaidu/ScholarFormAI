import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestCountWords:
    def test_empty_string(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._count_words("") == 0

    def test_none(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._count_words(None) == 0

    def test_basic_count(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._count_words("hello world") == 2

    def test_multiple_spaces(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._count_words("hello   world") == 2


class TestHasCitation:
    def test_numeric_bracket_citation(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._has_citation("as shown in [1]")

    def test_multiple_numeric_citations(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._has_citation("see [1, 2, 3]")

    def test_parenthetical_author_year(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._has_citation("(Smith, 2020)")

    def test_bracket_author_year(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._has_citation("[Smith, 2020]")

    def test_no_citation(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert not AgentPipeline._has_citation("This is plain text")

    def test_none_text(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert not AgentPipeline._has_citation(None)

    def test_empty_text(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert not AgentPipeline._has_citation("")


class TestExtractJson:
    def test_extracts_from_clean_json(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._extract_json('{"key": "val"}') == '{"key": "val"}'

    def test_extracts_from_fenced_json(self):
        from app.pipeline.generation.agent import AgentPipeline
        text = "```json\n{\"key\": \"val\"}\n```"
        assert AgentPipeline._extract_json(text) == '{"key": "val"}'

    def test_returns_none_when_no_braces(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._extract_json("no braces") is None

    def test_returns_none_when_unmatched(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._extract_json("{no closing") is None

    def test_returns_none_for_none(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._extract_json(None) is None


class TestExtractOutlineSections:
    def test_from_dict_outline(self):
        from app.pipeline.generation.agent import AgentPipeline
        outline = {"sections": [{"title": "Intro", "number": 1}]}
        result = AgentPipeline._extract_outline_sections(outline)
        assert len(result) == 1
        assert result[0]["title"] == "Intro"

    def test_from_list_outline(self):
        from app.pipeline.generation.agent import AgentPipeline
        result = AgentPipeline._extract_outline_sections(["Intro", "Methods"])
        assert len(result) == 2
        assert result[0]["title"] == "Intro"

    def test_empty_outline(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._extract_outline_sections({}) == []

    def test_none_outline(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._extract_outline_sections(None) == []

    def test_filters_empty_sections(self):
        from app.pipeline.generation.agent import AgentPipeline
        outline = {"sections": [None, {}, {"title": "Intro"}]}
        result = AgentPipeline._extract_outline_sections(outline)
        assert len(result) == 1


class TestNormalizeSections:
    def test_dict_input(self):
        from app.pipeline.generation.agent import AgentPipeline
        result = AgentPipeline._normalize_sections({"Intro": "text"})
        assert result == {"Intro": "text"}

    def test_list_input(self):
        from app.pipeline.generation.agent import AgentPipeline
        result = AgentPipeline._normalize_sections([
            {"title": "Intro", "content": "text"}
        ])
        assert result == {"Intro": "text"}

    def test_empty_input(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._normalize_sections({}) == {}

    def test_none_input(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._normalize_sections(None) == {}


class TestEnsureOutlineNumbers:
    def test_adds_numbers_to_sections(self):
        from app.pipeline.generation.agent import AgentPipeline
        outline = {"sections": [{"title": "Intro"}, {"title": "Methods"}]}
        result = AgentPipeline._ensure_outline_numbers(outline)
        assert result["sections"][0]["number"] == 1
        assert result["sections"][1]["number"] == 2

    def test_handles_string_sections(self):
        from app.pipeline.generation.agent import AgentPipeline
        outline = {"sections": ["Intro", "Methods"]}
        result = AgentPipeline._ensure_outline_numbers(outline)
        assert result["sections"][0]["number"] == 1
        assert result["sections"][0]["title"] == "Intro"

    def test_no_sections_key(self):
        from app.pipeline.generation.agent import AgentPipeline
        result = AgentPipeline._ensure_outline_numbers({})
        assert result == {}

    def test_none_sections(self):
        from app.pipeline.generation.agent import AgentPipeline
        result = AgentPipeline._ensure_outline_numbers({"sections": None})
        assert result == {"sections": None}


class TestMinWordsForLength:
    def test_short_returns_120(self):
        from app.pipeline.generation.agent import AgentPipeline
        ap = _make_agent()
        assert ap._min_words_for_length("short") == 120

    def test_long_returns_240(self):
        from app.pipeline.generation.agent import AgentPipeline
        ap = _make_agent()
        assert ap._min_words_for_length("long") == 240

    def test_default_returns_180(self):
        from app.pipeline.generation.agent import AgentPipeline
        ap = _make_agent()
        assert ap._min_words_for_length("medium") == 180

    def test_none_returns_180(self):
        from app.pipeline.generation.agent import AgentPipeline
        ap = _make_agent()
        assert ap._min_words_for_length(None) == 180


class TestSelectLowSections:
    def test_selects_below_threshold(self):
        from app.pipeline.generation.agent import AgentPipeline
        ap = _make_agent()
        sections = {"Intro": "short", "Long": "word " * 50}
        result = ap._select_low_sections(sections, min_words=10, limit=3)
        assert "Intro" in result

    def test_skips_references(self):
        from app.pipeline.generation.agent import AgentPipeline
        ap = _make_agent()
        sections = {"References": "[1] ref", "Intro": "short"}
        result = ap._select_low_sections(sections, min_words=10, limit=3)
        assert "References" not in result

    def test_empty_sections(self):
        from app.pipeline.generation.agent import AgentPipeline
        ap = _make_agent()
        assert ap._select_low_sections({}, min_words=10) == []


class TestApplyQualityFloor:
    def test_expands_short_section(self):
        from app.pipeline.generation.agent import AgentPipeline
        ap = _make_agent()
        sections = {"Intro": "short"}
        result = ap._apply_quality_floor(sections, ["Intro"], min_words=10)
        assert AgentPipeline._count_words(result["Intro"]) >= 10

    def test_skips_references_section(self):
        from app.pipeline.generation.agent import AgentPipeline
        ap = _make_agent()
        sections = {"references": ""}
        result = ap._apply_quality_floor(sections, ["references"], min_words=10)
        assert AgentPipeline._count_words(result.get("references", "")) == 0

    def test_adds_citation_when_missing(self):
        from app.pipeline.generation.agent import AgentPipeline
        ap = _make_agent()
        sections = {"Intro": "word " * 20}
        result = ap._apply_quality_floor(sections, ["Intro"], min_words=10)
        assert "[1]" in result["Intro"]


class TestConstructor:
    def test_default_quality_target(self):
        from app.pipeline.generation.agent import AgentPipeline
        ap = _make_agent()
        assert ap.quality_target == 70.0

    def test_max_quality_passes(self):
        from app.pipeline.generation.agent import AgentPipeline
        ap = _make_agent()
        assert ap.max_quality_passes == 1


class TestRun:
    @patch("app.pipeline.generation.agent.TaskParser")
    @patch("app.pipeline.generation.agent.AgentPipeline._retrieve_template_rules")
    @patch("app.pipeline.generation.agent.AgentPipeline._update_status")
    async def test_run_parses_and_researches(self, mock_upd, mock_rtr, mock_parser):
        from app.pipeline.generation.agent import AgentPipeline
        ap = _make_agent()
        mock_parser.return_value.parse = AsyncMock(return_value={"sections": ["Intro"]})
        mock_parser.return_value.last_turn = None
        mock_rtr.return_value = []
        ap.session_service.get_session = AsyncMock(return_value={"config_json": {}})
        ap._is_canceled = AsyncMock(return_value=False)
        ap._generate_outline = AsyncMock(return_value={"sections": []})

        await ap.run("session1", "Write a paper")
        mock_parser.return_value.parse.assert_awaited_once_with("Write a paper")


class TestResume:
    @patch("app.pipeline.generation.agent.get_section_prompt")
    @patch("app.pipeline.generation.agent.AgentPipeline._update_status")
    @patch("app.pipeline.generation.agent.AgentPipeline._emit_sse")
    async def test_resume_happy_path(self, mock_sse, mock_upd, mock_gsp):
        from app.pipeline.generation.agent import AgentPipeline
        ap = _make_agent()
        ap.session_service.get_session = AsyncMock(return_value={
            "config_json": {"sections": ["Intro"]},
            "outline_json": {"sections": [{"title": "Intro"}]},
        })
        ap.session_service.save_document_version = AsyncMock()
        ap.session_service.update_session = AsyncMock()
        ap._is_canceled = AsyncMock(return_value=False)
        ap._generate_section = AsyncMock(return_value="Section text")
        ap.citations.assemble = AsyncMock(return_value=({}, ""))
        ap._render_document = AsyncMock(return_value="out.docx")
        ap.quality_scorer.score = MagicMock(return_value={"overall_score": 85})
        mock_gsp.return_value = "Write section"

        await ap.resume("session1")
        ap._generate_section.assert_awaited()


class TestRewriteSection:
    @patch("app.pipeline.generation.agent.AgentPipeline._emit_sse")
    async def test_rewrite_section_basic(self, mock_sse):
        from app.pipeline.generation.agent import AgentPipeline
        ap = _make_agent()
        ap.session_service.get_session = AsyncMock(return_value={
            "config_json": {"citation_style": "ieee"},
            "outline_json": {},
            "progress": 90,
            "status": "processing",
        })
        ap.session_service.get_latest_document = AsyncMock(return_value={})
        ap.session_service.get_messages = AsyncMock(return_value=[])
        ap.session_service.update_session = AsyncMock()
        ap.session_service.save_document_version = AsyncMock()
        ap._llm_text = AsyncMock(return_value="Rewritten text")
        ap.citations.assemble = AsyncMock(return_value=({}, ""))
        ap._render_document = AsyncMock(return_value="out.docx")
        ap.quality_scorer.score = MagicMock(return_value={"overall_score": 80})
        ap._stream_chunks = AsyncMock()

        await ap.rewrite_section("session1", "Intro", "Make it better")
        ap._llm_text.assert_awaited()


class TestGenerateSection:
    @patch("app.pipeline.generation.agent.AgentPipeline._stream_chunks")
    async def test_generates_and_streams(self, mock_stream):
        from app.pipeline.generation.agent import AgentPipeline
        ap = _make_agent()
        ap._llm_text = AsyncMock(return_value="Generated text")
        result = await ap._generate_section("s1", "Intro", "Write something")
        assert result == "Generated text"


def _make_agent():
    from app.pipeline.generation.agent import AgentPipeline
    session_service = MagicMock()
    pipeline_orchestrator = MagicMock()
    return AgentPipeline(session_service, pipeline_orchestrator, pubsub=MagicMock())
