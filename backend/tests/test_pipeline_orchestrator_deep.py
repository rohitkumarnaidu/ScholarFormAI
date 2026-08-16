# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Deep unit tests for PipelineOrchestrator — covers every uncovered path."""

from __future__ import annotations

import asyncio
import os
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from app.pipeline.orchestrator import (
    _MAX_CONCURRENT_JOBS,
    PipelineOrchestrator,
    _pipeline_semaphore,
    get_rag_engine,
    get_reasoning_engine,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_orchestrator(**kwargs):
    with (
        patch("app.pipeline.orchestrator.get_reasoning_engine") as mock_re,
        patch("app.pipeline.orchestrator.get_rag_engine") as mock_rag,
        patch("app.pipeline.orchestrator.GROBIDClient") as mock_grobid,
        patch("app.pipeline.orchestrator.DoclingClient") as mock_docling,
        patch("app.pipeline.orchestrator.get_supabase_client", return_value=None),
    ):
        mock_re.return_value = MagicMock()
        mock_rag.return_value = MagicMock()
        mock_grobid.return_value = MagicMock()
        mock_docling.return_value = MagicMock()
        return PipelineOrchestrator(
            templates_dir=kwargs.get("templates_dir", "app/templates"),
            temp_dir=kwargs.get("temp_dir", "temp_test_orch"),
        )


class TestInit:
    def test_initialization_defaults(self):
        orch = _make_orchestrator()
        assert orch.templates_dir == "app/templates"
        assert orch.temp_dir == "temp_test_orch"
        assert orch.converter is not None
        assert orch.analyzer is not None
        assert orch.contract_loader is not None
        assert orch.ref_normalizer is not None
        assert orch.grobid_client is not None
        assert orch.docling_client is not None
        assert orch._stage_start_times == {}

    def test_initialization_custom_temp_dir(self, tmp_path):
        custom = str(tmp_path / "custom_tmp")
        orch = _make_orchestrator(temp_dir=custom)
        assert orch.temp_dir == custom

    def test_temp_dir_created(self, tmp_path):
        d = str(tmp_path / "my_temp")
        orch = _make_orchestrator(temp_dir=d)
        assert orch.temp_dir == d

    def test_contracts_dir_derived(self):
        orch = _make_orchestrator(templates_dir="/base/templates")
        assert "base" in orch.contracts_dir
        assert "pipeline" in orch.contracts_dir
        assert "contracts" in orch.contracts_dir


class TestSemaphore:
    def test_max_concurrent_jobs_constant(self):
        assert _MAX_CONCURRENT_JOBS == 5

    def test_semaphore_initial_value(self):
        assert _pipeline_semaphore._value == _MAX_CONCURRENT_JOBS

    def test_semaphore_acquire_release(self):
        assert _pipeline_semaphore.acquire(blocking=False) is True
        assert _pipeline_semaphore._value == _MAX_CONCURRENT_JOBS - 1
        _pipeline_semaphore.release()
        assert _pipeline_semaphore._value == _MAX_CONCURRENT_JOBS


class TestEngineHelpers:
    @patch("app.pipeline.orchestrator.resolve_optional_callable")
    def test_get_rag_engine(self, mock_resolve):
        mock_resolve.return_value = "rag_engine"
        result = get_rag_engine()
        assert result == "rag_engine"
        mock_resolve.assert_called_once_with("app.pipeline.intelligence.rag_engine", "get_rag_engine")

    @patch("app.pipeline.orchestrator.resolve_optional_callable")
    def test_get_reasoning_engine(self, mock_resolve):
        mock_resolve.return_value = "reasoning_engine"
        result = get_reasoning_engine()
        assert result == "reasoning_engine"
        mock_resolve.assert_called_once_with("app.pipeline.intelligence.reasoning_engine", "get_reasoning_engine")


class TestStageInterfaceCheck:
    @pytest.fixture
    def orch(self):
        return _make_orchestrator()

    def test_valid_stage(self, orch):
        class Good:
            def process(self, doc):
                return doc

        orch._check_stage_interface(Good(), "process", "TestStage")

    def test_invalid_stage_raises(self, orch):
        class Bad:
            pass

        with pytest.raises(RuntimeError, match="does not implement required method"):
            orch._check_stage_interface(Bad(), "process", "BadStage")

    def test_error_message_includes_type_name(self, orch):
        class Foo:
            pass

        with pytest.raises(RuntimeError, match="Foo"):
            orch._check_stage_interface(Foo(), "run", "MyStage")


class TestRecordStageTransition:
    @pytest.fixture
    def orch(self):
        return _make_orchestrator()

    def test_records_start_time(self, orch):
        orch._record_stage_transition("doc-1", "parsing", "PROCESSING")
        assert ("doc-1", "PARSING") in orch._stage_start_times

    def test_processing_does_not_pop(self, orch):
        orch._record_stage_transition("doc-1", "parsing", "PROCESSING")
        orch._record_stage_transition("doc-1", "parsing", "PROCESSING")
        assert ("doc-1", "PARSING") in orch._stage_start_times

    @patch("app.middleware.prometheus_metrics.MetricsManager.record_pipeline_stage_duration")
    def test_completed_records_duration(self, mock_record, orch):
        orch._record_stage_transition("doc-1", "parsing", "PROCESSING")
        orch._record_stage_transition("doc-1", "parsing", "COMPLETED")
        mock_record.assert_called_once()
        assert ("doc-1", "PARSING") not in orch._stage_start_times

    @patch("app.middleware.prometheus_metrics.MetricsManager.record_pipeline_stage_duration")
    def test_failed_records_duration(self, mock_record, orch):
        orch._record_stage_transition("doc-1", "parsing", "PROCESSING")
        orch._record_stage_transition("doc-1", "parsing", "FAILED")
        mock_record.assert_called_once()

    def test_unknown_status_ignored(self, orch):
        orch._record_stage_transition("doc-1", "parsing", "PROCESSING")
        orch._record_stage_transition("doc-1", "parsing", "PENDING")
        assert ("doc-1", "PARSING") in orch._stage_start_times

    def test_completed_without_start_ignored(self, orch):
        with patch("app.middleware.prometheus_metrics.MetricsManager.record_pipeline_stage_duration") as mock_record:
            orch._record_stage_transition("doc-1", "parsing", "COMPLETED")
            mock_record.assert_not_called()

    def test_duration_metrics_exception_swallowed(self, orch):
        orch._record_stage_transition("doc-1", "parsing", "PROCESSING")
        with patch(
            "app.middleware.prometheus_metrics.MetricsManager.record_pipeline_stage_duration", side_effect=Exception
        ):
            orch._record_stage_transition("doc-1", "parsing", "COMPLETED")

    def test_phase_upper_casing(self, orch):
        orch._record_stage_transition("doc-1", "Parsing", "PROCESSING")
        assert ("doc-1", "PARSING") in orch._stage_start_times

    def test_status_upper_casing(self, orch):
        orch._record_stage_transition("doc-1", "parsing", "processing")
        assert ("doc-1", "PARSING") in orch._stage_start_times


class MockSupabase:
    def __init__(self, existing_data=None):
        self._existing_data = existing_data or []
        self._execute_count = 0
        self.ops = []

    def table(self, name):
        self.ops.append(("table", name))
        return self

    def select(self, *cols):
        self.ops.append(("select", cols))
        return self

    def update(self, data):
        self.ops.append(("update", data))
        return self

    def insert(self, data):
        self.ops.append(("insert", data))
        return self

    def match(self, filters):
        self.ops.append(("match", filters))
        return self

    def eq(self, col, val):
        self.ops.append(("eq", (col, val)))
        return self

    def execute(self):
        self._execute_count += 1
        return MagicMock(data=self._existing_data)


class TestUpdateStatus:
    @pytest.fixture
    def orch(self):
        return _make_orchestrator()

    def test_without_supabase(self, orch):
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=None):
            orch._update_status("doc-1", "parsing", "COMPLETED", "Done")

    def test_inserts_new_record(self, orch):
        sb = MockSupabase(existing_data=[])
        with (
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch("app.routers.v1.stream.emit_event"),
        ):
            orch._update_status("doc-1", "parsing", "COMPLETED", "Done")
            tables = [o[1] for o in sb.ops if o[0] == "table"]
            inserts = [o[1] for o in sb.ops if o[0] == "insert"]
            assert "processing_status" in tables
            assert len(inserts) > 0

    def test_updates_existing_record(self, orch):
        sb = MockSupabase(existing_data=[{"id": 1}])
        with (
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch("app.routers.v1.stream.emit_event"),
        ):
            orch._update_status("doc-1", "parsing", "COMPLETED", "Done")
            ops = [o[0] for o in sb.ops]
            assert "update" in ops
            assert "insert" not in ops

    def test_sets_completed_status_on_persistence(self, orch):
        sb = MockSupabase(existing_data=[])
        with (
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch("app.routers.v1.stream.emit_event"),
        ):
            orch._update_status("doc-1", "PERSISTENCE", "COMPLETED", "All done")
            updates = [o[1] for o in sb.ops if o[0] == "update"]
            has_completed = any(d.get("status") == "COMPLETED" for d in updates if isinstance(d, dict))
            assert has_completed

    def test_sets_failed_status(self, orch):
        sb = MockSupabase(existing_data=[])
        with (
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch("app.routers.v1.stream.emit_event"),
        ):
            orch._update_status("doc-1", "parsing", "FAILED", "Error")
            updates = [o[1] for o in sb.ops if o[0] == "update"]
            has_error_msg = any("error_message" in d for d in updates if isinstance(d, dict))
            assert has_error_msg

    def test_with_progress(self, orch):
        sb = MockSupabase(existing_data=[])
        with (
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch("app.routers.v1.stream.emit_event"),
        ):
            orch._update_status("doc-1", "parsing", "PROCESSING", progress=50)
            updates = [o[1] for o in sb.ops if o[0] == "update"]
            has_progress = any("progress" in d for d in updates if isinstance(d, dict))
            assert has_progress

    def test_emit_event_called(self, orch):
        sb = MockSupabase(existing_data=[])
        with (
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch("app.routers.v1.stream.emit_event") as mock_emit,
        ):
            orch._update_status("doc-1", "parsing", "COMPLETED", "Done", progress=100)
            mock_emit.assert_called_once()

    def test_exception_during_update_logged(self, orch):
        sb = MagicMock()
        sb.table.side_effect = Exception("DB down")
        with (
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch("app.routers.v1.stream.emit_event"),
        ):
            orch._update_status("doc-1", "parsing", "COMPLETED")

    def test_transient_error_retry(self, orch):
        call_count = [0]

        class RetrySB:
            def table(self, name):
                return self

            def select(self, *a):
                return self

            def update(self, d):
                return self

            def insert(self, d):
                return self

            def match(self, filters):
                return self

            def eq(self, c, v):
                return self

            def execute(self):
                call_count[0] += 1
                if call_count[0] == 1:
                    raise Exception("RemoteProtocolError: server disconnected")
                return MagicMock(data=[])

        with (
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=RetrySB()),
            patch("app.routers.v1.stream.emit_event"),
        ):
            orch._update_status("doc-1", "parsing", "COMPLETED", "Done")
            assert call_count[0] >= 2


