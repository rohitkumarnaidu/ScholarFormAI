# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import json
import re
from unittest.mock import AsyncMock, MagicMock, patch, call, ANY

import pytest


@pytest.fixture
def AP():
    with (
        patch("app.pipeline.generation.agent.QualityScorer"),
        patch("app.pipeline.generation.agent.get_rag_engine"),
        patch("app.pipeline.generation.agent.RedisPubSub"),
        patch("app.pipeline.generation.agent.CitationAssemblyService"),
    ):
        from app.pipeline.generation.agent import AgentPipeline
        return AgentPipeline


@pytest.fixture
def agent(AP):
    ss = MagicMock()
    po = MagicMock()
    po._export_document.return_value = "/fake/output.docx"
    a = AP(ss, po)
    a.session_service = ss
    a.pipeline_orchestrator = po
    a.pubsub = AsyncMock()
    a.rag_engine = MagicMock()
    a.citations = MagicMock()
    a.quality_scorer = MagicMock()
    a.quality_target = 70.0
    a.max_quality_passes = 1
    return a


class TestInit:
    def test_default_pubsub_created(self, AP):
        ss = MagicMock()
        po = MagicMock()
        with (
            patch("app.pipeline.generation.agent.QualityScorer"),
            patch("app.pipeline.generation.agent.get_rag_engine"),
            patch("app.pipeline.generation.agent.RedisPubSub") as mock_ps,
            patch("app.pipeline.generation.agent.CitationAssemblyService"),
        ):
            a = AP(ss, po)
            mock_ps.assert_called_once()

    def test_provided_pubsub_used(self, AP):
        ss = MagicMock()
        po = MagicMock()
        with (
            patch("app.pipeline.generation.agent.QualityScorer"),
            patch("app.pipeline.generation.agent.get_rag_engine"),
            patch("app.pipeline.generation.agent.RedisPubSub") as mock_ps,
            patch("app.pipeline.generation.agent.CitationAssemblyService"),
        ):
            my_pubsub = MagicMock()
            a = AP(ss, po, pubsub=my_pubsub)
            mock_ps.assert_not_called()
            assert a.pubsub is my_pubsub

    def test_components_initialized(self, agent):
        assert agent.quality_scorer is not None
        assert agent.rag_engine is not None
        assert agent.citations is not None
        assert agent.pubsub is not None
        assert agent.quality_target == 70.0
        assert agent.max_quality_passes == 1


class TestCountWords:
    def test_none(self, AP):
        assert AP._count_words(None) == 0

    def test_empty_string(self, AP):
        assert AP._count_words("") == 0

    def test_single_word(self, AP):
        assert AP._count_words("hello") == 1

    def test_multiple_words(self, AP):
        assert AP._count_words("hello world foo") == 3

    def test_whitespace_only(self, AP):
        assert AP._count_words("   \n\t   ") == 0

    def test_non_string_int(self, AP):
        assert AP._count_words(42) == 1


class TestHasCitation:
    def test_none(self, AP):
        assert AP._has_citation(None) is False

    def test_empty(self, AP):
        assert AP._has_citation("") is False

    def test_bracket_number(self, AP):
        assert AP._has_citation("text [1]") is True

    def test_multiple_bracket_numbers(self, AP):
        assert AP._has_citation("text [1, 2, 3]") is True

    def test_parenthetical_author_year(self, AP):
        assert AP._has_citation("(Smith, 2020)") is True

    def test_bracket_author_year(self, AP):
        assert AP._has_citation("[Smith, 2020]") is True

    def test_no_citation(self, AP):
        assert AP._has_citation("Just some text without a reference") is False

    def test_incomplete_bracket(self, AP):
        assert AP._has_citation("text [1") is False


class TestExtractJson:
    def test_empty(self, AP):
        assert AP._extract_json("") is None

    def test_whitespace_only(self, AP):
        assert AP._extract_json("") is None

    def test_simple_json_object(self, AP):
        assert AP._extract_json('{"a": 1}') == '{"a": 1}'

    def test_json_with_surrounding_text(self, AP):
        result = AP._extract_json('text before {"a": 1} text after')
        assert result == '{"a": 1}'

    def test_json_with_code_fence(self, AP):
        result = AP._extract_json('```\n{"a": 1}\n```')
        assert result == '{"a": 1}'

    def test_json_with_json_lang_fence(self, AP):
        result = AP._extract_json('```json\n{"a": 1}\n```')
        assert result == '{"a": 1}'

    def test_no_braces(self, AP):
        assert AP._extract_json("hello world") is None

    def test_unmatched_braces(self, AP):
        assert AP._extract_json('{a: 1') is None

    def test_only_closing_brace(self, AP):
        assert AP._extract_json('}') is None


