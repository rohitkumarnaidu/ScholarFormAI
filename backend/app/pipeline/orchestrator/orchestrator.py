# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Pipeline Orchestrator — Coordinates all processing stages.

This module has been refactored from a 1350-line god class into a slim
coordination layer. Stage implementation details live in stages.py.
"""

import asyncio
import contextlib
import os
import threading
import time
from datetime import UTC
from typing import Any

from app.config.settings import settings
from app.models import Block, BlockType, PipelineDocument
from app.pipeline.orchestrator.events import StageEventEmitter
from app.pipeline.orchestrator.metrics import StageMetrics
from app.pipeline.orchestrator.phases import PipelinePhases
from app.pipeline.orchestrator.stages import PipelineStages


class _PackageLoggerProxy:
    """Forwards all logging calls to app.pipeline.orchestrator.logger at call time.
    This ensures test patches to that name are picked up dynamically."""

    def __getattr__(self, name):
        from app.pipeline.orchestrator import logger as _l

        return getattr(_l, name)


logger = _PackageLoggerProxy()

_MAX_CONCURRENT_JOBS = 5
_pipeline_semaphore = threading.Semaphore(_MAX_CONCURRENT_JOBS)
_ACQUIRE_TIMEOUT_SECONDS = float(settings.PIPELINE_ACQUIRE_TIMEOUT_SECONDS)


# -- Lazy resolvers (kept for backward compat with test patches) ----------


def get_rag_engine():
    from app.utils.singleton import resolve_optional_callable

    return resolve_optional_callable(
        "app.pipeline.intelligence.rag_engine",
        "get_rag_engine",
    )


def get_reasoning_engine():
    from app.utils.singleton import resolve_optional_callable

    return resolve_optional_callable(
        "app.pipeline.intelligence.reasoning_engine",
        "get_reasoning_engine",
    )


class PipelineOrchestrator:
    """
    Coordinates the full document processing pipeline from input file to
    final output. Stage implementations are delegated to PipelineStages.
    """

    def __init__(self, templates_dir: str = "app/templates", temp_dir: str | None = None):
        self.templates_dir = templates_dir
        self.temp_dir = temp_dir or "temp"
        os.makedirs(self.temp_dir, exist_ok=True)

        # Core services
        from app.pipeline.orchestrator import InputConverter

        self.converter = InputConverter()
        from app.pipeline.orchestrator import ContentAnalyzer

        self.analyzer = ContentAnalyzer()
        contracts_base = os.path.dirname(templates_dir)
        self.contracts_dir = os.path.join(contracts_base, "pipeline", "contracts")
        from app.pipeline.orchestrator import ContractLoader

        self.contract_loader = ContractLoader(contracts_dir=self.contracts_dir)
        from app.pipeline.orchestrator import ReferenceFormatterEngine

        self.ref_normalizer = ReferenceFormatterEngine(self.contract_loader)

        # External service clients
        from app.pipeline.orchestrator import GROBIDClient

        self.grobid_client = GROBIDClient()

        # Stage engine — all stage implementations delegated here
        self.stages = PipelineStages(
            templates_dir=self.templates_dir,
            temp_dir=self.temp_dir,
            contracts_dir=self.contracts_dir,
            converter=self.converter,
            grobid_client=self.grobid_client,
            run_with_timeout_fn=self._run_with_timeout,
        )

        # Metrics & events
        self.metrics = StageMetrics()
        self.events = StageEventEmitter()

        self._stage_start_times: dict[tuple[str, str], float] = {}

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    def run_pipeline(
        self,
        input_path: str,
        job_id: str,
        template_name: str | None = "IEEE",
        formatting_options: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Execute full pipeline sequentially. Acquires semaphore first."""
        from app.pipeline.orchestrator import _ACQUIRE_TIMEOUT_SECONDS, _pipeline_semaphore

        if not _pipeline_semaphore.acquire(timeout=_ACQUIRE_TIMEOUT_SECONDS):
            logger.warning("Semaphore full. Job %s rejected.", job_id)
            self._update_status(job_id, "SYSTEM", "FAILED", "Server is busy.")
            return {"status": "failed", "reason": "Server is busy"}
        try:
            return self._run_pipeline_internal(input_path, job_id, template_name, formatting_options)
        finally:
            _pipeline_semaphore.release()

    # ------------------------------------------------------------------ #
    #  Internal pipeline (the orchestration flow)                         #
    # ------------------------------------------------------------------ #

    def _run_pipeline_internal(
        self,
        input_path: str,
        job_id: str,
        template_name: str | None = "IEEE",
        formatting_options: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Orchestrate all pipeline stages sequentially."""
        logger.debug("_run_pipeline_internal started template='%s' options=%s", template_name, formatting_options)

        if formatting_options is None:
            formatting_options = {}
        runtime_flags = self._resolve_runtime_flags(formatting_options)
        formatting_options = {**formatting_options, **runtime_flags}
        logger.info(
            "Pipeline runtime flags job=%s fast=%s semantic=%s crossref=%s ai=%s",
            job_id,
            runtime_flags["fast_mode"],
            runtime_flags["semantic_parser"],
            runtime_flags["crossref_enrichment"],
            runtime_flags["ai_reasoning"],
        )

        job_id = str(job_id)
        response = {"status": "processing", "job_id": job_id, "message": ""}
        sb = None
        output_path = None
        doc_obj = None

        try:
            with self._safety_net(f"Pipeline Job {job_id}"):
                from app.pipeline.orchestrator import get_supabase_client

                sb = get_supabase_client()

                phases = PipelinePhases(self)

                # ---- Phase 1: Upload ----
                phases.phase_upload(job_id)

                # ---- Phase 2: Extraction ----
                from app.pipeline.orchestrator import ParserFactory

                factory = ParserFactory()
                file_ext = os.path.splitext(input_path)[1].lower()
                doc_obj = phases.phase_extraction(
                    factory, input_path, job_id, formatting_options, file_ext, sb, template_name
                )

                # ---- Phase 3: Structure Detection ----
                doc_obj = phases.phase_structure_detection(doc_obj, job_id)

                # ---- Phase 4: Semantic Parsing (optional) ----
                if runtime_flags["semantic_parser"]:
                    doc_obj = phases.phase_semantic_parsing(doc_obj)
                else:
                    logger.info("Fast mode: skipping semantic parser.")

                # ---- Phase 5: Classification ----
                doc_obj = phases.phase_classification(doc_obj, job_id)

                # ---- Phase 6: Content Analysis ----
                doc_obj = phases.phase_content_analysis(doc_obj, job_id, runtime_flags)

                # ---- Phase 7: Validation ----
                doc_obj, validation_results = phases.phase_validation(doc_obj, job_id, template_name, runtime_flags)

                # ---- Phase 8: Formatting ----
                doc_obj = phases.phase_formatting(doc_obj)

                # ---- Phase 9: Export ----
                output_path = phases.phase_export(doc_obj, input_path, job_id, sb)

                # ---- Phase 10: Persistence ----
                response = phases.phase_persistence(doc_obj, job_id, sb, output_path, validation_results, template_name)

        except asyncio.CancelledError:
            logger.info("Task %s cancelled by server reload/shutdown.", job_id)
            try:
                self._update_status(job_id, "SYSTEM", "FAILED", "Interrupted by server shutdown", progress=0)
                if sb:
                    sb.table("documents").update(
                        {
                            "status": "FAILED",
                            "error_message": "Interrupted by server shutdown",
                        }
                    ).eq("id", job_id).execute()
            except Exception:
                pass  # intentionally ignored
            return {"status": "cancelled", "message": "Interrupted by server shutdown"}

        except Exception as e:
            import traceback

            error_msg = str(e)
            logger.error("Pipeline Error: %s", error_msg)
            if doc_obj is not None:
                try:
                    self._persist_partial_result(job_id, doc_obj, sb)
                except Exception as persist_err:
                    logger.error("Failed to persist partial result: %s", persist_err)
            if output_path and os.path.exists(output_path):
                logger.warning("Non-fatal error: %s", error_msg)
                try:
                    from app.services.document_service import DocumentService

                    DocumentService.update_output_hash(job_id, PipelineStages.compute_sha256(output_path))
                except Exception:
                    pass  # intentionally ignored
                self._update_status(job_id, "PERSISTENCE", "COMPLETED", "Completed with warnings.", progress=100)
                if sb:
                    sb.table("documents").update(
                        {
                            "status": "COMPLETED_WITH_WARNINGS",
                            "error_message": f"Validation Warning: {error_msg}",
                            "output_path": output_path,
                        }
                    ).eq("id", job_id).execute()
                response["status"] = "success"
            else:
                self._update_status(job_id, "PERSISTENCE", "FAILED", error_msg, progress=0)
                if sb:
                    sb.table("documents").update(
                        {
                            "status": "FAILED",
                            "error_message": error_msg,
                        }
                    ).eq("id", job_id).execute()
                response["status"] = "error"
                response["message"] = f"Pipeline failed: {error_msg}"
            logger.error("Pipeline Error Traceback: %s", traceback.format_exc())

        return response

    # ------------------------------------------------------------------ #
    #  Edit Flow                                                          #
    # ------------------------------------------------------------------ #

    def run_edit_flow(
        self,
        job_id: str,
        edited_structured_data: dict[str, Any],
        template_name: str = "IEEE",
    ) -> dict[str, Any]:
        """Re-run validation and formatting on edited data."""
        job_id = str(job_id)
        try:
            from app.pipeline.orchestrator import get_supabase_client

            sb = get_supabase_client()
            if not sb:
                raise Exception("Supabase client unavailable.")

            doc_query = sb.table("documents").select("filename, output_path").eq("id", job_id).execute()
            if not doc_query.data:
                raise Exception("Original document not found")
            filename = doc_query.data[0]["filename"]
            source_output_path = doc_query.data[0]["output_path"]

            pipeline_doc = PipelineDocument(document_id=job_id)
            sections = edited_structured_data.get("sections", {})
            known_block_types = {m.value for m in BlockType}
            for sec_name, texts in sections.items():
                for idx, text in enumerate(texts):
                    block = Block(
                        block_id=f"edit_{idx}",
                        index=idx,
                        text=text,
                        block_type=BlockType(sec_name) if sec_name in known_block_types else BlockType.UNKNOWN,
                    )
                    pipeline_doc.blocks.append(block)

            self._update_status(job_id, "VALIDATION", "PROCESSING", "Re-validating...", progress=30)
            from app.pipeline.orchestrator import safe_model_dump, validate_document

            val_result = validate_document(pipeline_doc)
            validation_results = safe_model_dump(val_result)

            self._update_status(job_id, "VALIDATION", "PROCESSING", "Applying styles...", progress=60)
            from app.pipeline.orchestrator import Formatter

            formatted_doc = Formatter(templates_dir=self.templates_dir, contracts_dir=self.contracts_dir).process(
                pipeline_doc
            )

            output_path = None
            if formatted_doc:
                from app.pipeline.orchestrator import Exporter

                out_dir = os.path.join("output", f"{job_id}_edit")
                os.makedirs(out_dir, exist_ok=True)
                out_name = f"{os.path.splitext(filename)[0]}_edited.docx"
                output_path = os.path.abspath(os.path.join(out_dir, out_name))
                pipeline_doc.output_path = output_path
                Exporter().process(pipeline_doc)
                try:
                    from app.services.document_service import DocumentService

                    DocumentService.update_output_hash(job_id, PipelineStages.compute_sha256(output_path))
                except Exception:
                    pass  # intentionally ignored

            existing = sb.table("document_results").select("*").eq("document_id", job_id).execute()
            if existing.data:
                versions = (
                    sb.table("document_versions")
                    .select("version_number")
                    .eq("document_id", job_id)
                    .order("version_number", desc=True)
                    .limit(1)
                    .execute()
                )
                if versions.data:
                    try:
                        last_num = int(versions.data[0]["version_number"].replace("v", ""))
                        next_version = f"v{last_num + 1}"
                    except Exception:
                        from datetime import datetime

                        next_version = f"v_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
                else:
                    next_version = "v1"
                sb.table("document_versions").insert(
                    {
                        "document_id": job_id,
                        "version_number": next_version,
                        "edited_structured_data": existing.data[0]["structured_data"],
                        "output_path": source_output_path,
                        "created_at": "now()",
                    }
                ).execute()
                sb.table("document_results").update(
                    {
                        "structured_data": edited_structured_data,
                        "validation_results": validation_results,
                        "updated_at": "now()",
                    }
                ).eq("document_id", job_id).execute()
            else:
                from app.pipeline.orchestrator import AIExplainer

                explainer = AIExplainer()
                ai_explanations = explainer.explain_results(validation_results, template_name)
                validation_results["ai_explanations"] = ai_explanations
                sb.table("document_results").insert(
                    {
                        "document_id": job_id,
                        "structured_data": edited_structured_data,
                        "validation_results": validation_results,
                        "created_at": "now()",
                    }
                ).execute()

            sb.table("documents").update(
                {
                    "output_path": output_path,
                    "updated_at": "now()",
                }
            ).eq("id", job_id).execute()

            self._update_status(job_id, "PERSISTENCE", "COMPLETED", "Edit re-formatted.", progress=100)
            return {"status": "success", "output_path": output_path}

        except asyncio.CancelledError:
            logger.info("Edit flow %s cancelled by shutdown.", job_id)
            with contextlib.suppress(Exception):
                self._update_status(job_id, "SYSTEM", "FAILED", "Edit interrupted by shutdown", progress=0)
            return {"status": "cancelled", "message": "Edit interrupted by shutdown"}
        except Exception as e:
            logger.error("Edit flow error: %s", e)
            self._update_status(job_id, "PERSISTENCE", "FAILED", str(e), progress=0)
            return {"status": "error", "message": str(e)}

    # ------------------------------------------------------------------ #
    #  Status updates, cancellation, and persistence                      #
    # ------------------------------------------------------------------ #

    def _update_status(self, document_id, phase, status, message=None, progress: int | None = None):
        """Update processing status in Supabase and emit SSE event."""
        document_id = str(document_id)
        self._record_stage_transition(document_id, phase, status)
        from app.pipeline.orchestrator import get_supabase_client

        sb = get_supabase_client()
        if not sb:
            logger.warning("Supabase unavailable for status: %s -> %s", phase, status)
            return
        try:

            def _is_transient(exc: Exception) -> bool:
                text = str(exc).lower()
                return any(
                    kw in text
                    for kw in (
                        "remoteprotocolerror",
                        "server disconnected",
                        "timeout",
                        "connection reset",
                        "connection aborted",
                    )
                )

            def _run_with_retry(op_name, callback, _sb=None):
                nonlocal sb
                if _sb is not None:
                    sb = _sb
                for attempt in range(1, 4):
                    try:
                        return callback()
                    except Exception as exc:
                        retryable = _is_transient(exc) and attempt < 3
                        if not retryable:
                            raise
                        import time as _time

                        _time.sleep(0.15 * (2 ** (attempt - 1)))
                        refreshed = get_supabase_client(refresh=True)
                        if refreshed:
                            sb = refreshed

            from app.routers.v1.stream import emit_event

            data = {
                "document_id": document_id,
                "phase": phase,
                "status": status,
                "message": message,
                "progress_percentage": progress,
                "updated_at": "now()",
            }
            existing = _run_with_retry(
                "select",
                lambda: (
                    sb.table("processing_status")
                    .select("id")
                    .match({"document_id": document_id, "phase": phase})
                    .execute()
                ),
            )
            if existing.data:
                _run_with_retry(
                    "update",
                    lambda: (
                        sb.table("processing_status")
                        .update(data)
                        .match({"document_id": document_id, "phase": phase})
                        .execute()
                    ),
                )
            else:
                _run_with_retry("insert", lambda: sb.table("processing_status").insert(data).execute())

            doc_data = {"current_stage": phase, "updated_at": "now()"}
            if status == "COMPLETED":
                doc_data["status"] = "COMPLETED" if phase == "PERSISTENCE" else "PROCESSING"
            elif status == "FAILED":
                doc_data["status"] = "FAILED"
                doc_data["error_message"] = message
            else:
                doc_data["status"] = status
            if progress is not None:
                doc_data["progress"] = progress
            _run_with_retry(
                "doc_update", lambda: sb.table("documents").update(doc_data).eq("id", document_id).execute()
            )
            emit_event(
                document_id,
                "status_update",
                {
                    "phase": phase,
                    "status": status,
                    "message": message,
                    "progress": progress,
                },
            )
        except Exception as e:
            logger.error("Status update failed for job %s: %s", document_id, e)

    def _check_cancelled(self, job_id: str):
        try:
            from app.pipeline.orchestrator import get_supabase_client

            sb = get_supabase_client()
            if not sb:
                return
            response = sb.table("documents").select("status").eq("id", job_id).execute()
            if response.data and response.data[0].get("status") == "CANCELLED":
                logger.info("Job %s was cancelled by user.", job_id)
                raise asyncio.CancelledError("Job was cancelled by the user")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("Failed to check cancellation for job %s: %s", job_id, e)

    def _persist_partial_result(self, job_id: str, doc_obj: PipelineDocument, sb):
        if not sb or not doc_obj:
            return
        logger.info("Persisting partial results for failed job %s", job_id)
        try:
            from app.pipeline.orchestrator import build_structured_data

            structured_data = build_structured_data(doc_obj, partial=True)
            existing = sb.table("document_results").select("id").eq("document_id", job_id).execute()
            payload = {
                "document_id": job_id,
                "structured_data": structured_data,
                "validation_results": {"is_valid": False, "errors": ["Pipeline crashed early"]},
                "updated_at": "now()",
            }
            if existing.data:
                sb.table("document_results").update(payload).eq("document_id", job_id).execute()
            else:
                payload["created_at"] = "now()"
                sb.table("document_results").insert(payload).execute()
        except Exception as e:
            logger.error("Failed to persist partial result for %s: %s", job_id, e)

    # ------------------------------------------------------------------ #
    #  Utilities                                                          #
    # ------------------------------------------------------------------ #

    def _check_stage_interface(self, stage_instance, method_name, stage_name):
        if not hasattr(stage_instance, method_name):
            raise RuntimeError(
                f"Pipeline Stage Error: '{stage_name}' ({type(stage_instance).__name__}) "
                f"does not implement required method '{method_name}'."
            )

    def _record_stage_transition(self, document_id, phase, status):
        stage_key = (document_id, str(phase or "").upper())
        normalized = str(status or "").upper()
        if normalized == "PROCESSING":
            self._stage_start_times.setdefault(stage_key, time.perf_counter())
            return
        if normalized not in {"COMPLETED", "FAILED"}:
            return
        started_at = self._stage_start_times.pop(stage_key, None)
        if started_at is None:
            return
        try:
            from app.middleware.prometheus_metrics import MetricsManager

            MetricsManager.record_pipeline_stage_duration(stage_key[1].lower(), time.perf_counter() - started_at)
        except Exception:
            pass  # intentionally ignored

    def _run_with_timeout(self, func, timeout_sec, *args, cancel_event=None, **kwargs):
        import concurrent.futures

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout_sec)
        except concurrent.futures.TimeoutError:
            if cancel_event is not None:
                cancel_event.set()
            future.cancel()
            logger.warning("Stage timed out after %ds", timeout_sec)
            raise TimeoutError(f"Stage timed out after {timeout_sec}s")
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    @staticmethod
    def _coerce_bool(value, default=False):
        return PipelineStages.coerce_bool(value, default)

    def _resolve_runtime_flags(self, formatting_options: dict[str, Any] | None) -> dict[str, bool]:
        options = formatting_options or {}
        in_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST"))
        default_fast = bool(getattr(settings, "DEFAULT_FAST_MODE", False))
        if in_pytest or bool(getattr(settings, "LOW_MEMORY_MODE", False)):
            default_fast = True
        fast_mode = self._coerce_bool(options.get("fast_mode"), default_fast)
        return {
            "fast_mode": fast_mode,
            "semantic_parser": self._coerce_bool(options.get("semantic_parser"), not fast_mode),
            "crossref_enrichment": self._coerce_bool(options.get("crossref_enrichment"), not fast_mode),
            "ai_reasoning": self._coerce_bool(options.get("ai_reasoning"), not fast_mode),
        }

    def _sync_block_confidence(self, doc_obj) -> None:
        PipelineStages.sync_block_confidence(doc_obj)

    def _build_quality_summary(self, doc_obj, validation_results):
        confidences = []
        heading_candidates = 0
        for block in getattr(doc_obj, "blocks", []):
            if isinstance(getattr(block, "metadata", None), dict):
                if block.metadata.get("is_heading_candidate"):
                    heading_candidates += 1
                raw = block.metadata.get("classification_confidence") or block.metadata.get("nlp_confidence")
            else:
                raw = getattr(block, "classification_confidence", None)
            try:
                confidences.append(max(0.0, min(1.0, float(raw))))
            except (TypeError, ValueError):
                continue

        block_count = len(getattr(doc_obj, "blocks", []))
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        low_conf = sum(1 for c in confidences if c < 0.60)
        err_count = len(validation_results.get("errors", []) or [])
        warn_count = len(validation_results.get("warnings", []) or [])
        struct_score = 1.0 if heading_candidates > 0 else 0.45
        asset_score = 1.0 if (doc_obj.figures or doc_obj.tables) else 0.65
        penalty = min(0.65, (err_count * 0.06) + (warn_count * 0.01) + (low_conf * 0.015))
        quality_ratio = max(0.0, min(1.0, (avg_conf * 0.60) + (struct_score * 0.25) + (asset_score * 0.15) - penalty))
        quality_score = round(quality_ratio * 100, 2)

        from app.pipeline.orchestrator import build_structured_data, compute_quality_score

        structured_data = build_structured_data(doc_obj, partial=True)
        template_name = (
            doc_obj.template.template_name
            if getattr(doc_obj, "template", None) and getattr(doc_obj.template, "template_name", None)
            else "default"
        )

        quality_metrics = compute_quality_score(structured_data, template_name, validation_results)

        return {
            "quality_score": quality_metrics.get("overall_score", quality_score),
            "pipeline_quality_score": quality_score,
            "avg_confidence": round(avg_conf, 4),
            "min_confidence": round(min(confidences), 4) if confidences else 0.0,
            "block_count": block_count,
            "heading_candidates": heading_candidates,
            "figures": len(getattr(doc_obj, "figures", [])),
            "tables": len(getattr(doc_obj, "tables", [])),
            "errors": err_count,
            "warnings": warn_count,
            "low_conf_blocks": low_conf,
            "review_status": getattr(getattr(doc_obj, "review", None), "status", "N/A"),
            **quality_metrics,
        }

    def _log_quality_summary(self, job_id, summary):
        logger.info(
            "PIPELINE SCORE | job=%s | quality=%.2f%% | avg_conf=%.2f | min_conf=%.2f | "
            "headings=%d | blocks=%d | figures=%d | tables=%d | errors=%d | warnings=%d | review=%s",
            job_id,
            summary.get("quality_score", 0),
            summary.get("avg_confidence", 0),
            summary.get("min_confidence", 0),
            summary.get("heading_candidates", 0),
            summary.get("block_count", 0),
            summary.get("figures", 0),
            summary.get("tables", 0),
            summary.get("errors", 0),
            summary.get("warnings", 0),
            summary.get("review_status", "N/A"),
        )
        logger.info("Pipeline quality summary for job %s: %s", job_id, summary)

    @staticmethod
    def _extract_pymupdf_fallback_metadata(input_path: str) -> dict[str, Any]:
        return PipelineStages.extract_pymupdf_fallback_metadata(input_path)

    @staticmethod
    def _compute_sha256(filepath: str) -> str:
        return PipelineStages.compute_sha256(filepath)

    # ------------------------------------------------------------------ #
    #  Backward-compatible private method wrappers                        #
    #  These delegate to PipelineStages for code that calls the old       #
    #  private method names directly.                                     #
    # ------------------------------------------------------------------ #

    def _run_extraction_stage(self, factory, input_path, job_id, formatting_options, file_ext):
        return self.stages.extract_parse_content(factory, input_path, job_id, formatting_options, file_ext)

    def _run_structure_detection(self, doc_obj):
        return self.stages.detect_structure(doc_obj)

    def _run_semantic_parsing(self, doc_obj):
        return self.stages.run_semantic_parsing(doc_obj)

    def _run_classification(self, doc_obj):
        return self.stages.run_classification(doc_obj)

    def _run_validation_stage(self, doc_obj):
        return self.stages.run_validation(doc_obj)

    def _run_figure_analysis_stage(self, doc_obj):
        return self.stages.run_figure_analysis(doc_obj)

    def _run_formatting_stage(self, doc_obj):
        return self.stages.run_formatting(doc_obj)

    def _export_document(self, doc_obj, input_path, job_id):
        from app.pipeline.orchestrator import Exporter

        self._check_stage_interface(Exporter(), "process", "Exporter")
        return self.stages.export_document(doc_obj, input_path, job_id)

    # ------------------------------------------------------------------ #
    #  Context manager helpers                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _safety_net(label: str):
        from app.pipeline.safety import safe_execution

        return safe_execution(label)
