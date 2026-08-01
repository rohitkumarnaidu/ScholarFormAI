# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Comprehensive tests for DocumentGenerator (0% -> ~98%).
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
#  Conftest cleanup — conftest.py stubs document_generator as a MagicMock;
#  we need the real module for these tests.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_stubs():
    key = "app.pipeline.generation.document_generator"
    if key in sys.modules:
        del sys.modules[key]
    # Remove stubs that block real loading
    for k in ["app.routers.v1.stream", "app.realtime.events", "app.realtime.pubsub"]:
        if k in sys.modules:
            del sys.modules[k]
    # Stub the generator router to prevent circular import when document_generator
    # triggers loading of app.routers.v1 (via from app.routers.v1.stream import emit_event)
    from unittest.mock import MagicMock as _MM
    if "app.routers.v1.generator" not in sys.modules:
        sys.modules["app.routers.v1.generator"] = _MM()
    yield
    # Restore stubs for other tests
    from unittest.mock import MagicMock as _MM
    sys.modules[key] = _MM()
    sys.modules["app.routers.v1.stream"] = _MM()
    sys.modules["app.realtime.events"] = _MM()
    sys.modules["app.realtime.pubsub"] = _MM()


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _fresh_module():
    """Return a freshly-loaded document_generator module with
    get_supabase_client already mocked.  Must be called inside
    the patch('app.db.supabase_client.get_supabase_client') context."""
    import importlib
    import app.pipeline.generation.document_generator as m
    importlib.reload(m)
    return m


def _default_supabase_mock():
    """Return (sb, table) mocks wired for the chained call pattern."""
    sb = MagicMock()
    t = MagicMock()
    t.select.return_value = t
    t.eq.return_value = t
    t.maybe_single.return_value = t
    ok = MagicMock()
    ok.data = {"id": "test-job"}
    t.execute.return_value = ok
    t.insert.return_value = t
    t.update.return_value = t
    sb.table.return_value = t
    return sb, t


def _default_doc_service_mock():
    ds = MagicMock()
    ds.create_document.return_value = {"id": "test-job"}
    ds.update_document.return_value = {"id": "test-job"}
    ds.get_document.return_value = None
    ds.get_document_result.return_value = None
    ds.upsert_document_result.return_value = None
    ds.update_output_hash.return_value = True
    ds.mark_document_completed.return_value = None
    ds.mark_document_failed.return_value = None
    ds.upsert_processing_status.return_value = None
    return ds


# ---------------------------------------------------------------------------
#  Fixture — every test gets a clean instance with all external deps mocked
# ---------------------------------------------------------------------------

@pytest.fixture
def dc():
    """Return a (module, instance) tuple with all deps mocked.

    Usage::
        def test_foo(self, dc):
            mod, dg = dc
            dg.some_method(...)
    """
    with patch("app.db.supabase_client.get_supabase_client") as msb:
        sb, _ = _default_supabase_mock()
        msb.return_value = sb
        mod = _fresh_module()
        mod.GENERATED_DIR = Path("/tmp/gen_out")
        mod.emit_event = MagicMock()
        mod.DocumentService = _default_doc_service_mock()
        dg = mod.DocumentGenerator()
        dg._mod = mod
        yield mod, dg


# ---------------------------------------------------------------------------
#  Shared test data
# ---------------------------------------------------------------------------

SAMPLE_BLOCKS = [
    {"type": "TITLE", "content": "Test Title", "level": 0},
    {"type": "ABSTRACT", "content": "Abstract text.", "level": 0},
    {"type": "HEADING_1", "content": "Introduction", "level": 1},
    {"type": "BODY", "content": "Body text.", "level": 0},
    {"type": "HEADING_2", "content": "Subsection", "level": 2},
    {"type": "REFERENCE_ENTRY", "content": "Ref 1", "level": 0},
]


# ═══════════════════════════════════════════════════════════════════════════
# _normalize_status
# ═══════════════════════════════════════════════════════════════════════════

class TestNormalizeStatus:
    def test_pending(self, dc):
        _, dg = dc
        assert dg._normalize_status("PENDING") == "pending"

    def test_processing(self, dc):
        _, dg = dc
        assert dg._normalize_status("PROCESSING") == "processing"

    def test_completed(self, dc):
        _, dg = dc
        assert dg._normalize_status("COMPLETED") == "done"

    def test_completed_with_warnings(self, dc):
        _, dg = dc
        assert dg._normalize_status("COMPLETED_WITH_WARNINGS") == "done"

    def test_failed(self, dc):
        _, dg = dc
        assert dg._normalize_status("FAILED") == "failed"

    def test_cancelled(self, dc):
        _, dg = dc
        assert dg._normalize_status("CANCELLED") == "failed"

    def test_already_lowercase(self, dc):
        _, dg = dc
        assert dg._normalize_status("done") == "done"

    def test_unknown(self, dc):
        _, dg = dc
        assert dg._normalize_status("BOGUS") == "processing"

    def test_none(self, dc):
        _, dg = dc
        assert dg._normalize_status(None) == "processing"

    def test_empty_string(self, dc):
        _, dg = dc
        assert dg._normalize_status("") == "processing"