class TestCheckCancelled:
    @pytest.fixture
    def orch(self):
        return _make_orchestrator()

    def test_not_cancelled_returns_none(self, orch):
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=MagicMock()):
            with patch("app.pipeline.orchestrator.orchestrator.DocumentRepository") as mock_repo_cls:
                mock_repo = mock_repo_cls.return_value
                mock_repo._table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"status": "PROCESSING"}])
                result = orch._check_cancelled("job-1")
                assert result is None

    def test_cancelled_raises(self, orch):
        import asyncio
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=MagicMock()):
            with patch("app.pipeline.orchestrator.orchestrator.DocumentRepository") as mock_repo_cls:
                mock_repo = mock_repo_cls.return_value
                mock_repo._table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"status": "CANCELLED"}])
                with pytest.raises(asyncio.CancelledError):
                    orch._check_cancelled("job-1")

    def test_no_supabase_returns_none(self, orch):
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=None):
            result = orch._check_cancelled("job-1")
            assert result is None

    def test_exception_handled(self, orch):
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=MagicMock()):
            with patch("app.pipeline.orchestrator.orchestrator.DocumentRepository") as mock_repo_cls:
                mock_repo = mock_repo_cls.return_value
                mock_repo._table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("DB error")
                result = orch._check_cancelled("job-1")
                assert result is None