class TestExtractOutlineSections:
    def test_none(self, AP):
        assert AP._extract_outline_sections(None) == []

    def test_dict_with_sections(self, AP):
        sections = [{"title": "Intro"}, {"title": "Methods"}]
        outline = {"sections": sections}
        result = AP._extract_outline_sections(outline)
        assert result == sections

    def test_dict_empty_sections(self, AP):
        assert AP._extract_outline_sections({"sections": []}) == []

    def test_dict_no_sections_key(self, AP):
        assert AP._extract_outline_sections({"title": "X"}) == []

    def test_dict_with_falsy_items(self, AP):
        result = AP._extract_outline_sections({"sections": [{"title": "A"}, None, ""]})
        assert result == [{"title": "A"}]

    def test_list_of_dicts(self, AP):
        result = AP._extract_outline_sections([{"title": "A"}, {"title": "B"}])
        assert result == [{"title": "A"}, {"title": "B"}]

    def test_list_of_strings(self, AP):
        result = AP._extract_outline_sections(["Intro", "Methods"])
        assert result == [{"title": "Intro"}, {"title": "Methods"}]

    def test_empty_list(self, AP):
        assert AP._extract_outline_sections([]) == []

    def test_not_dict_or_list(self, AP):
        assert AP._extract_outline_sections("string") == []


class TestNormalizeSections:
    def test_none(self, AP):
        assert AP._normalize_sections(None) == {}

    def test_empty_dict(self, AP):
        assert AP._normalize_sections({}) == {}

    def test_dict_of_strings(self, AP):
        result = AP._normalize_sections({"Intro": "Hello", "Conclusion": "Bye"})
        assert result == {"Intro": "Hello", "Conclusion": "Bye"}

    def test_dict_with_non_string_values(self, AP):
        result = AP._normalize_sections({"A": 1, "B": None})
        assert result == {"A": "1", "B": "None"}

    def test_list_of_dicts(self, AP):
        sections = [{"title": "Intro", "content": "Hello"}, {"title": "Methods", "content": "Steps"}]
        result = AP._normalize_sections(sections)
        assert result == {"Intro": "Hello", "Methods": "Steps"}

    def test_list_with_section_key(self, AP):
        sections = [{"section": "Intro", "content": "Hello"}]
        result = AP._normalize_sections(sections)
        assert result == {"Intro": "Hello"}

    def test_list_with_missing_title(self, AP):
        sections = [{"content": "Hello"}]
        result = AP._normalize_sections(sections)
        assert result == {}

    def test_list_of_non_dicts(self, AP):
        assert AP._normalize_sections(["a", "b"]) == {}

    def test_other_type(self, AP):
        assert AP._normalize_sections(42) == {}


class TestEnsureOutlineNumbers:
    def test_no_sections(self, AP):
        result = AP._ensure_outline_numbers({"title": "X"})
        assert result == {"title": "X"}

    def test_sections_not_list(self, AP):
        result = AP._ensure_outline_numbers({"sections": "not a list"})
        assert result == {"sections": "not a list"}

    def test_empty_sections(self, AP):
        result = AP._ensure_outline_numbers({"sections": []})
        assert result == {"sections": []}

    def test_adds_numbers(self, AP):
        sections = [{"title": "A"}, {"title": "B"}]
        result = AP._ensure_outline_numbers({"sections": sections})
        assert result["sections"][0]["number"] == 1
        assert result["sections"][1]["number"] == 2
        assert result["sections"][0]["title"] == "A"

    def test_preserves_existing_number(self, AP):
        sections = [{"title": "A", "number": 5}]
        result = AP._ensure_outline_numbers({"sections": sections})
        assert result["sections"][0]["number"] == 5

    def test_section_as_title_fallback(self, AP):
        sections = [{"section": "Intro"}, {"section": "Methods"}]
        result = AP._ensure_outline_numbers({"sections": sections})
        assert result["sections"][0]["title"] == "Intro"
        assert result["sections"][1]["title"] == "Methods"

    def test_non_dict_section(self, AP):
        sections = ["Intro", "Methods"]
        result = AP._ensure_outline_numbers({"sections": sections})
        assert result["sections"][0] == {"number": 1, "title": "Intro"}
        assert result["sections"][1] == {"number": 2, "title": "Methods"}


class TestMinWordsForLength:
    def test_short(self, agent):
        assert agent._min_words_for_length("short") == 120

    def test_long(self, agent):
        assert agent._min_words_for_length("long") == 240

    def test_medium(self, agent):
        assert agent._min_words_for_length("medium") == 180

    def test_default(self, agent):
        assert agent._min_words_for_length("unknown") == 180

    def test_none(self, agent):
        assert agent._min_words_for_length(None) == 180

    def test_case_insensitive(self, agent):
        assert agent._min_words_for_length("SHORT") == 120
        assert agent._min_words_for_length("LONG") == 240


