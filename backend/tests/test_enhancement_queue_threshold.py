# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from types import SimpleNamespace

from app.services.enhancement_manager import enhancement_manager


class _BackgroundTasksStub:
    def __init__(self) -> None:
        self.calls = []

    def add_task(self, func, *args, **kwargs):  # noqa: ANN001
        self.calls.append((func, args, kwargs))


def test_dispatch_document_pipeline_queues_only_when_above_threshold(monkeypatch):
    from app.services import enhancement_manager as enhancement_module

    monkeypatch.setattr(enhancement_module.settings, "ENHANCEMENT_QUEUE_MIN_SECONDS", 5, raising=False)
    monkeypatch.setattr(enhancement_manager, "is_celery_queue_active", lambda: True)

    from app.tasks import celery_tasks

    apply_async_calls = []

    def fake_apply_async(*, args, queue):  # noqa: ANN001
        apply_async_calls.append((args, queue))
        return SimpleNamespace(id="task-123")

    monkeypatch.setattr(celery_tasks.process_document_task, "apply_async", fake_apply_async)

    background = _BackgroundTasksStub()
    dispatch = enhancement_manager.dispatch_document_pipeline(
        background_tasks=background,
        orchestrator=SimpleNamespace(),
        input_path="uploads/a.docx",
        job_id="job-1",
        template_name="IEEE",
        formatting_options={},
        estimated_duration_seconds=8.0,
    )
    assert dispatch["mode"] == "celery"
    assert apply_async_calls

    background2 = _BackgroundTasksStub()
    dispatch2 = enhancement_manager.dispatch_document_pipeline(
        background_tasks=background2,
        orchestrator=SimpleNamespace(),
        input_path="uploads/b.docx",
        job_id="job-2",
        template_name="IEEE",
        formatting_options={},
        estimated_duration_seconds=2.0,
    )
    assert dispatch2["mode"] == "background"
    assert len(background2.calls) == 1


def test_dispatch_synthesis_pipeline_respects_threshold(monkeypatch):
    from app.services import enhancement_manager as enhancement_module

    monkeypatch.setattr(enhancement_module.settings, "ENHANCEMENT_QUEUE_MIN_SECONDS", 5, raising=False)
    monkeypatch.setattr(enhancement_manager, "is_celery_queue_active", lambda: True)

    from app.tasks import celery_tasks

    apply_async_calls = []

    def fake_apply_async(*, args, queue):  # noqa: ANN001
        apply_async_calls.append((args, queue))
        return SimpleNamespace(id="synth-123")

    monkeypatch.setattr(celery_tasks.process_synthesis_task, "apply_async", fake_apply_async)

    background = _BackgroundTasksStub()
    dispatch = enhancement_manager.dispatch_synthesis_pipeline(
        background_tasks=background,
        run_pipeline=lambda *_args: None,
        session_id="session-1",
        file_paths=["a.pdf", "b.pdf"],
        template="IEEE",
        estimated_duration_seconds=9.0,
    )
    assert dispatch["mode"] == "celery"
    assert apply_async_calls

    background2 = _BackgroundTasksStub()
    dispatch2 = enhancement_manager.dispatch_synthesis_pipeline(
        background_tasks=background2,
        run_pipeline=lambda *_args: None,
        session_id="session-2",
        file_paths=["a.pdf", "b.pdf"],
        template="IEEE",
        estimated_duration_seconds=3.0,
    )
    assert dispatch2["mode"] == "background"
    assert len(background2.calls) == 1
