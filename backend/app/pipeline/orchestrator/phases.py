# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Pipeline Phases — Individual phase implementations extracted from
PipelineOrchestrator._run_pipeline_internal.

Each method on PipelinePhases corresponds to one logical phase of the
document processing pipeline and delegates to the orchestrator's services
via self.orchestrator.
"""

import os
import logging
from typing import Any, Optional, Tuple

from app.pipeline.orchestrator.stages import PipelineStages

logger = logging.getLogger(__name__)


class PipelinePhases:
    """Encapsulates each phase of the document processing pipeline.

    Each method corresponds to one phase in ``_run_pipeline_internal``
    and delegates to the orchestrator's services via ``self.orchestrator``.
    """

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    # ------------------------------------------------------------------ #
    #  Phase 1: Upload                                                    #
    # ------------------------------------------------------------------ #

    def phase_upload(self, job_id: str) -> None:
        self.orchestrator._update_status(
            job_id, "UPLOAD", "COMPLETED", "File uploaded.", progress=5
        )

    # ------------------------------------------------------------------ #
    #  Phase 2: Extraction                                                #
    # ------------------------------------------------------------------ #

    def phase_extraction(
        self,
        factory,
        input_path: str,
        job_id: str,
        formatting_options: dict,
        file_ext: str,
        sb,
        template_name: str,
    ):
        self.orchestrator._update_status(
            job_id, "EXTRACTION", "PROCESSING", progress=10
        )
        doc_obj = self.orchestrator._run_extraction_stage(
            factory, input_path, job_id, formatting_options, file_ext
        )
        doc_obj = self.orchestrator.stages.apply_llm_pdf_fallback(
            doc_obj, input_path, job_id, file_ext
        )
        self.orchestrator.stages.set_template(doc_obj, template_name)

        raw_text = "\n".join(b.text for b in doc_obj.blocks)
        if sb:
            sb.table("documents").update({
                "raw_text": raw_text,
                "original_file_path": input_path,
            }).eq("id", job_id).execute()

        self.orchestrator._update_status(
            job_id, "EXTRACTION", "COMPLETED", "Text extracted.", progress=20
        )

        # AI Extraction (GROBID + Docling)
        self.orchestrator._update_status(
            job_id,
            "EXTRACTION",
            "PROCESSING",
            "AI metadata extraction...",
            progress=22,
        )
        doc_obj = self.orchestrator.stages.extract_ai_metadata(
            doc_obj, input_path, file_ext, job_id
        )

        return doc_obj

    # ------------------------------------------------------------------ #
    #  Phase 3: Structure Detection                                       #
    # ------------------------------------------------------------------ #

    def phase_structure_detection(self, doc_obj, job_id: str):
        self.orchestrator._check_cancelled(job_id)
        self.orchestrator._update_status(
            job_id, "EXTRACTION", "PROCESSING", "Detecting structure...", progress=28
        )
        try:
            doc_obj = self.orchestrator._run_structure_detection(doc_obj)
            num_headings = len(getattr(doc_obj, "detected_headings", []))
            logger.info(
                "StructureDetector found %d headings for job %s",
                num_headings,
                job_id,
            )
        except Exception as sd_err:
            logger.warning("StructureDetector failed: %s. Proceeding.", sd_err)
        return doc_obj

    # ------------------------------------------------------------------ #
    #  Phase 4: Semantic Parsing                                          #
    # ------------------------------------------------------------------ #

    def phase_semantic_parsing(self, doc_obj):
        try:
            doc_obj = self.orchestrator._run_semantic_parsing(doc_obj)
        except Exception as e:
            logger.warning("Semantic parser failed: %s. Falling back.", e)
        return doc_obj

    # ------------------------------------------------------------------ #
    #  Phase 5: Classification                                            #
    # ------------------------------------------------------------------ #

    def phase_classification(self, doc_obj, job_id: str):
        self.orchestrator._update_status(
            job_id,
            "NLP_ANALYSIS",
            "PROCESSING",
            "Classifying content...",
            progress=40,
        )
        doc_obj = self.orchestrator._run_classification(doc_obj)
        self.orchestrator.stages.sync_block_confidence(doc_obj)
        return doc_obj

    # ------------------------------------------------------------------ #
    #  Phase 6: Content Analysis                                          #
    # ------------------------------------------------------------------ #

    def phase_content_analysis(
        self, doc_obj, job_id: str, runtime_flags: dict
    ):
        self.orchestrator._check_stage_interface(
            self.orchestrator.analyzer, "process", "ContentAnalyzer"
        )
        from app.pipeline.safety.retry_guard import execute_with_retry

        doc_obj = execute_with_retry(self.orchestrator.analyzer.process, doc_obj)
        doc_obj = self.orchestrator.stages.analyze_content(doc_obj, job_id)

        # Caption matching
        doc_obj = self.orchestrator.stages.match_captions(doc_obj)

        # Figure analysis (optional)
        if not runtime_flags.get("fast_mode", False):
            doc_obj = self.orchestrator.stages.run_figure_analysis(doc_obj)

        # Reference processing
        doc_obj = self.orchestrator.stages.process_references(doc_obj)

        self.orchestrator._update_status(
            job_id, "NLP_ANALYSIS", "COMPLETED", "Analysis complete.", progress=50
        )

        return doc_obj

    # ------------------------------------------------------------------ #
    #  Phase 7: Validation                                                #
    # ------------------------------------------------------------------ #

    def phase_validation(
        self,
        doc_obj,
        job_id: str,
        template_name: str,
        runtime_flags: dict,
    ) -> Tuple[Any, dict]:
        self.orchestrator._update_status(
            job_id, "VALIDATION", "PROCESSING", progress=60
        )
        if runtime_flags["crossref_enrichment"]:
            doc_obj = self.orchestrator.stages.run_crossref_validation(doc_obj)
        else:
            logger.info("Fast mode: skipping CrossRef enrichment.")

        self.orchestrator._update_status(
            job_id, "VALIDATION", "PROCESSING", "Applying styles...", progress=70
        )

        # AI Reasoning (optional)
        semantic_advice = {}
        if runtime_flags["ai_reasoning"]:
            semantic_advice = self.orchestrator.stages.run_ai_reasoning(
                doc_obj, template_name, job_id
            )
        else:
            logger.info("Fast mode: skipping AI reasoning.")

        if hasattr(doc_obj, "metadata") and doc_obj.metadata:
            doc_obj.metadata.ai_hints["semantic_advice"] = semantic_advice

        # Validation
        doc_obj = self.orchestrator._run_validation_stage(doc_obj)

        # Build quality summary
        validation_results = {
            "is_valid": doc_obj.is_valid,
            "errors": doc_obj.validation_errors,
            "warnings": doc_obj.validation_warnings,
            "stats": doc_obj.get_stats(),
            "ai_semantic_audit": semantic_advice,
        }
        quality_summary = self.orchestrator._build_quality_summary(
            doc_obj, validation_results
        )
        validation_results["quality_summary"] = quality_summary
        validation_results["quality_score"] = quality_summary.get("quality_score")
        self.orchestrator._log_quality_summary(job_id, quality_summary)

        return doc_obj, validation_results

    # ------------------------------------------------------------------ #
    #  Phase 8: Formatting                                                #
    # ------------------------------------------------------------------ #

    def phase_formatting(self, doc_obj):
        doc_obj = self.orchestrator._run_formatting_stage(doc_obj)
        return doc_obj

    # ------------------------------------------------------------------ #
    #  Phase 9: Export                                                    #
    # ------------------------------------------------------------------ #

    def phase_export(
        self, doc_obj, input_path: str, job_id: str, sb
    ) -> str:
        output_path = None
        if hasattr(doc_obj, "generated_doc") and doc_obj.generated_doc:
            output_path = self.orchestrator._export_document(
                doc_obj, input_path, job_id
            )
        else:
            logger.critical(
                "Formatter failed to produce generated_doc for job %s", job_id
            )
            if sb:
                sb.table("documents").update({
                    "status": "FAILED",
                    "error_message": "Formatting failed: No document artifact generated.",
                }).eq("id", job_id).execute()
            raise Exception("Formatting stage failed to generate output artifact.")
        return output_path

    # ------------------------------------------------------------------ #
    #  Phase 10: Persistence                                              #
    # ------------------------------------------------------------------ #

    def phase_persistence(
        self,
        doc_obj,
        job_id: str,
        sb,
        output_path: str,
        validation_results: dict,
        template_name: str,
    ) -> dict:
        response = {"status": "processing", "job_id": job_id, "message": ""}

        self.orchestrator._update_status(
            job_id, "PERSISTENCE", "PROCESSING", progress=90
        )
        from app.pipeline.orchestrator import AIExplainer

        explainer = AIExplainer()
        ai_explanations = explainer.explain_results(validation_results, template_name)
        validation_results["ai_explanations"] = ai_explanations
        from app.pipeline.orchestrator import build_structured_data

        structured_data = build_structured_data(doc_obj)

        doc_result_data = {
            "document_id": job_id,
            "structured_data": structured_data,
            "validation_results": validation_results,
            "created_at": "now()",
        }
        if sb:
            sb.table("document_results").insert(doc_result_data).execute()

        output_ready = bool(output_path and os.path.exists(output_path))
        if not output_ready and output_path and getattr(doc_obj, "generated_doc", None):
            output_ready = True

        if output_ready:
            if output_path and os.path.exists(output_path):
                try:
                    from app.services.document_service import DocumentService
                    DocumentService.update_output_hash(
                        job_id, PipelineStages.compute_sha256(output_path)
                    )
                except Exception as hash_exc:
                    logger.warning("Failed to persist output hash: %s", hash_exc)
            if sb:
                sb.table("documents").update({
                    "status": "COMPLETED",
                    "output_path": output_path,
                }).eq("id", job_id).execute()
            self.orchestrator._update_status(
                job_id,
                "PERSISTENCE",
                "COMPLETED",
                "All results persisted.",
                progress=100,
            )
            response["status"] = "success"
            response["message"] = "Processing complete."
            response["output_path"] = output_path
        else:
            if sb:
                sb.table("documents").update({
                    "status": "FAILED",
                    "error_message": "Output file generation failed.",
                }).eq("id", job_id).execute()
            self.orchestrator._update_status(
                job_id,
                "PERSISTENCE",
                "COMPLETED",
                "Output generation failed.",
                progress=100,
            )
            response["status"] = "error"
            response["message"] = "Processing failed: Output generation failed."

        return response
