# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch, call

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


# ── Init ──────────────────────────────────────────────────────────────────────

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
        my_pubsub = MagicMock()
        with (
            patch("app.pipeline.generation.agent.QualityScorer"),
            patch("app.pipeline.generation.agent.get_rag_engine"),
            patch("app.pipeline.generation.agent.RedisPubSub") as mock_ps,
            patch("app.pipeline.generation.agent.CitationAssemblyService"),
        ):
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


# ── Static helpers ────────────────────────────────────────────────────────────

class TestCountWords:
    def test_none(self, AP):
        assert AP._count_words(None) == 0
    def test_empty(self, AP):
        assert AP._count_words("") == 0
    def test_single(self, AP):
        assert AP._count_words("hello") == 1
    def test_multiple(self, AP):
        assert AP._count_words("a b c") == 3
    def test_whitespace(self, AP):
        assert AP._count_words("   \n\t   ") == 0
    def test_non_string(self, AP):
        assert AP._count_words(42) == 1


class TestHasCitation:
    def test_none(self, AP):
        assert AP._has_citation(None) is False
    def test_empty(self, AP):
        assert AP._has_citation("") is False
    def test_bracket_number(self, AP):
        assert AP._has_citation("text [1]") is True
    def test_multiple_numbers(self, AP):
        assert AP._has_citation("[1, 2, 3]") is True
    def test_parenthetical(self, AP):
        assert AP._has_citation("(Smith, 2020)") is True
    def test_bracket_author(self, AP):
        assert AP._has_citation("[Smith, 2020]") is True
    def test_no_match(self, AP):
        assert AP._has_citation("plain text") is False
    def test_partial_bracket(self, AP):
        assert AP._has_citation("[1") is False


class TestExtractJson:
    def test_none(self, AP):
        assert AP._extract_json(None) is None
    def test_empty(self, AP):
        assert AP._extract_json("") is None
    def test_simple(self, AP):
        assert AP._extract_json('{"a":1}') == '{"a":1}'
    def test_surrounding_text(self, AP):
        assert AP._extract_json('x {"a":1} y') == '{"a":1}'
    def test_code_fence(self, AP):
        assert AP._extract_json('```\n{"a":1}\n```') == '{"a":1}'
    def test_json_lang_fence(self, AP):
        assert AP._extract_json('```json\n{"a":1}\n```') == '{"a":1}'
    def test_no_braces(self, AP):
        assert AP._extract_json("hello") is None
    def test_unmatched(self, AP):
        assert AP._extract_json('{"a":1') is None
    def test_only_closing(self, AP):
        assert AP._extract_json("}") is None
    def test_reversed_braces(self, AP):
        assert AP._extract_json("}{") is None


class TestExtractOutlineSections:
    def test_none(self, AP):
        assert AP._extract_outline_sections(None) == []
    def test_dict_with_sections(self, AP):
        result = AP._extract_outline_sections({"sections": [{"title": "A"}, {"title": "B"}]})
        assert len(result) == 2
    def test_dict_no_sections_key(self, AP):
        assert AP._extract_outline_sections({"title": "X"}) == []
    def test_dict_falsy_items_filtered(self, AP):
        result = AP._extract_outline_sections({"sections": [{"title": "A"}, None, ""]})
        assert result == [{"title": "A"}]
    def test_list_of_dicts(self, AP):
        assert AP._extract_outline_sections([{"title": "A"}]) == [{"title": "A"}]
    def test_list_of_strings(self, AP):
        assert AP._extract_outline_sections(["Intro"]) == [{"title": "Intro"}]
    def test_empty_list(self, AP):
        assert AP._extract_outline_sections([]) == []
    def test_not_dict_or_list(self, AP):
        assert AP._extract_outline_sections("string") == []


