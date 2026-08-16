# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_session(**overrides) -> dict:
    base = {
        "id": "session-1",
        "user_id": "user-1",
        "status": "processing",
        "progress": 5,
        "config_json": {},
        "outline_json": {},
    }
    base.update(overrides)
    return base


@pytest.fixture
def agent():
    with (
        patch("app.pipeline.generation.agent.RedisPubSub") as mock_ps,
        patch("app.pipeline.generation.agent.get_rag_engine") as mock_rag,
        patch("app.pipeline.generation.agent.CitationAssemblyService") as mock_cite,
        patch("app.pipeline.generation.agent.QualityScorer") as mock_qs,
    ):
        mock_ps.return_value = MagicMock()
        mock_rag.return_value = MagicMock()
        mock_cite.return_value = MagicMock()
        mock_qs.return_value = MagicMock()
        from app.pipeline.generation.agent import AgentPipeline

        yield AgentPipeline(MagicMock(), MagicMock())


@pytest.fixture
def session_service():
    ss = MagicMock()
    ss.get_session = AsyncMock()
    ss.update_session = AsyncMock()
    ss.add_message = AsyncMock()
    ss.save_document_version = AsyncMock()
    ss.get_latest_document = AsyncMock()
    ss.get_messages = AsyncMock()
    return ss


@pytest.fixture
def pubsub():
    ps = MagicMock()
    ps.publish = AsyncMock()
    return ps


@pytest.fixture
def full_agent(session_service, pubsub):
    with (
        patch("app.pipeline.generation.agent.get_rag_engine") as mock_rag,
        patch("app.pipeline.generation.agent.CitationAssemblyService") as mock_cite,
        patch("app.pipeline.generation.agent.QualityScorer") as mock_qs,
    ):
        mock_rag.return_value = MagicMock()
        mock_cite.return_value = MagicMock()
        mock_qs.return_value = MagicMock()
        from app.pipeline.generation.agent import AgentPipeline

        yield AgentPipeline(session_service, MagicMock(), pubsub=pubsub)


# ══════════════════════════════════════════════════════════════════════════════
# AgentPipeline — core public methods
# ══════════════════════════════════════════════════════════════════════════════


class TestAgentPipelineRun:
    @pytest.mark.asyncio
    async def test_run_happy_path(self, full_agent):
        full_agent.session_service.get_session.return_value = _make_session()
        full_agent.pubsub.publish.return_value = None
        mock_outline = AsyncMock(return_value={"title": "Paper", "sections": []})
        mock_rules = MagicMock(return_value=[])
        mock_web = AsyncMock(return_value=[])
        mock_cancel = AsyncMock(return_value=False)
        mock_parse = AsyncMock(return_value={"title": "Paper", "sections": ["Intro"]})
        full_agent._generate_outline = mock_outline
        full_agent._retrieve_template_rules = mock_rules
        full_agent._run_web_research = mock_web
        full_agent._is_canceled = mock_cancel
        from app.pipeline.generation.task_parser import TaskParser

        with patch.object(TaskParser, "parse", mock_parse):
            await full_agent.run("session-1", "write a paper")
        full_agent.session_service.get_session.assert_awaited_once_with("session-1")
        assert full_agent.session_service.update_session.await_count >= 2

    @pytest.mark.asyncio
    async def test_run_canceled_after_task_parse(self, full_agent):
        full_agent.session_service.get_session.return_value = _make_session()
        mock_cancel = AsyncMock(return_value=True)
        mock_parse = AsyncMock(return_value={"title": "Paper", "sections": []})
        full_agent._is_canceled = mock_cancel
        from app.pipeline.generation.task_parser import TaskParser

        with patch.object(TaskParser, "parse", mock_parse):
            await full_agent.run("session-1", "write a paper")
        full_agent.session_service.update_session.assert_awaited()

    @pytest.mark.asyncio
    async def test_run_with_web_research(self, full_agent):
        full_agent.session_service.get_session.return_value = _make_session(config_json={"web_research": True})
        mock_web = AsyncMock(return_value=["result"])
        mock_outline = AsyncMock(return_value={"title": "Paper", "sections": []})
        mock_rules = MagicMock(return_value=[])
        mock_cancel = AsyncMock(return_value=False)
        mock_parse = AsyncMock(return_value={"title": "Paper", "sections": []})
        full_agent._generate_outline = mock_outline
        full_agent._retrieve_template_rules = mock_rules
        full_agent._run_web_research = mock_web
        full_agent._is_canceled = mock_cancel
        from app.pipeline.generation.task_parser import TaskParser

        with patch.object(TaskParser, "parse", mock_parse):
            await full_agent.run("session-1", "write a paper")
        mock_web.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_without_session(self, full_agent):
        full_agent.session_service.get_session.return_value = None
        mock_cancel = AsyncMock(return_value=False)
        mock_rules = MagicMock(return_value=[])
        mock_web = AsyncMock(return_value=[])
        mock_outline = AsyncMock(return_value={"title": "Paper", "sections": []})
        mock_parse = AsyncMock(return_value={"title": "Paper", "sections": []})
        full_agent._is_canceled = mock_cancel
        full_agent._retrieve_template_rules = mock_rules
        full_agent._run_web_research = mock_web
        full_agent._generate_outline = mock_outline
        from app.pipeline.generation.task_parser import TaskParser

        with patch.object(TaskParser, "parse", mock_parse):
            await full_agent.run("session-1", "write a paper")
        full_agent.session_service.update_session.assert_awaited()

    @pytest.mark.asyncio
    async def test_run_canceled_before_outline(self, full_agent):
        full_agent.session_service.get_session.return_value = _make_session()
        call_count = [0]

        async def cancel_side_effect(sid):
            call_count[0] += 1
            return call_count[0] >= 2

        mock_cancel = AsyncMock(side_effect=cancel_side_effect)
        mock_rules = MagicMock(return_value=[])
        mock_web = AsyncMock(return_value=[])
        mock_parse = AsyncMock(return_value={"title": "Paper", "sections": []})
        full_agent._is_canceled = mock_cancel
        full_agent._retrieve_template_rules = mock_rules
        full_agent._run_web_research = mock_web
        from app.pipeline.generation.task_parser import TaskParser

        with patch.object(TaskParser, "parse", mock_parse):
            await full_agent.run("session-1", "write a paper")


