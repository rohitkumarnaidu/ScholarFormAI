# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Individual pipeline stages extracted from the PipelineOrchestrator god class."""

import os
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any, Optional

from app.pipeline.safety.retry_guard import retry_with_backoff

logger = logging.getLogger(__name__)

_figure_analyzer_instance = None


def _get_figure_analyzer():
    global _figure_analyzer_instance
    if _figure_analyzer_instance is None:
        from app.pipeline.figures.analyzer import figure_analyzer

        _figure_analyzer_instance = figure_analyzer
    return _figure_analyzer_instance


class PipelineStages:
    """Individual pipeline stages as standalone methods."""

    def __init__(
        self,
        templates_dir: str,
        temp_dir: str,
        contracts_dir: str,
        converter,
        grobid_client,
        run_with_timeout_fn=None,
    ):
        self.templates_dir = templates_dir
        self.temp_dir = temp_dir
        self.contracts_dir = contracts_dir
        self.converter = converter
        self.grobid_client = grobid_client
        self._run_with_timeout = run_with_timeout_fn

    # ------------------------------------------------------------------ #
    #  Static/utility helpers (preserved for backward compat)             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def coerce_bool(value: Any, default: bool = False) -> bool:
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

    @staticmethod
    def extract_pymupdf_fallback_metadata(input_path: str) -> dict[str, Any]:
        try:
            import fitz
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

    @staticmethod
    def compute_sha256(filepath: str) -> str:
        hasher = hashlib.sha256()
        with open(filepath, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def sync_block_confidence(doc_obj) -> None:
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

    # ------------------------------------------------------------------ #
    #  Stage: Extraction (Phase 2)                                        #
    # ------------------------------------------------------------------ #

    @retry_with_backoff(max_retries=2, backoff_factor=1.0)
    def extract_parse_content(self, factory, input_path, job_id, formatting_options, file_ext):
        """Phase 2: Text extraction — parse or convert + parse."""
        parser_supported_formats = [".pdf", ".txt", ".html", ".htm", ".md", ".markdown", ".tex", ".latex"]
        if file_ext in parser_supported_formats:
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

    def apply_llm_pdf_fallback(self, doc_obj, input_path, job_id, file_ext):
        """LLM-based PDF fallback for scanned PDFs with empty extraction."""
        if (not doc_obj.blocks or all(b.text.strip() == "" for b in doc_obj.blocks)) and file_ext == ".pdf":
            try:
                from app.pipeline.parsing.llm_pdf_parser import LLMPDFParser

                logger.info("Empty extraction for PDF — trying LLM PDF parser fallback for job %s", job_id)
                llm_parser = LLMPDFParser()
                llm_doc = llm_parser.parse(input_path, job_id)
                if llm_doc.blocks and any(b.text.strip() for b in llm_doc.blocks):
                    doc_obj = llm_doc
                    logger.info("LLM PDF parser produced %d blocks for job %s", len(doc_obj.blocks), job_id)
            except Exception as llm_exc:
                logger.warning("LLM PDF parser fallback failed for job %s: %s", job_id, llm_exc)
        return doc_obj

    def set_template(self, doc_obj, template_name):
        """Set template info on document object."""
        if template_name:
            from app.models import TemplateInfo

            doc_obj.template = TemplateInfo(template_name=template_name)

    # ------------------------------------------------------------------ #
    #  Stage: AI Extraction (GROBID + Docling parallel)                   #
    # ------------------------------------------------------------------ #

    def extract_ai_metadata(self, doc_obj, input_path, file_ext, job_id):
        """Parallel GROBID + Docling extraction for PDF files."""
        if file_ext != ".pdf":
            return doc_obj

        has_grobid = (
            hasattr(doc_obj, "metadata") and doc_obj.metadata and doc_obj.metadata.ai_hints.get("grobid_metadata")
        )
        has_layout = hasattr(doc_obj, "metadata") and doc_obj.metadata and doc_obj.metadata.ai_hints.get("llm_layout")
        if has_grobid and has_layout:
            logger.info("AI Extraction already completed (Agent V2). Skipping parallel pass.")
            return doc_obj

        executor = ThreadPoolExecutor(max_workers=2)
        future_grobid = None
        future_layout = None
        grobid_metadata = {}
        layout_result = {}

        from app.pipeline.orchestrator import settings as _s

        try:

            def run_grobid():
                if not _s.GROBID_ENABLED:
                    logger.info("GROBID fallback disabled (GROBID_ENABLED=false).")
                    return {}
                if self.grobid_client.is_available():
                    try:
                        logger.info("Extracting metadata with GROBID...")
                        return self.grobid_client.process_header_document(input_path)
                    except Exception as e:
                        logger.warning("GROBID extraction failed: %s", e)
                return {}

            def run_llm_layout():
                if not _s.ENABLE_LLM_PDF_PARSER:
                    logger.info("LLM PDF parser disabled (ENABLE_LLM_PDF_PARSER=false).")
                    return {}
                try:
                    from app.pipeline.parsing.llm_pdf_parser import LLMPDFParser

                    logger.info("Analyzing layout with LLM PDF parser...")
                    llm_parser = LLMPDFParser()
                    return llm_parser.analyze_layout(input_path)
                except Exception as e:
                    logger.warning("LLM layout analysis failed: %s", e)
                return {}

            future_grobid = executor.submit(run_grobid)
            future_layout = executor.submit(run_llm_layout)
            grobid_timeout = int(_s.PIPELINE_GROBID_TIMEOUT_SECONDS)

            try:
                grobid_metadata = future_grobid.result(timeout=grobid_timeout)
            except FuturesTimeoutError:
                logger.warning("GROBID extraction timed out after %ss", grobid_timeout)
                if future_grobid:
                    future_grobid.cancel()
                grobid_metadata = {}

            try:
                layout_result = future_layout.result(timeout=grobid_timeout)
            except FuturesTimeoutError:
                logger.warning("LLM layout analysis timed out after %ss", grobid_timeout)
                if future_layout:
                    future_layout.cancel()
                layout_result = {}
        finally:
            for fut in (future_grobid, future_layout):
                if fut is not None and not fut.done():
                    fut.cancel()
            executor.shutdown(wait=False, cancel_futures=True)

        if grobid_metadata and isinstance(grobid_metadata, dict):
            if not hasattr(doc_obj, "metadata") or doc_obj.metadata is None:
                from app.models import DocumentMetadata

                doc_obj.metadata = DocumentMetadata()
            doc_obj.metadata.ai_hints["grobid_metadata"] = grobid_metadata
            logger.info(
                "GROBID extracted: Title='%s', Authors=%d",
                grobid_metadata.get("title", "N/A"),
                len(grobid_metadata.get("authors", [])),
            )

        if layout_result and isinstance(layout_result, dict):
            if not hasattr(doc_obj, "metadata") or doc_obj.metadata is None:
                from app.models import DocumentMetadata

                doc_obj.metadata = DocumentMetadata()
            doc_obj.metadata.ai_hints["llm_layout"] = layout_result
            logger.info(
                "LLM layout analyzed: %d elements found",
                len(layout_result.get("elements", [])),
            )

        if (
            _s.PYMUPDF_FALLBACK
            and not (grobid_metadata and isinstance(grobid_metadata, dict))
            and not (layout_result and isinstance(layout_result, dict))
        ):
            from app.models import DocumentMetadata

            pymupdf_metadata = self.extract_pymupdf_fallback_metadata(input_path)
            if pymupdf_metadata:
                if not hasattr(doc_obj, "metadata") or doc_obj.metadata is None:
                    from app.models import DocumentMetadata

                    doc_obj.metadata = DocumentMetadata()
                doc_obj.metadata.ai_hints["pymupdf_fallback"] = pymupdf_metadata
                if not doc_obj.metadata.title and pymupdf_metadata.get("title"):
                    doc_obj.metadata.title = str(pymupdf_metadata.get("title"))
                logger.info("PyMuPDF fallback metadata extracted (pages=%s).", pymupdf_metadata.get("page_count"))

        return doc_obj

    # ------------------------------------------------------------------ #
    #  Stage: Structure Detection (Phase 2.6)                             #
    # ------------------------------------------------------------------ #

    @retry_with_backoff(max_retries=1, backoff_factor=1.0)
    def detect_structure(self, doc_obj):
        from app.pipeline.orchestrator import StructureDetector

        detector = StructureDetector(contracts_dir=self.contracts_dir)
        return detector.process(doc_obj)

    # ------------------------------------------------------------------ #
    #  Stage: Semantic Parsing (NLP Layer 2)                              #
    # ------------------------------------------------------------------ #

    @retry_with_backoff(max_retries=2, backoff_factor=1.0)
    def run_semantic_parsing(self, doc_obj):
        from app.pipeline.orchestrator import settings as _s
        from app.pipeline.intelligence.semantic_parser import get_semantic_parser

        semantic_parser = get_semantic_parser()
        timeout = int(_s.PIPELINE_SEMANTIC_TIMEOUT_SECONDS)
        if self._run_with_timeout:
            semantic_blocks = self._run_with_timeout(
                semantic_parser.analyze_blocks,
                timeout,
                doc_obj.blocks,
            )
        else:
            semantic_blocks = semantic_parser.analyze_blocks(doc_obj.blocks)
        for i, b in enumerate(doc_obj.blocks):
            if i < len(semantic_blocks):
                b.metadata["semantic_intent"] = semantic_blocks[i]["predicted_section_type"]
                b.metadata["nlp_confidence"] = semantic_blocks[i]["confidence_score"]
        return doc_obj

    # ------------------------------------------------------------------ #
    #  Stage: Classification (Phase 2.7)                                  #
    # ------------------------------------------------------------------ #

    @retry_with_backoff(max_retries=2, backoff_factor=1.0)
    def run_classification(self, doc_obj):
        from app.pipeline.orchestrator import ContentClassifier

        classifier = ContentClassifier()
        return classifier.process(doc_obj)

    # ------------------------------------------------------------------ #
    #  Stage: Content Analysis (keyword extraction + caption matching)    #
    # ------------------------------------------------------------------ #

    def analyze_content(self, doc_obj, job_id):
        """Content analysis: keyword extraction + caption matching."""
        try:
            from app.pipeline.nlp.analyzer import extract_keywords

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
        return doc_obj

    def match_captions(self, doc_obj):
        from app.pipeline.orchestrator import CaptionMatcher, TableCaptionMatcher
        from app.pipeline.safety.retry_guard import execute_with_retry

        caption_matcher = CaptionMatcher(enable_vision=True)
        doc_obj = execute_with_retry(caption_matcher.process, doc_obj)
        table_caption_matcher = TableCaptionMatcher()
        doc_obj = execute_with_retry(table_caption_matcher.process, doc_obj)
        return doc_obj

    # ------------------------------------------------------------------ #
    #  Stage: Figure Analysis                                              #
    # ------------------------------------------------------------------ #

    def run_figure_analysis(self, doc_obj):
        from app.pipeline.orchestrator import safe_execution

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
                    results.append(
                        {"figure_id": getattr(fig, "figure_id", None), "valid": False, "error": "No export path"}
                    )
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

    # ------------------------------------------------------------------ #
    #  Stage: Reference Processing (parse + format)                       #
    # ------------------------------------------------------------------ #

    def process_references(self, doc_obj):
        from app.pipeline.orchestrator import ReferenceParser
        from app.pipeline.safety.retry_guard import execute_with_retry

        ref_parser = ReferenceParser()
        doc_obj = execute_with_retry(ref_parser.process, doc_obj)
        doc_obj = execute_with_retry(self.ref_normalizer.process, doc_obj)
        return doc_obj

    @property
    def ref_normalizer(self):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        from app.pipeline.contracts.loader import ContractLoader

        loader = ContractLoader(contracts_dir=self.contracts_dir)
        return ReferenceFormatterEngine(loader)

    # ------------------------------------------------------------------ #
    #  Stage: CrossRef Validation (optional)                               #
    # ------------------------------------------------------------------ #

    def run_crossref_validation(self, doc_obj):
        from app.pipeline.orchestrator import safe_execution

        with safe_execution("CrossRef Citation Validation"):
            try:
                from app.pipeline.orchestrator import settings as _s
                from app.services.crossref_client import get_crossref_client

                crossref = get_crossref_client()
                if hasattr(doc_obj, "references") and doc_obj.references:
                    logger.info("Validating %d references against CrossRef...", len(doc_obj.references))
                    workers = max(1, int(getattr(_s, "CROSSREF_MAX_WORKERS", 4)))
                    with ThreadPoolExecutor(max_workers=workers) as cr_exec:

                        def validate_ref(ref):
                            raw = getattr(ref, "raw_text", getattr(ref, "text", None))
                            if raw:
                                res = crossref.validate_citation(raw)
                                if res:
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
        return doc_obj

    # ------------------------------------------------------------------ #
    #  Stage: AI Reasoning (RAG + LLM, optional)                          #
    # ------------------------------------------------------------------ #

    def run_ai_reasoning(self, doc_obj, template_name, job_id):
        """RAG + LLM reasoning layer. Returns semantic_advice dict."""
        from app.pipeline.orchestrator import safe_execution, settings as _s

        semantic_advice = {}
        rag = self._resolve_rag_engine()
        reasoner = self._resolve_reasoning_engine()
        if rag is None or reasoner is None:
            logger.warning("AI reasoning engines unavailable for job %s.", job_id)
            return semantic_advice

        with safe_execution("AI Reasoning Layer (Non-Critical)"):
            rules_context = ""
            for sec in ["abstract", "introduction", "references", "figures"]:
                guidelines = []
                if hasattr(rag, "query_guidelines"):
                    guidelines = rag.query_guidelines(template_name, sec, top_k=2) or []
                elif hasattr(rag, "query_rules"):
                    rule_matches = rag.query_rules(template_name, sec, top_k=2) or []
                    guidelines = [r.get("text", "") for r in rule_matches if isinstance(r, dict) and r.get("text")]
                if guidelines:
                    rules_context += f"\n- {sec.title()}: {' '.join(guidelines)}"

            context_blocks = [
                {
                    "id": b.block_id,
                    "text": (b.text or "")[:120],
                    "type": b.metadata.get("semantic_intent") or getattr(b, "semantic_intent", ""),
                }
                for b in doc_obj.blocks[:12]
            ]

            if hasattr(reasoner, "generate_instruction_set"):
                timeout_sec = int(_s.PIPELINE_REASONING_TIMEOUT_SECONDS)
                import threading

                cancel_event = threading.Event()
                try:
                    if self._run_with_timeout:
                        semantic_advice = (
                            self._run_with_timeout(
                                reasoner.generate_instruction_set,
                                timeout_sec,
                                context_blocks,
                                rules_context,
                                1,
                                cancel_event=cancel_event,
                                cancellation_event=cancel_event,
                            )
                            or {}
                        )
                    else:
                        semantic_advice = reasoner.generate_instruction_set(context_blocks, rules_context, 1) or {}
                except TimeoutError:
                    logger.warning("AI reasoning timed out after %ss for job %s.", timeout_sec, job_id)
                    semantic_advice = {}
                except Exception as exc:
                    logger.warning("AI reasoning failed for job %s: %s.", job_id, exc)
                    semantic_advice = {}

                for instruction in semantic_advice.get("instructions", []):
                    if instruction.get("confidence", 0) < 0.70:
                        instruction["review_required"] = True

        return semantic_advice

    @staticmethod
    def _resolve_rag_engine():
        from app.utils.singleton import resolve_optional_callable

        return resolve_optional_callable(
            "app.pipeline.intelligence.rag_engine",
            "get_rag_engine",
        )

    @staticmethod
    def _resolve_reasoning_engine():
        from app.utils.singleton import resolve_optional_callable

        return resolve_optional_callable(
            "app.pipeline.intelligence.reasoning_engine",
            "get_reasoning_engine",
        )

    # ------------------------------------------------------------------ #
    #  Stage: Validation                                                  #
    # ------------------------------------------------------------------ #

    @retry_with_backoff(max_retries=2, backoff_factor=1.0)
    def run_validation(self, doc_obj):
        from app.pipeline.orchestrator import DocumentValidator

        validator = DocumentValidator(contracts_dir=self.contracts_dir)
        if self._run_with_timeout:
            return self._run_with_timeout(validator.process, 60, doc_obj)
        return validator.process(doc_obj)

    # ------------------------------------------------------------------ #
    #  Stage: Formatting                                                  #
    # ------------------------------------------------------------------ #

    @retry_with_backoff(max_retries=2, backoff_factor=1.0)
    def run_formatting(self, doc_obj):
        from app.pipeline.orchestrator import Formatter

        formatter = Formatter(templates_dir=self.templates_dir, contracts_dir=self.contracts_dir)
        if self._run_with_timeout:
            return self._run_with_timeout(formatter.process, 60, doc_obj)
        return formatter.process(doc_obj)

    # ------------------------------------------------------------------ #
    #  Stage: Export                                                      #
    # ------------------------------------------------------------------ #

    def export_document(self, doc_obj, input_path, job_id):
        from app.pipeline.orchestrator import Exporter

        exporter = Exporter()
        out_dir = os.path.join("output", str(job_id))
        os.makedirs(out_dir, exist_ok=True)
        out_name = f"{os.path.splitext(os.path.basename(input_path))[0]}_formatted.docx"
        output_path = os.path.abspath(os.path.join(out_dir, out_name))
        doc_obj.output_path = output_path
        exporter.process(doc_obj)
        return output_path