class TestNormalizeSections:
    def test_none(self, AP):
        assert AP._normalize_sections(None) == {}
    def test_empty_dict(self, AP):
        assert AP._normalize_sections({}) == {}
    def test_dict(self, AP):
        assert AP._normalize_sections({"A": "text"}) == {"A": "text"}
    def test_dict_non_string(self, AP):
        assert AP._normalize_sections({"A": 1}) == {"A": "1"}
    def test_list_of_dicts(self, AP):
        result = AP._normalize_sections([{"title": "Intro", "content": "Hello"}])
        assert result == {"Intro": "Hello"}
    def test_list_section_key(self, AP):
        result = AP._normalize_sections([{"section": "Intro", "content": "text"}])
        assert result == {"Intro": "text"}
    def test_list_no_title(self, AP):
        assert AP._normalize_sections([{"content": "text"}]) == {}
    def test_list_non_dict(self, AP):
        assert AP._normalize_sections(["a", "b"]) == {}
    def test_other(self, AP):
        assert AP._normalize_sections(42) == {}


class TestEnsureOutlineNumbers:
    def test_no_sections(self, AP):
        assert AP._ensure_outline_numbers({"title": "X"}) == {"title": "X"}
    def test_sections_not_list(self, AP):
        assert AP._ensure_outline_numbers({"sections": "bad"}) == {"sections": "bad"}
    def test_empty_sections(self, AP):
        assert AP._ensure_outline_numbers({"sections": []}) == {"sections": []}
    def test_adds_numbers(self, AP):
        result = AP._ensure_outline_numbers({"sections": [{"title": "A"}, {"title": "B"}]})
        assert result["sections"][0]["number"] == 1
        assert result["sections"][1]["number"] == 2
    def test_preserves_number(self, AP):
        result = AP._ensure_outline_numbers({"sections": [{"title": "A", "number": 5}]})
        assert result["sections"][0]["number"] == 5
    def test_section_as_title(self, AP):
        result = AP._ensure_outline_numbers({"sections": [{"section": "Intro"}]})
        assert result["sections"][0]["title"] == "Intro"
    def test_non_dict_section(self, AP):
        result = AP._ensure_outline_numbers({"sections": ["Intro"]})
        assert result["sections"][0] == {"number": 1, "title": "Intro"}


# ── Instance helpers ──────────────────────────────────────────────────────────

class TestMinWordsForLength:
    def test_short(self, agent):
        assert agent._min_words_for_length("short") == 120
    def test_long(self, agent):
        assert agent._min_words_for_length("long") == 240
    def test_medium(self, agent):
        assert agent._min_words_for_length("medium") == 180
    def test_unknown(self, agent):
        assert agent._min_words_for_length("unknown") == 180
    def test_none(self, agent):
        assert agent._min_words_for_length(None) == 180
    def test_case_insensitive(self, agent):
        assert agent._min_words_for_length("SHORT") == 120


class TestSelectLowSections:
    def test_empty(self, agent):
        assert agent._select_low_sections({}, 100) == []
    def test_all_above(self, agent):
        s = {"A": "word " * 200, "B": "word " * 200}
        result = agent._select_low_sections(s, 100)
        assert len(result) <= 3
    def test_some_below(self, agent):
        s = {"A": "short", "B": "word " * 200}
        result = agent._select_low_sections(s, 100)
        assert "A" in result
    def test_limit(self, agent):
        s = {f"S{i}": "short" for i in range(10)}
        assert len(agent._select_low_sections(s, 100, limit=3)) == 3
    def test_skips_references(self, agent):
        s = {"References": "short", "Intro": "short"}
        assert "References" not in agent._select_low_sections(s, 100)
    def test_skips_bibliography(self, agent):
        assert "Bibliography" not in agent._select_low_sections({"Bibliography": "short"}, 100)


class TestApplyQualityFloor:
    def test_empty(self, agent):
        result = agent._apply_quality_floor({}, ["Intro"], 50)
        assert isinstance(result, dict)
    def test_adds_words(self, agent):
        result = agent._apply_quality_floor({"Intro": "short"}, ["Intro"], 50)
        assert agent._count_words(result["Intro"]) >= 50
    def test_skips_references(self, agent):
        result = agent._apply_quality_floor({"Intro": "short", "References": "short"}, ["Intro", "References"], 50)
        assert agent._count_words(result["References"]) == 1
    def test_adds_citation(self, agent):
        result = agent._apply_quality_floor({"Intro": "word " * 60}, ["Intro"], 50)
        assert "[1]" in result["Intro"]
    def test_preserves_existing_citation(self, agent):
        result = agent._apply_quality_floor({"Intro": "word " * 60 + " [42]"}, ["Intro"], 50)
        assert "[1]" not in result["Intro"]
    def test_not_required_unaffected(self, agent):
        result = agent._apply_quality_floor({"A": "short", "B": "short"}, ["A"], 50)
        assert agent._count_words(result["B"]) == 1


