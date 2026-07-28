# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Document export service — handles PDF, LaTeX, and JATS compilation,
signed URL generation/verification, SHA256 integrity hashing, side-by-side
HTML comparison, and binary file download responses.
"""

from __future__ import annotations

import asyncio
import difflib
import hashlib
import logging
import os
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse

from app.config.settings import settings
from app.exceptions import DatabaseUnavailableError
from app.pipeline.export.latex_exporter import LaTeXExporter
from app.pipeline.export.pdf_exporter import PDFExporter
from app.schemas.user import User
from app.services.document_crud_service import DocumentCrudService

def _get_doc_service():
    from app.services.document_service import DocumentService
    return DocumentService

logger = logging.getLogger(__name__)

_READY_FOR_EXPORT_STATUSES = {"COMPLETED", "COMPLETED_WITH_WARNINGS"}
_SUPPORTED_EXPORT_FORMATS = {"docx", "pdf", "tex"}


class DocumentExportService:
    """
    Service responsible for document export, compilation, integrity verification,
    signed URLs, and side-by-side HTML comparison.
    """

    def __init__(
        self,
        crud_service: Optional[DocumentCrudService] = None,
        crud: Optional[DocumentCrudService] = None,
    ) -> None:
        self._crud = crud_service or crud or DocumentCrudService()

    @staticmethod
    def compute_sha256(filepath: str) -> str:
        """Compute a file SHA256 digest without loading the full file into memory."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def generate_signed_download_url(
        file_url: str,
        file_path: str,
        secret: str,
        expires_in_seconds: int = 3600,
        download_format: str = "docx",
    ) -> Dict[str, Any]:
        """Generate a HMAC-signed download URL."""
        return _get_doc_service().generate_signed_download_url(
            file_url=file_url,
            file_path=file_path,
            secret=secret,
            expires_in_seconds=expires_in_seconds,
            download_format=download_format,
        )

    @staticmethod
    def verify_signed_download(
        file_path: str,
        token: str,
        expires: int,
        secret: str,
        download_format: str = "docx",
    ) -> bool:
        """Verify an incoming HMAC-signed download request token."""
        return _get_doc_service().verify_signed_download(
            file_path=file_path,
            token=token,
            expires=expires,
            secret=secret,
            download_format=download_format,
        )

    def compile_pdf(self, input_docx_path: str, output_dir: str) -> str:
        """Compile/convert DOCX document to PDF format using PDFExporter."""
        try:
            exporter = PDFExporter()
            generated_path = exporter.convert_to_pdf(input_docx_path, output_dir)
            if not generated_path:
                raise HTTPException(status_code=500, detail="PDF conversion failed unexpectedly.")
            return generated_path
        except RuntimeError as re:
            logger.error("PDF Export Error: %s", re)
            raise HTTPException(status_code=400, detail=f"PDF export unavailable: {str(re)}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Unexpected PDF Error: %s", e)
            raise HTTPException(status_code=500, detail="An internal error occurred during PDF export.")

    def compile_latex(self, input_docx_path: str, output_dir: str) -> str:
        """Compile/convert DOCX document to LaTeX format using LaTeXExporter."""
        try:
            exporter = LaTeXExporter()
            generated_path = exporter.convert_to_latex(input_docx_path, output_dir)
            if not generated_path:
                raise HTTPException(status_code=500, detail="LaTeX conversion failed unexpectedly.")
            return generated_path
        except RuntimeError as runtime_error:
            logger.error("LaTeX Export Error: %s", runtime_error)
            raise HTTPException(status_code=400, detail=str(runtime_error))
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Unexpected LaTeX Error: %s", exc)
            raise HTTPException(status_code=500, detail="An internal error occurred during LaTeX export.")

    def compile_jats(self, document_id: str, output_dir: str) -> Dict[str, Any]:
        """Compile/export document to JATS XML format."""
        try:
            from app.pipeline.export.jats_exporter import JATSExporter

            exporter = JATSExporter()
            if not hasattr(exporter, "export"):
                raise HTTPException(status_code=501, detail="JATS export is not yet implemented.")
            result = exporter.export(str(document_id), str(output_dir or "."))
            return {
                "export_id": document_id,
                "format": "jats",
                "output_path": str(result),
                "status": "completed",
            }
        except ImportError:
            raise HTTPException(status_code=501, detail="JATS exporter is not available.")
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("JATS export failed for %s: %s", document_id, exc)
            raise HTTPException(status_code=500, detail=f"JATS export failed: {str(exc)}")

    async def get_comparison_data(
        self,
        job_id: str,
        current_user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """Get data for side-by-side comparison with HTML diff."""
        doc = await _get_doc_service().get_document(job_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        if doc.get("user_id") is not None:
            if not current_user or str(doc["user_id"]) != str(current_user.id):
                raise HTTPException(status_code=403, detail="Not authorized to access comparison data")

        if doc.get("status") not in _READY_FOR_EXPORT_STATUSES:
            logger.warning("Compare endpoint called too early for job %s. Status: %s", job_id, doc.get("status"))
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Comparison data not available. Job status: {doc.get('status')}. "
                    "Wait for COMPLETED or COMPLETED_WITH_WARNINGS status."
                ),
            )

        result = await _get_doc_service().get_document_result(job_id)
        if not result:
            logger.warning("DocumentResult missing for completed job %s", job_id)
            raise HTTPException(status_code=404, detail="Processing results not found")

        original_text = doc.get("raw_text") or ""
        formatted_text = ""
        structured_data = result.get("structured_data")
        if structured_data and isinstance(structured_data, dict):
            blocks = structured_data.get("blocks") or structured_data.get("sections", [])
            formatted_text = "\n\n".join([
                block.get("text", "") for block in blocks
                if isinstance(block, dict) and block.get("text")
            ])

        html_diff = await asyncio.to_thread(
            difflib.HtmlDiff(wrapcolumn=80).make_file,
            original_text.splitlines(keepends=True),
            formatted_text.splitlines(keepends=True),
            fromdesc="Original Document",
            todesc="Formatted Document",
            context=True,
            numlines=3,
        )

        return {
            "html_diff": html_diff,
            "original": {"raw_text": original_text, "structured_data": None},
            "formatted": {"structured_data": structured_data},
        }

    async def download_document(
        self,
        request: Request,
        job_id: str,
        format: str = "docx",
        token: Optional[str] = None,
        expires: Optional[int] = None,
        current_user: Optional[User] = None,
    ) -> Any:
        """Download the processed document in DOCX, PDF, or TeX format."""
        try:
            doc = await _get_doc_service().get_document(job_id)
            if not doc:
                raise HTTPException(status_code=404, detail="Document job not found")

            requested_format = (format or "").strip().lower()
            if requested_format not in _SUPPORTED_EXPORT_FORMATS:
                raise HTTPException(status_code=400, detail="Unsupported format. Supported: docx, pdf, tex")

            has_signed_token = token is not None or expires is not None
            if has_signed_token and (not token or expires is None):
                raise HTTPException(status_code=400, detail="Both token and expires are required for signed downloads.")

            if not has_signed_token and doc.get("user_id") is not None:
                if not current_user or str(doc["user_id"]) != str(current_user.id):
                    raise HTTPException(status_code=403, detail="Not authorized to download this document")

            if doc.get("status") not in _READY_FOR_EXPORT_STATUSES:
                logger.warning("Download endpoint called too early for job %s. Status: %s", job_id, doc.get("status"))
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Document not ready. Job status: {doc.get('status')}. "
                        "Wait for COMPLETED or COMPLETED_WITH_WARNINGS status."
                    ),
                )

            output_path = doc.get("output_path")
            if not output_path:
                logger.error("Output path missing for completed job %s", job_id)
                raise HTTPException(
                    status_code=500,
                    detail="Processing completed but output file path not set. Contact support.",
                )

            if not os.path.exists(output_path):
                logger.error("Output file missing on disk for job %s: %s", job_id, output_path)
                raise HTTPException(status_code=404, detail="Output file not found on server. File may have been deleted.")

            if not has_signed_token:
                if not settings.SIGNED_URL_SECRET:
                    raise HTTPException(status_code=500, detail="Signed download secret not configured.")
                parsed_request_url = urlsplit(str(request.url))
                filtered_query = [
                    (key, value)
                    for key, value in parse_qsl(parsed_request_url.query, keep_blank_values=True)
                    if key not in {"token", "expires"}
                ]
                base_url = urlunsplit(parsed_request_url._replace(query=urlencode(filtered_query)))
                signed = self.generate_signed_download_url(
                    file_url=base_url,
                    file_path=output_path,
                    secret=settings.SIGNED_URL_SECRET,
                    expires_in_seconds=3600,
                    download_format=requested_format,
                )
                return {"url": signed["url"], "expires": signed["expires"]}

            if not settings.SIGNED_URL_SECRET:
                raise HTTPException(status_code=500, detail="Signed download secret not configured.")

            if not self.verify_signed_download(
                file_path=output_path,
                token=token,  # type: ignore[arg-type]
                expires=expires,  # type: ignore[arg-type]
                secret=settings.SIGNED_URL_SECRET,
                download_format=requested_format,
            ):
                raise HTTPException(status_code=403, detail="Invalid or expired download token.")

            base_filename = os.path.splitext(doc.get("filename") or "document")[0]
            filename = f"{base_filename}_formatted.docx"

            # Verify SHA256 integrity for generated DOCX downloads
            if requested_format == "docx":
                stored_hash = (doc.get("output_hash") or "").strip()
                if stored_hash:
                    actual_hash = await asyncio.to_thread(self.compute_sha256, output_path)
                    if actual_hash != stored_hash:
                        logger.error(
                            "Output hash mismatch for job %s: expected=%s actual=%s",
                            job_id,
                            stored_hash,
                            actual_hash,
                        )
                        raise HTTPException(
                            status_code=500,
                            detail="Output integrity check failed. Please re-run processing.",
                        )
                else:
                    logger.warning("No stored output_hash for job %s. Skipping integrity comparison.", job_id)

            path_to_serve = output_path
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

            if requested_format == "pdf":
                pdf_path = output_path.replace(".docx", ".pdf")
                if not os.path.exists(pdf_path):
                    pdf_path = await asyncio.to_thread(self.compile_pdf, output_path, os.path.dirname(output_path))

                path_to_serve = pdf_path
                media_type = "application/pdf"
                filename = f"{base_filename}_formatted.pdf"

            if requested_format == "tex":
                tex_path = output_path.replace(".docx", ".tex")
                if not os.path.exists(tex_path):
                    tex_path = await asyncio.to_thread(self.compile_latex, output_path, os.path.dirname(output_path))

                path_to_serve = tex_path
                media_type = "application/x-latex"
                filename = f"{base_filename}_formatted.tex"

            return FileResponse(path=path_to_serve, media_type=media_type, filename=filename)

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error downloading document %s: %s", job_id, e)
            raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")