class TestAgentPipelineResume:
    @pytest.mark.asyncio
    async def test_resume_happy_path(self, full_agent):
        full_agent.session_service.get_session.return_value = _make_session(
            config_json={"title": "Paper", "sections": ["Intro", "Methods"]},
            outline_json={"sections": [{"title": "Intro"}, {"title": "Methods"}]},
            user_id="user-1",
        )
        mock_gs = AsyncMock(return_value="Section text")
        mock_render = AsyncMock(return_value="/out/docx")
        mock_boost = AsyncMock(return_value=({}, [], "/out/docx", {}))
        mock_cancel = AsyncMock(return_value=False)
        full_agent._generate_section = mock_gs
        full_agent._render_document = mock_render
        full_agent._boost_quality = mock_boost
        full_agent._is_canceled = mock_cancel
        full_agent.citations.assemble = AsyncMock(return_value=({}, ""))
        full_agent.quality_scorer.score.return_value = {"overall_score": 90.0}
        await full_agent.resume("session-1")
        assert full_agent.session_service.update_session.await_count >= 2

    @pytest.mark.asyncio
    async def test_resume_no_session(self, full_agent):
        full_agent.session_service.get_session.return_value = None
        await full_agent.resume("session-1")
        full_agent.session_service.update_session.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_resume_skips_references_section(self, full_agent):
        full_agent.session_service.get_session.return_value = _make_session(
            config_json={"title": "Paper", "sections": ["Intro", "References"]},
            outline_json={"sections": [{"title": "Intro"}, {"title": "References"}]},
            user_id="user-1",
        )
        mock_gs = AsyncMock(return_value="Intro text")
        mock_render = AsyncMock(return_value="/out/docx")
        mock_boost = AsyncMock(return_value=({}, [], "/out/docx", {}))
        mock_cancel = AsyncMock(return_value=False)
        full_agent._generate_section = mock_gs
        full_agent._render_document = mock_render
        full_agent._boost_quality = mock_boost
        full_agent._is_canceled = mock_cancel
        full_agent.citations.assemble = AsyncMock(return_value=({}, ""))
        full_agent.quality_scorer.score.return_value = {"overall_score": 90.0}
        await full_agent.resume("session-1")
        mock_gs.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_resume_with_cancel(self, full_agent):
        full_agent.session_service.get_session.return_value = _make_session(
            config_json={"title": "Paper", "sections": ["Intro"]},
            outline_json={"sections": [{"title": "Intro"}]},
            user_id="user-1",
        )
        full_agent._is_canceled = AsyncMock(return_value=True)
        await full_agent.resume("session-1")

    @pytest.mark.asyncio
    async def test_resume_quality_boost_applied(self, full_agent):
        full_agent.session_service.get_session.return_value = _make_session(
            config_json={"title": "Paper", "sections": ["Intro"]},
            outline_json={"sections": [{"title": "Intro"}]},
            user_id="user-1",
        )
        mock_gs = AsyncMock(return_value="Text")
        mock_render = AsyncMock(return_value="/out/docx")
        mock_cancel = AsyncMock(return_value=False)
        mock_boost = AsyncMock(return_value=({"Intro": "Improved"}, [], "/out2.docx", {"overall_score": 80.0}))
        full_agent._generate_section = mock_gs
        full_agent._render_document = mock_render
        full_agent._is_canceled = mock_cancel
        full_agent._boost_quality = mock_boost
        full_agent.quality_target = 100.0
        full_agent.quality_scorer.score.return_value = {"overall_score": 50.0}
        full_agent.citations.assemble = AsyncMock(return_value=({}, ""))
        await full_agent.resume("session-1")
        mock_boost.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_resume_no_template_rules_reloads(self, full_agent):
        full_agent.session_service.get_session.return_value = _make_session(
            config_json={"title": "Paper", "sections": ["Intro"]},
            outline_json={"sections": [{"title": "Intro"}]},
            user_id="user-1",
        )
        mock_rtr = MagicMock(return_value=[{"rule": "test"}])
        mock_gs = AsyncMock(return_value="Text")
        mock_render = AsyncMock(return_value="/out/docx")
        mock_boost = AsyncMock(return_value=({}, [], "/out/docx", {}))
        mock_cancel = AsyncMock(return_value=False)
        full_agent._retrieve_template_rules = mock_rtr
        full_agent._generate_section = mock_gs
        full_agent._render_document = mock_render
        full_agent._boost_quality = mock_boost
        full_agent._is_canceled = mock_cancel
        full_agent.citations.assemble = AsyncMock(return_value=({}, ""))
        full_agent.quality_scorer.score.return_value = {"overall_score": 90.0}
        await full_agent.resume("session-1")
        mock_rtr.assert_called_once()


class TestAgentPipelineRewriteSection:
    @pytest.mark.asyncio
    async def test_rewrite_section_happy_path(self, full_agent):
        full_agent.session_service.get_session.return_value = _make_session(
            config_json={"citation_style": "ieee"},
            progress=90,
            user_id="user-1",
        )
        full_agent.session_service.get_latest_document = AsyncMock(
            return_value={
                "content_json": {"sections": {"Intro": "Old text"}, "outline": {"sections": []}},
            }
        )
        full_agent.session_service.get_messages = AsyncMock(
            return_value=[
                {"role": "user", "content": "write about ML"},
            ]
        )
        mock_llm = AsyncMock(return_value="New rewritten text")
        mock_render = AsyncMock(return_value="/out/docx")
        mock_stream = AsyncMock()
        full_agent._llm_text = mock_llm
        full_agent._render_document = mock_render
        full_agent._stream_chunks = mock_stream
        full_agent.citations.assemble = AsyncMock(return_value=({"Intro": "New rewritten text"}, "Ref1\nRef2"))
        full_agent.quality_scorer.score.return_value = {"overall_score": 85.0}
        await full_agent.rewrite_section("session-1", "Intro", "expand this section")
        mock_llm.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rewrite_section_no_session(self, full_agent):
        full_agent.session_service.get_session.return_value = None
        await full_agent.rewrite_section("session-1", "Intro", "expand")
        full_agent.session_service.get_latest_document.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_rewrite_section_uses_history(self, full_agent):
        full_agent.session_service.get_session.return_value = _make_session(
            config_json={},
            progress=90,
            user_id="user-1",
        )
        full_agent.session_service.get_latest_document = AsyncMock(
            return_value={
                "content_json": {"sections": {"Intro": "Old"}, "outline": {}},
            }
        )
        full_agent.session_service.get_messages = AsyncMock(
            return_value=[
                {"role": "user", "content": "topic is ML"},
            ]
        )
        mock_llm = AsyncMock(return_value="Rewritten")
        mock_render = AsyncMock(return_value="/out.docx")
        mock_stream = AsyncMock()
        full_agent._llm_text = mock_llm
        full_agent._render_document = mock_render
        full_agent._stream_chunks = mock_stream
        full_agent.citations.assemble = AsyncMock(return_value=({"Intro": "Rewritten"}, ""))
        full_agent.quality_scorer.score.return_value = {"overall_score": 85.0}
        await full_agent.rewrite_section("session-1", "Intro", "expand")
        full_agent.session_service.get_messages.assert_awaited_once_with("session-1", limit=20)