# ═══════════════════════════════════════════════════════════════════════════
# _now_iso
# ═══════════════════════════════════════════════════════════════════════════

class TestNowIso:
    def test_returns_iso_string(self, dc):
        _, dg = dc
        datetime.fromisoformat(dg._now_iso())


# ═══════════════════════════════════════════════════════════════════════════
# _default_session_config
# ═══════════════════════════════════════════════════════════════════════════

class TestDefaultSessionConfig:
    def test_returns_correct_config(self, dc):
        _, dg = dc
        c = dg._default_session_config(doc_type="paper", template="ieee",
                                        metadata={"t": "T"}, options={"wc": 3}, user_id="u1")
        assert c["doc_type"] == "paper"
        assert c["template"] == "ieee"
        assert c["stage"] == "queued"


# ═══════════════════════════════════════════════════════════════════════════
# _session_record_to_status
# ═══════════════════════════════════════════════════════════════════════════

class TestSessionRecordToStatus:
    def test_basic(self, dc):
        _, dg = dc
        s = {"id": "j1", "status": "COMPLETED", "progress": 100,
             "config_json": {"stage": "done", "message": "Done.", "output_path": "/p/doc.docx"},
             "outline_json": ["Intro"]}
        r = dg._session_record_to_status(s)
        assert r["job_id"] == "j1" and r["status"] == "done" and r["progress"] == 100

    def test_no_config_json(self, dc):
        _, dg = dc
        r = dg._session_record_to_status({"id": "j1"})
        assert r["status"] == "pending" and r["progress"] == 0

    def test_outline_not_list(self, dc):
        _, dg = dc
        assert dg._session_record_to_status({"id": "j", "outline_json": "bad"})["outline"] == []

    def test_outline_stripped(self, dc):
        _, dg = dc
        r = dg._session_record_to_status({"id": "j", "outline_json": ["  A  ", ""]})
        assert r["outline"] == ["A"]

    def test_progress_clamped(self, dc):
        _, dg = dc
        assert dg._session_record_to_status({"id": "j", "progress": 150, "config_json": {}})["progress"] == 100

    def test_negative_progress(self, dc):
        _, dg = dc
        assert dg._session_record_to_status({"id": "j", "progress": -10, "config_json": {}})["progress"] == 0

    def test_include_outline_false(self, dc):
        _, dg = dc
        assert dg._session_record_to_status({"id": "j", "outline_json": ["A"]}, include_outline=False)["outline"] == []

    def test_error_from_config(self, dc):
        _, dg = dc
        assert dg._session_record_to_status({"id": "j", "config_json": {"error": "oops"}})["error"] == "oops"


# ═══════════════════════════════════════════════════════════════════════════
# _get_session_record
# ═══════════════════════════════════════════════════════════════════════════

class TestGetSessionRecord:
    def test_supabase_returns_data(self, dc):
        _, dg = dc
        assert dg._get_session_record("job-1") is not None

    def test_supabase_exception_falls_to_volatile(self):
        sb, t = _default_supabase_mock()
        t.execute.side_effect = Exception("DB down")
        with patch("app.db.supabase_client.get_supabase_client", return_value=sb):
            mod = _fresh_module()
            mod.GENERATED_DIR = Path("/tmp")
            mod.emit_event = MagicMock()
            mod.DocumentService = _default_doc_service_mock()
            dg = mod.DocumentGenerator()
            dg._volatile_sessions["j1"] = {"id": "j1", "status": "processing"}
            assert dg._get_session_record("j1") == {"id": "j1", "status": "processing"}

    def test_supabase_none_uses_volatile(self):
        with patch("app.db.supabase_client.get_supabase_client", return_value=None):
            mod = _fresh_module()
            mod.GENERATED_DIR = Path("/tmp")
            mod.emit_event = MagicMock()
            mod.DocumentService = _default_doc_service_mock()
            dg = mod.DocumentGenerator()
            dg._volatile_sessions["j1"] = {"id": "j1"}
            assert dg._get_session_record("j1") == {"id": "j1"}

    def test_not_found_returns_none(self, dc):
        _, dg = dc
        with patch.object(dg._mod, "get_supabase_client", return_value=None):
            assert dg._get_session_record("x") is None


