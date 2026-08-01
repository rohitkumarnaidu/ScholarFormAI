# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Document Validator - checks for structural and content validity.

All validation methods are wrapped in safe_function / safe_execution
so that a crash in any check degrades gracefully rather than aborting
the entire pipeline.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models import PipelineDocument as Document
from app.pipeline.base import PipelineStage
from app.pipeline.contracts.loader import ContractLoader
from app.pipeline.formatting.section_ordering import SectionOrderValidator
from app.pipeline.integrity.cross_ref import CrossReferenceEngine
from app.pipeline.safety.safe_execution import safe_execution, safe_function
from app.pipeline.services.crossref_client import CrossRefClient
from app.pipeline.validation.review_manager import ReviewManager

logger = logging.getLogger(__name__)


class ValidationResult(BaseModel):
    """Result of a document validation."""

    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DocumentValidator(PipelineStage):
    """
    Validates document structure and content completeness.
    Driven by contract rules.
    """

    def __init__(self, contracts_dir: str = "app/pipeline/contracts"):
        self.contract_loader = ContractLoader(contracts_dir=contracts_dir)
        self.order_validator = SectionOrderValidator(self.contract_loader)
        self.integrity_engine = CrossReferenceEngine()
        self.crossref_client = CrossRefClient()

    @staticmethod
    def _as_bool(value: Any, default: bool = False) -> bool:
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

    def process(self, document: Document) -> Document:
        """Standard pipeline stage entry point."""
        with safe_execution("Validator.process"):
            self.validate(document)
        return document

    @safe_function(
        fallback_value=ValidationResult(is_valid=False, errors=["Validation process crashed unexpectedly"]),
        error_message="Validator.validate failed",
    )
    def validate(self, document: Document) -> ValidationResult:
        """
        Run all validation checks.
        """
        start_time = datetime.now(UTC)

        errors = []
        warnings = []

        # 1. Section Completeness
        section_errors, section_warnings = self._check_sections(document)
        errors.extend(section_errors)
        warnings.extend(section_warnings)

        # 2. Figure Validation
        fig_errors, fig_warnings = self._check_figures(document)
        errors.extend(fig_errors)
        warnings.extend(fig_warnings)

        # 3. Reference Validation
        ref_errors, ref_warnings = self._check_references(document)
        errors.extend(ref_errors)
        warnings.extend(ref_warnings)

        # 4. Integrity / Cross-Reference Validation
        integrity_violations = self.integrity_engine.validate_integrity(document)
        for violation in integrity_violations:
            if "Dangling" in violation:
                errors.append(violation)
            else:
                warnings.append(violation)

        # 5. Table Validation
        table_errors, table_warnings = self._check_tables(document)
        errors.extend(table_errors)
        warnings.extend(table_warnings)

        # 6. CrossRef Validation (DOI) - optional in fast mode
        options = getattr(document, "formatting_options", {}) or {}
        if not self._as_bool(options.get("fast_mode"), False):
            doi_errors, doi_warnings = self._check_reference_integrity(document)
            # Treat as warnings for now to avoid blocking processing on external API failures
            warnings.extend(doi_warnings)
            warnings.extend(doi_errors)
        else:
            logger.debug("Validation fast mode enabled: skipping DOI CrossRef checks.")

        # 7. Confidence-Based HITL Signs
        review_manager = ReviewManager()
        review_manager.evaluate(document)

        # 7. Final Verdict
        is_valid = len(errors) == 0

        # Update Document
        document.is_valid = is_valid
        document.validation_errors = errors
        document.validation_warnings = warnings

        # Log
        duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
        document.add_processing_stage(
            stage_name="validation",
            status="success" if is_valid else "warning",
            message=f"Validation complete: {len(errors)} errors, {len(warnings)} warnings",
            duration_ms=duration_ms,
        )

        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings, stats=document.get_stats())

    def _check_sections(self, document: Document) -> tuple:
        errors = []
        warnings = []

        try:
            publisher = (
                document.template.template_name
                if document.template and hasattr(document.template, "template_name")
                else "IEEE"
            )
        except Exception:
            publisher = "IEEE"

        # Use contract-driven order validator
        try:
            order_violations = self.order_validator.validate_order(document, publisher)
            for violation in order_violations:
                if "Missing required" in violation:
                    errors.append(violation)
                else:
                    warnings.append(violation)
        except Exception as exc:
            logger.warning("Section order validation failed (non-fatal): %s", exc)
            warnings.append("Section order check skipped due to internal error")

        return errors, warnings

    def _check_figures(self, document: Document) -> tuple:
        errors = []
        warnings = []

        for fig in document.figures:
            if not fig.has_caption():
                warnings.append(f"Figure {fig.figure_id} missing caption")

        return errors, warnings

    def _check_references(self, document: Document) -> tuple:
        errors = []
        warnings = []

        if not document.references:
            # If References section exists but no references parsed -> Error
            # If References section missing -> Error/Warning handled above
            # If References section exists and references parsed -> check quality

            # Check if section exists
            sections = {s.lower() for s in document.get_section_names() if s}
            if "references" in sections:
                warnings.append("References section found but no reference entries parsed")
            return errors, warnings

        for ref in document.references:
            # Critical fields
            if not ref.year:
                warnings.append(f"Reference '{ref.citation_key}' missing publication year")
            if not ref.authors:
                errors.append(f"Reference '{ref.citation_key}' missing authors")
            if not ref.title:
                warnings.append(f"Reference '{ref.citation_key}' missing title")

        return errors, warnings

    def _check_tables(self, document: Document) -> tuple:
        warnings = []
        # Check Tables without captions
        if hasattr(document, "tables"):
            for i, table in enumerate(document.tables):
                if not table.caption_text:
                    warnings.append(f"Table {i + 1} missing caption")
        return [], warnings

    @safe_function(
        fallback_value=([], ["CrossRef validation skipped due to internal error"]),
        error_message="Reference integrity check failed",
    )
    def _check_reference_integrity(self, document: Document) -> tuple:
        """
        Validate references using CrossRef.
        """
        errors = []
        warnings = []

        if not document.references:
            return errors, warnings

        for ref in document.references:
            if ref.has_doi():
                try:
                    is_valid = self.crossref_client.validate_doi(ref.doi)

                    # Update reference metadata
                    if "validation" not in ref.metadata:
                        ref.metadata["validation"] = {}

                    ref.metadata["validation"]["crossref_checked"] = True
                    ref.metadata["validation"]["doi_valid"] = is_valid

                    if not is_valid:
                        warnings.append(f"Reference '{ref.citation_key}' has invalid DOI: {ref.doi}")
                        ref.metadata["validation"]["confidence"] = 0.0
                    else:
                        # Fetch metadata and calculate confidence
                        try:
                            cr_metadata = self.crossref_client.get_metadata(ref.doi)
                            ref_data = {"title": ref.title, "year": ref.year, "authors": ref.authors}
                            confidence = self.crossref_client.calculate_confidence(ref_data, cr_metadata)
                            ref.metadata["validation"]["confidence"] = confidence

                            if confidence < 0.5:
                                warnings.append(
                                    f"Reference '{ref.citation_key}' DOI match low confidence: {confidence:.2f}"
                                )

                        except Exception as e:
                            warnings.append(f"Failed to fetch metadata for DOI {ref.doi}: {str(e)}")

                except Exception as e:
                    warnings.append(f"CrossRef validation failed for {ref.citation_key}: {str(e)}")

        return errors, warnings


# Convenience
@safe_function(
    fallback_value=ValidationResult(is_valid=False, errors=["Global validation crashed unexpectedly"]),
    error_message="validate_document failed",
)
def validate_document(document: Document) -> ValidationResult:
    validator = DocumentValidator()
    return validator.validate(document)