class TestPersistPartialResult:
    @pytest.fixture
    def orch(self):
        return _make_orchestrator()

    def test_no_sb_returns(self, orch):
        orch._persist_partial_result("job-1", MagicMock(), None)

    def test_no_doc_returns(self, orch):
        orch._persist_partial_result("job-1", None, MagicMock())

    def test_persists_to_new_record(self, orch):
        with patch("app.pipeline.orchestrator.orchestrator.DocumentResultRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo._table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            with patch("app.pipeline.orchestrator.build_structured_data", return_value={}):
                orch._persist_partial_result("job-1", MagicMock(), MagicMock())
            mock_repo.insert_sync.assert_called_once()

    def test_persists_to_existing_record(self, orch):
        with patch("app.pipeline.orchestrator.orchestrator.DocumentResultRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo._table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": 1}])
            with patch("app.pipeline.orchestrator.build_structured_data", return_value={}):
                orch._persist_partial_result("job-1", MagicMock(), MagicMock())
            mock_repo.upsert_sync.assert_called_once()

    def test_exception_swallowed(self, orch):
        sb = MagicMock()
        sb.table.side_effect = Exception("fail")
        orch._persist_partial_result("job-1", MagicMock(), sb)


class TestRunWithTimeout:
    @pytest.fixture
    def orch(self):
        return _make_orchestrator()

    def test_function_completes(self, orch):
        def fast():
            return 42

        result = orch._run_with_timeout(fast, 5)
        assert result == 42

    def test_function_with_args(self, orch):
        result = orch._run_with_timeout(lambda a, b: a + b, 5, 2, 3)
        assert result == 5

    def test_function_times_out(self, orch):
        def slow():
            time.sleep(10)
            return "done"

        with pytest.raises(TimeoutError, match="timed out"):
            orch._run_with_timeout(slow, 1)

    def test_function_raises(self, orch):
        def crash():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            orch._run_with_timeout(crash, 5)

    def test_cancel_event_set_on_timeout(self, orch):
        evt = threading.Event()
        assert not evt.is_set()

        def slow():
            time.sleep(10)
            return "done"

        with pytest.raises(TimeoutError):
            orch._run_with_timeout(slow, 1, cancel_event=evt)
        assert evt.is_set()