class TestSelectLowSections:
    def test_empty_map(self, agent):
        assert agent._select_low_sections({}, 100) == []

    def test_all_above_min(self, agent):
        sections = {"Intro": "word " * 200, "Methods": "word " * 200}
        result = agent._select_low_sections(sections, 100)
        assert len(result) <= 3

    def test_some_below_min(self, agent):
        sections = {"Intro": "short", "Methods": "word " * 200}
        result = agent._select_low_sections(sections, 100)
        assert "Intro" in result
        assert "Methods" not in result

    def test_returns_at_most_limit(self, agent):
        sections = {f"S{i}": "short" for i in range(10)}
        result = agent._select_low_sections(sections, 100, limit=3)
        assert len(result) == 3

    def test_skips_references(self, agent):
        sections = {"References": "short", "Intro": "short"}
        result = agent._select_low_sections(sections, 100)
        assert "References" not in result

    def test_skips_bibliography(self, agent):
        sections = {"Bibliography": "short", "Intro": "short"}
        result = agent._select_low_sections(sections, 100)
        assert "Bibliography" not in result


class TestApplyQualityFloor:
    def test_empty_map(self, agent):
        result = agent._apply_quality_floor({}, ["Intro"], 50)
        assert isinstance(result, dict)

    def test_adds_words_to_short_section(self, agent):
        sections = {"Intro": "short"}
        result = agent._apply_quality_floor(sections, ["Intro"], 50)
        assert agent._count_words(result["Intro"]) >= 50

    def test_skips_references(self, agent):
        sections = {"Intro": "short", "References": "short"}
        result = agent._apply_quality_floor(sections, ["Intro", "References"], 50)
        assert agent._count_words(result["References"]) == 1

    def test_skips_bibliography(self, agent):
        sections = {"Intro": "short", "Bibliography": "short"}
        result = agent._apply_quality_floor(sections, ["Intro", "Bibliography"], 50)
        assert agent._count_words(result["Bibliography"]) == 1

    def test_adds_citation_if_missing(self, agent):
        sections = {"Intro": "word " * 60}
        result = agent._apply_quality_floor(sections, ["Intro"], 50)
        assert "[1]" in result["Intro"]

    def test_preserves_existing_citation(self, agent):
        sections = {"Intro": "word " * 60 + " [42]"}
        result = agent._apply_quality_floor(sections, ["Intro"], 50)
        assert "[1]" not in result["Intro"]

    def test_not_required_section_unaffected(self, agent):
        sections = {"Intro": "short", "Other": "short"}
        result = agent._apply_quality_floor(sections, ["Intro"], 50)
        assert agent._count_words(result["Other"]) == 1


class TestRetrieveTemplateRules:
    def test_empty_sections(self, agent):
        agent.rag_engine.query_rules.return_value = []
        result = agent._retrieve_template_rules("IEEE", [])
        agent.rag_engine.query_rules.assert_called_once_with("IEEE", "general", top_k=2)
        assert result == []

    def test_queries_each_section(self, agent):
        agent.rag_engine.query_rules.return_value = [{"text": "rule1"}]
        result = agent._retrieve_template_rules("IEEE", ["Intro", "Methods"])
        assert len(result) == 2
        assert agent.rag_engine.query_rules.call_count == 2

    def test_fallback_to_general_when_no_rules(self, agent):
        agent.rag_engine.query_rules.return_value = []
        result = agent._retrieve_template_rules("ACM", ["Intro", "Methods"])
        agent.rag_engine.query_rules.assert_any_call("ACM", "general", top_k=2)


class TestIsCanceled:
    @pytest.mark.asyncio
    async def test_not_canceled(self, agent):
        agent.session_service.get_session = AsyncMock(return_value={"status": "processing"})
        result = await agent._is_canceled("s1")
        assert result is False

    @pytest.mark.asyncio
    async def test_canceled(self, agent):
        agent.session_service.get_session = AsyncMock(return_value={"status": "canceled"})
        result = await agent._is_canceled("s1")
        assert result is True

    @pytest.mark.asyncio
    async def test_stopping(self, agent):
        agent.session_service.get_session = AsyncMock(return_value={"status": "stopping"})
        result = await agent._is_canceled("s1")
        assert result is True

    @pytest.mark.asyncio
    async def test_exception_returns_false(self, agent):
        agent.session_service.get_session = AsyncMock(side_effect=Exception("fail"))
        result = await agent._is_canceled("s1")
        assert result is False

    @pytest.mark.asyncio
    async def test_none_session(self, agent):
        agent.session_service.get_session = AsyncMock(return_value=None)
        result = await agent._is_canceled("s1")
        assert result is False


