# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

# RESERVED: Celery task definitions for future distributed processing.
# Not currently wired into the FastAPI runtime — kept for planned Redis/Celery migration.
import logging
import time
import asyncio
from celery import Celery
from celery.schedules import crontab
from kombu import Queue
from app.pipeline.orchestrator import PipelineOrchestrator
from app.config.settings import settings
from app.services.scibert_gate import persist_scibert_benchmark_result
from app.tasks.cleanup import cleanup_stranded_uploads

# ── Old ORM imports (kept for reference, replaced by DocumentService) ──────────
# from app.db.session import SessionLocal
# from app.models import PipelineDocument

from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)

# Configure Celery
celery_app = Celery(
    "manuscript_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)
celery_app.conf.task_queues = (
    Queue("interactive"),
    Queue("batch"),
)
celery_app.conf.task_routes = {
    "interactive.*": {"queue": "interactive"},
    "batch.*": {"queue": "batch"},
}
celery_app.conf.beat_schedule = {
    "cleanup-stranded-uploads-daily": {
        "task": "batch.cleanup_uploads",
        "schedule": crontab(hour=3, minute=0),
        "kwargs": {"upload_dir": "uploads"},
    }
}


@celery_app.task(name="interactive.process_document_async")
def process_document_task(document_id: str, use_agent: bool = True):
    """
    Asynchronously process a document using the Agent Orchestrator.

    Uses DocumentService (supabase-py) for all DB reads and writes.
    Old ORM equivalent used SessionLocal() + db.query(PipelineDocument).
    """
    logger.info("Starting async processing for document: %s", document_id)

    # ── Fetch document via supabase-py ─────────────────────────────────────────
    doc_row = DocumentService.get_document(document_id)
    if doc_row is None:
        logger.error(
            "process_document_task: Document %s not found or DB unavailable.", document_id
        )
        return False

    try:
        # ── Mark as PROCESSING ────────────────────────────────────────────────────
        DocumentService.update_document(document_id, {
            "status": "PROCESSING",
            "progress": 10,
            "current_stage": "Initializing agent orchestration...",
        })

        # ── Run pipeline ───────────────────────────────────────────────────────
        orchestrator = PipelineOrchestrator()
        start_time = time.time()
        orchestrator.run_pipeline(input_path=doc_row["original_file_path"], job_id=document_id)
        processing_time = time.time() - start_time

        # ── Mark as COMPLETED ──────────────────────────────────────────────────
        DocumentService.update_document(document_id, {
            "status": "COMPLETED",
            "progress": 100,
            "current_stage": f"Processing complete in {processing_time:.1f}s",
        })

        logger.info("Document %s processed successfully in %.1fs", document_id, processing_time)
        return True

    except Exception as exc:
        logger.error("Async processing failed for %s: %s", document_id, exc, exc_info=True)
        # Mark as FAILED — never raises
        DocumentService.mark_document_failed(document_id, str(exc))
        return False


@celery_app.task(name="interactive.process_generation_async")
def process_generation_task(job_id: str):
    """
    Run generate-from-scratch jobs through Celery when enabled.
    """
    logger.info("Starting async generation for job: %s", job_id)
    try:
        from app.pipeline.generation.document_generator import get_generator

        generator = get_generator()
        asyncio.run(generator.run_pipeline(str(job_id)))
        logger.info("Generation job %s completed successfully via Celery", job_id)
        return True
    except Exception as exc:
        logger.error("Generation task failed for %s: %s", job_id, exc, exc_info=True)
        DocumentService.mark_document_failed(str(job_id), str(exc))
        return False


@celery_app.task(name="interactive.process_synthesis_async")
def process_synthesis_task(session_id: str, file_paths: list[str], template: str):
    """
    Run multi-document synthesis through Celery when queue mode is active.
    """
    logger.info("Starting synthesis pipeline for session: %s", session_id)
    try:
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        from app.realtime.pubsub import RedisPubSub
        from app.services.generator_session_service import GeneratorSessionService
        from app.services.session_vector_store import SessionVectorStore

        synthesizer = MultiDocSynthesizer(
            session_service=GeneratorSessionService(),
            vector_store=SessionVectorStore(),
            llm_service=None,
            pipeline_orchestrator=PipelineOrchestrator(),
            pubsub=RedisPubSub(),
        )
        asyncio.run(synthesizer.run(str(session_id), list(file_paths or []), template or settings.DEFAULT_TEMPLATE))
        logger.info("Synthesis session %s completed via Celery", session_id)
        return True
    except Exception as exc:
        logger.error("Synthesis task failed for %s: %s", session_id, exc, exc_info=True)
        return False


@celery_app.task(name="interactive.process_agent_pipeline_async")
def process_agent_pipeline_task(session_id: str, user_prompt: str):
    """
    Run agent-based document generation pipeline via Celery.
    """
    logger.info("Starting agent pipeline for session: %s", session_id)
    try:
        from app.pipeline.generation.agent import AgentPipeline
        from app.services.generator_session_service import GeneratorSessionService
        from app.realtime.pubsub import RedisPubSub

        pipeline = AgentPipeline(
            session_service=GeneratorSessionService(),
            pipeline_orchestrator=PipelineOrchestrator(),
            pubsub=RedisPubSub(),
        )
        asyncio.run(pipeline.run(str(session_id), user_prompt))
        logger.info("Agent pipeline %s completed.", session_id)
        return True
    except Exception as exc:
        logger.error("Agent pipeline failed for %s: %s", session_id, exc, exc_info=True)
        DocumentService.mark_document_failed(str(session_id), str(exc))
        return False


@celery_app.task(name="interactive.process_agent_resume_async")
def process_agent_resume_task(session_id: str):
    """
    Resume agent pipeline after outline approval.
    """
    logger.info("Resuming agent pipeline for session: %s", session_id)
    try:
        from app.pipeline.generation.agent import AgentPipeline
        from app.services.generator_session_service import GeneratorSessionService
        from app.realtime.pubsub import RedisPubSub

        pipeline = AgentPipeline(
            session_service=GeneratorSessionService(),
            pipeline_orchestrator=PipelineOrchestrator(),
            pubsub=RedisPubSub(),
        )
        asyncio.run(pipeline.resume(str(session_id)))
        logger.info("Agent pipeline resume %s completed.", session_id)
        return True
    except Exception as exc:
        logger.error("Agent resume failed for %s: %s", session_id, exc, exc_info=True)
        DocumentService.mark_document_failed(str(session_id), str(exc))
        return False


@celery_app.task(name="interactive.process_agent_rewrite_async")
def process_agent_rewrite_task(session_id: str, section_name: str, instruction: str):
    """
    Rewrite a specific section in an agent-generated document.
    """
    logger.info("Rewriting section %s for session %s", section_name, session_id)
    try:
        from app.pipeline.generation.agent import AgentPipeline
        from app.services.generator_session_service import GeneratorSessionService
        from app.realtime.pubsub import RedisPubSub

        pipeline = AgentPipeline(
            session_service=GeneratorSessionService(),
            pipeline_orchestrator=PipelineOrchestrator(),
            pubsub=RedisPubSub(),
        )
        asyncio.run(pipeline.rewrite_section(str(session_id), section_name, instruction))
        logger.info("Section rewrite completed for %s", session_id)
        return True
    except Exception as exc:
        logger.error("Agent rewrite failed for %s: %s", session_id, exc, exc_info=True)
        DocumentService.mark_document_failed(str(session_id), str(exc))
        return False


@celery_app.task(name="interactive.process_edit_document_async")
def process_edit_document_task(job_id: str, edited_structured_data: dict, template_name: str = "IEEE"):
    """
    Run edit/reformat flow through Celery when enabled.
    """
    logger.info("Starting async edit flow for job: %s", job_id)
    try:
        orchestrator = PipelineOrchestrator()
        result = orchestrator.run_edit_flow(
            job_id=str(job_id),
            edited_structured_data=edited_structured_data or {},
            template_name=template_name or "IEEE",
        )
        ok = isinstance(result, dict) and result.get("status") == "success"
        if ok:
            logger.info("Edit job %s completed successfully via Celery", job_id)
        else:
            logger.warning("Edit job %s finished with non-success result: %s", job_id, result)
        return ok
    except Exception as exc:
        logger.error("Edit task failed for %s: %s", job_id, exc, exc_info=True)
        DocumentService.mark_document_failed(str(job_id), f"Edit flow failed: {exc}")
        return False


@celery_app.task(name="batch.cleanup_uploads")
def cleanup_uploads_task(upload_dir: str = "uploads", retention_days: int | None = None):
    """
    Batch queue task: delete uploads older than retention window.
    """
    result = cleanup_stranded_uploads(upload_dir=upload_dir, retention_days=retention_days)
    return {
        "deleted": int(result.get("deleted_files", 0)),
        "removed_dirs": int(result.get("removed_dirs", 0)),
        "retention_days": int(result.get("retention_days", retention_days or settings.RETENTION_DAYS)),
    }


@celery_app.task(name="batch.scibert_benchmark")
def scibert_benchmark_task(fixtures_dir: str | None = None):
    """
    Batch queue task: run SciBERT benchmark over stored fixtures.
    """
    import json
    from pathlib import Path
    from app.pipeline.intelligence.semantic_parser import SemanticParser
    from app.pipeline.parsing.parser_factory import ParserFactory

    base_dir = Path(fixtures_dir) if fixtures_dir else Path("tests") / "fixtures" / "scibert"
    labels_path = base_dir / "labels.json"
    if not labels_path.exists():
        logger.warning("SciBERT benchmark fixtures not found at %s", labels_path)
        return {"status": "missing_fixtures", "overall_f1": 0.0}

    labels_data = json.loads(labels_path.read_text(encoding="utf-8"))
    parser_factory = ParserFactory()
    semantic_parser = SemanticParser()

    def _macro_f1(y_true, y_pred):
        labels = sorted(set(y_true) | set(y_pred))
        f1s = []
        for label in labels:
            tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
            fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
            fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
            if tp == 0 and fp == 0 and fn == 0:
                continue
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 0.0 if (precision + recall) == 0 else (2 * precision * recall) / (precision + recall)
            f1s.append(f1)
        return sum(f1s) / len(f1s) if f1s else 0.0

    per_paper = {}
    overall_true = []
    overall_pred = []

    for filename, meta in labels_data.items():
        file_path = base_dir / filename
        labels = meta["labels"] if isinstance(meta, dict) else meta
        parser = parser_factory.get_parser(str(file_path))
        if parser is None:
            continue
        document = parser.parse(str(file_path), document_id=filename)
        predictions = semantic_parser.analyze_blocks(document.blocks)
        predicted_labels = [p["predicted_section_type"] for p in predictions]
        if len(predicted_labels) != len(labels):
            logger.warning("Label mismatch for %s (expected %d, got %d)", filename, len(labels), len(predicted_labels))
            continue
        f1 = _macro_f1(labels, predicted_labels)
        per_paper[filename] = f1
        overall_true.extend(labels)
        overall_pred.extend(predicted_labels)

    overall_f1 = _macro_f1(overall_true, overall_pred)
    persist_scibert_benchmark_result(overall_f1, source="celery_batch.scibert_benchmark")
    logger.info("SciBERT benchmark complete. Overall F1=%.4f", overall_f1)
    return {"status": "ok", "overall_f1": overall_f1, "per_paper": per_paper}