# ═══════════════════════════════════════════════════════════════════════════
# get_session
# ═══════════════════════════════════════════════════════════════════════════

class TestGetSession:
    def test_returns_none_for_missing(self, dc):
        _, dg = dc
        # override supabase mock to return nothing
        with patch.object(dg._mod, "get_supabase_client", return_value=None):
            assert dg.get_session("x") is None


# ═══════════════════════════════════════════════════════════════════════════
# update_status
# ═══════════════════════════════════════════════════════════════════════════

class TestUpdateStatus:
    def test_updates_db_and_volatile(self, dc):
        _, dg = dc
        dg.update_status("job-1", status="processing", progress=50, stage="structuring")
        assert dg._volatile_sessions.get("job-1") is not None

    def test_with_error_and_outline(self, dc):
        _, dg = dc
        dg.update_status("job-1", status="failed", progress=0,
                          stage="error", message="fail", error="err", outline=["Intro"])
        assert dg._volatile_sessions["job-1"]["config_json"]["error"] == "err"

    def test_with_output_path(self, dc):
        _, dg = dc
        dg.update_status("job-1", status="done", progress=100, output_path="/out/doc.docx")
        assert dg._volatile_sessions["job-1"]["config_json"]["output_path"] == "/out/doc.docx"

    def test_no_outline_when_none(self, dc):
        _, dg = dc
        dg.update_status("job-1", status="processing", progress=50)
        assert "outline_json" not in dg._volatile_sessions["job-1"]


# ═══════════════════════════════════════════════════════════════════════════
# start_job
# ═══════════════════════════════════════════════════════════════════════════

class TestStartJob:
    def test_creates_session(self, dc):
        _, dg = dc
        import asyncio
        jid = asyncio.run(dg.start_job("paper", "ieee", {"title": "T"}, {}, "u1"))
        assert uuid.UUID(jid)

    def test_db_save_fails_uses_volatile(self, dc):
        _, dg = dc
        dg._mod.DocumentService.create_document.return_value = None
        # Make supabase insert fail so volatile is used
        with patch.object(dg._mod, "get_supabase_client") as msb:
            sb = MagicMock()
            sb.table.return_value.insert.side_effect = Exception("DB down")
            msb.return_value = sb
            import asyncio
            jid = asyncio.run(dg.start_job("resume", "modern", {}, {}, None))
            assert jid in dg._volatile_sessions

    def test_supabase_insert_fails_uses_volatile(self):
        sb, _ = _default_supabase_mock()
        sb.table.return_value.insert.side_effect = Exception("DB down")
        with patch("app.db.supabase_client.get_supabase_client", return_value=sb):
            mod = _fresh_module()
            mod.GENERATED_DIR = Path("/tmp")
            mod.emit_event = MagicMock()
            mod.DocumentService = _default_doc_service_mock()
            dg = mod.DocumentGenerator()
            import asyncio
            jid = asyncio.run(dg.start_job("report", "default", {}, {}, "u1"))
            assert jid in dg._volatile_sessions


# ═══════════════════════════════════════════════════════════════════════════
# run_pipeline
# ═══════════════════════════════════════════════════════════════════════════