class TestEmitSse:
    @pytest.mark.asyncio
    async def test_basic(self, agent):
        with patch("app.pipeline.generation.agent.make_event") as mock_me:
            mock_me.return_value = {"event": "data"}
            await agent._emit_sse("s1", stage="test", progress=50, message="hello")
            mock_me.assert_called_once_with(
                "stage_update", session_id="s1", stage="test", progress=50,
                payload={"stage": "test", "progress": 50, "message": "hello"},
            )
            agent.pubsub.publish.assert_called_once_with("session:s1", {"event": "data"})

    @pytest.mark.asyncio
    async def test_with_extra(self, agent):
        with patch("app.pipeline.generation.agent.make_event") as mock_me:
            mock_me.return_value = {"event": "data"}
            await agent._emit_sse("s1", stage="test", progress=50, message="hello", extra={"foo": "bar"})
            payload = mock_me.call_args[1]["payload"]
            assert payload["foo"] == "bar"
            assert payload["stage"] == "test"


class TestStreamChunks:
    @pytest.mark.asyncio
    async def test_empty_text(self, agent):
        with patch("app.pipeline.generation.agent.make_event") as mock_me:
            await agent._stream_chunks("s1", event_type="chunk", stage="w", progress=50, text="")
            mock_me.assert_not_called()

    @pytest.mark.asyncio
    async def test_small_text_no_split(self, agent):
        with patch("app.pipeline.generation.agent.make_event") as mock_me:
            mock_me.return_value = {"event": "data"}
            await agent._stream_chunks("s1", event_type="chunk", stage="w", progress=50, text="hello", chunk_size=400)
            mock_me.assert_called_once()
            assert mock_me.call_args[1]["payload"]["content"] == "hello"

    @pytest.mark.asyncio
    async def test_large_text_split(self, agent):
        with patch("app.pipeline.generation.agent.make_event") as mock_me:
            mock_me.return_value = {"event": "data"}
            text = "a" * 1000
            await agent._stream_chunks("s1", event_type="chunk", stage="w", progress=50, text=text, chunk_size=400)
            assert mock_me.call_count == 3

    @pytest.mark.asyncio
    async def test_with_extra(self, agent):
        with patch("app.pipeline.generation.agent.make_event") as mock_me:
            mock_me.return_value = {"event": "data"}
            await agent._stream_chunks("s1", event_type="chunk", stage="w", progress=50, text="hi", extra={"reset": True})
            payload = mock_me.call_args[1]["payload"]
            assert payload["reset"] is True


class TestUpdateStatus:
    @pytest.mark.asyncio
    async def test_basic_update(self, agent):
        agent.session_service.update_session = AsyncMock()
        with patch.object(agent, "_emit_sse") as mock_sse:
            await agent._update_status("s1", status="processing", progress=50, message="working", config={"stage": "test"})
            agent.session_service.update_session.assert_called_once()
            kwargs = agent.session_service.update_session.call_args.kwargs
            assert kwargs["status"] == "processing"
            assert kwargs["progress"] == 50
            mock_sse.assert_called_once()

    @pytest.mark.asyncio
    async def test_clamps_progress(self, agent):
        agent.session_service.update_session = AsyncMock()
        with patch.object(agent, "_emit_sse"):
            await agent._update_status("s1", status="done", progress=150, message="done", config={})
            assert agent.session_service.update_session.call_args.kwargs["progress"] == 100
            await agent._update_status("s1", status="start", progress=-5, message="start", config={})
            assert agent.session_service.update_session.call_args.kwargs["progress"] == 0

    @pytest.mark.asyncio
    async def test_includes_outline(self, agent):
        agent.session_service.update_session = AsyncMock()
        with patch.object(agent, "_emit_sse"):
            await agent._update_status("s1", status="done", progress=100, message="done", config={}, outline={"sections": []})
            assert agent.session_service.update_session.call_args.kwargs["outline_json"] == {"sections": []}


class TestPersistLlmTurn:
    @pytest.mark.asyncio
    async def test_adds_three_messages(self, agent):
        agent.session_service.add_message = AsyncMock()
        await agent._persist_llm_turn("s1", "sys", "usr", "ast")
        assert agent.session_service.add_message.call_count == 3
        calls = agent.session_service.add_message.call_args_list
        assert calls[0].args == ("s1", "system", "sys")
        assert calls[1].args == ("s1", "user", "usr")
        assert calls[2].args == ("s1", "assistant", "ast")


class TestLlmText:
    @pytest.mark.asyncio
    async def test_basic_call(self, agent):
        with (
            patch("app.pipeline.generation.agent.generate_with_fallback") as mock_gwf,
            patch.object(agent, "_persist_llm_turn") as mock_persist,
        ):
            mock_gwf.return_value = {"text": "  result  "}
            result = await agent._llm_text("s1", "system msg", "user msg")
            assert result == "result"
            mock_gwf.assert_called_once()
            mock_persist.assert_called_once_with("s1", "system msg", "user msg", "result")

    @pytest.mark.asyncio
    async def test_empty_result(self, agent):
        with (
            patch("app.pipeline.generation.agent.generate_with_fallback") as mock_gwf,
            patch.object(agent, "_persist_llm_turn"),
        ):
            mock_gwf.return_value = {"text": ""}
            result = await agent._llm_text("s1", "sys", "usr")
            assert result == ""

    @pytest.mark.asyncio
    async def test_max_tokens_passed(self, agent):
        with (
            patch("app.pipeline.generation.agent.generate_with_fallback") as mock_gwf,
            patch.object(agent, "_persist_llm_turn"),
        ):
            mock_gwf.return_value = {"text": "x"}
            await agent._llm_text("s1", "sys", "usr", max_tokens=999)
            assert mock_gwf.call_args.kwargs["max_tokens"] == 999


