import asyncio
import contextlib
import logging
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.api.models import (
    FormatRequest,
    FormatResponse,
    PreviewRequest,
    PreviewResponse,
    StyleInfo,
    ValidateRequest,
    ValidateResponse,
)
from app.core.config import settings
from app.core.exceptions import StyleNotFoundError
from app.services.document_service import DocumentService
from app.services.formatter import ManuscriptFormatter
from app.services.parser import ManuscriptParser
from app.services.style_registry import StyleRegistry
from app.services.validator import ManuscriptValidator

logger = logging.getLogger(__name__)

router = APIRouter()
formatter = ManuscriptFormatter()
parser = ManuscriptParser()
validator = ManuscriptValidator()
style_registry = StyleRegistry()


@router.post("/format", response_model=FormatResponse, summary="Format a manuscript")
async def format_manuscript(request: FormatRequest):
    if not style_registry.get_style(request.style_id):
        raise StyleNotFoundError(request.style_id)

    style = style_registry.get_style(request.style_id)
    options = request.options

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        output_path = tmp.name

    try:
        doc_path = await asyncio.to_thread(formatter.format, request.manuscript, style, output_path, options)
        page_count = await asyncio.to_thread(formatter.estimate_pages, doc_path)
        logger.info(
            "Formatted manuscript '%s' with style '%s' (%d pages)",
            request.manuscript.title,
            request.style_id,
            page_count,
        )

        job_id = Path(doc_path).stem
        file_url = f"/api/v1/documents/{job_id}/download"
        secret = (
            getattr(settings, "SIGNED_URL_SECRET", None)
            or getattr(settings, "SECRET_KEY", None)
            or "default-secret-key"
        )
        try:
            signed = DocumentService.generate_signed_download_url(
                file_url=file_url,
                file_path=doc_path,
                secret=secret,
                expires_in_seconds=3600,
                download_format="docx",
            )
            download_url = signed["url"]
        except Exception:
            download_url = file_url

        return FormatResponse(
            download_url=download_url,
            pages=page_count,
            metadata={
                "title": request.manuscript.title,
                "sections": len(request.manuscript.sections),
            },
            style_applied=request.style_id,
        )
    except Exception as e:
        logger.error("Formatting failed: %s", str(e))
        raise HTTPException(status_code=422, detail=f"Formatting failed: {str(e)}")
    finally:
        if os.path.exists(output_path):
            with contextlib.suppress(OSError):
                os.remove(output_path)


@router.post("/validate", response_model=ValidateResponse, summary="Validate a manuscript")
async def validate_manuscript(request: ValidateRequest):
    if not style_registry.get_style(request.style_id):
        raise StyleNotFoundError(request.style_id)

    result = await asyncio.to_thread(validator.validate, request.manuscript, request.style_id)
    logger.info(
        "Validated manuscript '%s': valid=%s, errors=%d, warnings=%d",
        request.manuscript.title,
        result["valid"],
        len(result["errors"]),
        len(result["warnings"]),
    )
    return ValidateResponse(**result)


@router.post("/preview", response_model=PreviewResponse, summary="Generate HTML preview")
async def preview_manuscript(request: PreviewRequest):
    if not style_registry.get_style(request.style_id):
        raise StyleNotFoundError(request.style_id)

    style = style_registry.get_style(request.style_id)
    html = await asyncio.to_thread(formatter.generate_html_preview, request.manuscript, style)
    return PreviewResponse(html=html, style_applied=request.style_id)


@router.get("/styles", response_model=list[StyleInfo], summary="List all formatting styles")
async def list_styles():
    return style_registry.list_styles()


@router.get("/styles/{style_id}", response_model=StyleInfo, summary="Get style details")
async def get_style(style_id: str):
    if style_id not in [s["id"] for s in style_registry.list_styles()]:
        raise StyleNotFoundError(style_id)
    return style_registry.get_style_info(style_id)