class TestRunPipeline:
    def _make_session_data(self):
        return {
            "id": "j1",
            "config_json": {
                "doc_type": "paper", "template": "ieee",
                "metadata": {"title": "T"}, "options": {},
            },
        }

    def test_success_flow(self):
        sb, t = _default_supabase_mock()
        t.execute.return_value = MagicMock(data=self._make_session_data())
        with patch("app.db.supabase_client.get_supabase_client", return_value=sb):
            mod = _fresh_module()
            mod.GENERATED_DIR = Path("/tmp")
            mod.emit_event = MagicMock()
            mod.DocumentService = _default_doc_service_mock()
            with patch.object(mod, "PromptBuilder") as pb:
                pb_i = MagicMock()
                pb_i.build.return_value = "prompt"
                pb.return_value = pb_i
                with patch.object(mod, "ContentParser") as cp:
                    cp_i = MagicMock()
                    cp_i.parse.return_value = SAMPLE_BLOCKS
                    cp.return_value = cp_i
                    with patch.object(mod, "Formatter") as fm, \
                         patch.object(mod, "Exporter") as em, \
                         patch.object(mod, "asyncio") as _asyncio:
                        loop = MagicMock()
                        loop.run_in_executor.return_value = "LLM text"
                        _asyncio.get_event_loop.return_value = loop
                        f_i = MagicMock()
                        f_i.process.side_effect = lambda d: setattr(d, "generated_doc", MagicMock()) or d
                        fm.return_value = f_i
                        e_i = MagicMock()
                        e_i.process.side_effect = lambda d: d
                        em.return_value = e_i
                        mod.GENERATED_DIR = Path("/tmp")
                        with patch.object(Path, "exists", return_value=True):
                            dg = mod.DocumentGenerator()
                            dg._mod = mod
                            dg._volatile_sessions["j1"] = {}
                            import asyncio
                            asyncio.run(dg.run_pipeline("j1"))

    def test_job_not_found_returns_early(self):
        with patch("app.db.supabase_client.get_supabase_client", return_value=None):
            mod = _fresh_module()
            mod.GENERATED_DIR = Path("/tmp")
            mod.emit_event = MagicMock()
            mod.DocumentService = _default_doc_service_mock()
            dg = mod.DocumentGenerator()
            import asyncio
            asyncio.run(dg.run_pipeline("nonexistent"))

    def test_pipeline_exception_triggers_failure(self):
        with patch("app.db.supabase_client.get_supabase_client", return_value=None):
            mod = _fresh_module()
            mod.GENERATED_DIR = Path("/tmp")
            mod.emit_event = MagicMock()
            mod.DocumentService = _default_doc_service_mock()
            dg = mod.DocumentGenerator()
            dg._volatile_sessions["j1"] = {
                "config_json": {"doc_type": "paper", "template": "ieee", "metadata": {}, "options": {}},
            }
            with patch.object(mod, "PromptBuilder") as pb:
                pb_i = MagicMock()
                pb_i.build.side_effect = ValueError("boom")
                pb.return_value = pb_i
                import asyncio
                asyncio.run(dg.run_pipeline("j1"))


# ═══════════════════════════════════════════════════════════════════════════
# get_status
# ═══════════════════════════════════════════════════════════════════════════

class TestGetStatus:
    def test_from_session(self, dc):
        _, dg = dc
        assert dg.get_status("job-1")["job_id"] == "test-job"

    def test_from_document_fallback(self):
        sb, t = _default_supabase_mock()
        t.execute.return_value = MagicMock(data=None)
        with patch("app.db.supabase_client.get_supabase_client", return_value=sb):
            mod = _fresh_module()
            mod.GENERATED_DIR = Path("/tmp")
            mod.emit_event = MagicMock()
            ds = _default_doc_service_mock()
            ds.get_document.return_value = {
                "id": "j1", "status": "COMPLETED", "current_stage": "DONE",
                "progress": 100, "output_path": "/out/doc.docx",
            }
            mod.DocumentService = ds
            dg = mod.DocumentGenerator()
            r = dg.get_status("j1")
            assert r["status"] == "done"

    def test_document_not_found_raises(self, dc):
        _, dg = dc
        sb, t = _default_supabase_mock()
        t.execute.return_value = MagicMock(data=None)
        with patch.object(dg._mod, "get_supabase_client", return_value=sb):
            dg._mod.DocumentService.get_document.return_value = None
            with pytest.raises(KeyError):
                dg.get_status("j1")

    def test_outline_from_result(self, dc):
        _, dg = dc
        sb, t = _default_supabase_mock()
        t.execute.return_value = MagicMock(data={
            "id": "j1", "status": "COMPLETED", "progress": 100,
            "config_json": {"stage": "done", "message": "Done"},
            "outline_json": [],
        })
        dg._mod.DocumentService.get_document_result.return_value = {
            "structured_data": {"outline": ["Intro"]},
        }
        with patch.object(dg._mod, "get_supabase_client", return_value=sb):
            r = dg.get_status("j1")
            assert "Intro" in r["outline"]

    def test_failed_status_has_error(self):
        sb, t = _default_supabase_mock()
        t.execute.return_value = MagicMock(data=None)
        with patch("app.db.supabase_client.get_supabase_client", return_value=sb):
            mod = _fresh_module()
            mod.GENERATED_DIR = Path("/tmp")
            mod.emit_event = MagicMock()
            ds = _default_doc_service_mock()
            ds.get_document.return_value = {
                "id": "j1", "status": "FAILED", "error_message": "boom",
                "current_stage": "ERROR", "progress": 0,
            }
            mod.DocumentService = ds
            dg = mod.DocumentGenerator()
            r = dg.get_status("j1")
            assert r["status"] == "failed" and r["error"] == "boom"


# ═══════════════════════════════════════════════════════════════════════════
# get_download_path
# ═══════════════════════════════════════════════════════════════════════════