class TestLlmJson:
    @pytest.mark.asyncio
    async def test_successful_extraction(self, agent):
        with patch.object(agent, "_llm_text") as mock_text:
            mock_text.return_value = '{"key": "value"}'
            result = await agent._llm_json("s1", "sys", "usr")
            assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_empty_text_returns_none(self, agent):
        with patch.object(agent, "_llm_text") as mock_text:
            mock_text.return_value = ""
            result = await agent._llm_json("s1", "sys", "usr")
            assert result is None

    @pytest.mark.asyncio
    async def test_no_json_returns_none(self, agent):
        with patch.object(agent, "_llm_text") as mock_text:
            mock_text.return_value = "no json here"
            result = await agent._llm_json("s1", "sys", "usr")
            assert result is None

    @pytest.mark.asyncio
    async def test_invalid_json_returns_none(self, agent):
        with patch.object(agent, "_llm_text") as mock_text:
            mock_text.return_value = '{"key": broken}'
            result = await agent._llm_json("s1", "sys", "usr")
            assert result is None


class TestGenerateSection:
    @pytest.mark.asyncio
    async def test_basic(self, agent):
        with (
            patch.object(agent, "_llm_text") as mock_text,
            patch.object(agent, "_stream_chunks") as mock_stream,
        ):
            mock_text.return_value = "section content"
            result = await agent._generate_section("s1", "Intro", "some prompt")
            assert result == "section content"
            mock_text.assert_called_once_with("s1", "You are an academic writing assistant. Draft the 'Intro' section.", "some prompt", max_tokens=1400)
            mock_stream.assert_called_once()


class TestGenerateOutline:
    @pytest.mark.asyncio
    async def test_successful(self, agent):
        with (
            patch.object(agent, "_llm_json") as mock_json,
            patch.object(agent, "_stream_chunks"),
        ):
            mock_json.return_value = {"title": "Paper", "sections": [{"number": 1, "title": "Intro"}]}
            result = await agent._generate_outline("s1", {"title": "Paper", "sections": ["Intro"]}, [], [])
            assert result["title"] == "Paper"

    @pytest.mark.asyncio
    async def test_fallback_when_llm_returns_none(self, agent):
        with (
            patch.object(agent, "_llm_json") as mock_json,
            patch.object(agent, "_stream_chunks"),
        ):
            mock_json.return_value = None
            result = await agent._generate_outline("s1", {"title": "My Paper", "sections": ["Intro", "Methods"]}, [], [])
            assert result["title"] == "My Paper"
            assert len(result["sections"]) == 2

    @pytest.mark.asyncio
    async def test_fallback_no_title(self, agent):
        with (
            patch.object(agent, "_llm_json") as mock_json,
            patch.object(agent, "_stream_chunks"),
        ):
            mock_json.return_value = None
            result = await agent._generate_outline("s1", {"sections": ["Intro"]}, [], [])
            assert result["title"] == "Generated Paper"
            assert result["sections"][0]["title"] == "Intro"

    @pytest.mark.asyncio
    async def test_fallback_empty_sections(self, agent):
        with (
            patch.object(agent, "_llm_json") as mock_json,
            patch.object(agent, "_stream_chunks"),
        ):
            mock_json.return_value = None
            result = await agent._generate_outline("s1", {"title": "X"}, [], [])
            assert result["sections"] == []


class TestRenderDocument:
    @pytest.mark.asyncio
    async def test_basic(self, agent):
        with (
            patch("app.pipeline.generation.agent.generate_block_id") as mock_gid,
            patch("app.pipeline.generation.agent.Formatter") as mock_fmt,
        ):
            mock_gid.side_effect = [f"blk_{i:03d}" for i in range(20)]
            mock_fmt_instance = mock_fmt.return_value
            mock_fmt_instance.process.return_value = MagicMock()
            agent.pipeline_orchestrator._export_document.return_value = "/out/output.docx"
            result = await agent._render_document(
                "s1",
                {"keywords": ["ml"], "template": "IEEE"},
                {"title": "Paper"},
                {"Intro": "Hello world", "Methods": "Step one\n\nStep two"},
                ["[1] Ref"],
            )
            assert result == "/out/output.docx"
            assert agent.pipeline_orchestrator._export_document.called

    @pytest.mark.asyncio
    async def test_without_references(self, agent):
        with (
            patch("app.pipeline.generation.agent.generate_block_id") as mock_gid,
            patch("app.pipeline.generation.agent.Formatter"),
        ):
            mock_gid.side_effect = [f"blk_{i:03d}" for i in range(20)]
            agent.pipeline_orchestrator._export_document.return_value = "/out/doc.docx"
            result = await agent._render_document("s1", {"keywords": []}, {"title": "X"}, {"A": "B"}, [])
            assert result == "/out/doc.docx"