class TestRetrieveTemplateRules:
    def test_empty_sections(self, agent):
        agent.rag_engine.query_rules.return_value = []
        result = agent._retrieve_template_rules("IEEE", [])
        assert result == []
    def test_queries_each_section(self, agent):
        agent.rag_engine.query_rules.return_value = [{"text": "rule"}]
        result = agent._retrieve_template_rules("IEEE", ["Intro", "Methods"])
        assert len(result) == 2
    def test_fallback_to_general(self, agent):
        agent.rag_engine.query_rules.return_value = []
        result = agent._retrieve_template_rules("ACM", ["Intro"])
        agent.rag_engine.query_rules.assert_any_call("ACM", "general", top_k=2)


class TestIsCanceled:
    @pytest.mark.asyncio
    async def test_not_canceled(self, agent):
        agent.session_service.get_session = AsyncMock(return_value={"status": "processing"})
        assert await agent._is_canceled("s1") is False
    @pytest.mark.asyncio
    async def test_canceled(self, agent):
        agent.session_service.get_session = AsyncMock(return_value={"status": "canceled"})
        assert await agent._is_canceled("s1") is True
    @pytest.mark.asyncio
    async def test_stopping(self, agent):
        agent.session_service.get_session = AsyncMock(return_value={"status": "stopping"})
        assert await agent._is_canceled("s1") is True
    @pytest.mark.asyncio
    async def test_exception(self, agent):
        agent.session_service.get_session = AsyncMock(side_effect=Exception("fail"))
        assert await agent._is_canceled("s1") is False
    @pytest.mark.asyncio
    async def test_none_session(self, agent):
        agent.session_service.get_session = AsyncMock(return_value=None)
        assert await agent._is_canceled("s1") is False


class TestEmitSse:
    @pytest.mark.asyncio
    async def test_basic(self, agent):
        with patch("app.pipeline.generation.agent.make_event") as mock_me:
            mock_me.return_value = {"event": "data"}
            await agent._emit_sse("s1", stage="test", progress=50, message="hello")
            agent.pubsub.publish.assert_called_once_with("session:s1", {"event": "data"})
    @pytest.mark.asyncio
    async def test_with_extra(self, agent):
        with patch("app.pipeline.generation.agent.make_event") as mock_me:
            mock_me.return_value = {"event": "data"}
            await agent._emit_sse("s1", stage="test", progress=50, message="hello", extra={"foo": "bar"})
            payload = mock_me.call_args[1]["payload"]
            assert payload["foo"] == "bar"


class TestStreamChunks:
    @pytest.mark.asyncio
    async def test_empty_text(self, agent):
        with patch("app.pipeline.generation.agent.make_event") as mock_me:
            await agent._stream_chunks("s1", event_type="chunk", stage="w", progress=50, text="")
            mock_me.assert_not_called()
    @pytest.mark.asyncio
    async def test_small_text(self, agent):
        with patch("app.pipeline.generation.agent.make_event") as mock_me:
            mock_me.return_value = {"event": "data"}
            await agent._stream_chunks("s1", event_type="chunk", stage="w", progress=50, text="hello")
            assert mock_me.call_count == 1
    @pytest.mark.asyncio
    async def test_large_text(self, agent):
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
    async def test_basic(self, agent):
        agent.session_service.update_session = AsyncMock()
        with patch.object(agent, "_emit_sse") as mock_sse:
            await agent._update_status("s1", status="processing", progress=50, message="working", config={"k": "v"})
            assert agent.session_service.update_session.called
            mock_sse.assert_called_once()
    @pytest.mark.asyncio
    async def test_clamps_progress(self, agent):
        agent.session_service.update_session = AsyncMock()
        with patch.object(agent, "_emit_sse"):
            await agent._update_status("s1", status="done", progress=150, message="x", config={})
            assert agent.session_service.update_session.call_args.kwargs["progress"] == 100
            await agent._update_status("s1", status="start", progress=-5, message="x", config={})
            assert agent.session_service.update_session.call_args.kwargs["progress"] == 0
    @pytest.mark.asyncio
    async def test_with_outline(self, agent):
        agent.session_service.update_session = AsyncMock()
        with patch.object(agent, "_emit_sse"):
            await agent._update_status("s1", status="done", progress=100, message="x", config={}, outline={"s": []})
            assert agent.session_service.update_session.call_args.kwargs["outline_json"] == {"s": []}