class TestAgentPipelineIsCanceled:
    @pytest.mark.asyncio
    async def test_not_canceled(self, full_agent):
        full_agent.session_service.get_session.return_value = _make_session(status="processing")
        result = await full_agent._is_canceled("session-1")
        assert result is False

    @pytest.mark.asyncio
    async def test_canceled(self, full_agent):
        full_agent.session_service.get_session.return_value = _make_session(status="canceled")
        result = await full_agent._is_canceled("session-1")
        assert result is True

    @pytest.mark.asyncio
    async def test_stopping(self, full_agent):
        full_agent.session_service.get_session.return_value = _make_session(status="stopping")
        result = await full_agent._is_canceled("session-1")
        assert result is True

    @pytest.mark.asyncio
    async def test_exception_returns_false(self, full_agent):
        full_agent.session_service.get_session = AsyncMock(side_effect=Exception("DB error"))
        result = await full_agent._is_canceled("session-1")
        assert result is False


class TestAgentPipelineUpdateStatus:
    @pytest.mark.asyncio
    async def test_update_status_basic(self, full_agent):
        full_agent.session_service.update_session = AsyncMock()
        full_agent.pubsub.publish = AsyncMock()
        await full_agent._update_status(
            "session-1", status="processing", progress=50, message="Working", config={"key": "val"}, stage="writing"
        )
        full_agent.session_service.update_session.assert_awaited_once()
        full_agent.pubsub.publish.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_status_clamps_progress(self, full_agent):
        full_agent.session_service.update_session = AsyncMock()
        full_agent.pubsub.publish = AsyncMock()
        await full_agent._update_status("session-1", status="done", progress=150, message="Done", config={})
        call_args = full_agent.session_service.update_session.await_args
        assert call_args[1]["progress"] == 100

    @pytest.mark.asyncio
    async def test_update_status_negative_clamped(self, full_agent):
        full_agent.session_service.update_session = AsyncMock()
        full_agent.pubsub.publish = AsyncMock()
        await full_agent._update_status("session-1", status="pending", progress=-10, message="Start", config={})
        call_args = full_agent.session_service.update_session.await_args
        assert call_args[1]["progress"] == 0

    @pytest.mark.asyncio
    async def test_update_status_with_outline(self, full_agent):
        full_agent.session_service.update_session = AsyncMock()
        full_agent.pubsub.publish = AsyncMock()
        await full_agent._update_status(
            "session-1",
            status="processing",
            progress=40,
            message="Outline ready",
            config={},
            stage="outline",
            outline={"sections": []},
        )
        call_args = full_agent.session_service.update_session.await_args
        assert "outline_json" in call_args[1]


class TestAgentPipelineEmitSse:
    @pytest.mark.asyncio
    async def test_emit_sse_basic(self, full_agent):
        full_agent.pubsub.publish = AsyncMock(return_value=None)
        await full_agent._emit_sse("session-1", stage="writing", progress=50, message="Working")
        full_agent.pubsub.publish.assert_awaited_once()
        channel = full_agent.pubsub.publish.await_args[0][0]
        assert channel == "session:session-1"

    @pytest.mark.asyncio
    async def test_emit_sse_with_extra(self, full_agent):
        full_agent.pubsub.publish = AsyncMock()
        await full_agent._emit_sse("session-1", stage="done", progress=100, message="Done", extra={"section": "Intro"})
        full_agent.pubsub.publish.assert_awaited_once()


class TestAgentPipelineStreamChunks:
    @pytest.mark.asyncio
    async def test_stream_chunks_empty_skipped(self, full_agent):
        full_agent.pubsub.publish = AsyncMock()
        await full_agent._stream_chunks("session-1", event_type="writing_chunk", stage="writing", progress=50, text="")
        full_agent.pubsub.publish.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_stream_chunks_small_text(self, full_agent):
        full_agent.pubsub.publish = AsyncMock()
        await full_agent._stream_chunks(
            "session-1", event_type="writing_chunk", stage="writing", progress=50, text="Hello", chunk_size=400
        )
        full_agent.pubsub.publish.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stream_chunks_large_text(self, full_agent):
        full_agent.pubsub.publish = AsyncMock()
        long_text = "Hello " * 200
        await full_agent._stream_chunks(
            "session-1", event_type="writing_chunk", stage="writing", progress=50, text=long_text, chunk_size=100
        )
        assert full_agent.pubsub.publish.await_count >= 2

    @pytest.mark.asyncio
    async def test_stream_chunks_with_extra(self, full_agent):
        full_agent.pubsub.publish = AsyncMock()
        await full_agent._stream_chunks(
            "session-1",
            event_type="writing_chunk",
            stage="writing",
            progress=50,
            text="Test",
            extra={"section": "Intro"},
        )
        call_args = full_agent.pubsub.publish.await_args
        assert call_args is not None


class TestAgentPipelinePersistLlmTurn:
    @pytest.mark.asyncio
    async def test_persist_llm_turn(self, full_agent):
        full_agent.session_service.add_message = AsyncMock()
        await full_agent._persist_llm_turn("session-1", "system prompt", "user msg", "assistant msg")
        assert full_agent.session_service.add_message.await_count == 3


class TestAgentPipelineGenerateSection:
    @pytest.mark.asyncio
    async def test_generate_section(self, full_agent):
        mock_llm = AsyncMock(return_value="Section content")
        mock_stream = AsyncMock()
        full_agent._llm_text = mock_llm
        full_agent._stream_chunks = mock_stream
        result = await full_agent._generate_section("session-1", "Introduction", "Write intro", user_id="user-1")
        assert result == "Section content"
        mock_stream.assert_awaited_once()


class TestAgentPipelineGenerateOutline:
    @pytest.mark.asyncio
    async def test_generate_outline_success(self, full_agent):
        mock_llm = AsyncMock(
            return_value={"title": "Paper", "sections": [{"number": 1, "title": "Intro", "key_points": []}]}
        )
        mock_stream = AsyncMock()
        full_agent._llm_json = mock_llm
        full_agent._stream_chunks = mock_stream
        result = await full_agent._generate_outline("session-1", {"title": "Paper", "sections": ["Intro"]}, [], [])
        assert result["title"] == "Paper"

    @pytest.mark.asyncio
    async def test_generate_outline_fallback(self, full_agent):
        mock_llm = AsyncMock(return_value=None)
        mock_stream = AsyncMock()
        full_agent._llm_json = mock_llm
        full_agent._stream_chunks = mock_stream
        result = await full_agent._generate_outline("session-1", {"title": "Paper", "sections": ["Intro"]}, [], [])
        assert result["title"] == "Paper"


class TestAgentPipelineLlmText:
    @pytest.mark.asyncio
    async def test_llm_text_success(self, full_agent):
        with patch("app.pipeline.generation.agent.generate_with_fallback") as mock_gwf:
            mock_gwf.return_value = {"text": "  Generated text  "}
            full_agent.session_service.add_message = AsyncMock()
            result = await full_agent._llm_text("session-1", "system", "user msg", max_tokens=1200, user_id="user-1")
        assert result == "Generated text"
        assert full_agent.session_service.add_message.await_count == 3

    @pytest.mark.asyncio
    async def test_llm_text_empty(self, full_agent):
        with patch("app.pipeline.generation.agent.generate_with_fallback") as mock_gwf:
            mock_gwf.return_value = {"text": ""}
            full_agent.session_service.add_message = AsyncMock()
            result = await full_agent._llm_text("session-1", "system", "user msg")
        assert result == ""