class TestRunWebResearch:
    @pytest.mark.asyncio
    async def test_with_query(self, agent):
        with patch("langchain_community.tools.DuckDuckGoSearchResults") as mock_ddg:
            tool = MagicMock()
            tool.invoke.return_value = "results"
            mock_ddg.return_value = tool
            result = await agent._run_web_research({"title": "ML Survey", "keywords": ["machine", "learning"]})
            assert result == "results"

    @pytest.mark.asyncio
    async def test_fallback_query(self, agent):
        with patch("langchain_community.tools.DuckDuckGoSearchResults") as mock_ddg:
            tool = MagicMock()
            tool.invoke.return_value = "results"
            mock_ddg.return_value = tool
            result = await agent._run_web_research({"title": "", "keywords": []})
            assert result == "results"

    @pytest.mark.asyncio
    async def test_import_failure(self, agent):
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "DuckDuckGoSearchResults" in str(name):
                raise ImportError("not available")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = await agent._run_web_research({"title": "test", "keywords": []})
            assert result == []

    @pytest.mark.asyncio
    async def test_tool_exception(self, agent):
        with patch("langchain_community.tools.DuckDuckGoSearchResults") as mock_ddg:
            tool = MagicMock()
            tool.invoke.side_effect = Exception("API error")
            mock_ddg.return_value = tool
            result = await agent._run_web_research({"title": "test", "keywords": ["ai"]})
            assert result == []

    @pytest.mark.asyncio
    async def test_tool_run_fallback(self, agent):
        with patch("langchain_community.tools.DuckDuckGoSearchResults") as mock_ddg:
            class NoInvoke:
                def run(self, query=""):
                    return "results"
            mock_ddg.return_value = NoInvoke()
            result = await agent._run_web_research({"title": "test", "keywords": ["ai"]})
            assert result == "results"