class TestPersistLlmTurn:
    @pytest.mark.asyncio
    async def test_three_messages(self, agent):
        agent.session_service.add_message = AsyncMock()
        await agent._persist_llm_turn("s1", "sys", "usr", "ast")
        assert agent.session_service.add_message.call_count == 3


class TestLlmText:
    @pytest.fixture
    def mock_persist(self, agent):
        agent.session_service.add_message = AsyncMock()
        return agent.session_service.add_message

    @pytest.mark.asyncio
    async def test_basic(self, agent, mock_persist):
        with patch("app.pipeline.generation.agent.generate_with_fallback") as mock_gwf:
            mock_gwf.return_value = {"text": "  result  "}
            result = await agent._llm_text("s1", "sys", "usr")
            assert result == "result"
    @pytest.mark.asyncio
    async def test_empty(self, agent, mock_persist):
        with patch("app.pipeline.generation.agent.generate_with_fallback") as mock_gwf:
            mock_gwf.return_value = {"text": ""}
            result = await agent._llm_text("s1", "sys", "usr")
            assert result == ""
    @pytest.mark.asyncio
    async def test_max_tokens(self, agent, mock_persist):
        with patch("app.pipeline.generation.agent.generate_with_fallback") as mock_gwf:
            mock_gwf.return_value = {"text": "x"}
            await agent._llm_text("s1", "sys", "usr", max_tokens=999)
            assert mock_gwf.call_args.kwargs["max_tokens"] == 999


class TestLlmJson:
    @pytest.mark.asyncio
    async def test_success(self, agent):
        with patch.object(agent, "_llm_text") as mock_t:
            mock_t.return_value = '{"key": "val"}'
            assert await agent._llm_json("s1", "sys", "usr") == {"key": "val"}
    @pytest.mark.asyncio
    async def test_empty_text(self, agent):
        with patch.object(agent, "_llm_text") as mock_t:
            mock_t.return_value = ""
            assert await agent._llm_json("s1", "sys", "usr") is None
    @pytest.mark.asyncio
    async def test_no_json(self, agent):
        with patch.object(agent, "_llm_text") as mock_t:
            mock_t.return_value = "no json"
            assert await agent._llm_json("s1", "sys", "usr") is None
    @pytest.mark.asyncio
    async def test_invalid_json(self, agent):
        with patch.object(agent, "_llm_text") as mock_t:
            mock_t.return_value = '{"key": broken}'
            assert await agent._llm_json("s1", "sys", "usr") is None


class TestGenerateSection:
    @pytest.mark.asyncio
    async def test_basic(self, agent):
        with patch.object(agent, "_llm_text") as mock_t:
            mock_t.return_value = "content"
            result = await agent._generate_section("s1", "Intro", "prompt")
            assert result == "content"


class TestGenerateOutline:
    @pytest.mark.asyncio
    async def test_success(self, agent):
        with patch.object(agent, "_llm_json") as mock_j:
            mock_j.return_value = {"title": "Paper", "sections": [{"number": 1, "title": "Intro"}]}
            result = await agent._generate_outline("s1", {"title": "Paper", "sections": []}, [], [])
            assert result["title"] == "Paper"
    @pytest.mark.asyncio
    async def test_fallback(self, agent):
        with patch.object(agent, "_llm_json") as mock_j:
            mock_j.return_value = None
            result = await agent._generate_outline("s1", {"title": "My Paper", "sections": ["Intro"]}, [], [])
            assert result["title"] == "My Paper"
            assert len(result["sections"]) == 1
    @pytest.mark.asyncio
    async def test_fallback_no_title(self, agent):
        with patch.object(agent, "_llm_json") as mock_j:
            mock_j.return_value = None
            result = await agent._generate_outline("s1", {"sections": ["Intro"]}, [], [])
            assert result["title"] == "Generated Paper"