class TestAgentPipelineLlmJson:
    @pytest.mark.asyncio
    async def test_llm_json_valid(self, full_agent):
        mock_text = AsyncMock(return_value='{"key": "value"}')
        full_agent._llm_text = mock_text
        result = await full_agent._llm_json("session-1", "system", "user msg")
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_llm_json_empty(self, full_agent):
        mock_text = AsyncMock(return_value="")
        full_agent._llm_text = mock_text
        result = await full_agent._llm_json("session-1", "system", "user msg")
        assert result is None

    @pytest.mark.asyncio
    async def test_llm_json_no_extract(self, full_agent):
        mock_text = AsyncMock(return_value="no json here")
        full_agent._llm_text = mock_text
        result = await full_agent._llm_json("session-1", "system", "user msg")
        assert result is None

    @pytest.mark.asyncio
    async def test_llm_json_decode_error(self, full_agent):
        mock_text = AsyncMock(return_value='{"key"}')
        full_agent._llm_text = mock_text
        result = await full_agent._llm_json("session-1", "system", "user msg")
        assert result is None


class TestAgentPipelineRetrieveTemplateRules:
    def test_retrieve_template_rules(self, agent):
        agent.rag_engine = MagicMock()
        agent.rag_engine.query_rules.side_effect = lambda t, s, top_k=2: [{"template": t, "section": s}]
        result = agent._retrieve_template_rules("IEEE", ["Intro", "Methods"])
        assert len(result) >= 2

    def test_retrieve_template_rules_fallback(self, agent):
        agent.rag_engine = MagicMock()
        agent.rag_engine.query_rules.side_effect = lambda t, s, top_k=2: []
        result = agent._retrieve_template_rules("IEEE", ["Intro"])
        agent.rag_engine.query_rules.assert_any_call("IEEE", "Intro", top_k=2)
        agent.rag_engine.query_rules.assert_any_call("IEEE", "general", top_k=2)
        assert result == []

    def test_retrieve_template_rules_empty_sections(self, agent):
        agent.rag_engine = MagicMock()
        agent.rag_engine.query_rules.side_effect = lambda t, s, top_k=2: [{"rule": s}]
        result = agent._retrieve_template_rules("IEEE", [])
        agent.rag_engine.query_rules.assert_called_once_with("IEEE", "general", top_k=2)
        assert result == [{"rule": "general"}]


class TestAgentPipelineRunWebResearch:
    @pytest.mark.asyncio
    async def test_web_research_success(self, agent):
        mock_tool = MagicMock()
        mock_tool.invoke.return_value = "results"
        with (
            patch("app.pipeline.generation.agent.asyncio.to_thread", new=AsyncMock(return_value="results")),
            patch("langchain_community.tools.DuckDuckGoSearchResults", return_value=mock_tool),
        ):
            result = await agent._run_web_research({"title": "AI", "keywords": ["ML"]})
            assert result == "results"

    @pytest.mark.asyncio
    async def test_web_research_fallback_to_run(self, agent):
        mock_tool = MagicMock()
        mock_tool.invoke = MagicMock(side_effect=AttributeError("no invoke"))
        mock_tool.run = MagicMock(return_value="fallback")
        with (
            patch("app.pipeline.generation.agent.asyncio.to_thread", new=AsyncMock(return_value="fallback")),
            patch("langchain_community.tools.DuckDuckGoSearchResults", return_value=mock_tool),
        ):
            result = await agent._run_web_research({"title": "AI", "keywords": ["ML"]})
            assert result == "fallback"

    @pytest.mark.asyncio
    async def test_web_research_no_query(self, agent):
        mock_tool = MagicMock()
        mock_tool.invoke.return_value = "results"
        with (
            patch("app.pipeline.generation.agent.asyncio.to_thread", new=AsyncMock(return_value="results")),
            patch("langchain_community.tools.DuckDuckGoSearchResults", return_value=mock_tool),
        ):
            result = await agent._run_web_research({})
            assert result == "results"

    @pytest.mark.asyncio
    async def test_web_research_import_fail(self, agent):
        with patch("app.pipeline.generation.agent.logger"):
            result = await agent._run_web_research({"title": "AI"})
        assert result == []

    @pytest.mark.asyncio
    async def test_web_research_exception(self, agent):
        mock_tool = MagicMock()
        mock_tool.invoke = MagicMock(side_effect=Exception("tool error"))
        with (
            patch(
                "app.pipeline.generation.agent.asyncio.to_thread", new=AsyncMock(side_effect=Exception("tool error"))
            ),
            patch("langchain_community.tools.DuckDuckGoSearchResults", return_value=mock_tool),
        ):
            result = await agent._run_web_research({"title": "AI"})
            assert result == []


class TestAgentPipelineRenderDocument:
    @pytest.mark.asyncio
    async def test_render_document(self, agent):
        agent.pipeline_orchestrator._export_document = MagicMock(return_value="/out/docx")
        with patch("app.pipeline.generation.agent.Formatter") as MockFmt:
            fmt = MagicMock()
            fmt.process.return_value = MagicMock()
            MockFmt.return_value = fmt
            result = await agent._render_document(
                session_id="session-1",
                task_spec={"template": "IEEE", "keywords": ["ML"]},
                outline={"title": "Paper"},
                sections={"Intro": "Hello world."},
                references=["[1] Ref here"],
            )
        assert result == "/out/docx"

    @pytest.mark.asyncio
    async def test_render_document_no_references(self, agent):
        agent.pipeline_orchestrator._export_document = MagicMock(return_value="/out/docx")
        with patch("app.pipeline.generation.agent.Formatter") as MockFmt:
            fmt = MagicMock()
            fmt.process.return_value = MagicMock()
            MockFmt.return_value = fmt
            result = await agent._render_document(
                session_id="session-1",
                task_spec={"template": "APA", "keywords": []},
                outline={"title": "Paper"},
                sections={"Intro": "Text."},
                references=[],
            )
        assert result == "/out/docx"


