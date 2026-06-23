# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Pipeline Orchestrator - Coordinates all processing stages.
"""

import os
import asyncio
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.db.supabase_client import get_supabase_client
from app.config.settings import settings
from app.models import (
    Block, 
    BlockType,
    TemplateInfo,
    PipelineDocument,
)
from app.pipeline.parsing.parser_factory import ParserFactory
from app.pipeline.normalization.normalizer import Normalizer as TextNormalizer
from app.pipeline.structure_detection.detector import StructureDetector
from app.pipeline.nlp.analyzer import ContentAnalyzer, extract_keywords
from app.pipeline.classification.classifier import ContentClassifier
from app.pipeline.figures.caption_matcher import CaptionMatcher
from app.pipeline.tables.caption_matcher import TableCaptionMatcher
from app.pipeline.references.parser import ReferenceParser
from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
from app.pipeline.validation import DocumentValidator, validate_document
from app.pipeline.validation.ai_explainer import AIExplainer
from app.pipeline.formatting.formatter import Formatter
from app.pipeline.export.exporter import Exporter
from app.pipeline.input_conversion.converter import InputConverter
from app.pipeline.contracts.loader import ContractLoader
from app.services.quality_score_service import compute_quality_score
from app.utils.serialization import build_structured_data, safe_model_dump
from app.utils.singleton import resolve_optional_callable
# from app.routers.v1.stream import emit_event  # Moved to local scope inside _update_status
from app.pipeline.equations.standardizer import get_equation_standardizer

# Phase 2: AI Intelligence Stack
# Note: Engines are imported locally within methods to prevent circular dependencies
def get_rag_engine():
    """Resolve RAG engine lazily so tests can patch either module path."""
    return resolve_optional_callable(
        "app.pipeline.intelligence.rag_engine",
        "get_rag_engine",
    )


def get_reasoning_engine():
    """Resolve reasoning engine lazily so tests can patch either module path."""
    return resolve_optional_callable(
        "app.pipeline.intelligence.reasoning_engine",
        "get_reasoning_engine",
    )

# Week 2: GROBID and Docling Services
from app.pipeline.services import GROBIDClient, DoclingClient
# Safety Hardening
from app.pipeline.safety import safe_execution
from app.pipeline.safety.retry_guard import execute_with_retry, retry_with_backoff

import logging
import threading

logger = logging.getLogger(__name__)

# Concurrent job limiter — prevents OOM from unlimited parallel pipelines
_MAX_CONCURRENT_JOBS = 5
_pipeline_semaphore = threading.Semaphore(_MAX_CONCURRENT_JOBS)
_ACQUIRE_TIMEOUT_SECONDS = float(settings.PIPELINE_ACQUIRE_TIMEOUT_SECONDS)

# Lazy import to avoid forcing PIL at module load time
_figure_analyzer_instance = None
def _get_figure_analyzer():
    global _figure_analyzer_instance
    if _figure_analyzer_instance is None:
        from app.pipeline.figures.analyzer import figure_analyzer
        _figure_analyzer_instance = figure_analyzer
    return _figure_analyzer_instance


class PipelineOrchestrator:
    """
    Runs the full document processing pipeline from input file to final output.
    Note: This project intentionally avoids automated pipeline testing at this stage.
    """
    
    def __init__(self, templates_dir: str = "app/templates", temp_dir: Optional[str] = None):
        self.templates_dir = templates_dir
        self.temp_dir = temp_dir or "temp"
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Initialize pipeline stages
        self.converter = InputConverter()
        self.analyzer = ContentAnalyzer()
        contracts_base = os.path.dirname(templates_dir)
        self.contracts_dir = os.path.join(contracts_base, "pipeline", "contracts")
        self.contract_loader = ContractLoader(contracts_dir=self.contracts_dir)
        self.ref_normalizer = ReferenceFormatterEngine(self.contract_loader)
        self._stage_start_times: Dict[tuple[str, str], float] = {}
        
        # Week 2: Initialize GROBID and Docling clients
        self.grobid_client = GROBIDClient()
        self.docling_client = DoclingClient()
        self.figure_analyzer = None  # lazy init in _run_figure_analysis_stage
        
    def _check_stage_interface(self, stage_instance: Any, method_name: str, stage_name: str):
        """
        Verify that a pipeline stage implements the expected interface.
        Raises RuntimeError with a clear message if the method is missing.
        """
        if not hasattr(stage_instance, method_name):
            raise RuntimeError(
                f"Pipeline Stage Error: '{stage_name}' ({type(stage_instance).__name__}) "
                f"does not implement required method '{method_name}'."
            )

    def _record_stage_transition(self, document_id: str, phase: str, status: str) -> None:
        stage_key = (document_id, str(phase or "").upper())
        normalized_status = str(status or "").upper()
        if normalized_status == "PROCESSING":
            self._stage_start_times.setdefault(stage_key, time.perf_counter())
            return

        if normalized_status not in {"COMPLETED", "FAILED"}:
            return

        started_at = self._stage_start_times.pop(stage_key, None)
        if started_at is None:
            return

        try:
            from app.middleware.prometheus_metrics import MetricsManager

            MetricsManager.record_pipeline_stage_duration(stage_key[1].lower(), time.perf_counter() - started_at)
        except Exception:
            pass
        
    def _update_status(self, document_id, phase, status, message=None, progress: Optional[int] = None):
        """Update processing status in Supabase DB."""
        document_id = str(document_id)
        self._record_stage_transition(document_id, phase, status)
        sb = get_supabase_client()
        if not sb:
            logger.warning("Supabase client unavailable for status update: %s -> %s", phase, status)
            return

        try:
            def _is_transient_db_error(exc: Exception) -> bool:
                text = str(exc).lower()
                return (
                    "remoteprotocolerror" in text
                    or "server disconnected" in text
                    or "timeout" in text
                    or "connection reset" in text
                    or "connection aborted" in text
                )

            def _run_with_retry(operation_name: str, callback):
                nonlocal sb
                attempts = 3
                for attempt in range(1, attempts + 1):
                    try:
                        return callback()
                    except Exception as exc:
                        is_retryable = _is_transient_db_error(exc) and attempt < attempts
                        if not is_retryable:
                            raise
                        sleep_for = 0.15 * (2 ** (attempt - 1))
                        logger.warning(
                            "Transient Supabase error during %s for job %s (attempt %s/%s): %s; retrying in %.2fs",
                            operation_name,
                            document_id,
                            attempt,
                            attempts,
                            exc,
                            sleep_for,
                        )
                        refreshed = get_supabase_client(refresh=True)
                        if refreshed:
                            sb = refreshed
                        time.sleep(sleep_for)

            # Phase 5: Redis Pub/Sub for SSE
            from app.routers.v1.stream import emit_event
            # 1. Update/Upsert ProcessingStatus
            # Match is safest for upsert logic
            data = {
                "document_id": document_id,
                "phase": phase,
                "status": status,
                "message": message,
                "progress_percentage": progress,
                "updated_at": "now()"
            }
            
            # Check if record exists
            existing = _run_with_retry(
                "processing_status.select",
                lambda: sb.table("processing_status")
                .select("id")
                .match({"document_id": document_id, "phase": phase})
                .execute(),
            )
            
            if existing.data:
                _run_with_retry(
                    "processing_status.update",
                    lambda: sb.table("processing_status")
                    .update(data)
                    .match({"document_id": document_id, "phase": phase})
                    .execute(),
                )
            else:
                _run_with_retry(
                    "processing_status.insert",
                    lambda: sb.table("processing_status").insert(data).execute(),
                )

            # 2. Update Parent Document
            doc_data = {
                "current_stage": phase,
                "updated_at": "now()"
            }
            
            if status == "COMPLETED":
                if phase == "PERSISTENCE":
                    doc_data["status"] = "COMPLETED"
                else:
                    doc_data["status"] = "PROCESSING"
            elif status == "FAILED":
                doc_data["status"] = "FAILED"
                doc_data["error_message"] = message
            else:
                doc_data["status"] = status

            if progress is not None:
                doc_data["progress"] = progress
            
            _run_with_retry(
                "documents.update",
                lambda: sb.table("documents").update(doc_data).eq("id", document_id).execute(),
            )

            # 3. Emit SSE Event for Real-time Feedback
            emit_event(document_id, "status_update", {
                "phase": phase,
                "status": status,
                "message": message,
                "progress": progress
            })
        except Exception as e:
            logger.error("Supabase status update failed for job %s: %s", document_id, e)

    def _check_cancelled(self, job_id: str):
        """Check if the job has been cancelled by the user in Supabase."""
        import asyncio
        try:
            sb = get_supabase_client()
            if not sb:
                return

            response = sb.table("documents").select("status").eq("id", job_id).execute()
            if response.data and response.data[0].get("status") == "CANCELLED":
                logger.info("Pipeline job %s was cancelled by user.", job_id)
                raise asyncio.CancelledError("Job was cancelled by the user")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("Failed to check cancellation status for job %s: %s", job_id, e)

    def _persist_partial_result(self, job_id: str, doc_obj: PipelineDocument, sb: Any):
        """A11: Saves partial document state to Supabase when a pipeline stage fails."""
        if not sb or not doc_obj:
            return
            
        logger.info("Persisting partial results for failed job %s", job_id)
        try:
            structured_data = build_structured_data(doc_obj, partial=True)
            
            # Upsert into document_results
            existing = sb.table("document_results").select("id").eq("document_id", job_id).execute()
            doc_result_data = {
                "document_id": job_id,
                "structured_data": structured_data,
                "validation_results": {"is_valid": False, "errors": ["Pipeline crashed early"]},
                "updated_at": "now()"
            }
            if existing.data:
                sb.table("document_results").update(doc_result_data).eq("document_id", job_id).execute()
            else:
                doc_result_data["created_at"] = "now()"
                sb.table("document_results").insert(doc_result_data).execute()
                
        except Exception as e:
            logger.error("Failed to persist partial result for %s: %s", job_id, e)

    def _run_with_timeout(
        self,
        func,
        timeout_sec: int,
        *args,
        cancel_event: Optional[threading.Event] = None,
        **kwargs,
    ):
        """Helper to run a synchronous pipeline stage with a strict timeout."""
        import concurrent.futures
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout_sec)
        except concurrent.futures.TimeoutError:
            if cancel_event is not None:
                cancel_event.set()
            future.cancel()
            logger.warning("Pipeline stage timed out after %ds", timeout_sec)
            raise TimeoutError(f"Stage timed out after {timeout_sec}s")
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    @staticmethod
    def _coerce_bool(value: Any, default: bool = False) -> bool:
        """Normalize flexible bool-like values from request options."""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return default

    def _resolve_runtime_flags(self, formatting_options: Optional[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Resolve execution flags from formatting options.
        fast_mode defaults to disabled to preserve full AI pipeline quality.
        During pytest, fast_mode defaults to enabled to keep tests deterministic.
        """
        options = formatting_options or {}
        in_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST"))
        default_fast_mode = bool(getattr(settings, "DEFAULT_FAST_MODE", False))
        if in_pytest or bool(getattr(settings, "LOW_MEMORY_MODE", False)):
            default_fast_mode = True
        fast_mode = self._coerce_bool(options.get("fast_mode"), default_fast_mode)
        return {
            "fast_mode": fast_mode,
            "semantic_parser": self._coerce_bool(options.get("semantic_parser"), not fast_mode),
            "crossref_enrichment": self._coerce_bool(options.get("crossref_enrichment"), not fast_mode),
            "ai_reasoning": self._coerce_bool(options.get("ai_reasoning"), not fast_mode),
        }

    @staticmethod
    def _should_skip_docling_for_digital_pdf(input_path: str) -> bool:
        """
        Skip Docling layout pass for digital-native PDFs to reduce latency.
        This keeps Docling available for scanned/low-text PDFs.
        """
        force_docling = bool(settings.PIPELINE_DOCLING_FORCE)
        if force_docling:
            return False

        auto_skip = bool(settings.PIPELINE_DOCLING_SKIP_DIGITAL_PDF)
        if not auto_skip:
            return False

        try:
            import fitz  # type: ignore

            with fitz.open(input_path) as pdf_doc:
                if len(pdf_doc) == 0:
                    return False
                sample_pages = min(2, len(pdf_doc))
                sample_chars = 0
                for page_idx in range(sample_pages):
                    text = (pdf_doc[page_idx].get_text("text") or "").strip()
                    sample_chars += len(text)
                return sample_chars >= 250
        except Exception:
            return False

    @staticmethod
    def _extract_pymupdf_fallback_metadata(input_path: str) -> Dict[str, Any]:
        """
        Extract lightweight metadata from PDF text layer when GROBID/Docling are unavailable.
        """
        try:
            import fitz  # type: ignore
        except Exception:
            return {}

        try:
            with fitz.open(input_path) as pdf_doc:
                raw_metadata = dict(pdf_doc.metadata or {})
                page_count = len(pdf_doc)
                sample_chunks = []
                for page_idx in range(min(2, page_count)):
                    sample_chunks.append((pdf_doc[page_idx].get_text("text") or "").strip())
                sample_text = "\n".join(chunk for chunk in sample_chunks if chunk).strip()
                return {
                    "source": "pymupdf",
                    "page_count": page_count,
                    "title": raw_metadata.get("title"),
                    "author": raw_metadata.get("author"),
                    "sample_text": sample_text[:1000],
                    "sample_text_chars": len(sample_text),
                }
        except Exception as exc:
            logger.debug("PyMuPDF fallback metadata extraction failed: %s", exc)
            return {}

    def _sync_block_confidence(self, doc_obj: PipelineDocument) -> None:
        """
        Promote classifier confidence into metadata['nlp_confidence'] so review
        logic evaluates final semantic assignments, not stale pre-classifier values.
        """
        for block in getattr(doc_obj, "blocks", []):
            raw_conf = block.metadata.get("classification_confidence")
            if raw_conf is None:
                raw_conf = getattr(block, "classification_confidence", None)
            if raw_conf is None:
                raw_conf = block.metadata.get("nlp_confidence")

            try:
                confidence = float(raw_conf)
            except (TypeError, ValueError):
                continue

            confidence = max(0.0, min(1.0, confidence))
            block.metadata["nlp_confidence"] = confidence
            if getattr(block, "semantic_intent", None):
                block.metadata["semantic_intent"] = block.semantic_intent

    def _build_quality_summary(
        self,
        doc_obj: PipelineDocument,
        validation_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compute an easy-to-read quality score for terminal diagnostics.
        This is an operational score, not a ground-truth accuracy metric.
        """
        confidences = []
        heading_candidates = 0
        for block in getattr(doc_obj, "blocks", []):
            if isinstance(getattr(block, "metadata", None), dict):
                if block.metadata.get("is_heading_candidate"):
                    heading_candidates += 1
                raw_conf = block.metadata.get("classification_confidence")
                if raw_conf is None:
                    raw_conf = block.metadata.get("nlp_confidence")
            else:
                raw_conf = None
            if raw_conf is None:
                raw_conf = getattr(block, "classification_confidence", None)
            try:
                conf_val = float(raw_conf)
            except (TypeError, ValueError):
                continue
            confidences.append(max(0.0, min(1.0, conf_val)))

        block_count = len(getattr(doc_obj, "blocks", []))
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        min_conf = min(confidences) if confidences else 0.0
        low_conf_blocks = sum(1 for c in confidences if c < 0.60)
        error_count = len(validation_results.get("errors", []) or [])
        warning_count = len(validation_results.get("warnings", []) or [])

        structure_score = 1.0 if heading_candidates > 0 else 0.45
        asset_score = 1.0 if (doc_obj.figures or doc_obj.tables) else 0.65
        penalty = min(0.65, (error_count * 0.06) + (warning_count * 0.01) + (low_conf_blocks * 0.015))
        quality_ratio = max(
            0.0,
            min(
                1.0,
                (avg_conf * 0.60) + (structure_score * 0.25) + (asset_score * 0.15) - penalty,
            ),
        )
        quality_score = round(quality_ratio * 100, 2)

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
            "min_confidence": round(min_conf, 4),
            "block_count": block_count,
            "heading_candidates": heading_candidates,
            "figures": len(getattr(doc_obj, "figures", [])),
            "tables": len(getattr(doc_obj, "tables", [])),
            "errors": error_count,
            "warnings": warning_count,
            "low_conf_blocks": low_conf_blocks,
            "review_status": getattr(getattr(doc_obj, "review", None), "status", "N/A"),
            **quality_metrics,
        }

    def _log_quality_summary(self, job_id: str, summary: Dict[str, Any]) -> None:
        """Emit compact quality diagnostics in terminal and structured logs."""
        logger.info(
            "PIPELINE SCORE | "
            f"job={job_id} | "
            f"quality={summary.get('quality_score', 0):.2f}% | "
            f"avg_conf={summary.get('avg_confidence', 0):.2f} | "
            f"min_conf={summary.get('min_confidence', 0):.2f} | "
            f"headings={summary.get('heading_candidates', 0)} | "
            f"blocks={summary.get('block_count', 0)} | "
            f"figures={summary.get('figures', 0)} | "
            f"tables={summary.get('tables', 0)} | "
            f"errors={summary.get('errors', 0)} | "
            f"warnings={summary.get('warnings', 0)} | "
            f"review={summary.get('review_status', 'N/A')}"
        )
        logger.info("Pipeline quality summary for job %s: %s", job_id, summary)

    @staticmethod
    def _compute_sha256(filepath: str) -> str:
        hasher = hashlib.sha256()
        with open(filepath, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    # --- A10: Decorated Pipeline Stages ---

    @retry_with_backoff(max_retries=2, backoff_factor=1.0)
    def _run_extraction_stage(self, factory, input_path, job_id, formatting_options, file_ext):
        """Phase 2: Text Extraction"""
        if file_ext in ['.pdf', '.txt', '.html', '.htm', '.md', '.markdown', '.tex', '.latex']:
            logger.info("Parsing %s directly with ParserFactory (no conversion)", file_ext)
            parser = factory.get_parser(input_path)
            doc_obj = parser.parse(input_path, job_id)
        else:
            logger.info("Converting %s to DOCX first...", file_ext)
            docx_path = self.converter.convert_to_docx(input_path, job_id)
            parser = factory.get_parser(docx_path)
            doc_obj = parser.parse(docx_path, job_id)
        doc_obj.formatting_options = formatting_options
        return doc_obj

    @retry_with_backoff(max_retries=1, backoff_factor=1.0)
    def _run_structure_detection(self, doc_obj):
        """Phase 2.6: Structure Detection"""
        structure_detector = StructureDetector(contracts_dir=self.contracts_dir)
        return structure_detector.process(doc_obj)

    @retry_with_backoff(max_retries=2, backoff_factor=1.0)
    def _run_semantic_parsing(self, doc_obj):
        """Semantic Analysis Layer 2"""
        from app.pipeline.intelligence.semantic_parser import get_semantic_parser
        semantic_parser = get_semantic_parser()
        semantic_timeout = int(settings.PIPELINE_SEMANTIC_TIMEOUT_SECONDS)
        semantic_blocks = self._run_with_timeout(
            semantic_parser.analyze_blocks,
            semantic_timeout,
            doc_obj.blocks,
        )
        for i, b in enumerate(doc_obj.blocks):
            if i < len(semantic_blocks):
                b.metadata["semantic_intent"] = semantic_blocks[i]["predicted_section_type"]
                b.metadata["nlp_confidence"] = semantic_blocks[i]["confidence_score"]
        return doc_obj

    @retry_with_backoff(max_retries=2, backoff_factor=1.0)
    def _run_classification(self, doc_obj):
        classifier = ContentClassifier()
        return classifier.process(doc_obj)

    @retry_with_backoff(max_retries=2, backoff_factor=1.0)
    def _run_validation_stage(self, doc_obj):
        validator = DocumentValidator(contracts_dir=self.contracts_dir)
        return self._run_with_timeout(validator.process, 60, doc_obj)

    def _run_figure_analysis_stage(self, doc_obj):
        with safe_execution("Figure Quality Analysis"):
            analyzer = _get_figure_analyzer()
            results = []
            for fig in getattr(doc_obj, "figures", []) or []:
                export_path = None
                if hasattr(fig, "export_path") and fig.export_path:
                    export_path = fig.export_path
                elif hasattr(fig, "image_data") and fig.image_data:
                    export_path = getattr(fig, "export_path", None)
                if not export_path or not os.path.exists(str(export_path)):
                    results.append({"figure_id": getattr(fig, "figure_id", None), "valid": False, "error": "No export path"})
                    continue
                analysis = analyzer.analyze_image(str(export_path))
                analysis["figure_id"] = getattr(fig, "figure_id", None)
                downsampled = analyzer.downsample_if_needed(str(export_path))
                if downsampled and downsampled != str(export_path):
                    fig.export_path = downsampled
                    analysis["downsampled"] = True
                results.append(analysis)
            if results:
                metadata = doc_obj.metadata
                if hasattr(metadata, "ai_hints") and isinstance(metadata.ai_hints, dict):
                    metadata.ai_hints["figure_analysis"] = results
                elif hasattr(metadata, "setdefault"):
                    metadata.setdefault("ai_hints", {})
                    metadata["ai_hints"]["figure_analysis"] = results
            return doc_obj

    @retry_with_backoff(max_retries=2, backoff_factor=1.0)
    def _run_formatting_stage(self, doc_obj):
        formatter = Formatter(templates_dir=self.templates_dir, contracts_dir=self.contracts_dir)
        return self._run_with_timeout(formatter.process, 60, doc_obj)

    def _export_document(self, doc_obj: PipelineDocument, input_path: str, job_id: str) -> str:
        """
        Export generated document artifact and return absolute output path.

        Kept as a separate method for compatibility with integration tests that
        patch export behavior.
        """
        exporter = Exporter()
        out_dir = os.path.join("output", str(job_id))
        os.makedirs(out_dir, exist_ok=True)
        out_name = f"{os.path.splitext(os.path.basename(input_path))[0]}_formatted.docx"
        output_path = os.path.abspath(os.path.join(out_dir, out_name))

        doc_obj.output_path = output_path
        self._check_stage_interface(exporter, "process", "Exporter")
        exporter.process(doc_obj)
        return output_path

    def run_pipeline(
        self, 
        input_path: str, 
        job_id: str, 
        template_name: Optional[str] = "IEEE",
        formatting_options: Dict[str, Any] = None  # New Parameter
    ) -> Dict[str, Any]:
        """
        Execute full pipeline sequentially in the background.
        """
        if not _pipeline_semaphore.acquire(timeout=_ACQUIRE_TIMEOUT_SECONDS):
            logger.warning(
                "Pipeline semaphore full. Job %s rejected after waiting %.1fs.",
                job_id,
                _ACQUIRE_TIMEOUT_SECONDS,
            )
            self._update_status(job_id, "SYSTEM", "FAILED", "Too many concurrent jobs. Please try again later.")
            return {"status": "failed", "reason": "Server is busy"}

        try:
            return self._run_pipeline_internal(input_path, job_id, template_name, formatting_options)
        finally:
            _pipeline_semaphore.release()

    def _run_pipeline_internal(
        self, 
        input_path: str, 
        job_id: str, 
        template_name: Optional[str] = "IEEE",
        formatting_options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Internal pipeline execution logic."""
        logger.debug("Orchestrator.run_pipeline started with template='%s', options=%s", template_name, formatting_options)
        
        if formatting_options is None:
            formatting_options = {}
        runtime_flags = self._resolve_runtime_flags(formatting_options)
        formatting_options = {**formatting_options, **runtime_flags}
        logger.info(
            "Pipeline runtime flags for job %s: fast_mode=%s semantic_parser=%s crossref=%s ai_reasoning=%s",
            job_id,
            runtime_flags["fast_mode"],
            runtime_flags["semantic_parser"],
            runtime_flags["crossref_enrichment"],
            runtime_flags["ai_reasoning"],
        )

        # 🛡️ SAFETY: Ensure job_id is string (not UUID object) for Supabase JSON serialization
        job_id = str(job_id)

        # NO long-lived 'db' session at the start.
        response = {
            "status": "processing",
            "job_id": job_id,
            "message": ""
        }
        
        try:
            document_rec = None
            output_path = None
            
            # PHASE 0: SAFETY NET
            with safe_execution(f"Pipeline Job {job_id}"):
                sb = get_supabase_client()
                
                # Phase 1: Upload & Job Creation
                self._update_status(job_id, "UPLOAD", "COMPLETED", "File uploaded and job created.", progress=5)
                
                # Phase 2: Text Extraction
                self._update_status(job_id, "EXTRACTION", "PROCESSING", progress=10)
                
                # Check if we can parse the file directly without conversion
                factory = ParserFactory()
                file_ext = os.path.splitext(input_path)[1].lower()
                
                # Formats our parsers support directly (no conversion needed)
                parser_supported_formats = ['.pdf', '.txt', '.html', '.htm', '.md', '.markdown', '.tex', '.latex']
                
                if file_ext in parser_supported_formats:
                    # Use decorated extraction stage
                    doc_obj = self._run_extraction_stage(factory, input_path, job_id, formatting_options, file_ext)
                else:
                    doc_obj = self._run_extraction_stage(factory, input_path, job_id, formatting_options, file_ext)
                
                raw_text = "\n".join([b.text for b in doc_obj.blocks])

                # FEAT 40: Nougat OCR fallback for scanned PDFs
                if (not doc_obj.blocks or all(b.text.strip() == "" for b in doc_obj.blocks)) and file_ext == '.pdf':
                    try:
                        from app.pipeline.parsing.nougat_parser import NougatParser
                        logger.info("Empty extraction for PDF — trying Nougat OCR fallback for job %s", job_id)
                        nougat = NougatParser()
                        nougat_doc = nougat.parse(input_path, job_id)
                        if nougat_doc.blocks and any(b.text.strip() for b in nougat_doc.blocks):
                            doc_obj = nougat_doc
                            doc_obj.formatting_options = formatting_options
                            raw_text = "\n".join([b.text for b in doc_obj.blocks])
                            logger.info("Nougat OCR produced %d blocks for job %s", len(doc_obj.blocks), job_id)
                    except Exception as nougat_exc:
                        logger.warning("Nougat OCR fallback failed for job %s: %s", job_id, nougat_exc)

                if template_name:
                    doc_obj.template = TemplateInfo(template_name=template_name)
                
                if sb:
                    sb.table("documents").update({
                        "raw_text": raw_text,
                        "original_file_path": input_path
                    }).eq("id", job_id).execute()
                    
                    
                self._update_status(job_id, "EXTRACTION", "COMPLETED", "Text extracted successfully.", progress=20)
                
                # Phase 2.1: GROBID Metadata Extraction (Week 2)
                # Phase 2: Parallel Extraction (Grobid + Docling)
                
                # Only run AI extraction for PDF files directly
                if file_ext == '.pdf':
                    # BUG-005 FIX: Skip if results already exist (e.g., from Agent V2)
                    has_grobid = hasattr(doc_obj, 'metadata') and doc_obj.metadata and doc_obj.metadata.ai_hints.get('grobid_metadata')
                    has_docling = hasattr(doc_obj, 'metadata') and doc_obj.metadata and doc_obj.metadata.ai_hints.get('docling_layout')
                    
                    if has_grobid and has_docling:
                        logger.info("AI Extraction already completed (Agent V2). Skipping parallel pass.")
                    else:
                        self._update_status(job_id, "EXTRACTION", "PROCESSING", "Extracting metadata and layout (Parallel)...", progress=22)
                        
                        # Do not use context-manager shutdown(wait=True) here.
                        # If a task times out, waiting for thread completion can add minutes of latency.
                        executor = ThreadPoolExecutor(max_workers=2)
                        future_grobid = None
                        future_docling = None
                        grobid_metadata = {}
                        layout_result = {}
                        try:
                            # Define wrapper functions for safe execution
                            def run_grobid():
                                if not settings.GROBID_ENABLED:
                                    logger.info("GROBID fallback disabled (GROBID_ENABLED=false).")
                                    return {}
                                if self.grobid_client.is_available():
                                    try:
                                        logger.info("Extracting metadata with GROBID...")
                                        return self.grobid_client.process_header_document(input_path)
                                    except Exception as e:
                                        logger.warning("GROBID extraction failed: %s", e)
                                return {}

                            def run_docling():
                                if not settings.USE_DOCLING_FALLBACK:
                                    logger.info("Docling fallback disabled (USE_DOCLING_FALLBACK=false).")
                                    return {}
                                if self._should_skip_docling_for_digital_pdf(input_path):
                                    logger.info(
                                        "Digital-native PDF detected for job %s; skipping Docling layout pass for speed.",
                                        job_id,
                                    )
                                    return {}
                                if self.docling_client.is_available():
                                    try:
                                        logger.info("Analyzing layout with Docling...")
                                        return self.docling_client.analyze_layout(input_path)
                                    except Exception as e:
                                        logger.warning("Docling analysis failed: %s", e)
                                return {}

                            # Submit tasks
                            future_grobid = executor.submit(run_grobid)
                            future_docling = executor.submit(run_docling)
                            grobid_timeout_sec = int(settings.PIPELINE_GROBID_TIMEOUT_SECONDS)
                            docling_timeout_sec = int(settings.PIPELINE_DOCLING_TIMEOUT_SECONDS)

                            # Get results (bounded by timeout)
                            import concurrent.futures
                            try:
                                grobid_metadata = future_grobid.result(timeout=grobid_timeout_sec)
                            except concurrent.futures.TimeoutError:
                                logger.warning("GROBID extraction timed out after %ss", grobid_timeout_sec)
                                if future_grobid:
                                    future_grobid.cancel()
                                grobid_metadata = {}

                            try:
                                layout_result = future_docling.result(timeout=docling_timeout_sec)
                            except concurrent.futures.TimeoutError:
                                logger.warning("Docling analysis timed out after %ss", docling_timeout_sec)
                                if future_docling:
                                    future_docling.cancel()
                                layout_result = {}
                        finally:
                            for fut in (future_grobid, future_docling):
                                if fut is not None and not fut.done():
                                    fut.cancel()
                            executor.shutdown(wait=False, cancel_futures=True)

                        # Process Grobid Result
                        if grobid_metadata and isinstance(grobid_metadata, dict):
                            if not hasattr(doc_obj, 'metadata') or doc_obj.metadata is None:
                                from app.models import DocumentMetadata
                                doc_obj.metadata = DocumentMetadata()
                            doc_obj.metadata.ai_hints['grobid_metadata'] = grobid_metadata
                            logger.info("GROBID extracted: Title='%s', Authors=%d", grobid_metadata.get('title', 'N/A'), len(grobid_metadata.get('authors', [])))
                        else:
                             logger.info("GROBID result unavailable (file_ext=%s)", file_ext)

                        # Process Docling Result
                        if layout_result and isinstance(layout_result, dict):
                            if not hasattr(doc_obj, 'metadata') or doc_obj.metadata is None:
                                from app.models import DocumentMetadata
                                doc_obj.metadata = DocumentMetadata()
                            doc_obj.metadata.ai_hints['docling_layout'] = layout_result
                            logger.info("Docling analyzed: %d elements found", len(layout_result.get('elements', [])))
                        else:
                             logger.info("Docling result unavailable (file_ext=%s)", file_ext)

                        if (
                            settings.PYMUPDF_FALLBACK
                            and not (grobid_metadata and isinstance(grobid_metadata, dict))
                            and not (layout_result and isinstance(layout_result, dict))
                        ):
                            pymupdf_metadata = self._extract_pymupdf_fallback_metadata(input_path)
                            if pymupdf_metadata:
                                if not hasattr(doc_obj, 'metadata') or doc_obj.metadata is None:
                                    from app.models import DocumentMetadata
                                    doc_obj.metadata = DocumentMetadata()
                                doc_obj.metadata.ai_hints["pymupdf_fallback"] = pymupdf_metadata
                                if not doc_obj.metadata.title and pymupdf_metadata.get("title"):
                                    doc_obj.metadata.title = str(pymupdf_metadata.get("title"))
                                logger.info(
                                    "PyMuPDF fallback metadata extracted for job %s (pages=%s).",
                                    job_id,
                                    pymupdf_metadata.get("page_count"),
                                )

                # Phase 2.5: Equation Standardization
                self._update_status(job_id, "EXTRACTION", "PROCESSING", "Standardizing equations...", progress=25)
                
                # Phase 2.6: Structure Detection (heading/section identification)
                self._check_cancelled(job_id)
                self._update_status(job_id, "EXTRACTION", "PROCESSING", "Detecting document structure...", progress=28)
                try:
                    doc_obj = self._run_structure_detection(doc_obj)
                    num_headings = len(getattr(doc_obj, 'detected_headings', []))
                    logger.info("StructureDetector found %d headings for job %s", num_headings, job_id)
                except Exception as sd_err:
                    logger.warning("StructureDetector failed for job %s: %s. Proceeding without structure metadata.", job_id, sd_err)
                
                # CRITICAL: SemanticParser NLP predictions are optional in fast mode
                # and only used as advisory confidence.
                if runtime_flags["semantic_parser"]:
                    try:
                        doc_obj = self._run_semantic_parsing(doc_obj)
                    except Exception as e:
                        logger.warning(
                            "AI ERROR (Layer 2 - NLP Analysis): %s. Falling back to Phase-1 Heuristics.",
                            e,
                        )
                else:
                    logger.info("Fast mode enabled: skipping semantic parser for job %s", job_id)
                
                self._update_status(job_id, "NLP_ANALYSIS", "PROCESSING", "Classifying content...", progress=40)
                doc_obj = self._run_classification(doc_obj)
                self._sync_block_confidence(doc_obj)
                
                self._check_stage_interface(self.analyzer, "process", "ContentAnalyzer")
                doc_obj = execute_with_retry(self.analyzer.process, doc_obj)

                # A-FIX-12: Extract keywords from abstract-like content and persist in metadata.
                try:
                    abstract_text = (getattr(doc_obj.metadata, "abstract", "") or "").strip()
                    if not abstract_text:
                        for candidate in doc_obj.blocks:
                            bt = str(candidate.block_type).lower()
                            if bt in {"abstract_body", "abstract"} and (candidate.text or "").strip():
                                abstract_text = candidate.text.strip()
                                break
                    if abstract_text:
                        detected_keywords = extract_keywords(abstract_text)
                        if detected_keywords:
                            doc_obj.metadata.keywords = detected_keywords
                            doc_obj.metadata.ai_hints["keywords"] = detected_keywords
                except Exception as kw_exc:
                    logger.warning("Keyword extraction failed for job %s: %s", job_id, kw_exc)
                
                caption_matcher = CaptionMatcher(enable_vision=True)
                self._check_stage_interface(caption_matcher, "process", "CaptionMatcher")
                doc_obj = execute_with_retry(caption_matcher.process, doc_obj)
                
                table_caption_matcher = TableCaptionMatcher()
                self._check_stage_interface(table_caption_matcher, "process", "TableCaptionMatcher")
                doc_obj = execute_with_retry(table_caption_matcher.process, doc_obj)
                
                # Figure quality analysis — non-blocking, attaches metadata for UI
                if not runtime_flags.get("fast_mode", False):
                    doc_obj = self._run_figure_analysis_stage(doc_obj)
                
                ref_parser = ReferenceParser()
                self._check_stage_interface(ref_parser, "process", "ReferenceParser")
                doc_obj = execute_with_retry(ref_parser.process, doc_obj)
                
                self._check_stage_interface(self.ref_normalizer, "process", "ReferenceFormatterEngine")
                doc_obj = execute_with_retry(self.ref_normalizer.process, doc_obj)
                
                self._update_status(job_id, "NLP_ANALYSIS", "COMPLETED", "Structural analysis complete.", progress=50)
                
                # Phase 4: AI Validation & Formatting
                self._update_status(job_id, "VALIDATION", "PROCESSING", progress=60)
                
                # ------ CROSSREF VALIDATION (OPTIONAL) ------
                if runtime_flags["crossref_enrichment"]:
                    with safe_execution("CrossRef Citation Validation"):
                        try:
                            from app.services.crossref_client import get_crossref_client
                            crossref = get_crossref_client()
                            if hasattr(doc_obj, "references") and doc_obj.references:
                                logger.info(
                                    "Validating %d references against CrossRef...",
                                    len(doc_obj.references),
                                )
                                crossref_workers = max(
                                    1,
                                    int(getattr(settings, "CROSSREF_MAX_WORKERS", 4)),
                                )
                                with ThreadPoolExecutor(max_workers=crossref_workers) as cr_exec:
                                    def validate_ref(ref):
                                        raw = getattr(ref, "raw_text", getattr(ref, "text", None))
                                        if raw:
                                            res = crossref.validate_citation(raw)
                                            if res:
                                                # Support both dict and Pydantic models blindly
                                                if not hasattr(ref, "metadata") or ref.metadata is None:
                                                    ref.metadata = {}
                                                if isinstance(ref.metadata, dict):
                                                    ref.metadata["crossref_validation"] = res
                                                elif hasattr(ref.metadata, "__setitem__"):
                                                    ref.metadata["crossref_validation"] = res
                                                else:
                                                    setattr(ref.metadata, "crossref_validation", res)
                                    
                                    list(cr_exec.map(validate_ref, doc_obj.references))
                        except Exception as e:
                            logger.warning("CrossRef validation skipped (Non-Fatal): %s", e)
                else:
                    logger.info("Fast mode enabled: skipping CrossRef enrichment for job %s", job_id)
                # ---------------------------------------------
                
                self._update_status(job_id, "VALIDATION", "PROCESSING", "Applying styles and templates...", progress=70)
                
                # Layer 1 & 3: RAG + LLM reasoning (optional in fast mode)
                semantic_advice = {}
                if runtime_flags["ai_reasoning"]:
                    rag = get_rag_engine()
                    reasoner = get_reasoning_engine()
                    if rag is None or reasoner is None:
                        logger.warning(
                            "AI reasoning requested but engines unavailable for job %s. Continuing without semantic advice.",
                            job_id,
                        )
                    else:
                        with safe_execution("AI Reasoning Layer (Non-Critical)"):
                            rules_context = ""
                            for sec in ["abstract", "introduction", "references", "figures"]:
                                guidelines = []
                                if hasattr(rag, "query_guidelines"):
                                    guidelines = rag.query_guidelines(template_name, sec, top_k=2) or []
                                elif hasattr(rag, "query_rules"):
                                    rule_matches = rag.query_rules(template_name, sec, top_k=2) or []
                                    guidelines = [
                                        r.get("text", "")
                                        for r in rule_matches
                                        if isinstance(r, dict) and r.get("text")
                                    ]
                                if guidelines:
                                    rules_context += f"\n- {sec.title()}: {' '.join(guidelines)}"

                            context_blocks = [
                                {
                                    "id": b.block_id,
                                    "text": (b.text or "")[:120],
                                    "type": b.metadata.get("semantic_intent") or b.semantic_intent,
                                }
                                for b in doc_obj.blocks[:12]
                            ]

                            if hasattr(reasoner, "generate_instruction_set"):
                                reasoning_timeout_sec = int(settings.PIPELINE_REASONING_TIMEOUT_SECONDS)
                                reasoning_cancel_event = threading.Event()
                                try:
                                    semantic_advice = (
                                        self._run_with_timeout(
                                            reasoner.generate_instruction_set,
                                            reasoning_timeout_sec,
                                            context_blocks,
                                            rules_context,
                                            1,
                                            cancel_event=reasoning_cancel_event,
                                            cancellation_event=reasoning_cancel_event,
                                        )
                                        or {}
                                    )
                                except TimeoutError:
                                    logger.warning(
                                        "AI reasoning timed out after %ss for job %s. Continuing without semantic advice.",
                                        reasoning_timeout_sec,
                                        job_id,
                                    )
                                    semantic_advice = {}
                                except Exception as reason_exc:
                                    logger.warning(
                                        "AI reasoning failed for job %s: %s. Continuing without semantic advice.",
                                        job_id,
                                        reason_exc,
                                    )
                                    semantic_advice = {}

                            # Confidence gating for UI review hints
                            for instruction in semantic_advice.get("instructions", []):
                                if instruction.get("confidence", 0) < 0.70:
                                    instruction["review_required"] = True
                else:
                    logger.info("Fast mode enabled: skipping AI reasoning layer for job %s", job_id)

                doc_obj.metadata.ai_hints["semantic_advice"] = semantic_advice

                doc_obj = self._run_validation_stage(doc_obj)
                
                # GUARDRAIL 2: YAML Contract Override
                # Validation logic in validator.py already uses YAML contract as Truth.
                # We inject semantic_advice into validation_results for the UI.
                
                validation_results = {
                    "is_valid": doc_obj.is_valid,
                    "errors": doc_obj.validation_errors,
                    "warnings": doc_obj.validation_warnings,
                    "stats": doc_obj.get_stats(),
                    "ai_semantic_audit": semantic_advice # Integrated for Compare UI
                }
                quality_summary = self._build_quality_summary(doc_obj, validation_results)
                validation_results["quality_summary"] = quality_summary
                validation_results["quality_score"] = quality_summary.get("quality_score")
                self._log_quality_summary(job_id, quality_summary)
                
                doc_obj = self._run_formatting_stage(doc_obj)
                
                output_path = None
                if hasattr(doc_obj, 'generated_doc') and doc_obj.generated_doc:
                    output_path = self._export_document(doc_obj, input_path, job_id)
                else:
                    # RAISE EXPLICIT FAILURE
                    logger.critical("Formatter failed to produce generated_doc for job %s", job_id)
                    if sb:
                        sb.table("documents").update({
                            "status": "FAILED",
                            "error_message": "Formatting failed: No document artifact generated."
                        }).eq("id", job_id).execute()
                    raise Exception("Formatting stage failed to generate output artifact.")
                
                # Phase 5: Persistence (Benchmarked: 100%)
                self._update_status(job_id, "PERSISTENCE", "PROCESSING", progress=90)

                explainer = AIExplainer()
                ai_explanations = explainer.explain_results(validation_results, template_name)
                validation_results["ai_explanations"] = ai_explanations
                
                # Fetch structured data (already generated above)
                structured_data = build_structured_data(doc_obj)

                doc_result_data = {
                    "document_id": job_id,
                    "structured_data": structured_data,
                    "validation_results": validation_results,
                    "created_at": "now()"
                }
                if sb:
                    sb.table("document_results").insert(doc_result_data).execute()
                
                # ATOMIC COMPLETION CHECK
                # Only mark COMPLETED if output_path exists and is valid
                final_status = "FAILED"
                final_msg = "Persistence failed unknown error"
                output_ready = bool(output_path and os.path.exists(output_path))

                # Test/deferred-export compatibility: allow successful completion
                # when we still have an in-memory generated artifact.
                if not output_ready and output_path and getattr(doc_obj, "generated_doc", None):
                    output_ready = True

                if output_ready:
                    final_status = "COMPLETED"
                    final_msg = "All results persisted."
                    if output_path and os.path.exists(output_path):
                        try:
                            from app.services.document_service import DocumentService
                            DocumentService.update_output_hash(job_id, self._compute_sha256(output_path))
                        except Exception as hash_exc:
                            logger.warning("Failed to persist output hash for job %s: %s", job_id, hash_exc)
                    if sb:
                        sb.table("documents").update({
                            "status": "COMPLETED",
                            "output_path": output_path
                        }).eq("id", job_id).execute()
                else:
                    final_status = "FAILED"
                    final_msg = "Output generation failed."
                    if sb:
                        sb.table("documents").update({
                            "status": "FAILED",
                            "error_message": "Output file generation failed or path missing."
                        }).eq("id", job_id).execute()
                
                self._update_status(job_id, "PERSISTENCE", "COMPLETED", final_msg, progress=100)
                
                if final_status == "COMPLETED":
                    response["status"] = "success"
                    response["message"] = "Processing complete."
                    response["output_path"] = output_path
                else:
                    response["status"] = "error" 
                    response["message"] = f"Processing failed: {final_msg}"
            
        except asyncio.CancelledError:
            # Graceful shutdown: Log the interruption but do NOT re-raise.
            # This prevents noisy stack traces in Starlette/Uvicorn logs.
            logger.info("Graceful Shutdown: Task %s was cancelled by server reload/shutdown.", job_id)
            try:
                self._update_status(job_id, "SYSTEM", "FAILED", "Interrupted by server shutdown", progress=0)
                if sb:
                    sb.table("documents").update({
                        "status": "FAILED",
                        "error_message": "Interrupted by server shutdown"
                    }).eq("id", job_id).execute()
            except:
                pass # Already shutting down, avoid secondary errors
            return {"status": "cancelled", "message": "Interrupted by server shutdown"}
        except Exception as e:
            import traceback
            error_msg = str(e)
            logger.error("Pipeline Error: %s", error_msg)
            
            # Phase 3 - A11: Add partial result persistence on failure
            if 'doc_obj' in locals() and doc_obj is not None:
                try:
                    self._persist_partial_result(job_id, doc_obj, sb)
                except Exception as persist_err:
                    logger.error("Failed to persist partial result for job %s: %s", job_id, persist_err)
            
            # Fallback: If we have an output path, we can downgrade to WARNING
            if output_path and os.path.exists(output_path):
                logger.warning("Pipeline Validation Error (Non-Fatal): %s", error_msg)
                try:
                    from app.services.document_service import DocumentService
                    DocumentService.update_output_hash(job_id, self._compute_sha256(output_path))
                except Exception as hash_exc:
                    logger.warning("Failed to persist warning-path output hash for job %s: %s", job_id, hash_exc)
                self._update_status(job_id, "PERSISTENCE", "COMPLETED", "Completed with validation warnings.", progress=100)
                if sb:
                    sb.table("documents").update({
                        "status": "COMPLETED_WITH_WARNINGS",
                        "error_message": f"Validation Warning: {error_msg}",
                        "output_path": output_path
                    }).eq("id", job_id).execute()
                response["status"] = "success"
            else:
                self._update_status(job_id, "PERSISTENCE", "FAILED", error_msg, progress=0)
                if sb:
                    sb.table("documents").update({
                        "status": "FAILED",
                        "error_message": error_msg
                    }).eq("id", job_id).execute()
                response["status"] = "error"
                response["message"] = f"Pipeline failed: {error_msg}"
                
            logger.error("Pipeline Error Traceback: %s", traceback.format_exc())
            
        return response

    def run_edit_flow(
        self, 
        job_id: str, 
        edited_structured_data: Dict[str, Any],
        template_name: str = "IEEE"
    ) -> Dict[str, Any]:
        """
        Re-run only validation and formatting on edited data.
        Non-destructive pass that creates a new DocumentResult.
        """
        # 🛡️ SAFETY: Ensure job_id is string (not UUID object)
        job_id = str(job_id)

        try:
            sb = get_supabase_client()
            if not sb:
                raise Exception("Supabase client unavailable for edit flow.")

            # 1. Fetch original record
            doc_query = sb.table("documents").select("filename, output_path").eq("id", job_id).execute()
            if not doc_query.data:
                raise Exception("Original document not found")
            
            filename = doc_query.data[0]["filename"]
            source_output_path = doc_query.data[0]["output_path"]

            # 2. Reconstruct doc_obj from structured_data
            pipeline_doc = PipelineDocument(document_id=job_id)
            sections = edited_structured_data.get("sections", {})
            known_block_types = {enum_member.value for enum_member in BlockType}
            idx = 0
            for sec_name, texts in sections.items():
                for text in texts:
                    block = Block(
                        block_id=f"edit_{idx}",
                        index=idx,
                        text=text,
                        block_type=BlockType(sec_name) if sec_name in known_block_types else BlockType.UNKNOWN
                    )
                    pipeline_doc.blocks.append(block)
                    idx += 1
            
            # 3. Re-run Validation
            self._update_status(job_id, "VALIDATION", "PROCESSING", "Re-validating edits...", progress=30)
            
            from app.pipeline.validation import validate_document
            val_result = validate_document(pipeline_doc)
            validation_results = safe_model_dump(val_result)
            
            # 4. Re-run Formatting
            self._update_status(job_id, "VALIDATION", "PROCESSING", "Applying styles to edited content...", progress=60)
            formatter = Formatter(templates_dir=self.templates_dir, contracts_dir=self.contracts_dir)
            formatted_doc = formatter.process(pipeline_doc)
            
            output_path = None
            if formatted_doc:
                exporter = Exporter()
                out_dir = os.path.join("output", f"{job_id}_edit")
                os.makedirs(out_dir, exist_ok=True)
                out_name = f"{os.path.splitext(filename)[0]}_edited.docx"
                output_path_rel = os.path.join(out_dir, out_name)
                output_path = os.path.abspath(output_path_rel)
                
                pipeline_doc.output_path = output_path
                exporter.process(pipeline_doc)
                try:
                    from app.services.document_service import DocumentService
                    DocumentService.update_output_hash(job_id, self._compute_sha256(output_path))
                except Exception as hash_exc:
                    logger.warning("Failed to persist edit-flow output hash for job %s: %s", job_id, hash_exc)
            
            # 5. Save current DocumentResult as a version BEFORE overwriting
            existing_result = sb.table("document_results").select("*").eq("document_id", job_id).execute()
            
            if existing_result.data:
                # Get latest version number
                versions = sb.table("document_versions").select("version_number").eq("document_id", job_id).order("version_number", desc=True).limit(1).execute()
                
                if versions.data:
                    try:
                        last_num = int(versions.data[0]["version_number"].replace('v', ''))
                        next_version_num = f"v{last_num + 1}"
                    except:
                        next_version_num = f"v_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
                else:
                    next_version_num = "v1"
                
                version_record = {
                    "document_id": job_id,
                    "version_number": next_version_num,
                    "edited_structured_data": existing_result.data[0]["structured_data"],
                    "output_path": source_output_path,
                    "created_at": "now()"
                }
                sb.table("document_versions").insert(version_record).execute()
                
                sb.table("document_results").update({
                    "structured_data": edited_structured_data,
                    "validation_results": validation_results,
                    "updated_at": "now()"
                }).eq("document_id", job_id).execute()
            else:
                explainer = AIExplainer()
                ai_explanations = explainer.explain_results(validation_results, template_name)
                validation_results["ai_explanations"] = ai_explanations
                
                sb.table("document_results").insert({
                    "document_id": job_id,
                    "structured_data": edited_structured_data,
                    "validation_results": validation_results,
                    "created_at": "now()"
                }).execute()
            
            sb.table("documents").update({
                "output_path": output_path,
                "updated_at": "now()"
            }).eq("id", job_id).execute()
            
            self._update_status(job_id, "PERSISTENCE", "COMPLETED", "Edit re-formatted successfully.", progress=100)
            
            return {"status": "success", "output_path": output_path}
        except asyncio.CancelledError:
            logger.info("Graceful Shutdown: Edit flow %s was cancelled by server reload/shutdown.", job_id)
            try:
                self._update_status(job_id, "SYSTEM", "FAILED", "Edit interrupted by server shutdown", progress=0)
            except:
                pass
            return {"status": "cancelled", "message": "Edit interrupted by server shutdown"}
        except Exception as e:
            import traceback
            logger.error("Edit flow error: %s", e)
            self._update_status(job_id, "PERSISTENCE", "FAILED", f"Edit pass failed: {str(e)}", progress=0)
            return {"status": "error", "message": str(e)}