class TestRenderDocument:
    @pytest.mark.asyncio
    async def test_basic(self, agent):
        with patch("app.pipeline.generation.agent.generate_block_id") as mock_gid:
            mock_gid.side_effect = [f"blk_{i:03d}" for i in range(20)]
            result = await agent._render_document(
                "s1", {"keywords": ["ml"], "template": "IEEE"},
                {"title": "Paper"}, {"Intro": "Hello\n\nWorld"}, ["[1] Ref"],
            )
            assert result == "/fake/output.docx"
    @pytest.mark.asyncio
    async def test_no_references(self, agent):
        with patch("app.pipeline.generation.agent.generate_block_id") as mock_gid:
            mock_gid.side_effect = [f"blk_{i:03d}" for i in range(20)]
            result = await agent._render_document("s1", {"keywords": []}, {"title": "X"}, {"A": "B"}, [])
            assert result == "/fake/output.docx"


class TestRunWebResearch:
    @pytest.mark.asyncio
    async def test_with_query(self, agent):
        with patch("langchain_community.tools.DuckDuckGoSearchResults") as mock_ddg:
            tool = MagicMock()
            tool.invoke.return_value = "results"
            mock_ddg.return_value = tool
            result = await agent._run_web_research({"title": "ML Survey", "keywords": ["ml"]})
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
        original = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if "DuckDuckGoSearchResults" in str(name):
                raise ImportError("not available")
            return original(name, *args, **kwargs)
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
        with patch.object(agent, "_select_low_sections") as mock_sel:
            mock_sel.return_value = []
            result = await agent._boost_quality(
                session_id="s1", task_spec={}, template_rules=[], outline={},
                sections_map={"A": "text"}, references=[], config={"output_path": "/out", "quality": {}},
            )
            assert result[0] == {"A": "text"}
    @pytest.mark.asyncio
    async def test_with_low_sections(self, agent):
        with (
            patch.object(agent, "_select_low_sections") as mock_sel,
            patch.object(agent, "_llm_text") as mock_t,
            patch.object(agent, "_stream_chunks"),
            patch.object(agent, "_is_canceled") as mock_c,
        ):
            mock_sel.return_value = ["Intro"]
            mock_c.return_value = False
            mock_t.return_value = "Improved"
            agent.citations.assemble = AsyncMock(return_value=({"Intro": "Improved"}, "refs"))
            agent.session_service.update_session = AsyncMock()
            agent.session_service.save_document_version = AsyncMock()
            agent.quality_scorer.score.return_value = {"overall_score": 85}
            result = await agent._boost_quality(
                session_id="s1", task_spec={"length": "medium"}, template_rules=[], outline={},
                sections_map={"Intro": "old"}, references=[], config={"output_path": "/out", "quality": {}},
            )
            assert "Intro" in result[0]
    @pytest.mark.asyncio
    async def test_cancelled_during_loop(self, agent):
        agent.session_service.update_session = AsyncMock()
        with (
            patch.object(agent, "_select_low_sections") as mock_sel,
            patch.object(agent, "_is_canceled") as mock_c,
        ):
            mock_sel.return_value = ["Intro"]
            mock_c.return_value = True
            result = await agent._boost_quality(
                session_id="s1", task_spec={}, template_rules=[], outline={},
                sections_map={"Intro": "old"}, references=["[1] Ref"], config={"output_path": "/out", "quality": {}},
            )
            assert result is None
    @pytest.mark.asyncio
    async def test_quality_floor_applied(self, agent):
        with (
            patch.object(agent, "_select_low_sections") as mock_sel,
            patch.object(agent, "_llm_text"),
            patch.object(agent, "_stream_chunks"),
            patch.object(agent, "_is_canceled") as mock_c,
        ):
            mock_sel.side_effect = [["Intro"], ["References"]]
            mock_c.return_value = False
            agent.citations.assemble = AsyncMock(return_value=({"Intro": "Improved"}, "refs"))
            agent.session_service.update_session = AsyncMock()
            agent.session_service.save_document_version = AsyncMock()
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
            patch.object(agent, "_is_canceled") as mock_c,
            patch.object(agent, "_retrieve_template_rules") as mock_rtr,
            patch.object(agent, "_run_web_research") as mock_rwr,
            patch.object(agent, "_generate_outline") as mock_go,
        ):
            mock_c.return_value = False
            mock_rtr.return_value = [{"rule": "x"}]
            mock_rwr.return_value = []
            mock_go.return_value = {"title": "Paper", "sections": []}
            agent.session_service.get_session = AsyncMock(return_value={"config_json": {"k": "v"}})
            parser = MagicMock()
            parser.parse = AsyncMock(return_value={"template": "IEEE", "sections": ["Intro"], "title": "Paper"})
            parser.last_turn = {"system": "s", "user": "u", "assistant": "a"}
            mock_tp_cls.return_value = parser
            with patch.object(agent, "_persist_llm_turn"):
                await agent.run("s1", "write paper")
            assert agent.session_service.get_session.called
    @pytest.mark.asyncio
    async def test_cancelled_after_parse(self, agent):
        with (
            patch("app.pipeline.generation.agent.TaskParser") as mock_tp_cls,
            patch.object(agent, "_update_status"),
            patch.object(agent, "_is_canceled") as mock_c,
        ):
            mock_c.side_effect = [False, True]
            agent.session_service.get_session = AsyncMock(return_value={"config_json": {}})
            parser = MagicMock()
            parser.parse = AsyncMock(return_value={"template": "IEEE"})
            parser.last_turn = None
            mock_tp_cls.return_value = parser
            await agent.run("s1", "prompt")
    @pytest.mark.asyncio
    async def test_session_none(self, agent):
        with (
            patch("app.pipeline.generation.agent.TaskParser") as mock_tp_cls,
            patch.object(agent, "_update_status"),
            patch.object(agent, "_is_canceled") as mock_c,
            patch.object(agent, "_retrieve_template_rules"),
            patch.object(agent, "_run_web_research"),
            patch.object(agent, "_generate_outline"),
        ):
            mock_c.return_value = False
            agent.session_service.get_session = AsyncMock(return_value=None)
            parser = MagicMock()
            parser.parse = AsyncMock(return_value={"template": "IEEE"})
            parser.last_turn = None
            mock_tp_cls.return_value = parser
            await agent.run("s1", "prompt")
    @pytest.mark.asyncio
    async def test_web_research_optional(self, agent):
        with (
            patch("app.pipeline.generation.agent.TaskParser") as mock_tp_cls,
            patch.object(agent, "_update_status"),
            patch.object(agent, "_is_canceled") as mock_c,
            patch.object(agent, "_retrieve_template_rules"),
            patch.object(agent, "_run_web_research") as mock_rwr,
            patch.object(agent, "_generate_outline"),
        ):
            mock_c.return_value = False
            agent.session_service.get_session = AsyncMock(return_value={"config_json": {}})
            parser = MagicMock()
            parser.parse = AsyncMock(return_value={"template": "IEEE", "web_research": True})
            parser.last_turn = None
            mock_tp_cls.return_value = parser
            await agent.run("s1", "write paper with research")
            mock_rwr.assert_called_once()