class TestAgentPipelineBoostQuality:
    @pytest.mark.asyncio
    async def test_boost_quality_no_low_sections(self, full_agent):
        full_agent._select_low_sections = MagicMock(return_value=[])
        result = await full_agent._boost_quality(
            session_id="s1",
            task_spec={},
            template_rules=[],
            outline={},
            sections_map={"Intro": "long " * 100},
            references=[],
            config={},
            user_id=None,
        )
        assert result[0] == {"Intro": "long " * 100}

    @pytest.mark.asyncio
    async def test_boost_quality_improves_low_sections(self, full_agent):
        full_agent._select_low_sections = MagicMock(return_value=["Intro"])
        full_agent._min_words_for_length = MagicMock(return_value=120)
        full_agent.session_service.update_session = AsyncMock()
        full_agent.pubsub.publish = AsyncMock()
        mock_llm = AsyncMock(return_value="Improved section text")
        mock_stream = AsyncMock()
        mock_render = AsyncMock(return_value="/out/docx")
        mock_cancel = AsyncMock(return_value=False)
        full_agent._llm_text = mock_llm
        full_agent._stream_chunks = mock_stream
        full_agent._render_document = mock_render
        full_agent._is_canceled = mock_cancel
        full_agent.citations.assemble = AsyncMock(return_value=({"Intro": "Improved section text"}, "Ref"))
        full_agent.quality_scorer.score.return_value = {"overall_score": 95.0}
        result = await full_agent._boost_quality(
            session_id="s1",
            task_spec={},
            template_rules=[],
            outline={},
            sections_map={"Intro": "short"},
            references=[],
            config={},
            user_id=None,
        )
        assert "Improved section text" in result[0]["Intro"]

    @pytest.mark.asyncio
    async def test_boost_quality_applies_floor_when_still_low(self, full_agent):
        full_agent._select_low_sections = MagicMock(return_value=["Intro"])
        full_agent._min_words_for_length = MagicMock(return_value=120)
        full_agent.session_service.update_session = AsyncMock()
        full_agent.pubsub.publish = AsyncMock()
        mock_llm = AsyncMock(return_value="Short")
        mock_stream = AsyncMock()
        mock_render = AsyncMock(return_value="/out/docx")
        mock_cancel = AsyncMock(return_value=False)
        mock_floor = MagicMock(return_value={"Intro": "Short " + "filler " * 30 + " [1]"})
        full_agent._llm_text = mock_llm
        full_agent._apply_quality_floor = mock_floor
        full_agent._stream_chunks = mock_stream
        full_agent._render_document = mock_render
        full_agent._is_canceled = mock_cancel
        full_agent.citations.assemble = AsyncMock(return_value=({"Intro": "text"}, ""))
        full_agent.quality_scorer.score.return_value = {"overall_score": 40.0}
        await full_agent._boost_quality(
            session_id="s1",
            task_spec={},
            template_rules=[],
            outline={},
            sections_map={"Intro": "short"},
            references=[],
            config={},
            user_id=None,
        )
        mock_floor.assert_called_once()

    @pytest.mark.asyncio
    async def test_boost_quality_canceled(self, full_agent):
        full_agent._select_low_sections = MagicMock(return_value=["Intro"])
        full_agent.session_service.update_session = AsyncMock()
        full_agent._is_canceled = AsyncMock(return_value=True)
        await full_agent._boost_quality(
            session_id="s1",
            task_spec={},
            template_rules=[],
            outline={},
            sections_map={"Intro": "short"},
            references=[],
            config={},
            user_id=None,
        )


class TestAgentPipelineSelectLowSections:
    def test_select_low_sections_below_threshold(self, agent):
        sm = {"Intro": "short", "Methods": "a " * 100, "References": "refs"}
        result = agent._select_low_sections(sm, 50, limit=2)
        assert "Intro" in result
        assert "References" not in result

    def test_select_low_sections_empty_map(self, agent):
        assert agent._select_low_sections({}, 100) == []

    def test_select_low_sections_returns_lowest_when_all_above(self, agent):
        sm = {"Intro": "a " * 50, "Methods": "b " * 100, "Refs": "c " * 75}
        result = agent._select_low_sections(sm, 30, limit=2)
        assert len(result) == 2

    def test_select_low_sections_skips_references(self, agent):
        sm = {"Intro": "a", "References": "b " * 200, "Bibliography": "c " * 200}
        result = agent._select_low_sections(sm, 100, limit=3)
        assert "References" not in result
        assert "Bibliography" not in result


class TestAgentPipelineApplyQualityFloor:
    def test_apply_quality_floor_min_words(self, agent):
        sm = {"Intro": "short text"}
        required = ["Intro"]
        result = agent._apply_quality_floor(sm, required, min_words=20)
        assert agent._count_words(result["Intro"]) >= 20
        assert "[1]" in result["Intro"]

    def test_apply_quality_floor_skips_references(self, agent):
        sm = {"References": "already long enough text here"}
        result = agent._apply_quality_floor(sm, ["References"], min_words=200)
        assert result["References"] == "already long enough text here"

    def test_apply_quality_floor_adds_citation_when_missing(self, agent):
        sm = {"Intro": "a " * 50}
        result = agent._apply_quality_floor(sm, ["Intro"], min_words=50)
        assert "[1]" in result["Intro"]

    def test_apply_quality_floor_keeps_existing_citation(self, agent):
        sm = {"Intro": "a " * 50 + " [2]"}
        result = agent._apply_quality_floor(sm, ["Intro"], min_words=50)
        assert "[2]" in result["Intro"]


class TestAgentPipelineHasCitation:
    def test_has_citation_numeric(self):
        from app.pipeline.generation.agent import AgentPipeline

        assert AgentPipeline._has_citation("see [1]") is True
        assert AgentPipeline._has_citation("see [1,2,3]") is True
        assert AgentPipeline._has_citation("no cite") is False

    def test_has_citation_parenthetical_author_year(self):
        from app.pipeline.generation.agent import AgentPipeline

        assert AgentPipeline._has_citation("(Smith, 2020)") is True
        assert AgentPipeline._has_citation("(Doe et al., 2019)") is True

    def test_has_citation_bracket_author_year(self):
        from app.pipeline.generation.agent import AgentPipeline

        assert AgentPipeline._has_citation("[Smith, 2020]") is True

    def test_has_citation_none(self):
        from app.pipeline.generation.agent import AgentPipeline

        assert AgentPipeline._has_citation(None) is False


class TestAgentPipelineCountWords:
    def test_count_words(self):
        from app.pipeline.generation.agent import AgentPipeline

        assert AgentPipeline._count_words("one two three") == 3
        assert AgentPipeline._count_words("") == 0
        assert AgentPipeline._count_words(None) == 0
        assert AgentPipeline._count_words("  spaced  ") == 1


class TestAgentPipelineMinWordsForLength:
    def test_min_words_for_length(self, agent):
        assert agent._min_words_for_length("short") == 120
        assert agent._min_words_for_length("long") == 240
        assert agent._min_words_for_length("medium") == 180
        assert agent._min_words_for_length("unknown") == 180