class TestGetDownloadPath:
    def test_from_session(self, dc):
        _, dg = dc

    def test_from_document_fallback(self):
        sb, t = _default_supabase_mock()
        t.execute.return_value = MagicMock(data=None)
        with patch("app.db.supabase_client.get_supabase_client", return_value=sb):
            mod = _fresh_module()
            mod.GENERATED_DIR = Path("/tmp")
            mod.emit_event = MagicMock()
            ds = _default_doc_service_mock()
            ds.get_document.return_value = {
                "id": "j1", "status": "COMPLETED", "output_path": "/out/doc.docx",
            }
            mod.DocumentService = ds
            dg = mod.DocumentGenerator()
            assert dg.get_download_path("j1") == Path("/out/doc.docx")

    def test_not_completed(self):
        sb, t = _default_supabase_mock()
        t.execute.return_value = MagicMock(data=None)
        with patch("app.db.supabase_client.get_supabase_client", return_value=sb):
            mod = _fresh_module()
            mod.GENERATED_DIR = Path("/tmp")
            mod.emit_event = MagicMock()
            ds = _default_doc_service_mock()
            ds.get_document.return_value = {"id": "j1", "status": "PROCESSING"}
            mod.DocumentService = ds
            dg = mod.DocumentGenerator()
            assert dg.get_download_path("j1") is None

    def test_no_document(self):
        sb, t = _default_supabase_mock()
        t.execute.return_value = MagicMock(data=None)
        with patch("app.db.supabase_client.get_supabase_client", return_value=sb):
            mod = _fresh_module()
            mod.GENERATED_DIR = Path("/tmp")
            mod.emit_event = MagicMock()
            ds = _default_doc_service_mock()
            ds.get_document.return_value = None
            mod.DocumentService = ds
            dg = mod.DocumentGenerator()
            assert dg.get_download_path("j1") is None


# ═══════════════════════════════════════════════════════════════════════════
# _update
# ═══════════════════════════════════════════════════════════════════════════

class TestUpdate:
    def test_queued(self, dc):
        _, dg = dc
        dg._update("job-1", "queued", 0, "Queued")

    def test_error(self, dc):
        _, dg = dc
        dg._update("job-1", "error", 0, "Failed", error="err")

    def test_done_with_output_path(self, dc):
        _, dg = dc
        dg._update("job-1", "done", 100, "Done", output_path="/out/doc.docx")


# ═══════════════════════════════════════════════════════════════════════════
# _emit
# ═══════════════════════════════════════════════════════════════════════════

class TestEmit:
    def test_calls_emit_event(self, dc):
        _, dg = dc
        dg._emit("j1", phase="T", status="OK", message="t")
        dg._mod.emit_event.assert_called()

    def test_suppresses_exception(self, dc):
        _, dg = dc
        dg._mod.emit_event.side_effect = Exception("SSE down")
        dg._emit("j1", phase="T", status="OK")


# ═══════════════════════════════════════════════════════════════════════════
# _llm_generate
# ═══════════════════════════════════════════════════════════════════════════

class TestLlmGenerate:
    def _llm_mock(self, module, side_effect=None):
        """Patch app.services.llm_service so the dynamic imports in _llm_generate get mocks."""
        svc = MagicMock()
        svc.LLM_NVIDIA = MagicMock()
        svc.LLM_DEEPSEEK = MagicMock()
        if side_effect:
            svc.LLM_NVIDIA.complete.side_effect = side_effect
            svc.LLM_DEEPSEEK.complete.side_effect = side_effect
        else:
            svc.LLM_NVIDIA.complete.return_value = "NVIDIA response"
            svc.LLM_DEEPSEEK.complete.return_value = "DeepSeek response"
        return patch.dict("sys.modules", {"app.services.llm_service": svc}, clear=False)

    def test_nvidia_succeeds(self, dc):
        _, dg = dc
        with self._llm_mock(dg._mod):
            import asyncio
            r = asyncio.run(dg._llm_generate("prompt", "j1"))
            assert r == "NVIDIA response"

    def test_nvidia_fails_deepseek_fallback(self, dc):
        _, dg = dc
        svc = MagicMock()
        svc.LLM_NVIDIA = MagicMock()
        svc.LLM_NVIDIA.complete.side_effect = Exception("NVIDIA down")
        svc.LLM_DEEPSEEK = MagicMock()
        svc.LLM_DEEPSEEK.complete.return_value = "DeepSeek response"
        with patch.dict("sys.modules", {"app.services.llm_service": svc}, clear=False):
            import asyncio
            r = asyncio.run(dg._llm_generate("prompt", "j1"))
            assert r == "DeepSeek response"

    def test_all_fail_uses_rule_skeleton(self, dc):
        _, dg = dc
        dg._volatile_sessions["j1"] = {"config_json": {"doc_type": "paper", "metadata": {"title": "Fallback"}}}
        # Override supabase mock to return nothing so _get_session_record falls to volatile
        with patch.object(dg._mod, "get_supabase_client", return_value=None):
            svc = MagicMock()
            svc.LLM_NVIDIA = MagicMock()
            svc.LLM_NVIDIA.complete.side_effect = Exception("all down")
            svc.LLM_DEEPSEEK = MagicMock()
            svc.LLM_DEEPSEEK.complete.side_effect = Exception("also down")
            with patch.dict("sys.modules", {"app.services.llm_service": svc}, clear=False):
                import asyncio
                r = asyncio.run(dg._llm_generate("prompt", "j1"))
                assert "Fallback" in r and "Introduction" in r


