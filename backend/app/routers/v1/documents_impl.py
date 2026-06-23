# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import asyncio
import copy
import logging
import os
import uuid
import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from typing import Optional, Dict, Any, List
from datetime import datetime
from time import monotonic

from fastapi import Depends, UploadFile, File, HTTPException, BackgroundTasks, Query, Form, Request
from app.utils.dependencies import get_current_user, get_optional_user
from app.utils.logging_context import log_extra
from app.schemas.user import User
from app.services.document_service import DocumentService
from app.services.audit_log_service import audit_log_service
from app.services.enhancement_manager import enhancement_manager
from app.pipeline.orchestrator import PipelineOrchestrator
from app.pipeline.export.latex_exporter import LaTeXExporter
from app.pipeline.export.pdf_exporter import PDFExporter
from app.config.settings import settings
from app.utils.virus_scanner import virus_scanner
from app.exceptions import DatabaseUnavailableError

# ── Old SQLAlchemy imports (kept for reference, replaced by DocumentService) ───
# from sqlalchemy import exc
# from app.db.session import SessionLocal
# from app.models import Document, ProcessingStatus, DocumentResult

logger = logging.getLogger(__name__)
_STATUS_CACHE_MISS = object()
_status_cache_lock: asyncio.Lock | None = None
_status_response_cache: dict[str, tuple[float, Dict[str, Any]]] = {}
_MAX_STALE_STATUS_SECONDS = 90.0

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
_READY_FOR_EXPORT_STATUSES = {"COMPLETED", "COMPLETED_WITH_WARNINGS"}
_SUPPORTED_EXPORT_FORMATS = {"docx", "pdf", "tex"}
MAX_DAILY_UPLOADS = 20

ACCEPTED_EXTENSIONS = {
    ".docx",
    ".doc",
    ".pdf",
    ".odt",
    ".rtf",
    ".tex",
    ".txt",
    ".html",
    ".htm",
    ".md",
    ".markdown",
}


async def _scan_uploaded_file(file_path: str) -> dict[str, str | bool]:
    scan_result = await virus_scanner.scan(file_path)
    if not scan_result.get("clean", True):
        try:
            os.remove(file_path)
        except OSError:
            pass
        raise HTTPException(
            status_code=422,
            detail=f"Malware detected: {scan_result.get('result', 'unknown')}",
        )
    return scan_result