class TestAgentPipelineEnsureOutlineNumbers:
    def test_ensure_outline_numbers(self):
        from app.pipeline.generation.agent import AgentPipeline

        ol = {"sections": [{"title": "Intro"}, {"title": "Body"}]}
        result = AgentPipeline._ensure_outline_numbers(ol)
        assert result["sections"][0]["number"] == 1
        assert result["sections"][1]["number"] == 2

    def test_ensure_outline_numbers_non_list(self):
        from app.pipeline.generation.agent import AgentPipeline

        ol = {"sections": "not list"}
        result = AgentPipeline._ensure_outline_numbers(ol)
        assert result is ol

    def test_ensure_outline_numbers_string_items(self):
        from app.pipeline.generation.agent import AgentPipeline

        ol = {"sections": ["Intro", "Body"]}
        result = AgentPipeline._ensure_outline_numbers(ol)
        assert result["sections"][0]["title"] == "Intro"
        assert result["sections"][0]["number"] == 1

    def test_ensure_outline_numbers_section_fallback(self):
        from app.pipeline.generation.agent import AgentPipeline

        ol = {"sections": [{"section": "Intro"}]}
        result = AgentPipeline._ensure_outline_numbers(ol)
        assert result["sections"][0]["title"] == "Intro"
        assert result["sections"][0]["number"] == 1


class TestAgentPipelineExtractOutlineSections:
    def test_extract_outline_sections_dict(self):
        from app.pipeline.generation.agent import AgentPipeline

        result = AgentPipeline._extract_outline_sections({"sections": [{"title": "Intro"}, {"title": "Body"}]})
        assert len(result) == 2
        assert result[0]["title"] == "Intro"

    def test_extract_outline_sections_list(self):
        from app.pipeline.generation.agent import AgentPipeline

        result = AgentPipeline._extract_outline_sections(["Intro", "Body"])
        assert result[0]["title"] == "Intro"

    def test_extract_outline_sections_empty(self):
        from app.pipeline.generation.agent import AgentPipeline

        assert AgentPipeline._extract_outline_sections("invalid") == []

    def test_extract_outline_sections_none(self):
        from app.pipeline.generation.agent import AgentPipeline

        assert AgentPipeline._extract_outline_sections(None) == []


class TestAgentPipelineNormalizeSections:
    def test_normalize_sections_dict(self):
        from app.pipeline.generation.agent import AgentPipeline

        result = AgentPipeline._normalize_sections({"Intro": "text"})
        assert result == {"Intro": "text"}

    def test_normalize_sections_list(self):
        from app.pipeline.generation.agent import AgentPipeline

        result = AgentPipeline._normalize_sections([{"title": "Intro", "content": "text"}])
        assert result == {"Intro": "text"}

    def test_normalize_sections_empty(self):
        from app.pipeline.generation.agent import AgentPipeline

        assert AgentPipeline._normalize_sections("bad") == {}

    def test_normalize_sections_none(self):
        from app.pipeline.generation.agent import AgentPipeline

        assert AgentPipeline._normalize_sections(None) == {}


class TestAgentPipelineExtractJson:
    def test_extract_json_none(self):
        from app.pipeline.generation.agent import AgentPipeline

        assert AgentPipeline._extract_json(None) is None

    def test_extract_json_code_fence(self):
        from app.pipeline.generation.agent import AgentPipeline

        result = AgentPipeline._extract_json('```json\n{"a": 1}\n```')
        assert result == '{"a": 1}'

    def test_extract_json_plain(self):
        from app.pipeline.generation.agent import AgentPipeline

        assert AgentPipeline._extract_json('{"a": 1}') == '{"a": 1}'

    def test_extract_json_no_braces(self):
        from app.pipeline.generation.agent import AgentPipeline

        assert AgentPipeline._extract_json("plain text") is None

    def test_extract_json_unmatched(self):
        from app.pipeline.generation.agent import AgentPipeline

        assert AgentPipeline._extract_json('{"a":') is None


# ══════════════════════════════════════════════════════════════════════════════
# DocumentGenerator — remaining gaps
# ══════════════════════════════════════════════════════════════════════════════


class TestDocumentGeneratorComputeSha256:
    def test_compute_sha256_integration(self, tmp_path):
        from app.pipeline.generation.document_generator import DocumentGenerator

        f = tmp_path / "test.bin"
        f.write_bytes(b"hello world" * 1000)
        digest = DocumentGenerator._compute_sha256(f)
        assert isinstance(digest, str)
        assert len(digest) == 64

    def test_compute_sha256_different_content(self, tmp_path):
        from app.pipeline.generation.document_generator import DocumentGenerator

        a = tmp_path / "a.bin"
        b = tmp_path / "b.bin"
        a.write_text("hello")
        b.write_text("world")
        assert DocumentGenerator._compute_sha256(a) != DocumentGenerator._compute_sha256(b)