class TestStageRecordingIntegration:
    @pytest.fixture
    def orch(self):
        return _make_orchestrator()

    def test_full_stage_lifecycle(self, orch):
        with patch("app.middleware.prometheus_metrics.MetricsManager.record_pipeline_stage_duration"):
            orch._record_stage_transition("doc-1", "parsing", "PROCESSING")
            assert ("doc-1", "PARSING") in orch._stage_start_times
            orch._record_stage_transition("doc-1", "parsing", "COMPLETED")
            assert ("doc-1", "PARSING") not in orch._stage_start_times

    def test_multiple_stages_tracked(self, orch):
        with patch("app.middleware.prometheus_metrics.MetricsManager.record_pipeline_stage_duration"):
            orch._record_stage_transition("doc-1", "parsing", "PROCESSING")
            orch._record_stage_transition("doc-1", "formatting", "PROCESSING")
            assert len(orch._stage_start_times) == 2

    def test_multiple_documents_isolated(self, orch):
        with patch("app.middleware.prometheus_metrics.MetricsManager.record_pipeline_stage_duration"):
            orch._record_stage_transition("doc-1", "parsing", "PROCESSING")
            orch._record_stage_transition("doc-2", "parsing", "PROCESSING")
            assert len(orch._stage_start_times) == 2


class TestUpdateStatusEdgeCases:
    @pytest.fixture
    def orch(self):
        return _make_orchestrator()

    def test_document_id_coerced(self, orch):
        sb = MockSupabase(existing_data=[])
        with (
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch("app.routers.v1.stream.emit_event"),
        ):
            orch._update_status(123, "parsing", "COMPLETED")

    def test_phase_null_handled(self, orch):
        sb = MockSupabase(existing_data=[])
        with (
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch("app.routers.v1.stream.emit_event"),
        ):
            orch._update_status("doc-1", None, "COMPLETED")


def teardown_module():
    import shutil

    for d in ["temp_test_orch", "temp_test_failures", "temp_test_timeout", "temp_test_concurrent", "temp_test_cancel"]:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