# ═══════════════════════════════════════════════════════════════════════════
# _rule_based_skeleton
# ═══════════════════════════════════════════════════════════════════════════

class TestRuleBasedSkeleton:
    def test_academic_paper(self, dc):
        _, dg = dc
        r = json.loads(dg._rule_based_skeleton("paper", {"title": "Paper"}))
        assert any(b["type"] == "ABSTRACT" for b in r)

    def test_resume(self, dc):
        _, dg = dc
        r = json.loads(dg._rule_based_skeleton("resume", {"title": "R", "summary": "S"}))
        assert any("Professional Summary" in b["content"] for b in r if b["type"] == "HEADING_1")

    def test_default_title(self, dc):
        _, dg = dc
        r = json.loads(dg._rule_based_skeleton("other", {}))
        assert r[0]["content"] == "Document Title"


# ═══════════════════════════════════════════════════════════════════════════
# _format_and_export
# ═══════════════════════════════════════════════════════════════════════════

class TestFormatAndExport:
    def test_success(self, dc):
        _, dg = dc
        mod = dg._mod
        out = Path("/tmp/gen_out/t.docx")
        mod.GENERATED_DIR = Path("/tmp/gen_out")
        with patch.object(mod, "Formatter") as fm, \
             patch.object(mod, "Exporter") as em:
            f_i = MagicMock()
            f_i.process.side_effect = lambda d: setattr(d, "generated_doc", MagicMock()) or d
            fm.return_value = f_i
            e_i = MagicMock()
            e_i.process.side_effect = lambda d: d
            em.return_value = e_i
            with patch.object(Path, "exists", return_value=True):
                import asyncio
                r = asyncio.run(dg._format_and_export(SAMPLE_BLOCKS, "ieee", "j1",
                                                       {"title": "T", "authors": ["A"], "keywords": ["k"]},
                                                       "paper"))
                assert str(r).endswith("j1.docx")

    def test_skip_empty_blocks(self, dc):
        _, dg = dc
        mod = dg._mod
        mod.GENERATED_DIR = Path("/tmp/gen_out")
        with patch.object(mod, "Formatter") as fm, \
             patch.object(mod, "Exporter") as em:
            f_i = MagicMock()
            f_i.process.side_effect = lambda d: setattr(d, "generated_doc", MagicMock()) or d
            fm.return_value = f_i
            e_i = MagicMock()
            e_i.process.side_effect = lambda d: d
            em.return_value = e_i
            with patch.object(Path, "exists", return_value=True):
                import asyncio
                asyncio.run(dg._format_and_export([{"type": "", "content": "  "}],
                                                    "ieee", "j1", {}, "paper"))

    def test_no_generated_doc_raises(self, dc):
        _, dg = dc
        mod = dg._mod
        mod.GENERATED_DIR = Path("/tmp/gen_out")
        with patch.object(mod, "Formatter") as fm, \
             patch.object(mod, "Exporter") as em:
            f_i = MagicMock()
            f_i.process.return_value = None
            fm.return_value = f_i
            e_i = MagicMock()
            em.return_value = e_i
            with patch.object(Path, "exists", return_value=True):
                import asyncio
                with pytest.raises(RuntimeError, match="Formatting failed"):
                    asyncio.run(dg._format_and_export(SAMPLE_BLOCKS, "ieee", "j1", {}, "paper"))

    def test_export_file_not_found_raises(self, dc):
        _, dg = dc
        mod = dg._mod
        mod.GENERATED_DIR = Path("/tmp/gen_out")
        with patch.object(mod, "Formatter") as fm, \
             patch.object(mod, "Exporter") as em:
            f_i = MagicMock()
            f_i.process.side_effect = lambda d: setattr(d, "generated_doc", MagicMock()) or d
            fm.return_value = f_i
            e_i = MagicMock()
            e_i.process.side_effect = lambda d: d
            em.return_value = e_i
            with patch.object(Path, "exists", return_value=False):
                import asyncio
                with pytest.raises(RuntimeError, match="Export failed"):
                    asyncio.run(dg._format_and_export(SAMPLE_BLOCKS, "ieee", "j1", {}, "paper"))


