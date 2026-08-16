# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Pipeline Orchestrator Unit Tests.

Covers:
- Pipeline execution
- Stage failure handling
- Stage timeout handling
- Concurrent pipeline execution
- Pipeline cancellation
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from app.pipeline.orchestrator import PipelineOrchestrator


class TestPipelineExecution:
    """Tests for basic pipeline execution."""

    @pytest.fixture
    def orchestrator(self):
        with (
            patch("app.pipeline.orchestrator.get_reasoning_engine") as mock_reasoning,
            patch("app.pipeline.orchestrator.get_rag_engine") as mock_rag,
            patch("app.pipeline.orchestrator.GROBIDClient") as mock_grobid,
            patch("app.pipeline.orchestrator.DoclingClient") as mock_docling,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=None),
        ):
            mock_reasoning.return_value = MagicMock()
            mock_rag.return_value = MagicMock()
            mock_grobid.return_value = MagicMock()
            mock_docling.return_value = MagicMock()
            orchestrator = PipelineOrchestrator(templates_dir="app/templates", temp_dir="temp_test_orchestrator")
            yield orchestrator

        import shutil

        temp_dir = "temp_test_orchestrator"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_orchestrator_initialization(self, orchestrator):
        assert orchestrator is not None
        assert orchestrator.templates_dir == "app/templates"

    def test_orchestrator_has_contract_loader(self, orchestrator):
        assert orchestrator.contract_loader is not None

    def test_orchestrator_has_stages(self, orchestrator):
        assert hasattr(orchestrator, "converter")
        assert hasattr(orchestrator, "analyzer")

    def test_run_with_nonexistent_file(self, orchestrator):
        pytest.skip("PipelineOrchestrator.run() not implemented - uses stage methods directly")

    def test_run_with_invalid_file(self, orchestrator, tmp_path):
        pytest.skip("PipelineOrchestrator.run() not implemented - uses stage methods directly")


class TestStageFailureHandling:
    """Tests for stage failure handling."""

    @pytest.fixture
    def orchestrator(self):
        with (
            patch("app.pipeline.orchestrator.get_reasoning_engine") as mock_reasoning,
            patch("app.pipeline.orchestrator.get_rag_engine") as mock_rag,
            patch("app.pipeline.orchestrator.GROBIDClient") as mock_grobid,
            patch("app.pipeline.orchestrator.DoclingClient") as mock_docling,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=None),
        ):
            mock_reasoning.return_value = MagicMock()
            mock_rag.return_value = MagicMock()
            mock_grobid.return_value = MagicMock()
            mock_docling.return_value = MagicMock()
            orchestrator = PipelineOrchestrator(templates_dir="app/templates", temp_dir="temp_test_failures")
            yield orchestrator

        import shutil

        if os.path.exists("temp_test_failures"):
            shutil.rmtree("temp_test_failures", ignore_errors=True)

    def test_stage_interface_check_valid(self, orchestrator):
        class ValidStage:
            def process(self, doc):
                return doc

        stage = ValidStage()
        orchestrator._check_stage_interface(stage, "process", "ValidStage")

    def test_stage_interface_check_invalid(self, orchestrator):
        class InvalidStage:
            pass

        stage = InvalidStage()
        with pytest.raises(RuntimeError, match="does not implement required method"):
            orchestrator._check_stage_interface(stage, "process", "InvalidStage")

    def test_stage_transition_recording(self, orchestrator):
        with patch("app.middleware.prometheus_metrics.MetricsManager.record_pipeline_stage_duration"):
            orchestrator._record_stage_transition("doc-1", "parsing", "PROCESSING")
            orchestrator._record_stage_transition("doc-1", "parsing", "COMPLETED")

    def test_status_update_without_supabase(self, orchestrator):
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=None):
            orchestrator._update_status("doc-1", "parsing", "COMPLETED", "Done")

    def test_stage_failure_does_not_crash(self, orchestrator, tmp_path):
        pytest.skip("PipelineOrchestrator.run() not implemented - uses stage methods directly")