TEXT_EXTENSIONS = {".tex", ".txt", ".html", ".htm", ".md", ".markdown"}
MAGIC_BYTES_MAP = {
    b"\x50\x4b\x03\x04": {".docx", ".odt"},  # ZIP-backed Office/OpenDocument
    b"\x50\x4b\x05\x06": {".docx", ".odt"},  # Empty ZIP archive
    b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1": {".doc"},  # CFB (legacy Word)
    b"%PDF": {".pdf"},
    b"{\\rtf": {".rtf"},
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_status_cache_lock() -> asyncio.Lock:
    global _status_cache_lock
    if _status_cache_lock is None:
        _status_cache_lock = asyncio.Lock()
    return _status_cache_lock


def _document_status_ttl_seconds() -> float:
    raw_ttl = getattr(settings, "DOCUMENT_STATUS_CACHE_TTL_SECONDS", 1)
    try:
        ttl = float(raw_ttl)
    except (TypeError, ValueError):
        ttl = 1.0
    return max(0.0, ttl)


def _status_cache_key(job_id: str, current_user: Optional[User]) -> str:
    user_id = getattr(current_user, "id", None) if current_user is not None else None
    owner_segment = str(user_id) if user_id is not None else "__anon__"
    return f"{owner_segment}|{str(job_id)}"


def _clone_status_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return copy.deepcopy(payload)


async def _get_cached_status_response(cache_key: str) -> Any:
    ttl_seconds = _document_status_ttl_seconds()
    if ttl_seconds <= 0:
        return _STATUS_CACHE_MISS

    now = monotonic()
    async with _get_status_cache_lock():
        cached = _status_response_cache.get(cache_key)
        if not cached:
            return _STATUS_CACHE_MISS

        expiry, payload = cached
        if now >= expiry:
            return _STATUS_CACHE_MISS

        return _clone_status_payload(payload)


async def _get_stale_status_response(cache_key: str, *, max_stale_seconds: float = _MAX_STALE_STATUS_SECONDS) -> Any:
    ttl_seconds = _document_status_ttl_seconds()
    if ttl_seconds <= 0:
        return _STATUS_CACHE_MISS

    now = monotonic()
    async with _get_status_cache_lock():
        cached = _status_response_cache.get(cache_key)
        if not cached:
            return _STATUS_CACHE_MISS

        expiry, payload = cached
        stale_age = max(0.0, now - expiry)
        if stale_age > max_stale_seconds:
            _status_response_cache.pop(cache_key, None)
            return _STATUS_CACHE_MISS

        return _clone_status_payload(payload)


async def _set_cached_status_response(cache_key: str, payload: Dict[str, Any]) -> None:
    ttl_seconds = _document_status_ttl_seconds()
    async with _get_status_cache_lock():
        if ttl_seconds <= 0:
            _status_response_cache.pop(cache_key, None)
            return
        now = monotonic()
        _status_response_cache[cache_key] = (
            now + ttl_seconds,
            _clone_status_payload(payload),
        )
        stale_cutoff = now - _MAX_STALE_STATUS_SECONDS
        stale_keys = [
            key
            for key, (expiry, _) in _status_response_cache.items()
            if (expiry - ttl_seconds) < stale_cutoff
        ]
        for key in stale_keys:
            _status_response_cache.pop(key, None)


def _reset_document_status_cache_for_tests() -> None:
    global _status_cache_lock
    _status_response_cache.clear()
    _status_cache_lock = None


def _require_db():
    """Raise HTTP 503 when the Supabase client is not configured."""
    from app.db.supabase_client import get_supabase_client
    if get_supabase_client() is None:
        raise HTTPException(
            status_code=503,
            detail="Database not configured. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.",
        )


def _compute_sha256(filepath: str) -> str:
    """Compute a file SHA256 digest without loading the full file into memory."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _enforce_daily_upload_quota(current_user: Optional[User]) -> None:
    # Daily limits are enforced by TierRateLimitMiddleware (guest-only for now).
    return


def _record_upload_ack_duration(started_at: float) -> None:
    try:
        from app.middleware.prometheus_metrics import MetricsManager

        MetricsManager.record_upload_ack_duration(max(0.0, monotonic() - started_at))
    except Exception:
        pass


def _normalize_provider_name(value: Any) -> Optional[str]:
    token = str(value or "").strip().lower()
    if not token:
        return None
    if token.startswith("nvidia"):
        return "nvidia"
    if token.startswith("groq"):
        return "groq"
    if token.startswith("ollama") or token.startswith("deepseek"):
        return "ollama"
    if token.startswith("gpt") or token.startswith("openai"):
        return "openai"
    if token.startswith("anthropic") or token.startswith("claude"):
        return "anthropic"
    if "rule" in token:
        return "rule_based"
    return token


def _extract_quality_payload(result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    validation_results = (result or {}).get("validation_results") or {}
    quality_summary = validation_results.get("quality_summary") or {}
    quality = None
    overall_score = validation_results.get("quality_score") or quality_summary.get("overall_score") or quality_summary.get("quality_score")
    template_compliance = quality_summary.get("template_compliance")
    if template_compliance is None:
        template_compliance = quality_summary.get("template_compliance_pct")
    content_quality = quality_summary.get("content_quality")
    if content_quality is None:
        content_quality = quality_summary.get("content_completeness_pct")
    citation_count = quality_summary.get("citation_count")
    missing_sections = quality_summary.get("missing_sections") or []
    llm_provider_used = (
        _normalize_provider_name(quality_summary.get("llm_provider_used"))
        or _normalize_provider_name(validation_results.get("llm_provider_used"))
    )
    if llm_provider_used is None:
        ai_semantic_audit = validation_results.get("ai_semantic_audit") or {}
        llm_provider_used = _normalize_provider_name(
            ai_semantic_audit.get("llm_provider") or ai_semantic_audit.get("model")
        )

    if any(
        value is not None
        for value in (overall_score, template_compliance, content_quality, citation_count, llm_provider_used)
    ) or missing_sections:
        quality = {
            "overall_score": overall_score,
            "template_compliance": template_compliance,
            "content_quality": content_quality,
            "citation_count": citation_count,
            "missing_sections": missing_sections,
            "llm_provider_used": llm_provider_used,
        }
    return {
        "quality_score": overall_score,
        "quality_summary": quality_summary or None,
        "quality": quality,
    }


def _build_initial_status_payload(job_id: str) -> Dict[str, Any]:
    return {
        "job_id": job_id,
        "status": "PROCESSING",
        "current_phase": "UPLOAD",
        "phase": "UPLOAD",
        "progress_percentage": 0,
        "message": "Upload complete. Processing started...",
        "updated_at": None,
        "phases": [],
        "quality_score": None,
        "quality_summary": None,
        "quality": None,
    }


async def _validate_magic_bytes(
    file: UploadFile,
    *,
    content: Optional[bytes] = None,
    file_ext: Optional[str] = None,
) -> bytes:
    """
    Validate extension + file signature.
    Returns content bytes to avoid duplicate reads at call-sites.
    """
    payload = content if content is not None else await file.read()
    ext = (file_ext or os.path.splitext(file.filename or "")[1]).lower()

    if ext not in ACCEPTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{ext}'. Allowed types: {', '.join(sorted(ACCEPTED_EXTENSIONS))}",
        )

    if ext in TEXT_EXTENSIONS:
        try:
            payload.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail=f"File is not valid UTF-8 text for extension '{ext}'.",
            )
        return payload

    header = payload[:8]
    for magic, allowed_exts in MAGIC_BYTES_MAP.items():
        if header[: len(magic)] == magic and ext in allowed_exts:
            return payload

    raise HTTPException(
        status_code=400,
        detail=f"Unsupported file format or spoofed extension '{ext}'.",
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────

# ── Endpoint to get processing status (SSE) ────────────────────────────

async def upload_document_chunked(
    request: Request,
    background_tasks: BackgroundTasks,
    file_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    file: UploadFile = File(...),
    template: str = Form(settings.DEFAULT_TEMPLATE),
    add_page_numbers: bool = Form(True),
    add_borders: bool = Form(False),
    add_cover_page: bool = Form(False),
    generate_toc: bool = Form(False),
    add_line_numbers: bool = Form(False),
    line_spacing: Optional[float] = Form(None),
    page_size: str = Form("Letter"),
    fast_mode: bool = Form(False),
    current_user: User = Depends(get_current_user)
):
    """
    FEAT 42: Chunked file upload for large documents
    """
    _require_db()
    if chunk_index == 0:
        _enforce_daily_upload_quota(current_user)
    request_started_at = monotonic()
    
    import re
    if not re.match(r"^[a-zA-Z0-9-]+$", file_id):
        raise HTTPException(status_code=400, detail="Invalid file_id. Path traversal blocked.")
        
    # Store chunks in a temporary directory
    from pathlib import Path
    upload_dir = Path("data/uploads/temp")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Save the chunk with 5MB limit
    chunk_path = upload_dir / f"{file_id}.part{chunk_index}"
    try:
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Chunk exceeds 5MB limit.")
            
        with open(chunk_path, "wb") as f:
            f.write(content)
            
        # Check if all chunks have been received
        received_chunks = len(list(upload_dir.glob(f"{file_id}.part*")))
        if received_chunks == total_chunks:
            # Validate total assembled size before merging
            total_size = sum(p.stat().st_size for p in upload_dir.glob(f"{file_id}.part*"))
            if total_size > settings.MAX_FILE_SIZE:
                for p in upload_dir.glob(f"{file_id}.part*"):
                    p.unlink()
                raise HTTPException(status_code=413, detail=f"Total file size exceeds limit.")

            # Reassemble the file
            final_path = upload_dir / f"{file_id}_complete"
            hasher = hashlib.sha256()
            with open(final_path, "wb") as outfile:
                for i in range(total_chunks):
                    part_path = upload_dir / f"{file_id}.part{i}"
                    if part_path.exists():
                        with open(part_path, "rb") as infile:
                            chunk_data = infile.read()
                            hasher.update(chunk_data)
                            outfile.write(chunk_data)
                        os.remove(part_path)  # Cleanup piece

            original_filename = os.path.basename(file.filename or f"{file_id}.docx")
            file_ext = os.path.splitext(original_filename)[1].lower() or ".docx"
            if file_ext not in ACCEPTED_EXTENSIONS:
                final_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file type '{file_ext}'. Allowed types: {', '.join(sorted(ACCEPTED_EXTENSIONS))}",
                )

            assembled_content = final_path.read_bytes()
            await _validate_magic_bytes(file, content=assembled_content, file_ext=file_ext)

            job_id = uuid.uuid4()
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            file_path = os.path.abspath(os.path.join(UPLOAD_DIR, f"{job_id}{file_ext}"))
            upload_dir_abs = os.path.abspath(UPLOAD_DIR)
            if not file_path.startswith(upload_dir_abs):
                final_path.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail="Invalid file path detected")

            os.replace(final_path, file_path)
            scan_result = await _scan_uploaded_file(file_path)

            formatting_options = {
                "page_numbers": add_page_numbers,
                "borders": add_borders,
                "cover_page": add_cover_page,
                "toc": generate_toc,
                "line_numbers": add_line_numbers,
                "line_spacing": line_spacing,
                "page_size": page_size,
                "fast_mode": fast_mode,
                "virus_scan": scan_result,
            }

            created = await DocumentService.create_document(
                doc_id=str(job_id),
                user_id=str(current_user.id),
                filename=original_filename,
                template=template,
                original_file_path=file_path,
                formatting_options=formatting_options,
                file_hash=hasher.hexdigest(),
            )
            if created is None:
                try:
                    os.remove(file_path)
                except OSError:
                    pass
                raise HTTPException(status_code=503, detail="Database temporarily unavailable. Please retry later.")

            orchestrator = PipelineOrchestrator()
            dispatch_info = enhancement_manager.dispatch_document_pipeline(
                background_tasks=background_tasks,
                orchestrator=orchestrator,
                input_path=file_path,
                job_id=str(job_id),
                template_name=template,
                formatting_options=formatting_options,
                estimated_duration_seconds=10.0,
            )
            logger.info(
                "Chunk upload dispatch mode for job %s: %s",
                job_id,
                dispatch_info.get("mode"),
                extra=log_extra(job_id=job_id),
            )

            await audit_log_service.log(
                user_id=str(current_user.id) if current_user else None,
                action="upload",
                resource_type="document",
                resource_id=str(job_id),
                ip_address=request.client.host if request.client else None,
                details={
                    "filename": original_filename,
                    "template": template,
                    "chunked": True,
                },
            )

            await _set_cached_status_response(
                _status_cache_key(str(job_id), current_user),
                _build_initial_status_payload(str(job_id)),
            )
            payload = {
                "status": "complete",
                "job_id": str(job_id),
                "file_id": file_id,
                "file_hash": hasher.hexdigest(),
            }
            _record_upload_ack_duration(request_started_at)
            return payload
            
        payload = {
            "status": "chunk_received",
            "chunk_index": chunk_index,
            "total_chunks": total_chunks
        }
        _record_upload_ack_duration(request_started_at)
        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling chunked upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload chunk.")

async def list_documents(
    status: Optional[str] = Query(None, description="Filter by status (PROCESSING, COMPLETED, FAILED)"),
    template: Optional[str] = Query(None, description="Filter by template (IEEE, Springer, APA)"),
    start_date: Optional[datetime] = Query(None, description="Filter by created_at >= start_date"),
    end_date: Optional[datetime] = Query(None, description="Filter by created_at <= end_date"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    List documents for the current user with optional filtering and pagination.
    Returns empty list for anonymous users.
    """
    _require_db()

    if not current_user:
        return {"documents": [], "total": 0, "limit": limit, "offset": offset}

    try:
        documents = await DocumentService.list_documents(
            user_id=current_user.id,
            status=status,
            template=template,
            limit=limit,
            offset=offset,
        )
        total = await DocumentService.count_documents(
            user_id=current_user.id,
            status=status,
            template=template,
        )

        return {
            "documents": [
                {
                    "id": str(doc.get("id")),
                    "filename": doc.get("filename"),
                    "template": doc.get("template"),
                    "status": doc.get("status"),
                    "progress": doc.get("progress", 0),
                    "current_stage": doc.get("current_stage"),
                    "error_message": doc.get("error_message"),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at"),
                }
                for doc in documents
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except DatabaseUnavailableError:
        raise HTTPException(status_code=503, detail="Database temporarily unavailable. Please retry later.")
    except Exception as e:
        logger.error("Error listing documents: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    template: str = Form(settings.DEFAULT_TEMPLATE),
    add_page_numbers: bool = Form(True),
    add_borders: bool = Form(False),
    add_cover_page: bool = Form(False),
    generate_toc: bool = Form(False),
    add_line_numbers: bool = Form(False),
    line_spacing: Optional[float] = Form(None),
    page_size: str = Form("Letter"),
    fast_mode: bool = Form(False),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Handle document upload and trigger async background processing.
    """
    _require_db()
    _enforce_daily_upload_quota(current_user)
    request_started_at = monotonic()

    logger.debug("upload_document received template='%s' from request.", template)

    job_id = None
    try:
        # ── File validation ────────────────────────────────────────────────────

        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ACCEPTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type '{file_ext}'. Allowed types: {', '.join(sorted(ACCEPTED_EXTENSIONS))}"
            )

        safe_filename = os.path.basename(file.filename)
        if safe_filename != file.filename or '..' in file.filename:
            raise HTTPException(status_code=400, detail="Invalid filename. Path traversal detected.")

        file_content = await file.read()
        file_size = len(file_content)

        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large ({file_size / 1024 / 1024:.1f}MB). Maximum size is {settings.MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
            )

        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty. Please upload a valid document.")

        # ── Magic bytes validation ─────────────────────────────────────────
        file_content = await _validate_magic_bytes(file, content=file_content, file_ext=file_ext)

        # ── File storage ───────────────────────────────────────────────────────

        job_id = uuid.uuid4()
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_path = os.path.abspath(os.path.join(UPLOAD_DIR, f"{job_id}{file_ext}"))
        upload_dir_abs = os.path.abspath(UPLOAD_DIR)

        if not file_path.startswith(upload_dir_abs):
            raise HTTPException(status_code=400, detail="Invalid file path detected")

        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        scan_result = await _scan_uploaded_file(file_path)

        # ── DB insert via DocumentService ──────────────────────────────────────

        formatting_options = {
            "page_numbers": add_page_numbers,
            "borders": add_borders,
            "cover_page": add_cover_page,
            "toc": generate_toc,
            "line_numbers": add_line_numbers,
            "line_spacing": line_spacing,
            "page_size": page_size,
            "fast_mode": fast_mode,
            "virus_scan": scan_result,
        }

        file_hash = hashlib.sha256(file_content).hexdigest()

        created = await DocumentService.create_document(
            doc_id=str(job_id),
            user_id=str(current_user.id) if current_user else None,
            filename=safe_filename,
            template=template,
            original_file_path=file_path,
            formatting_options=formatting_options,
            file_hash=file_hash,
        )

        if created is None:
            raise HTTPException(status_code=503, detail="Database temporarily unavailable. Please retry later.")

        # ── Background pipeline ────────────────────────────────────────────────

        orchestrator = PipelineOrchestrator()
        dispatch_info = enhancement_manager.dispatch_document_pipeline(
            background_tasks=background_tasks,
            orchestrator=orchestrator,
            input_path=file_path,
            job_id=str(job_id),
            template_name=template,
            formatting_options=formatting_options,
            estimated_duration_seconds=10.0,
        )
        logger.info(
            "Upload dispatch mode for job %s: %s",
            job_id,
            dispatch_info.get("mode"),
            extra=log_extra(job_id=job_id),
        )

        await audit_log_service.log(
            user_id=str(current_user.id) if current_user else None,
            action="upload",
            resource_type="document",
            resource_id=str(job_id),
            ip_address=request.client.host if request.client else None,
            details={
                "filename": safe_filename,
                "template": template,
                "file_hash": file_hash,
            },
        )

        await _set_cached_status_response(
            _status_cache_key(str(job_id), current_user),
            _build_initial_status_payload(str(job_id)),
        )

        payload = {"message": "Processing started", "job_id": str(job_id), "status": "PROCESSING"}
        _record_upload_ack_duration(request_started_at)
        return payload

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(
            "Upload error: %s\n%s",
            e,
            traceback.format_exc(),
            extra=log_extra(job_id=job_id) if job_id else None,
        )
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


async def get_status(
    job_id: str,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get the detailed processing status of a document.
    """
    try:
        cache_key = _status_cache_key(job_id, current_user)
        cached_payload = await _get_cached_status_response(cache_key)
        if cached_payload is not _STATUS_CACHE_MISS:
            return cached_payload

        doc = await DocumentService.get_document(job_id)
        if not doc:
            # Briefly retry to tolerate transient DB reconnects / eventual consistency right after upload.
            await asyncio.sleep(0.25)
            doc = await DocumentService.get_document(job_id)

        if not doc:
            statuses = await DocumentService.get_processing_statuses(job_id)
            if statuses:
                latest = max(
                    statuses,
                    key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""),
                )
                payload = {
                    "job_id": job_id,
                    "status": latest.get("status") or "PROCESSING",
                    "current_phase": latest.get("phase") or "UPLOADED",
                    "phase": latest.get("phase") or "UPLOADED",
                    "progress_percentage": latest.get("progress_percentage") or 0,
                    "message": latest.get("message") or "Processing...",
                    "updated_at": latest.get("updated_at") or latest.get("created_at"),
                    "phases": [
                        {
                            "phase": s.get("phase"),
                            "status": s.get("status"),
                            "message": s.get("message"),
                            "progress": s.get("progress_percentage"),
                            "updated_at": s.get("updated_at"),
                        }
                        for s in statuses
                    ],
                    "quality_score": None,
                    "quality_summary": None,
                    "quality": None,
                }
                await _set_cached_status_response(cache_key, payload)
                return payload

            stale_payload = await _get_stale_status_response(cache_key)
            if stale_payload is not _STATUS_CACHE_MISS:
                stale_payload["message"] = "Reconnecting to status backend. Retrying..."
                stale_payload["stale"] = True
                return stale_payload

            raise HTTPException(status_code=404, detail="Document job not found")

        # Security: ownership check
        if doc.get("user_id") is not None:
            if not current_user or str(doc["user_id"]) != str(current_user.id):
                raise HTTPException(status_code=403, detail="Not authorized to access this document")

        statuses = await DocumentService.get_processing_statuses(job_id)
        doc_status = str(doc.get("status") or "").upper()
        should_fetch_result = doc_status in _READY_FOR_EXPORT_STATUSES
        result = await DocumentService.get_document_result(job_id) if should_fetch_result else None
        quality_payload = _extract_quality_payload(result)

        payload = {
            "job_id": job_id,
            "status": doc.get("status"),
            "current_phase": doc.get("current_stage") or "UPLOADED",
            "phase": doc.get("current_stage") or "UPLOADED",
            "progress_percentage": doc.get("progress") or 0,
            "message": doc.get("error_message") or (
                (doc.get("current_stage") + "...") if doc.get("current_stage") else "Processing..."
            ),
            "updated_at": doc.get("updated_at") or doc.get("created_at"),
            "phases": [
                {
                    "phase": s.get("phase"),
                    "status": s.get("status"),
                    "message": s.get("message"),
                    "progress": s.get("progress_percentage"),
                    "updated_at": s.get("updated_at"),
                }
                for s in statuses
            ],
            "quality_score": quality_payload["quality_score"],
            "quality_summary": quality_payload["quality_summary"],
            "quality": quality_payload["quality"],
        }
        await _set_cached_status_response(cache_key, payload)
        return payload
    except HTTPException:
        raise
    except DatabaseUnavailableError:
        raise HTTPException(status_code=503, detail="Database temporarily unavailable")
    except Exception as e:
        logger.error("Status check failed for job %s: %s", job_id, e)
        raise HTTPException(status_code=500, detail="Status check failed")


async def get_document_summary(
    job_id: str,
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Lightweight job summary for URL-based page hydration."""
    doc = await DocumentService.get_document(job_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")

    if doc.get("user_id") is not None:
        if not current_user or str(doc["user_id"]) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to access this document")

    status = doc.get("status")
    result = await DocumentService.get_document_result(job_id) if status in _READY_FOR_EXPORT_STATUSES else None
    quality_payload = _extract_quality_payload(result)
    return {
        "id": job_id,
        "status": status,
        "filename": doc.get("filename"),
        "template": doc.get("template"),
        "created_at": doc.get("created_at"),
        "output_path": doc.get("output_path") if status in _READY_FOR_EXPORT_STATUSES else None,
        "quality": quality_payload["quality"],
    }


async def edit_document(
    request: Request,
    job_id: str,
    data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Handle user edits and trigger non-destructive re-formatting.
    """
    try:
        doc = await DocumentService.get_document(job_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        if doc.get("user_id") is not None:
            if not current_user or str(doc["user_id"]) != str(current_user.id):
                raise HTTPException(status_code=403, detail="Not authorized to edit this document")

        edited_data = data.get("edited_structured_data")
        if not edited_data:
            raise HTTPException(status_code=400, detail="Missing edited_structured_data")

        orchestrator = PipelineOrchestrator()
        dispatch_info = enhancement_manager.dispatch_edit_flow(
            background_tasks=background_tasks,
            orchestrator=orchestrator,
            job_id=job_id,
            edited_structured_data=edited_data,
            template_name=doc.get("template"),
            estimated_duration_seconds=8.0,
        )
        logger.info("Edit dispatch mode for job %s: %s", job_id, dispatch_info.get("mode"))

        await audit_log_service.log(
            user_id=str(current_user.id) if current_user else None,
            action="edit",
            resource_type="document",
            resource_id=str(job_id),
            ip_address=request.client.host if request.client else None,
            details={
                "filename": doc.get("filename"),
                "template": doc.get("template"),
                "edited_structured_data_keys": sorted((edited_data or {}).keys()) if isinstance(edited_data, dict) else [],
            },
        )

        return {"message": "Edit received, re-formatting started", "job_id": job_id, "status": "PROCESSING"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error editing document %s: %s", job_id, e)
        raise HTTPException(status_code=500, detail=f"Edit failed: {str(e)}")


async def get_preview(
    job_id: str,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get the structured preview data for a document.
    """
    try:
        doc = await DocumentService.get_document(job_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document job not found")

        if doc.get("user_id") is not None:
            if not current_user or str(doc["user_id"]) != str(current_user.id):
                raise HTTPException(status_code=403, detail="Not authorized to preview this document")

        result = await DocumentService.get_document_result(job_id)
        if not result:
            raise HTTPException(status_code=404, detail="Processing results not found")

        quality_payload = _extract_quality_payload(result)

        return {
            "structured_data": result.get("structured_data"),
            "validation_results": result.get("validation_results"),
            "quality_score": quality_payload["quality_score"],
            "quality_summary": quality_payload["quality_summary"],
            "quality": quality_payload["quality"],
            "metadata": {
                "filename": doc.get("filename"),
                "template": doc.get("template"),
                "status": doc.get("status"),
                "created_at": doc.get("created_at"),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving preview for %s: %s", job_id, e)
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


async def get_comparison_data(
    job_id: str,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get data for side-by-side comparison with HTML diff.
    """
    import difflib

    try:
        doc = await DocumentService.get_document(job_id)
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

        result = await DocumentService.get_document_result(job_id)
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

        html_diff = difflib.HtmlDiff(wrapcolumn=80).make_file(
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error comparing documents for %s: %s", job_id, e)
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


async def download_document(
    request: Request,
    job_id: str,
    format: str = "docx",
    token: Optional[str] = Query(None),
    expires: Optional[int] = Query(None),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Download the processed document in DOCX or PDF format.
    Returns actual binary file stream.
    """
    from fastapi.responses import FileResponse

    try:
        doc = await DocumentService.get_document(job_id)
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
            signed = DocumentService.generate_signed_download_url(
                file_url=base_url,
                file_path=output_path,
                secret=settings.SIGNED_URL_SECRET,
                expires_in_seconds=3600,
                download_format=requested_format,
            )
            return {"url": signed["url"], "expires": signed["expires"]}

        if not settings.SIGNED_URL_SECRET:
            raise HTTPException(status_code=500, detail="Signed download secret not configured.")

        if not DocumentService.verify_signed_download(
            file_path=output_path,
            token=token,
            expires=expires,
            secret=settings.SIGNED_URL_SECRET,
            download_format=requested_format,
        ):
            raise HTTPException(status_code=403, detail="Invalid or expired download token.")

        base_filename = os.path.splitext(doc.get("filename") or "document")[0]
        filename = f"{base_filename}_formatted.docx"

        # --- A14: Verify SHA256 integrity for generated DOCX downloads ---
        if requested_format == "docx":
            stored_hash = (doc.get("output_hash") or "").strip()
            if stored_hash:
                actual_hash = _compute_sha256(output_path)
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
                try:
                    exporter = PDFExporter()
                    generated_path = exporter.convert_to_pdf(output_path, os.path.dirname(output_path))
                    if not generated_path:
                        raise HTTPException(status_code=500, detail="PDF conversion failed unexpectedly.")
                    pdf_path = generated_path
                except RuntimeError as re:
                    logger.error("PDF Export Error for job %s: %s", job_id, re)
                    raise HTTPException(status_code=400, detail=f"PDF export unavailable: {str(re)}")
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error("Unexpected PDF Error for job %s: %s", job_id, e)
                    raise HTTPException(status_code=500, detail="An internal error occurred during PDF export.")

            path_to_serve = pdf_path
            media_type = "application/pdf"
            filename = f"{base_filename}_formatted.pdf"

        if requested_format == "tex":
            tex_path = output_path.replace(".docx", ".tex")
            if not os.path.exists(tex_path):
                try:
                    exporter = LaTeXExporter()
                    generated_path = exporter.convert_to_latex(output_path, os.path.dirname(output_path))
                    if not generated_path:
                        raise HTTPException(status_code=500, detail="LaTeX conversion failed unexpectedly.")
                    tex_path = generated_path
                except RuntimeError as runtime_error:
                    logger.error("LaTeX Export Error for job %s: %s", job_id, runtime_error)
                    raise HTTPException(status_code=400, detail=str(runtime_error))
                except HTTPException:
                    raise
                except Exception as exc:
                    logger.error("Unexpected LaTeX Error for job %s: %s", job_id, exc)
                    raise HTTPException(status_code=500, detail="An internal error occurred during LaTeX export.")

            path_to_serve = tex_path
            media_type = "application/x-latex"
            filename = f"{base_filename}_formatted.tex"

        return FileResponse(path=path_to_serve, media_type=media_type, filename=filename)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error downloading document %s: %s", job_id, e)
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


async def delete_document(
    request: Request,
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a document and its associated output files.
    Requires authentication and ownership verification.
    """
    try:
        doc = await DocumentService.get_document(job_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Ownership check
        if doc.get("user_id") is not None:
            if str(doc["user_id"]) != str(current_user.id):
                raise HTTPException(status_code=403, detail="Not authorized to delete this document")

        # Remove output file if it exists
        output_path = doc.get("output_path")
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError as e:
                logger.warning("Failed to remove output file %s: %s", output_path, e)

        # Remove uploaded file if it exists
        original_path = doc.get("original_file_path")
        if original_path and os.path.exists(original_path):
            try:
                os.remove(original_path)
            except OSError as e:
                logger.warning("Failed to remove uploaded file %s: %s", original_path, e)

        # Delete from database
        await DocumentService.delete_document(job_id, str(current_user.id))

        await audit_log_service.log(
            user_id=str(current_user.id) if current_user else None,
            action="delete",
            resource_type="document",
            resource_id=str(job_id),
            ip_address=request.client.host if request.client else None,
            details={"filename": doc.get("filename")},
        )

        return {"status": "deleted", "job_id": job_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting document %s: %s", job_id, e)
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


# ── FEAT 39: Batch Upload ──────────────────────────────────────────────────────

async def batch_upload(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    template: str = Form("none"),
    current_user: User = Depends(get_current_user),
):
    """
    Upload multiple documents at once. Each file is processed independently.
    Maximum 10 files per batch.
    """
    _require_db()
    _enforce_daily_upload_quota(current_user)

    if len(files) > settings.MAX_BATCH_FILES:
        raise HTTPException(status_code=400, detail=f"Maximum {settings.MAX_BATCH_FILES} files per batch upload.")

    # Daily upload caps are enforced by TierRateLimitMiddleware (guest-only for now).

    results = []
    for file in files:
        job_id = str(uuid.uuid4())
        try:
            # Validate file extension
            ext = os.path.splitext(file.filename or "")[1].lower()
            if ext not in ACCEPTED_EXTENSIONS:
                results.append({
                    "filename": file.filename,
                    "status": "rejected",
                    "reason": f"Unsupported format: {ext}",
                })
                continue

            # Save file
            safe_name = f"{job_id}{ext}"
            file_path = os.path.join(UPLOAD_DIR, safe_name)
            content = await file.read()

            if len(content) > settings.MAX_FILE_SIZE:
                results.append({
                    "filename": file.filename,
                    "status": "rejected",
                    "reason": f"File exceeds {settings.MAX_FILE_SIZE // (1024 * 1024)}MB limit",
                })
                continue

            # A-FIX-17: Shared magic-byte validation for every file in batch.
            content = await _validate_magic_bytes(file, content=content, file_ext=ext)

            with open(file_path, "wb") as f:
                f.write(content)

            # Create DB record
            await DocumentService.create_document(
                doc_id=job_id,
                filename=file.filename,
                original_file_path=file_path,
                template=template,
                user_id=str(current_user.id) if current_user else None,
                file_hash=hashlib.sha256(content).hexdigest(),
            )

            # Start background processing
            orchestrator = PipelineOrchestrator()
            dispatch_info = enhancement_manager.dispatch_document_pipeline(
                background_tasks=background_tasks,
                orchestrator=orchestrator,
                input_path=file_path,
                job_id=job_id,
                template_name=template,
                formatting_options={},
                queue_name="batch",
                estimated_duration_seconds=12.0,
            )
            logger.info(
                "Batch upload dispatch mode for job %s: %s",
                job_id,
                dispatch_info.get("mode"),
                extra=log_extra(job_id=job_id),
            )

            results.append({
                "filename": file.filename,
                "job_id": job_id,
                "status": "processing",
            })

        except Exception as e:
            logger.error(
                "Batch upload failed for %s: %s",
                file.filename,
                e,
                extra=log_extra(job_id=job_id),
            )
            results.append({
                "filename": file.filename,
                "status": "failed",
                "reason": "An internal error occurred during batch processing.",
            })

    await audit_log_service.log(
        user_id=str(current_user.id) if current_user else None,
        action="batch_upload",
        resource_type="document_batch",
        resource_id=None,
        ip_address=request.client.host if request.client else None,
        details={
            "template": template,
            "file_count": len(files),
            "accepted_jobs": [item["job_id"] for item in results if item.get("job_id")],
            "rejected_files": [
                {"filename": item.get("filename"), "status": item.get("status")}
                for item in results
                if item.get("status") != "processing"
            ],
        },
    )

    return {"jobs": results, "total": len(results)}