class TestBoostQuality:
    @pytest.mark.asyncio
    async def test_no_low_sections(self, agent):
        with (
            patch.object(agent, "_select_low_sections") as mock_select,
            patch.object(agent, "_min_words_for_length") as mock_mwl,
        ):
            mock_mwl.return_value = 180
            mock_select.return_value = []
            result = await agent._boost_quality(
                session_id="s1", task_spec={}, template_rules=[], outline={},
                sections_map={"A": "text"}, references=[], config={"output_path": "/out", "quality": {}},
            )
            assert result[0] == {"A": "text"}
            assert result[3] == {}

    @pytest.mark.asyncio
    async def test_with_low_sections(self, agent):
        with (
            patch.object(agent, "_select_low_sections") as mock_select,
            patch.object(agent, "_min_words_for_length") as mock_mwl,
            patch.object(agent, "_llm_text") as mock_text,
            patch.object(agent, "_stream_chunks"),
            patch.object(agent, "_is_canceled") as mock_cancel,
        ):
            mock_mwl.return_value = 100
            mock_select.return_value = ["Intro"]
            mock_cancel.return_value = False
            mock_text.return_value = "Improved section content"
            agent.citations.assemble = AsyncMock(return_value=({"Intro": "Improved"}, "refs"))
            agent.session_service.update_session = AsyncMock()
            agent.session_service.save_document_version = AsyncMock()
            agent.pipeline_orchestrator._export_document.return_value = "/out/improved.docx"
            agent.quality_scorer.score.return_value = {"overall_score": 85}

            with patch.object(agent, "_apply_quality_floor") as mock_floor:
                mock_floor.return_value = {"Intro": "Improved with filler"}
                result = await agent._boost_quality(
                    session_id="s1", task_spec={"length": "medium"}, template_rules=[], outline={},
                    sections_map={"Intro": "old"}, references=[], config={"output_path": "/out", "quality": {}},
                )
                assert "Intro" in result[0]

    @pytest.mark.asyncio
    async def test_cancelled_during_loop(self, agent):
        agent.session_service.update_session = AsyncMock()
        with (
            patch.object(agent, "_select_low_sections") as mock_select,
            patch.object(agent, "_min_words_for_length") as mock_mwl,
            patch.object(agent, "_is_canceled") as mock_cancel,
            patch.object(agent, "_emit_sse"),
        ):
            mock_mwl.return_value = 100
            mock_select.return_value = ["Intro"]
            mock_cancel.return_value = True
            result = await agent._boost_quality(
                session_id="s1", task_spec={}, template_rules=[], outline={},
                sections_map={"Intro": "old"}, references=["[1] Ref"], config={"output_path": "/out", "quality": {}},
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_quality_floor_applied_when_below_target(self, agent):
        with (
            patch.object(agent, "_select_low_sections") as mock_select,
            patch.object(agent, "_min_words_for_length") as mock_mwl,
            patch.object(agent, "_llm_text"),
            patch.object(agent, "_stream_chunks"),
            patch.object(agent, "_is_canceled") as mock_cancel,
        ):
            mock_mwl.return_value = 100
            mock_select.side_effect = [["Intro"], ["References"]]  # second call returns [] after improvement
            mock_cancel.return_value = False
            agent.citations.assemble = AsyncMock(return_value=({"Intro": "Improved"}, "refs"))
            agent.session_service.update_session = AsyncMock()
            agent.session_service.save_document_version = AsyncMock()
            agent.pipeline_orchestrator._export_document.return_value = "/out/doc.docx"
            agent.quality_scorer.score.return_value = {"overall_score": 60}
            agent.quality_target = 70

            result = await agent._boost_quality(
                session_id="s1", task_spec={"length": "medium", "sections": ["Intro"]},
                template_rules=[], outline={}, sections_map={"Intro": "old"},
                references=["[1] Ref"], config={"output_path": "/out", "quality": {}},
            )
            assert result is not None


class TestRun:
    @pytest.mark.asyncio
    async def test_full_run(self, agent):
        with (
            patch("app.pipeline.generation.agent.TaskParser") as mock_tp_cls,
            patch.object(agent, "_update_status"),
            patch.object(agent, "_persist_llm_turn"),
            patch.object(agent, "_is_canceled") as mock_cancel,
            patch.object(agent, "_retrieve_template_rules") as mock_rtr,
            patch.object(agent, "_run_web_research") as mock_rwr,
            patch.object(agent, "_generate_outline") as mock_go,
        ):
            mock_cancel.return_value = False
            mock_rtr.return_value = [{"rule": "x"}]
            mock_rwr.return_value = []
            mock_go.return_value = {"title": "Paper", "sections": []}
            agent.session_service.get_session = AsyncMock(return_value={"config_json": {"key": "val"}})
            parser = MagicMock()
            parser.parse = AsyncMock(return_value={"template": "IEEE", "sections": ["Intro"], "title": "My Paper"})
            parser.last_turn = {"system": "s", "user": "u", "assistant": "a"}
            mock_tp_cls.return_value = parser
            await agent.run("s1", "write a paper")
            assert agent.session_service.get_session.called
            assert parser.parse.called

    @pytest.mark.asyncio
    async def test_cancelled_after_task_parse(self, agent):
        with (
            patch("app.pipeline.generation.agent.TaskParser") as mock_tp_cls,
            patch.object(agent, "_update_status"),
            patch.object(agent, "_persist_llm_turn"),
            patch.object(agent, "_is_canceled") as mock_cancel,
        ):
            mock_cancel.side_effect = [False, True]
            agent.session_service.get_session = AsyncMock(return_value={"config_json": {}})
            parser = MagicMock()
            parser.parse = AsyncMock(return_value={"template": "IEEE"})
            parser.last_turn = None
            mock_tp_cls.return_value = parser
            await agent.run("s1", "prompt")
            assert agent.session_service.get_session.called

    @pytest.mark.asyncio
    async def test_session_config_fallback(self, agent):
        with (
            patch("app.pipeline.generation.agent.TaskParser") as mock_tp_cls,
            patch.object(agent, "_update_status"),
            patch.object(agent, "_persist_llm_turn"),
            patch.object(agent, "_is_canceled") as mock_cancel,
            patch.object(agent, "_retrieve_template_rules"),
            patch.object(agent, "_run_web_research"),
            patch.object(agent, "_generate_outline"),
        ):
            mock_cancel.return_value = False
            agent.session_service.get_session = AsyncMock(return_value=None)
            parser = MagicMock()
            parser.parse = AsyncMock(return_value={"template": "IEEE"})
            parser.last_turn = None
            mock_tp_cls.return_value = parser
            await agent.run("s1", "prompt")
            assert True


class TestResume:
    @pytest.mark.asyncio
    async def test_session_not_found(self, agent):
        agent.session_service.get_session = AsyncMock(return_value=None)
        await agent.resume("s1")
        assert True

    @pytest.mark.asyncio
    async def test_full_resume(self, agent):
        with (
            patch.object(agent, "_update_status"),
            patch.object(agent, "_is_canceled") as mock_cancel,
            patch.object(agent, "_retrieve_template_rules") as mock_rtr,
            patch.object(agent, "_generate_section") as mock_gs,
            patch.object(agent, "_emit_sse"),
            patch.object(agent, "_boost_quality"),
            patch("app.pipeline.generation.agent.get_section_prompt") as mock_gsp,
        ):
            mock_cancel.return_value = False
            mock_rtr.return_value = []
            mock_gs.return_value = "section text"
            mock_gsp.return_value = "prompt text"
            agent.citations.assemble = AsyncMock(return_value=({"Intro": "section"}, "refs\nline2"))
            agent.pipeline_orchestrator._export_document.return_value = "/out/output.docx"
            agent.session_service.get_session = AsyncMock(return_value={
                "config_json": {"template": "IEEE", "sections": ["Intro"]},
                "outline_json": {"sections": [{"title": "Intro"}]},
                "progress": 40,
            })
            agent.session_service.update_session = AsyncMock()
            agent.session_service.save_document_version = AsyncMock()
            agent.quality_scorer.score.return_value = {"overall_score": 95}
            await agent.resume("s1")
            assert mock_gs.called

    @pytest.mark.asyncio
    async def test_template_rules_fallback(self, agent):
        with (
            patch.object(agent, "_update_status"),
            patch.object(agent, "_is_canceled"),
            patch.object(agent, "_retrieve_template_rules") as mock_rtr,
            patch.object(agent, "_generate_section"),
            patch.object(agent, "_emit_sse"),
            patch.object(agent, "_boost_quality"),
            patch("app.pipeline.generation.agent.get_section_prompt"),
        ):
            mock_rtr.return_value = [{"rule": "x"}]
            agent.citations.assemble = AsyncMock(return_value=({"Intro": "text"}, ""))
            agent.pipeline_orchestrator._export_document.return_value = "/out/o.docx"
            agent.session_service.get_session = AsyncMock(return_value={
                "config_json": {},
                "outline_json": {},
                "progress": 40,
            })
            agent.session_service.update_session = AsyncMock()
            agent.session_service.save_document_version = AsyncMock()
            agent.quality_scorer.score.return_value = {"overall_score": 85}
            await agent.resume("s1")
            mock_rtr.assert_called_once()


class TestRewriteSection:
    @pytest.mark.asyncio
    async def test_session_not_found(self, agent):
        agent.session_service.get_session = AsyncMock(return_value=None)
        await agent.rewrite_section("s1", "Intro", "make it better")
        assert True

    @pytest.mark.asyncio
    async def test_full_rewrite(self, agent):
        with (
            patch.object(agent, "_llm_text") as mock_text,
            patch.object(agent, "_stream_chunks"),
            patch.object(agent, "_render_document") as mock_render,
            patch.object(agent, "_emit_sse"),
        ):
            mock_text.return_value = "Rewritten content"
            mock_render.return_value = "/out/rewritten.docx"
            agent.session_service.get_session = AsyncMock(return_value={
                "config_json": {},
                "outline_json": {},
                "progress": 90,
                "status": "completed",
            })
            agent.session_service.get_latest_document = AsyncMock(return_value={
                "content_json": {"outline": {}, "sections": {"Intro": "old"}},
            })
            agent.session_service.get_messages = AsyncMock(return_value=[
                {"role": "user", "content": "write paper"},
            ])
            agent.session_service.update_session = AsyncMock()
            agent.session_service.save_document_version = AsyncMock()
            agent.citations.assemble = AsyncMock(return_value=({"Intro": "Rewritten"}, "refs"))
            agent.quality_scorer.score.return_value = {"overall_score": 90}
            await agent.rewrite_section("s1", "Intro", "expand")
            assert agent.session_service.get_session.called

    @pytest.mark.asyncio
    async def test_with_sanitized_history(self, agent):
        with (
            patch.object(agent, "_llm_text") as mock_text,
            patch.object(agent, "_stream_chunks"),
            patch.object(agent, "_render_document") as mock_render,
            patch.object(agent, "_emit_sse"),
            patch("app.pipeline.generation.agent.sanitize_for_llm") as mock_san,
        ):
            mock_text.return_value = "Rewritten content"
            mock_render.return_value = "/out/rewritten.docx"
            mock_san.return_value = "sanitized"
            agent.session_service.get_session = AsyncMock(return_value={
                "config_json": {"citation_style": "apa"},
                "outline_json": {},
                "progress": 90,
                "status": "completed",
            })
            agent.session_service.get_latest_document = AsyncMock(return_value={
                "content_json": {"outline": {}, "sections": {"Intro": "old"}},
            })
            agent.session_service.get_messages = AsyncMock(return_value=[])
            agent.session_service.update_session = AsyncMock()
            agent.session_service.save_document_version = AsyncMock()
            agent.citations.assemble = AsyncMock(return_value=({"Intro": "Rewritten"}, "refs"))
            agent.quality_scorer.score.return_value = {"overall_score": 80}
            await agent.rewrite_section("s1", "Intro", "improve")
            mock_san.assert_called_once()