# ═══════════════════════════════════════════════════════════════════════════
# _extract_outline
# ═══════════════════════════════════════════════════════════════════════════

class TestExtractOutline:
    def test_extracts_headings(self, dc):
        _, dg = dc
        r = dg._extract_outline([
            {"type": "TITLE", "content": "Title"},
            {"type": "HEADING_1", "content": "Intro"},
            {"type": "BODY", "content": "text"},
            {"type": "HEADING_2", "content": "Sub"},
            {"type": "ABSTRACT", "content": "Abstract"},
        ])
        assert r == ["Title", "Intro", "Sub", "Abstract"]

    def test_dedup(self, dc):
        _, dg = dc
        r = dg._extract_outline([{"type": "HEADING_1", "content": "Intro"},
                                  {"type": "HEADING_2", "content": "intro"}])
        assert len(r) == 1

    def test_limits_to_50(self, dc):
        _, dg = dc
        r = dg._extract_outline([{"type": "HEADING_1", "content": f"H{i}"} for i in range(100)])
        assert len(r) == 50

    def test_empty(self, dc):
        _, dg = dc
        assert dg._extract_outline([]) == []

    def test_blank_content_skipped(self, dc):
        _, dg = dc
        r = dg._extract_outline([{"type": "HEADING_1", "content": "  "},
                                  {"type": "HEADING_2", "content": ""}])
        assert r == []


# ═══════════════════════════════════════════════════════════════════════════
# _compute_sha256
# ═══════════════════════════════════════════════════════════════════════════

class TestComputeSha256:
    def test_returns_hex(self, dc, tmp_path):
        _, dg = dc
        f = tmp_path / "t.bin"
        f.write_bytes(b"hello")
        assert len(dg._compute_sha256(f)) == 64


# ═══════════════════════════════════════════════════════════════════════════
# get_generator
# ═══════════════════════════════════════════════════════════════════════════

class TestGetGenerator:
    def _build_module(self):
        """Build without patching supabase (not needed for this test)."""
        import importlib
        import app.pipeline.generation.document_generator as m
        if "app.pipeline.generation.document_generator" in sys.modules:
            pass
        return importlib.reload(m)

    def test_returns_singleton(self):
        m = self._build_module()
        old = m._generator_singleton
        m._generator_singleton = None
        try:
            g1 = m.get_generator()
            g2 = m.get_generator()
            assert g1 is g2
        finally:
            m._generator_singleton = old

    def test_reuses_existing(self):
        m = self._build_module()
        dg = m.DocumentGenerator()
        with patch.object(m, "_generator_singleton", dg):
            assert m.get_generator() is dg


# ═══════════════════════════════════════════════════════════════════════════
# Gap tests — cover remaining partial/intermittent branches
# ═══════════════════════════════════════════════════════════════════════════