class TestDocumentGeneratorNormalizeStatus:
    def test_normalize_status_all(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        assert DocumentGenerator._normalize_status("PENDING") == "pending"
        assert DocumentGenerator._normalize_status("PROCESSING") == "processing"
        assert DocumentGenerator._normalize_status("COMPLETED") == "done"
        assert DocumentGenerator._normalize_status("COMPLETED_WITH_WARNINGS") == "done"
        assert DocumentGenerator._normalize_status("FAILED") == "failed"
        assert DocumentGenerator._normalize_status("CANCELLED") == "failed"
        assert DocumentGenerator._normalize_status("unknown") == "processing"
        assert DocumentGenerator._normalize_status(None) == "processing"


class TestDocumentGeneratorSessionRecordToStatus:
    def test_session_record_to_status_empty_config(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        dg = DocumentGenerator()
        session = {"id": "j1"}
        result = dg._session_record_to_status(session)
        assert result["job_id"] == "j1"
        assert result["stage"] == "queued"


class TestDocumentGeneratorStartJobErrors:
    @pytest.mark.asyncio
    async def test_start_job_supabase_none(self):
        with (
            patch("app.pipeline.generation.document_generator.DocumentService") as MockDS,
            patch("app.pipeline.generation.document_generator.get_supabase_client", return_value=None),
            patch("app.pipeline.generation.document_generator.emit_event"),
        ):
            MockDS.create_document.return_value = None
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            job_id = await dg.start_job("paper", "ieee", {}, {}, "u1")
            assert job_id in dg._volatile_sessions


class TestDocumentGeneratorGetDownloadPath:
    def test_get_download_path_not_done(self):
        with (
            patch("app.pipeline.generation.document_generator.get_supabase_client", return_value=None),
            patch("app.pipeline.generation.document_generator.DocumentService") as MockDS,
        ):
            MockDS.get_document.return_value = None
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._volatile_sessions["j1"] = {
                "id": "j1",
                "status": "pending",
                "progress": 0,
                "config_json": {"stage": "queued", "message": ""},
            }
            assert dg.get_download_path("j1") is None


class TestDocumentGeneratorGetStatus:
    def test_get_status_without_session_fallback(self):
        with patch("app.pipeline.generation.document_generator.DocumentService") as MockDS:
            MockDS.get_document.return_value = {
                "status": "COMPLETED",
                "current_stage": "DONE",
                "progress": 100,
                "output_path": "/tmp/doc.docx",
            }
            MockDS.get_document_result.return_value = {
                "structured_data": {"outline": ["Intro"]},
            }
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            status = dg.get_status("unknown")
            assert status["status"] == "done"

    def test_get_status_raises_on_not_found(self):
        with patch("app.pipeline.generation.document_generator.DocumentService") as MockDS:
            MockDS.get_document.return_value = None
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            with pytest.raises(KeyError):
                dg.get_status("nonexistent")


class TestDocumentGeneratorLLmGenerateEdgeCases:
    @pytest.mark.asyncio
    async def test_llm_generate_nvidia_exception_deepseek_success(self):
        with patch("app.pipeline.generation.document_generator.get_supabase_client", return_value=None):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            with patch("app.services.llm_service.LLM_NVIDIA") as mock_nvidia:
                mock_nvidia.complete.side_effect = RuntimeError("NVIDIA down")
                with patch("app.services.llm_service.LLM_DEEPSEEK") as mock_deepseek:
                    mock_deepseek.complete.return_value = "DeepSeek response"
                    result = await dg._llm_generate("prompt", "j1")
                    assert result == "DeepSeek response"

    @pytest.mark.asyncio
    async def test_llm_generate_all_failures(self):
        with patch("app.pipeline.generation.document_generator.get_supabase_client", return_value=None):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._volatile_sessions["j1"] = {
                "id": "j1",
                "config_json": {"doc_type": "paper", "metadata": {"title": "Fallback"}},
            }
            with patch("app.services.llm_service.LLM_NVIDIA") as mock_nvidia:
                mock_nvidia.complete.side_effect = RuntimeError("down")
                with patch("app.services.llm_service.LLM_DEEPSEEK") as mock_deepseek:
                    mock_deepseek.complete.side_effect = RuntimeError("also down")
                    result = await dg._llm_generate("prompt", "j1")
                    assert "Fallback" in result


class TestDocumentGeneratorFormatAndExportEdgeCases:
    @pytest.mark.asyncio
    async def test_format_and_export_empty_blocks(self, tmp_path):
        from app.pipeline.generation.document_generator import DocumentGenerator

        dg = DocumentGenerator()
        with (
            patch("app.pipeline.generation.document_generator.get_supabase_client"),
            patch("app.pipeline.generation.document_generator.Formatter") as MockFmt,
            patch("app.pipeline.generation.document_generator.Exporter") as MockExp,
            patch("app.pipeline.generation.document_generator.GENERATED_DIR", tmp_path),
        ):
            fmt = MagicMock()
            fmt.process.return_value = MagicMock(generated_doc=MagicMock())
            MockFmt.return_value = fmt
            exp = MagicMock()
            MockExp.return_value = exp
            docx_path = tmp_path / "job-empty.docx"
            docx_path.write_text("content")
            result = await dg._format_and_export(
                raw_blocks=[],
                template="ieee",
                job_id="job-empty",
                metadata={},
                doc_type="paper",
            )
            assert result == docx_path.resolve()


# ══════════════════════════════════════════════════════════════════════════════
# PromptBuilder — edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestPromptBuilderEdgeCases:
    def test_build_academic_paper_empty_sections(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder

        result = PromptBuilder().build("academic_paper", {"title": "T"}, {})
        assert "Introduction" in result
        assert "Methodology" in result

    def test_build_resume_empty_education(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder

        result = PromptBuilder().build("resume", {"name": "Alice"}, {})
        assert "Alice" in result

    def test_build_portfolio_empty_projects(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder

        result = PromptBuilder().build("portfolio", {"name": "Researcher"}, {})
        assert "Researcher" in result

    def test_build_report_placeholder_true(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder

        result = PromptBuilder().build("report", {"title": "Report"}, {"include_placeholder_content": True})
        assert "2-4 paragraphs" in result

    def test_build_thesis_chapter_1_skip_author(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder

        result = PromptBuilder().build("thesis", {"chapter_number": 2, "chapter_title": "Methods"}, {})
        assert "Chapter 2" in result


# ══════════════════════════════════════════════════════════════════════════════
# QualityScorer — remaining coverage
# ══════════════════════════════════════════════════════════════════════════════


class TestQualityScorerEdgeCases:
    def test_score_with_dict_content(self):
        from app.pipeline.generation.quality_scorer import QualityScorer

        scorer = QualityScorer()
        content = {"section_one": "word " * 200, "section_two": "cite " * 50}
        result = scorer.score(content, "ieee", {"sections": ["section_one", "section_two"]})
        assert result["word_count"] > 0

    def test_score_with_none_content(self):
        from app.pipeline.generation.quality_scorer import QualityScorer

        scorer = QualityScorer()
        result = scorer.score(None, "ieee", {})
        assert result["overall_score"] == 0.0

    def test_required_sections_not_list(self):
        from app.pipeline.generation.quality_scorer import QualityScorer

        result = QualityScorer._required_sections({"sections": "not a list"}, {"A": "text"})
        assert result == ["A"]

    def test_word_count_handles_non_string(self):
        from app.pipeline.generation.quality_scorer import QualityScorer

        assert QualityScorer._word_count(None) == 0
        assert QualityScorer._word_count(12345) == 1

    def test_count_citations_none(self):
        from app.pipeline.generation.quality_scorer import QualityScorer

        assert QualityScorer._count_citations(None) == 0

    def test_section_balance_no_counts(self):
        from app.pipeline.generation.quality_scorer import QualityScorer

        assert QualityScorer._section_balance({}, []) == 0.0

    def test_citation_score_edge(self):
        from app.pipeline.generation.quality_scorer import QualityScorer

        assert QualityScorer._citation_score(0, 0) == 0.0
        assert QualityScorer._citation_score(10, 0) == 0.0

    def test_score_with_citations_in_dict(self):
        from app.pipeline.generation.quality_scorer import QualityScorer

        scorer = QualityScorer()
        content = {
            "Introduction": "word " * 150 + " [1] [2]",
            "Methods": "word " * 150 + " (Smith, 2020)",
        }
        result = scorer.score(content, "ieee", {"sections": ["Introduction", "Methods"]})
        assert result["citation_count"] >= 2

    def test_score_empty_sections_list(self):
        from app.pipeline.generation.quality_scorer import QualityScorer

        scorer = QualityScorer()
        content = {"sections": []}
        result = scorer.score(content, "ieee", {"sections": []})
        assert result["overall_score"] == 0.0


# ══════════════════════════════════════════════════════════════════════════════
# ContentParser — edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestContentParserEdgeCases:
    def test_parse_with_section_title_alias(self):
        from app.pipeline.generation.content_parser import ContentParser

        result = ContentParser().parse('[{"type":"SECTION","content":"Intro","level":1}]', "paper")
        assert result[0]["type"] == "BODY"

    def test_load_json_not_list(self):
        from app.pipeline.generation.content_parser import ContentParser

        with pytest.raises(ValueError, match="JSON array"):
            ContentParser._load_json("{}")

    def test_normalise_non_dict_uses_body(self):
        from app.pipeline.generation.content_parser import ContentParser

        result = ContentParser._normalise("raw string", 0)
        assert result["type"] == "BODY"
        assert result["content"] == "raw string"

    def test_normalise_unknown_level(self):
        from app.pipeline.generation.content_parser import ContentParser

        with pytest.raises(ValueError):
            ContentParser._normalise({"type": "BODY", "content": "x", "level": "abc"}, 0)

    def test_extract_json_fences_with_newline_after_lang(self):
        from app.pipeline.generation.content_parser import ContentParser

        text = '```json\n[{"a":1}]\n```'
        result = ContentParser._extract_json(text)
        assert '[{"a":1}]' in result

    def test_extract_json_plain_fences_no_lang(self):
        from app.pipeline.generation.content_parser import ContentParser

        text = '```\n[{"a":1}]\n```'
        result = ContentParser._extract_json(text)
        assert '[{"a":1}]' in result


# ══════════════════════════════════════════════════════════════════════════════
# SectionPrompts — edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestSectionPromptsEdgeCases:
    def test_get_section_prompt_empty_context(self):
        from app.pipeline.generation.section_prompts import get_section_prompt

        prompt = get_section_prompt("Abstract", {})
        assert prompt is not None
        assert "academic abstract" in prompt.lower()

    def test_get_section_prompt_unknown_with_full_context(self):
        from app.pipeline.generation.section_prompts import get_section_prompt

        prompt = get_section_prompt(
            "Custom",
            {
                "task_spec": {"title": "Test"},
                "template_rules": [{"rule": "APA"}],
                "outline": ["Intro"],
                "previous_sections": {"Intro": "text"},
            },
        )
        assert "rigorous academic section" in prompt.lower()

    def test_truncate_with_none(self):
        from app.pipeline.generation.section_prompts import _truncate

        assert _truncate(None) == ""

    def test_truncate_empty_string(self):
        from app.pipeline.generation.section_prompts import _truncate

        assert _truncate("") == ""

    def test_truncate_short(self):
        from app.pipeline.generation.section_prompts import _truncate

        assert _truncate("hello") == "hello"

    def test_truncate_long(self):
        from app.pipeline.generation.section_prompts import _truncate

        text = "a" * 2000
        result = _truncate(text, limit=100)
        assert len(result) <= 104
        assert result.endswith("...")

    def test_section_prompts_has_all_keys(self):
        from app.pipeline.generation.section_prompts import SECTION_PROMPTS

        expected = {"Abstract", "Introduction", "Literature Review", "Methods", "Results", "Discussion", "Conclusion"}
        assert set(SECTION_PROMPTS.keys()) == expected


# ══════════════════════════════════════════════════════════════════════════════
# TaskParser — edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestTaskParserEdgeCases:
    def test_load_templates_empty(self, tmp_path):
        with patch("app.pipeline.generation.task_parser.Path") as MockPath:
            mock_app_dir = MagicMock()
            mock_app_dir.parents.__getitem__.return_value = tmp_path
            MockPath.return_value.resolve.return_value = mock_app_dir
            from app.pipeline.generation.task_parser import _load_templates

            result = _load_templates()
            assert isinstance(result, dict)

    def test_extract_json_none_input(self):
        from app.pipeline.generation.task_parser import _extract_json

        assert _extract_json(None) is None

    def test_extract_json_empty(self):
        from app.pipeline.generation.task_parser import _extract_json

        assert _extract_json("") is None

    def test_extract_json_only_closing_brace(self):
        from app.pipeline.generation.task_parser import _extract_json

        assert _extract_json("}") is None

    def test_keywords_from_prompt_none(self):
        from app.pipeline.generation.task_parser import _keywords_from_prompt

        assert _keywords_from_prompt(None) == []

    def test_keywords_from_prompt_short_tokens(self):
        from app.pipeline.generation.task_parser import _keywords_from_prompt

        result = _keywords_from_prompt("a an the is it at")
        assert all(len(k) >= 4 for k in result)

    def test_validate_spec_with_none_values(self):
        from app.pipeline.generation.task_parser import TaskParser

        parser = TaskParser()
        spec = parser._validate_spec({"doc_type": None, "template": None, "tone": None}, "prompt")
        assert spec["doc_type"] == "research_paper"
        assert spec["template"] == "IEEE"

    def test_validate_spec_citation_style_falls_to_template(self):
        from app.pipeline.generation.task_parser import TaskParser

        parser = TaskParser()
        spec = parser._validate_spec({"template": "APA", "citation_style": ""}, "prompt")
        assert spec["citation_style"] == "apa"

    def test_validate_spec_title_generated_from_doc_type(self):
        from app.pipeline.generation.task_parser import TaskParser

        parser = TaskParser()
        spec = parser._validate_spec({"doc_type": "review", "title": ""}, "prompt")
        assert "Review" in spec["title"]

    def test_validate_spec_invalid_template_falls_to_default(self):
        from app.pipeline.generation.task_parser import TaskParser

        parser = TaskParser()
        spec = parser._validate_spec({"template": "nonexistent"}, "prompt")
        assert spec["template"] == "IEEE"

    def test_validate_spec_empty_sections_uses_default(self):
        from app.pipeline.generation.task_parser import TaskParser

        parser = TaskParser()
        spec = parser._validate_spec({"sections": []}, "prompt")
        assert "Abstract" in spec["sections"]

    def test_validate_spec_non_list_sections_uses_default(self):
        from app.pipeline.generation.task_parser import TaskParser

        parser = TaskParser()
        spec = parser._validate_spec({"sections": "not a list"}, "prompt")
        assert "Abstract" in spec["sections"]

    def test_validate_spec_keywords_empty_list(self):
        from app.pipeline.generation.task_parser import TaskParser

        parser = TaskParser()
        spec = parser._validate_spec({"keywords": []}, "deep learning paper")
        assert len(spec["keywords"]) > 0

    @pytest.mark.asyncio
    async def test_parse_with_invalid_json_response(self):
        from app.pipeline.generation.task_parser import TaskParser

        parser = TaskParser()
        with patch(
            "app.pipeline.generation.task_parser.asyncio.to_thread", new=AsyncMock(return_value="not valid json at all")
        ):
            result = await parser.parse("write a paper")
        assert result["doc_type"] == "research_paper"

    @pytest.mark.asyncio
    async def test_parse_with_partial_json_containing_text(self):
        from app.pipeline.generation.task_parser import TaskParser

        parser = TaskParser()
        with patch("app.pipeline.generation.task_parser.generate") as mock_gen:
            mock_gen.return_value = 'Some text ```json\n{"title": "Custom"}\n``` and more'
            result = await parser.parse("write a paper")
        assert result["title"] == "Custom"