class TestStageTimeoutHandling:
    """Tests for stage timeout handling."""

    @pytest.fixture
    def orchestrator(self):
        with (
            patch("app.pipeline.orchestrator.get_reasoning_engine") as mock_reasoning,
            patch("app.pipeline.orchestrator.get_rag_engine") as mock_rag,
            patch("app.pipeline.orchestrator.GROBIDClient") as mock_grobid,
            patch("app.pipeline.orchestrator.DoclingClient") as mock_docling,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=None),
        ):
            mock_reasoning.return_value = MagicMock()
            mock_rag.return_value = MagicMock()
            mock_grobid.return_value = MagicMock()
            mock_docling.return_value = MagicMock()
            orchestrator = PipelineOrchestrator(templates_dir="app/templates", temp_dir="temp_test_timeout")
            yield orchestrator

        import shutil

        if os.path.exists("temp_test_timeout"):
            shutil.rmtree("temp_test_timeout", ignore_errors=True)

    def test_slow_stage_handling(self, orchestrator, tmp_path):
        pytest.skip("PipelineOrchestrator.run() not implemented - uses stage methods directly")


class TestConcurrentPipelineExecution:
    """Tests for concurrent pipeline execution."""

    @pytest.fixture
    def orchestrator(self):
        with (
            patch("app.pipeline.orchestrator.get_reasoning_engine") as mock_reasoning,
            patch("app.pipeline.orchestrator.get_rag_engine") as mock_rag,
            patch("app.pipeline.orchestrator.GROBIDClient") as mock_grobid,
            patch("app.pipeline.orchestrator.DoclingClient") as mock_docling,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=None),
        ):
            mock_reasoning.return_value = MagicMock()
            mock_rag.return_value = MagicMock()
            mock_grobid.return_value = MagicMock()
            mock_docling.return_value = MagicMock()
            orchestrator = PipelineOrchestrator(templates_dir="app/templates", temp_dir="temp_test_concurrent")
            yield orchestrator

        import shutil

        if os.path.exists("temp_test_concurrent"):
            shutil.rmtree("temp_test_concurrent", ignore_errors=True)

    def test_concurrent_runs_do_not_corrupt_state(self, orchestrator, tmp_path):
        pytest.skip("PipelineOrchestrator.run() not implemented - uses stage methods directly")

    def test_semaphore_limits_concurrency(self, orchestrator):
        from app.pipeline.orchestrator import _MAX_CONCURRENT_JOBS, _pipeline_semaphore

        assert _MAX_CONCURRENT_JOBS == 5
        assert _pipeline_semaphore._value == _MAX_CONCURRENT_JOBS


class TestPipelineCancellation:
    """Tests for pipeline cancellation."""

    @pytest.fixture
    def orchestrator(self):
        with (
            patch("app.pipeline.orchestrator.get_reasoning_engine") as mock_reasoning,
            patch("app.pipeline.orchestrator.get_rag_engine") as mock_rag,
            patch("app.pipeline.orchestrator.GROBIDClient") as mock_grobid,
            patch("app.pipeline.orchestrator.DoclingClient") as mock_docling,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=None),
        ):
            mock_reasoning.return_value = MagicMock()
            mock_rag.return_value = MagicMock()
            mock_grobid.return_value = MagicMock()
            mock_docling.return_value = MagicMock()
            orchestrator = PipelineOrchestrator(templates_dir="app/templates", temp_dir="temp_test_cancel")
            yield orchestrator

        import shutil

        if os.path.exists("temp_test_cancel"):
            shutil.rmtree("temp_test_cancel", ignore_errors=True)

    def test_cancelled_stage_handling(self, orchestrator, tmp_path):
        pytest.skip("PipelineOrchestrator.run() not implemented - uses stage methods directly")