class TestResume:
    @pytest.mark.asyncio
    async def test_session_not_found(self, agent):
        agent.session_service.get_session = AsyncMock(return_value=None)
        await agent.resume("s1")
    @pytest.mark.asyncio
    async def test_full_resume(self, agent):
        with (
            patch.object(agent, "_update_status"),
            patch.object(agent, "_is_canceled") as mock_c,
            patch.object(agent, "_generate_section") as mock_gs,
            patch.object(agent, "_emit_sse"),
            patch("app.pipeline.generation.agent.get_section_prompt") as mock_gsp,
        ):
            mock_c.return_value = False
            mock_gs.return_value = "section text"
            mock_gsp.return_value = "prompt text"
            agent.citations.assemble = AsyncMock(return_value=({"Intro": "section"}, "refs\nline2"))
            agent.quality_scorer.score.return_value = {"overall_score": 95}
            agent.session_service.get_session = AsyncMock(return_value={
                "config_json": {"template": "IEEE", "sections": ["Intro"]},
                "outline_json": {"sections": [{"title": "Intro"}]},
                "progress": 40,
            })
            agent.session_service.update_session = AsyncMock()
            agent.session_service.save_document_version = AsyncMock()
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
            patch("app.pipeline.generation.agent.get_section_prompt"),
        ):
            mock_rtr.return_value = [{"rule": "x"}]
            agent.citations.assemble = AsyncMock(return_value=({"Intro": "text"}, ""))
            agent.quality_scorer.score.return_value = {"overall_score": 85}
            agent.session_service.get_session = AsyncMock(return_value={
                "config_json": {}, "outline_json": {}, "progress": 40,
            })
            agent.session_service.update_session = AsyncMock()
            agent.session_service.save_document_version = AsyncMock()
            await agent.resume("s1")
            mock_rtr.assert_called_once()
    @pytest.mark.asyncio
    async def test_skips_references_section(self, agent):
        with (
            patch.object(agent, "_update_status"),
            patch.object(agent, "_is_canceled") as mock_c,
            patch.object(agent, "_generate_section") as mock_gs,
            patch.object(agent, "_emit_sse"),
            patch("app.pipeline.generation.agent.get_section_prompt") as mock_gsp,
        ):
            mock_c.return_value = False
            mock_gs.return_value = "text"
            mock_gsp.return_value = "prompt"
            agent.citations.assemble = AsyncMock(return_value=({}, ""))
            agent.quality_scorer.score.return_value = {"overall_score": 90}
            agent.session_service.get_session = AsyncMock(return_value={
                "config_json": {"template": "IEEE"},
                "outline_json": {"sections": [{"title": "References"}, {"title": "Intro"}]},
                "progress": 40,
            })
            agent.session_service.update_session = AsyncMock()
            agent.session_service.save_document_version = AsyncMock()
            await agent.resume("s1")
            mock_gs.assert_called_once()
            assert mock_gs.call_args[0][1] == "Intro"


