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
    },
    "purge-expired-vector-sessions-hourly": {
        "task": "batch.purge_expired_vector_sessions",
        "schedule": crontab(minute=0),
    },
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
    try:
        doc_row = asyncio.run(DocumentService.get_document(document_id))
    except Exception:
        logger.error("process_document_task: Document %s not found or DB unavailable.", document_id)
        return False
    if doc_row is None:
        logger.error("process_document_task: Document %s not found or DB unavailable.", document_id)
        return False

    try:
        # ── Mark as PROCESSING ────────────────────────────────────────────────────
        asyncio.run(
            DocumentService.update_document(
                document_id,
                {
                    "status": "PROCESSING",
                    "progress": 10,
                    "current_stage": "Initializing agent orchestration...",
                },
            )
        )

        # ── Run pipeline ───────────────────────────────────────────────────────
        orchestrator = PipelineOrchestrator()
        start_time = time.time()
        orchestrator.run_pipeline(input_path=doc_row["original_file_path"], job_id=document_id)
        processing_time = time.time() - start_time

        # ── Mark as COMPLETED ──────────────────────────────────────────────────
        asyncio.run(
            DocumentService.update_document(
                document_id,
                {
                    "status": "COMPLETED",
                    "progress": 100,
                    "current_stage": f"Processing complete in {processing_time:.1f}s",
                },
            )
        )

        logger.info("Document %s processed successfully in %.1fs", document_id, processing_time)
        return True

    except Exception as exc:
        logger.error("Async processing failed for %s: %s", document_id, exc, exc_info=True)
        # Mark as FAILED — never raises
        try:
            asyncio.run(DocumentService.mark_document_failed(document_id, str(exc)))
        except Exception:
            pass
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


@celery_app.task(name="batch.purge_expired_vector_sessions")
def purge_expired_vector_sessions():
    """
    Batch queue task: Purge expired vector store sessions from ChromaDB
    when their Redis TTL key (vector_session:{session_id}:ttl) is missing or expired.
    Falls back gracefully when Redis or ChromaDB is absent/disabled.
    """
    try:
        from app.services.session_vector_store import SessionVectorStore
        from app.cache.redis_cache import redis_cache

        r_client = redis_cache.client
        if not r_client:
            logger.info("purge_expired_vector_sessions: Redis unavailable or disabled. Skipping Redis-based purge.")
            return {"purged_collections": 0, "status": "redis_unavailable"}

        store = SessionVectorStore()
        chroma = store._load_chroma()
        if not chroma:
            logger.warning("purge_expired_vector_sessions: chromadb unavailable. Skipping purge.")
            return {"purged_collections": 0, "status": "chromadb_unavailable"}

        try:
            client = store._get_client()
            collections = client.list_collections()
        except Exception as exc:
            logger.warning("purge_expired_vector_sessions: Failed listing ChromaDB collections: %s", exc)
            return {"purged_collections": 0, "status": "error", "detail": str(exc)}

        purged_count = 0
        for col in collections:
            col_name = getattr(col, "name", str(col))
            if not col_name.startswith("session_"):
                continue

            session_id = col_name[len("session_") :]
            redis_key = f"vector_session:{session_id}:ttl"

            try:
                if not r_client.exists(redis_key):
                    store.delete_collection(session_id)
                    purged_count += 1
                    logger.info("purge_expired_vector_sessions: Purged expired vector store collection: %s", col_name)
            except Exception as exc:
                logger.warning("purge_expired_vector_sessions: Error checking/purging %s: %s", session_id, exc)

        return {"purged_collections": purged_count, "status": "success"}
    except Exception as exc:
        logger.error("purge_expired_vector_sessions failed: %s", exc, exc_info=True)
        return {"purged_collections": 0, "status": "error", "error": str(exc)}