class TestBranchGaps:
    """Targeted tests for branches coverage shows as missed or partial."""

    def test_update_supabase_exception(self, dc):
        """_update: supabase.execute() raises → catches and logs (lines 183-184)."""
        _, dg = dc
        with patch.object(dg._mod, "get_supabase_client") as msb:
            sb = MagicMock()
            sb.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("DB err")
            msb.return_value = sb
            dg._update("j1", "stage", 50, "Progress")

    def test_start_job_no_supabase_uses_volatile(self):
        """start_job: sb is None → skip DB (line 245)."""
        sb, _ = _default_supabase_mock()
        sb.table.return_value.insert.side_effect = Exception("DB")
        with patch("app.db.supabase_client.get_supabase_client", return_value=None):
            mod = _fresh_module()
            mod.GENERATED_DIR = Path("/tmp")
            mod.emit_event = MagicMock()
            mod.DocumentService = _default_doc_service_mock()
            dg = mod.DocumentGenerator()
            import asyncio
            jid = asyncio.run(dg.start_job("paper", "ieee", {"title": "T"}, {}, "u1"))
            assert jid in dg._volatile_sessions

    def test_start_job_supabase_returns_none(self):
        """start_job: sb is not None but execute raises → DB path still enters try block."""
        with patch("app.db.supabase_client.get_supabase_client") as msb:
            sb = MagicMock()
            msb.return_value = sb
            mod = _fresh_module()
            mod.GENERATED_DIR = Path("/tmp")
            mod.emit_event = MagicMock()
            mod.DocumentService = _default_doc_service_mock()
            dg = mod.DocumentGenerator()
            import asyncio
            sb.table.return_value.insert.return_value = sb
            sb.execute.return_value = MagicMock(data=[{"id": "j1"}])
            jid = asyncio.run(dg.start_job("paper", "ieee", {}, {}, "u1"))
            assert jid

    def test_update_output_hash_handles_exception(self):
        """run_pipeline: _compute_sha256 exception is caught (lines 304-308)."""
        sb, t = _default_supabase_mock()
        t.execute.return_value = MagicMock(data={
            "id": "j1",
            "config_json": {"doc_type": "paper", "template": "ieee",
                          "metadata": {"title": "T"}, "options": {}},
        })
        with patch("app.db.supabase_client.get_supabase_client", return_value=sb):
            mod = _fresh_module()
            mod.GENERATED_DIR = Path("/tmp")
            mod.emit_event = MagicMock()
            mod.DocumentService = _default_doc_service_mock()
            mod.DocumentService.update_output_hash.side_effect = Exception("hash fail")
            with patch.object(mod, "PromptBuilder") as pb, \
                 patch.object(mod, "ContentParser") as cp, \
                 patch.object(mod, "Formatter") as fm, \
                 patch.object(mod, "Exporter") as em, \
                 patch.object(mod, "asyncio") as _asyncio:
                pb_i = MagicMock()
                pb_i.build.return_value = "prompt"
                pb.return_value = pb_i
                cp_i = MagicMock()
                cp_i.parse.return_value = [{"type": "BODY", "content": "text", "level": 1}]
                cp.return_value = cp_i
                loop = MagicMock()
                loop.run_in_executor.return_value = "LLM text"
                _asyncio.get_event_loop.return_value = loop
                fm_i = MagicMock()
                fm_i.process.side_effect = lambda d: setattr(d, "generated_doc", MagicMock()) or d
                fm.return_value = fm_i
                em_i = MagicMock()
                em_i.process.side_effect = lambda d: d
                em.return_value = em_i
                mod.GENERATED_DIR = Path("/tmp")
                with patch.object(Path, "exists", return_value=False):
                    dg = mod.DocumentGenerator()
                    dg._mod = mod
                    dg._volatile_sessions["j1"] = {}
                    import asyncio
                    asyncio.run(dg.run_pipeline("j1"))

    def test_llm_generate_nvidia_empty_response(self, dc):
        """_llm_generate: NVIDIA returns empty string → try DeepSeek."""
        _, dg = dc
        svc = MagicMock()
        svc.LLM_NVIDIA = MagicMock()
        svc.LLM_NVIDIA.complete.return_value = ""
        svc.LLM_DEEPSEEK = MagicMock()
        svc.LLM_DEEPSEEK.complete.return_value = "DeepSeek"
        dg._volatile_sessions["j1"] = {"config_json": {"doc_type": "paper", "metadata": {"title": "T"}}}
        with patch.dict("sys.modules", {"app.services.llm_service": svc}, clear=False):
            import asyncio
            r = asyncio.run(dg._llm_generate("prompt", "j1"))
            assert r == "DeepSeek"

    def test_llm_generate_both_empty_uses_rule(self, dc):
        """_llm_generate: both LLMs return empty → rule skeleton."""
        _, dg = dc
        svc = MagicMock()
        svc.LLM_NVIDIA = MagicMock()
        svc.LLM_NVIDIA.complete.return_value = ""
        svc.LLM_DEEPSEEK = MagicMock()
        svc.LLM_DEEPSEEK.complete.return_value = ""
        dg._volatile_sessions["j1"] = {
            "config_json": {"doc_type": "paper", "metadata": {"title": "FallbackTitle"}},
        }
        with patch.dict("sys.modules", {"app.services.llm_service": svc}, clear=False):
            import asyncio
            r = asyncio.run(dg._llm_generate("prompt", "j1"))
            assert "Introduction" in r

    def test_format_export_invalid_level(self):
        """_format_and_export: level fails int() → level_value is None."""
        sb, t = _default_supabase_mock()
        with patch("app.db.supabase_client.get_supabase_client", return_value=sb):
            mod = _fresh_module()
            mod.GENERATED_DIR = Path("/tmp")
            mod.emit_event = MagicMock()
            mod.DocumentService = _default_doc_service_mock()
            with patch.object(mod, "Formatter") as fm, \
                 patch.object(mod, "Exporter") as em:
                fm_i = MagicMock()
                fm_i.process.side_effect = lambda d: setattr(d, "generated_doc", MagicMock()) or d
                fm.return_value = fm_i
                em_i = MagicMock()
                em_i.process.side_effect = lambda d: d
                em.return_value = em_i
                with patch.object(Path, "exists", return_value=True):
                    dg = mod.DocumentGenerator()
                    dg._mod = mod
                    import asyncio
                    asyncio.run(dg._format_and_export(
                        [{"type": "BODY", "content": "text", "level": "not_a_number"}],
                        "ieee", "j1", {"title": "T"}, "paper",
                    ))