class TestRewriteSection:
    @pytest.mark.asyncio
    async def test_session_not_found(self, agent):
        agent.session_service.get_session = AsyncMock(return_value=None)
        await agent.rewrite_section("s1", "Intro", "improve")
    @pytest.mark.asyncio
    async def test_full_rewrite(self, agent):
        with (
            patch.object(agent, "_llm_text") as mock_t,
            patch.object(agent, "_stream_chunks"),
            patch.object(agent, "_emit_sse"),
        ):
            mock_t.return_value = "Rewritten"
            agent.session_service.get_session = AsyncMock(return_value={
                "config_json": {}, "outline_json": {}, "progress": 90, "status": "completed",
            })
            agent.session_service.get_latest_document = AsyncMock(return_value={
                "content_json": {"outline": {}, "sections": {"Intro": "old"}},
            })
            agent.session_service.get_messages = AsyncMock(return_value=[{"role": "user", "content": "write"}])
            agent.session_service.update_session = AsyncMock()
            agent.session_service.save_document_version = AsyncMock()
            agent.citations.assemble = AsyncMock(return_value=({"Intro": "Rewritten"}, "refs"))
            agent.quality_scorer.score.return_value = {"overall_score": 90}
            await agent.rewrite_section("s1", "Intro", "expand")
    @pytest.mark.asyncio
    async def test_with_sanitized_history(self, agent):
        with (
            patch.object(agent, "_llm_text") as mock_t,
            patch.object(agent, "_stream_chunks"),
            patch.object(agent, "_emit_sse"),
            patch("app.pipeline.generation.agent.sanitize_for_llm") as mock_san,
        ):
            mock_t.return_value = "Rewritten"
            mock_san.return_value = "sanitized"
            agent.session_service.get_session = AsyncMock(return_value={
                "config_json": {"citation_style": "apa"}, "outline_json": {},
                "progress": 90, "status": "completed",
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
