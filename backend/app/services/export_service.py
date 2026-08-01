# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Export Service Facade — routes document export requests through the service layer.

Routers MUST use this facade instead of importing PDFExporter, LaTeXExporter,
or other export pipeline modules directly.
"""

from __future__ import annotations

import logging
from typing import Any

from app.exceptions import PipelineError, ValidationError

logger = logging.getLogger(__name__)

_SUPPORTED_EXPORT_FORMATS = {"docx", "pdf", "tex", "jats"}


class ExportService:
    """
    Facade for document export operations (PDF, LaTeX, JATS).

    Encapsulates all direct exporter pipeline imports behind a stable service interface.
    """

    async def export_document(
        self,
        document_id: str,
        export_format: str,
        output_dir: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Export a document in the requested format.

        Args:
            document_id: The document to export.
            export_format: One of 'docx', 'pdf', 'tex', 'jats'.
            output_dir: Optional output directory override.
            options: Additional export options.

        Returns:
            A dict with export_id, format, and output_path.

        Raises:
            ValidationError: If the format is unsupported.
            NotFoundError: If the source document cannot be found.
            PipelineError: If the export process fails.
        """
        normalized_format = (export_format or "").strip().lower()
        if normalized_format not in _SUPPORTED_EXPORT_FORMATS:
            raise ValidationError(
                message=f"Unsupported export format '{export_format}'. "
                f"Supported: {', '.join(sorted(_SUPPORTED_EXPORT_FORMATS))}.",
                details={"format": export_format, "supported": list(_SUPPORTED_EXPORT_FORMATS)},
            )

        if normalized_format == "pdf":
            return await self._export_pdf(document_id, output_dir, options or {})
        elif normalized_format == "tex":
            return await self._export_latex(document_id, output_dir, options or {})
        elif normalized_format == "jats":
            return await self._export_jats(document_id, output_dir, options or {})

        # docx: pass-through (already in docx format)
        return {
            "export_id": document_id,
            "format": "docx",
            "output_path": output_dir,
            "status": "completed",
        }

    async def _export_pdf(
        self,
        document_id: str,
        output_dir: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            from app.pipeline.export.pdf_exporter import PDFExporter

            exporter = PDFExporter()
            result = exporter.convert_to_pdf(
                str(document_id),
                str(output_dir or "."),
            )
            if not result:
                raise PipelineError(
                    message="PDF conversion returned no output.",
                    stage="export_pdf",
                    details={"document_id": document_id},
                )
            return {
                "export_id": document_id,
                "format": "pdf",
                "output_path": str(result),
                "status": "completed",
            }
        except PipelineError:
            raise
        except Exception as exc:
            logger.error("PDF export failed for %s: %s", document_id, exc)
            raise PipelineError(
                message="PDF export failed.",
                stage="export_pdf",
                details={"document_id": document_id, "error": str(exc)},
            ) from exc

    async def _export_latex(
        self,
        document_id: str,
        output_dir: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            from app.pipeline.export.latex_exporter import LaTeXExporter

            exporter = LaTeXExporter()
            result = exporter.export_to_latex(
                str(document_id),
                str(output_dir or "."),
            )
            return {
                "export_id": document_id,
                "format": "tex",
                "output_path": str(result),
                "status": "completed",
            }
        except Exception as exc:
            logger.error("LaTeX export failed for %s: %s", document_id, exc)
            raise PipelineError(
                message="LaTeX export failed.",
                stage="export_latex",
                details={"document_id": document_id, "error": str(exc)},
            ) from exc

    async def _export_jats(
        self,
        document_id: str,
        output_dir: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            from app.pipeline.export.jats_exporter import JATSExporter

            exporter = JATSExporter()
            # Check if JATS exporter exists (may not be implemented)
            if not hasattr(exporter, "export"):
                raise PipelineError(
                    message="JATS export is not yet implemented.",
                    stage="export_jats",
                    details={"document_id": document_id},
                )
            result = exporter.export(str(document_id), str(output_dir or "."))
            return {
                "export_id": document_id,
                "format": "jats",
                "output_path": str(result),
                "status": "completed",
            }
        except PipelineError:
            raise
        except ImportError:
            raise PipelineError(
                message="JATS exporter is not available.",
                stage="export_jats",
                details={"document_id": document_id},
            )
        except Exception as exc:
            logger.error("JATS export failed for %s: %s", document_id, exc)
            raise PipelineError(
                message="JATS export failed.",
                stage="export_jats",
                details={"document_id": document_id, "error": str(exc)},
            ) from exc

    async def get_export_status(self, export_id: str) -> dict[str, Any]:
        """
        Get the status of an export operation.

        Args:
            export_id: The export operation ID.

        Returns:
            Status dict.
        """
        return {
            "export_id": export_id,
            "status": "completed",
        }


# Singleton for dependency injection
export_service = ExportService()
