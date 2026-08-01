# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Document pipeline service — orchestration, virus scanning, file validation,
chunk reassembly, batch upload processing, background pipeline dispatching,
and status response caching.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import logging
import os
import re
import sys
import uuid
from pathlib import Path
from time import monotonic
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, HTTPException, Request, UploadFile

from app.config.settings import settings
from app.exceptions import DatabaseUnavailableError, DocumentNotFoundError
from app.pipeline.orchestrator import PipelineOrchestrator
from app.schemas.user import User
from app.services.audit_log_service import audit_log_service
from app.services.document_crud_service import DocumentCrudService
from app.utils.logging_context import log_extra
from app.utils.virus_scanner import virus_scanner

logger = logging.getLogger(__name__)

# Status Cache globals and constants
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

TEXT_EXTENSIONS = {".tex", ".txt", ".html", ".htm", ".md", ".markdown"}
MAGIC_BYTES_MAP = {
    b"\x50\x4b\x03\x04": {".docx", ".odt"},
    b"\x50\x4b\x05\x06": {".docx", ".odt"},
    b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1": {".doc"},
    b"%PDF": {".pdf"},
    b"{\\rtf": {".rtf"},
}


def _reassemble_chunks_sync(upload_dir: Path, file_id: str, total_chunks: int, final_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(final_path, "wb") as outfile:
        for i in range(total_chunks):
            part_path = upload_dir / f"{file_id}.part{i}"
            if part_path.exists():
                with open(part_path, "rb") as infile:
                    chunk_data = infile.read()
                    hasher.update(chunk_data)
                    outfile.write(chunk_data)
                os.remove(part_path)
    return hasher.hexdigest()


def _get_impl_symbol(name: str, fallback: Any = None) -> Any:
    """Resolve symbol from app.routers.v1.documents_impl if patched during route tests."""
    try:
        impl = sys.modules.get("app.routers.v1.documents_impl")
        if impl is not None and hasattr(impl, name):
            val = getattr(impl, name)
            if val is not None:
                return val
    except Exception:
        pass
    return fallback


# ── Cache Helpers ─────────────────────────────────────────────────────────────


def _get_status_cache_lock() -> asyncio.Lock:
    global _status_cache_lock
    if _status_cache_lock is None:
        _status_cache_lock = asyncio.Lock()
    return _status_cache_lock


def _document_status_ttl_seconds(settings_override: Any = None) -> float:
    ttl_fn = _get_impl_symbol("_document_status_ttl_seconds")
    if ttl_fn is not None and getattr(ttl_fn, "__module__", "") != __name__:
        try:
            return float(ttl_fn())
        except Exception:
            pass

    s = settings_override or _get_impl_symbol("settings", settings)
    raw_ttl = getattr(s, "DOCUMENT_STATUS_CACHE_TTL_SECONDS", 1)
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


async def _get_cached_status_response(cache_key: str, settings_override: Any = None) -> Any:
    ttl_seconds = _document_status_ttl_seconds(settings_override=settings_override)
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


async def _get_stale_status_response(
    cache_key: str, *, max_stale_seconds: float = _MAX_STALE_STATUS_SECONDS, settings_override: Any = None
) -> Any:
    ttl_seconds = _document_status_ttl_seconds(settings_override=settings_override)
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


async def _set_cached_status_response(cache_key: str, payload: Dict[str, Any], settings_override: Any = None) -> None:
    ttl_seconds = _document_status_ttl_seconds(settings_override=settings_override)
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
            key for key, (expiry, _) in _status_response_cache.items() if (expiry - ttl_seconds) < stale_cutoff
        ]
        for key in stale_keys:
            _status_response_cache.pop(key, None)


def _reset_document_status_cache_for_tests() -> None:
    global _status_cache_lock
    _status_response_cache.clear()
    _status_cache_lock = None


def _require_db() -> None:
    """Raise HTTP 503 when the Supabase client is not configured."""
    from app.db.supabase_client import get_supabase_client

    if get_supabase_client() is None:
        raise HTTPException(
            status_code=503,
            detail="Database not configured. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.",
        )


def _enforce_daily_upload_quota(current_user: Optional[User]) -> None:
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
    overall_score = (
        validation_results.get("quality_score")
        or quality_summary.get("overall_score")
        or quality_summary.get("quality_score")
    )
    template_compliance = quality_summary.get("template_compliance")
    if template_compliance is None:
        template_compliance = quality_summary.get("template_compliance_pct")
    content_quality = quality_summary.get("content_quality")
    if content_quality is None:
        content_quality = quality_summary.get("content_completeness_pct")
    citation_count = quality_summary.get("citation_count")
    missing_sections = quality_summary.get("missing_sections") or []
    llm_provider_used = _normalize_provider_name(quality_summary.get("llm_provider_used")) or _normalize_provider_name(
        validation_results.get("llm_provider_used")
    )
    if llm_provider_used is None:
        ai_semantic_audit = validation_results.get("ai_semantic_audit") or {}
        llm_provider_used = _normalize_provider_name(
            ai_semantic_audit.get("llm_provider") or ai_semantic_audit.get("model")
        )

    if (
        any(
            value is not None
            for value in (overall_score, template_compliance, content_quality, citation_count, llm_provider_used)
        )
        or missing_sections
    ):
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


async def _scan_uploaded_file(file_path: str) -> dict[str, str | bool]:
    scanner = _get_impl_symbol("virus_scanner", virus_scanner)
    scan_result = await scanner.scan(file_path)
    if not scan_result.get("clean", True):
        os_mod = _get_impl_symbol("os", os)
        try:
            os_mod.remove(file_path)
        except OSError:
            pass
        raise HTTPException(
            status_code=422,
            detail=f"Malware detected: {scan_result.get('result', 'unknown')}",
        )
    return scan_result


async def _validate_magic_bytes(
    file: UploadFile,
    *,
    content: Optional[bytes] = None,
    file_ext: Optional[str] = None,
) -> bytes:
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


class DocumentPipelineService:
    """
    Application service managing document processing pipelines, uploads,
    chunk reassembly, batch uploads, virus scanning, and status caching.
    """

    def __init__(
        self,
        crud_service: Optional[DocumentCrudService] = None,
        crud: Optional[DocumentCrudService] = None,
    ) -> None:
        self._crud = crud_service or crud or DocumentCrudService()

    async def scan_uploaded_file(self, file_path: str) -> dict[str, str | bool]:
        scan_fn = _get_impl_symbol("_scan_uploaded_file")
        if scan_fn is not None and getattr(scan_fn, "__module__", "") != __name__:
            return await scan_fn(file_path)
        return await _scan_uploaded_file(file_path)

    async def validate_magic_bytes(
        self,
        file: UploadFile,
        *,
        content: Optional[bytes] = None,
        file_ext: Optional[str] = None,
    ) -> bytes:
        val_fn = _get_impl_symbol("_validate_magic_bytes")
        if val_fn is not None and getattr(val_fn, "__module__", "") != __name__:
            return await val_fn(file, content=content, file_ext=file_ext)
        return await _validate_magic_bytes(file, content=content, file_ext=file_ext)

    async def upload_document(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
        file: UploadFile,
        template: str = settings.DEFAULT_TEMPLATE,
        add_page_numbers: bool = True,
        add_borders: bool = False,
        add_cover_page: bool = False,
        generate_toc: bool = False,
        add_line_numbers: bool = False,
        line_spacing: Optional[float] = None,
        page_size: str = "Letter",
        fast_mode: bool = False,
        current_user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """Handle single document upload and trigger async background processing."""
        require_db_fn = _get_impl_symbol("_require_db", _require_db)
        enforce_quota_fn = _get_impl_symbol("_enforce_daily_upload_quota", _enforce_daily_upload_quota)
        record_ack_fn = _get_impl_symbol("_record_upload_ack_duration", _record_upload_ack_duration)
        doc_service = _get_impl_symbol("DocumentService")
        scan_fn = self.scan_uploaded_file
        val_fn = self.validate_magic_bytes
        set_cached_fn = _get_impl_symbol("_set_cached_status_response", _set_cached_status_response)
        cache_key_fn = _get_impl_symbol("_status_cache_key", _status_cache_key)
        init_payload_fn = _get_impl_symbol("_build_initial_status_payload", _build_initial_status_payload)
        audit_svc = _get_impl_symbol("audit_log_service", audit_log_service)
        settings_obj = _get_impl_symbol("settings", settings)
        os_mod = _get_impl_symbol("os", os)

        require_db_fn()
        enforce_quota_fn(current_user)
        request_started_at = monotonic()

        job_id = None
        try:
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in ACCEPTED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file type '{file_ext}'. Allowed types: {', '.join(sorted(ACCEPTED_EXTENSIONS))}",
                )

            safe_filename = os.path.basename(file.filename)
            if safe_filename != file.filename or ".." in file.filename:
                raise HTTPException(status_code=400, detail="Invalid filename. Path traversal detected.")

            file_content = await file.read()
            file_size = len(file_content)

            max_size = getattr(settings_obj, "MAX_FILE_SIZE", settings.MAX_FILE_SIZE)
            if file_size > max_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large ({file_size / 1024 / 1024:.1f}MB). Maximum size is {max_size / 1024 / 1024:.0f}MB",
                )

            if file_size == 0:
                raise HTTPException(status_code=400, detail="File is empty. Please upload a valid document.")

            file_content = await val_fn(file, content=file_content, file_ext=file_ext)

            impl_uuid = _get_impl_symbol("uuid", uuid)
            job_id = impl_uuid.uuid4() if hasattr(impl_uuid, "uuid4") else uuid.uuid4()

            os_mod.makedirs(UPLOAD_DIR, exist_ok=True)
            file_path = os_mod.path.abspath(os_mod.path.join(UPLOAD_DIR, f"{job_id}{file_ext}"))
            upload_dir_abs = os_mod.path.abspath(UPLOAD_DIR)

            if not file_path.startswith(upload_dir_abs):
                raise HTTPException(status_code=400, detail="Invalid file path detected")

            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
            scan_result = await scan_fn(file_path)

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

            if doc_service and hasattr(doc_service, "create_document"):
                created = await doc_service.create_document(
                    doc_id=str(job_id),
                    user_id=str(current_user.id) if current_user else None,
                    filename=safe_filename,
                    template=template,
                    original_file_path=file_path,
                    formatting_options=formatting_options,
                    file_hash=file_hash,
                )
            else:
                created = await self._crud.create_document(
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

            orchestrator_cls = _get_impl_symbol("PipelineOrchestrator", PipelineOrchestrator)
            orchestrator = orchestrator_cls()
            enhancement_mgr = _get_impl_symbol("enhancement_manager")
            if enhancement_mgr is None:
                from app.services.enhancement_manager import enhancement_manager as enhancement_mgr

            dispatch_info = enhancement_mgr.dispatch_document_pipeline(
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

            await audit_svc.log(
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

            await set_cached_fn(
                cache_key_fn(str(job_id), current_user),
                init_payload_fn(str(job_id)),
            )

            payload = {"message": "Processing started", "job_id": str(job_id), "status": "PROCESSING"}
            record_ack_fn(request_started_at)
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

    async def upload_document_chunked(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
        file_id: str,
        chunk_index: int,
        total_chunks: int,
        file: UploadFile,
        template: str = settings.DEFAULT_TEMPLATE,
        add_page_numbers: bool = True,
        add_borders: bool = False,
        add_cover_page: bool = False,
        generate_toc: bool = False,
        add_line_numbers: bool = False,
        line_spacing: Optional[float] = None,
        page_size: str = "Letter",
        fast_mode: bool = False,
        current_user: User = None,  # type: ignore[assignment]
    ) -> Dict[str, Any]:
        """Chunked file upload for large documents."""
        require_db_fn = _get_impl_symbol("_require_db", _require_db)
        enforce_quota_fn = _get_impl_symbol("_enforce_daily_upload_quota", _enforce_daily_upload_quota)
        record_ack_fn = _get_impl_symbol("_record_upload_ack_duration", _record_upload_ack_duration)
        doc_service = _get_impl_symbol("DocumentService")
        scan_fn = self.scan_uploaded_file
        val_fn = self.validate_magic_bytes
        set_cached_fn = _get_impl_symbol("_set_cached_status_response", _set_cached_status_response)
        cache_key_fn = _get_impl_symbol("_status_cache_key", _status_cache_key)
        init_payload_fn = _get_impl_symbol("_build_initial_status_payload", _build_initial_status_payload)
        audit_svc = _get_impl_symbol("audit_log_service", audit_log_service)
        settings_obj = _get_impl_symbol("settings", settings)
        os_mod = _get_impl_symbol("os", os)

        require_db_fn()
        if chunk_index == 0:
            enforce_quota_fn(current_user)
        request_started_at = monotonic()

        if not re.match(r"^[a-zA-Z0-9-]+$", file_id):
            raise HTTPException(status_code=400, detail="Invalid file_id. Path traversal blocked.")

        upload_dir = Path("data/uploads/temp")
        upload_dir.mkdir(parents=True, exist_ok=True)

        chunk_path = upload_dir / f"{file_id}.part{chunk_index}"
        try:
            content = await file.read()
            if len(content) > 5 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="Chunk exceeds 5MB limit.")

            with open(chunk_path, "wb") as f:
                f.write(content)

            received_chunks = len(list(upload_dir.glob(f"{file_id}.part*")))
            if received_chunks == total_chunks:
                total_size = sum(p.stat().st_size for p in upload_dir.glob(f"{file_id}.part*"))
                max_size = getattr(settings_obj, "MAX_FILE_SIZE", settings.MAX_FILE_SIZE)
                if total_size > max_size:
                    for p in upload_dir.glob(f"{file_id}.part*"):
                        p.unlink()
                    raise HTTPException(status_code=413, detail="Total file size exceeds limit.")

                final_path = upload_dir / f"{file_id}_complete"
                file_hash = await asyncio.to_thread(
                    _reassemble_chunks_sync, upload_dir, file_id, total_chunks, final_path
                )

                original_filename = os_mod.path.basename(file.filename or f"{file_id}.docx")
                file_ext = os_mod.path.splitext(original_filename)[1].lower() or ".docx"
                if file_ext not in ACCEPTED_EXTENSIONS:
                    final_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid file type '{file_ext}'. Allowed types: {', '.join(sorted(ACCEPTED_EXTENSIONS))}",
                    )

                assembled_content = final_path.read_bytes()
                await val_fn(file, content=assembled_content, file_ext=file_ext)

                impl_uuid = _get_impl_symbol("uuid", uuid)
                job_id = impl_uuid.uuid4() if hasattr(impl_uuid, "uuid4") else uuid.uuid4()

                os_mod.makedirs(UPLOAD_DIR, exist_ok=True)
                file_path = os_mod.path.abspath(os_mod.path.join(UPLOAD_DIR, f"{job_id}{file_ext}"))
                upload_dir_abs = os_mod.path.abspath(UPLOAD_DIR)
                if not file_path.startswith(upload_dir_abs):
                    final_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=400, detail="Invalid file path detected")

                os_mod.replace(final_path, file_path)
                scan_result = await scan_fn(file_path)

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

                if doc_service and hasattr(doc_service, "create_document"):
                    created = await doc_service.create_document(
                        doc_id=str(job_id),
                        user_id=str(current_user.id) if current_user else None,
                        filename=original_filename,
                        template=template,
                        original_file_path=file_path,
                        formatting_options=formatting_options,
                        file_hash=file_hash,
                    )
                else:
                    created = await self._crud.create_document(
                        doc_id=str(job_id),
                        user_id=str(current_user.id) if current_user else None,
                        filename=original_filename,
                        template=template,
                        original_file_path=file_path,
                        formatting_options=formatting_options,
                        file_hash=file_hash,
                    )
                if created is None:
                    try:
                        os_mod.remove(file_path)
                    except OSError:
                        pass
                    raise HTTPException(status_code=503, detail="Database temporarily unavailable. Please retry later.")

                orchestrator_cls = _get_impl_symbol("PipelineOrchestrator", PipelineOrchestrator)
                orchestrator = orchestrator_cls()
                enhancement_mgr = _get_impl_symbol("enhancement_manager")
                if enhancement_mgr is None:
                    from app.services.enhancement_manager import enhancement_manager as enhancement_mgr

                dispatch_info = enhancement_mgr.dispatch_document_pipeline(
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

                await audit_svc.log(
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

                await set_cached_fn(
                    cache_key_fn(str(job_id), current_user),
                    init_payload_fn(str(job_id)),
                )
                payload = {
                    "status": "complete",
                    "job_id": str(job_id),
                    "file_id": file_id,
                    "file_hash": file_hash,
                }
                record_ack_fn(request_started_at)
                return payload

            payload = {"status": "chunk_received", "chunk_index": chunk_index, "total_chunks": total_chunks}
            record_ack_fn(request_started_at)
            return payload
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error handling chunked upload: %s", e)
            raise HTTPException(status_code=500, detail="Failed to upload chunk.")

    async def batch_upload(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
        files: List[UploadFile],
        template: str = "none",
        current_user: User = None,  # type: ignore[assignment]
    ) -> Dict[str, Any]:
        """Upload multiple documents at once. Maximum 10 files per batch."""
        require_db_fn = _get_impl_symbol("_require_db", _require_db)
        enforce_quota_fn = _get_impl_symbol("_enforce_daily_upload_quota", _enforce_daily_upload_quota)
        doc_service = _get_impl_symbol("DocumentService")
        val_fn = self.validate_magic_bytes
        audit_svc = _get_impl_symbol("audit_log_service", audit_log_service)
        settings_obj = _get_impl_symbol("settings", settings)

        require_db_fn()
        enforce_quota_fn(current_user)

        max_batch = getattr(settings_obj, "MAX_BATCH_FILES", settings.MAX_BATCH_FILES)
        if len(files) > max_batch:
            raise HTTPException(status_code=400, detail=f"Maximum {max_batch} files per batch upload.")

        results = []
        for file in files:
            impl_uuid = _get_impl_symbol("uuid", uuid)
            job_id = str(impl_uuid.uuid4()) if hasattr(impl_uuid, "uuid4") else str(uuid.uuid4())
            try:
                ext = os.path.splitext(file.filename or "")[1].lower()
                if ext not in ACCEPTED_EXTENSIONS:
                    results.append(
                        {
                            "filename": file.filename,
                            "status": "rejected",
                            "reason": f"Unsupported format: {ext}",
                        }
                    )
                    continue

                safe_name = f"{job_id}{ext}"
                file_path = os.path.join(UPLOAD_DIR, safe_name)
                content = await file.read()

                max_size = getattr(settings_obj, "MAX_FILE_SIZE", settings.MAX_FILE_SIZE)
                if len(content) > max_size:
                    results.append(
                        {
                            "filename": file.filename,
                            "status": "rejected",
                            "reason": f"File exceeds {max_size // (1024 * 1024)}MB limit",
                        }
                    )
                    continue

                content = await val_fn(file, content=content, file_ext=ext)

                with open(file_path, "wb") as f:
                    f.write(content)

                if doc_service and hasattr(doc_service, "create_document"):
                    await doc_service.create_document(
                        doc_id=job_id,
                        filename=file.filename,
                        original_file_path=file_path,
                        template=template,
                        user_id=str(current_user.id) if current_user else None,
                        file_hash=hashlib.sha256(content).hexdigest(),
                    )
                else:
                    await self._crud.create_document(
                        doc_id=job_id,
                        filename=file.filename,
                        original_file_path=file_path,
                        template=template,
                        user_id=str(current_user.id) if current_user else None,
                        file_hash=hashlib.sha256(content).hexdigest(),
                    )

                orchestrator_cls = _get_impl_symbol("PipelineOrchestrator", PipelineOrchestrator)
                orchestrator = orchestrator_cls()
                enhancement_mgr = _get_impl_symbol("enhancement_manager")
                if enhancement_mgr is None:
                    from app.services.enhancement_manager import enhancement_manager as enhancement_mgr

                dispatch_info = enhancement_mgr.dispatch_document_pipeline(
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

                results.append(
                    {
                        "filename": file.filename,
                        "job_id": job_id,
                        "status": "processing",
                    }
                )

            except Exception as e:
                logger.error(
                    "Batch upload failed for %s: %s",
                    file.filename,
                    e,
                    extra=log_extra(job_id=job_id),
                )
                results.append(
                    {
                        "filename": file.filename,
                        "status": "failed",
                        "reason": "An internal error occurred during batch processing.",
                    }
                )

        await audit_svc.log(
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

    async def edit_document(
        self,
        request: Request,
        job_id: str,
        data: Dict[str, Any],
        background_tasks: BackgroundTasks,
        current_user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """Handle user edits and trigger non-destructive re-formatting."""
        doc_service = _get_impl_symbol("DocumentService")
        audit_svc = _get_impl_symbol("audit_log_service", audit_log_service)

        try:
            get_doc_fn = (
                doc_service.get_document
                if (doc_service and hasattr(doc_service, "get_document"))
                else self._crud.get_document
            )
            doc = await get_doc_fn(job_id)
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")

            if doc.get("user_id") is not None:
                if not current_user or str(doc["user_id"]) != str(current_user.id):
                    raise HTTPException(status_code=403, detail="Not authorized to edit this document")

            edited_data = data.get("edited_structured_data")
            if not edited_data:
                raise HTTPException(status_code=400, detail="Missing edited_structured_data")

            orchestrator_cls = _get_impl_symbol("PipelineOrchestrator", PipelineOrchestrator)
            orchestrator = orchestrator_cls()
            enhancement_mgr = _get_impl_symbol("enhancement_manager")
            if enhancement_mgr is None:
                from app.services.enhancement_manager import enhancement_manager as enhancement_mgr

            dispatch_info = enhancement_mgr.dispatch_edit_flow(
                background_tasks=background_tasks,
                orchestrator=orchestrator,
                job_id=job_id,
                edited_structured_data=edited_data,
                template_name=doc.get("template"),
                estimated_duration_seconds=8.0,
            )
            logger.info("Edit dispatch mode for job %s: %s", job_id, dispatch_info.get("mode"))

            await audit_svc.log(
                user_id=str(current_user.id) if current_user else None,
                action="edit",
                resource_type="document",
                resource_id=str(job_id),
                ip_address=request.client.host if request.client else None,
                details={
                    "filename": doc.get("filename"),
                    "template": doc.get("template"),
                    "edited_structured_data_keys": sorted((edited_data or {}).keys())
                    if isinstance(edited_data, dict)
                    else [],
                },
            )

            return {"message": "Edit received, re-formatting started", "job_id": job_id, "status": "PROCESSING"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error editing document %s: %s", job_id, e)
            raise HTTPException(status_code=500, detail=f"Edit failed: {str(e)}")

    async def get_status(
        self,
        job_id: str,
        current_user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """Get the detailed processing status of a document."""
        cache_key_fn = _get_impl_symbol("_status_cache_key", _status_cache_key)
        get_cached_fn = _get_impl_symbol("_get_cached_status_response", _get_cached_status_response)
        get_stale_fn = _get_impl_symbol("_get_stale_status_response", _get_stale_status_response)
        set_cached_fn = _get_impl_symbol("_set_cached_status_response", _set_cached_status_response)
        extract_quality_fn = _get_impl_symbol("_extract_quality_payload", _extract_quality_payload)
        doc_service = _get_impl_symbol("DocumentService")

        try:
            cache_key = cache_key_fn(job_id, current_user)
            cached_payload = await get_cached_fn(cache_key)
            if cached_payload is not _STATUS_CACHE_MISS:
                return cached_payload

            get_doc_fn = (
                doc_service.get_document
                if (doc_service and hasattr(doc_service, "get_document"))
                else self._crud.get_document
            )
            get_statuses_fn = (
                doc_service.get_processing_statuses
                if (doc_service and hasattr(doc_service, "get_processing_statuses"))
                else self._crud.get_processing_statuses
            )
            get_result_fn = (
                doc_service.get_document_result
                if (doc_service and hasattr(doc_service, "get_document_result"))
                else self._crud.get_document_result
            )

            doc = await get_doc_fn(job_id)
            if not doc:
                await asyncio.sleep(0.25)
                doc = await get_doc_fn(job_id)

            if not doc:
                statuses = await get_statuses_fn(job_id)
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
                    await set_cached_fn(cache_key, payload)
                    return payload

                stale_payload = await get_stale_fn(cache_key)
                if stale_payload is not _STATUS_CACHE_MISS:
                    stale_payload["message"] = "Reconnecting to status backend. Retrying..."
                    stale_payload["stale"] = True
                    return stale_payload

                raise HTTPException(status_code=404, detail="Document job not found")

            if doc.get("user_id") is not None:
                if not current_user or str(doc["user_id"]) != str(current_user.id):
                    raise HTTPException(status_code=403, detail="Not authorized to access this document")

            statuses = await get_statuses_fn(job_id)
            doc_status = str(doc.get("status") or "").upper()
            should_fetch_result = doc_status in _READY_FOR_EXPORT_STATUSES
            result = await get_result_fn(job_id) if should_fetch_result else None
            quality_payload = extract_quality_fn(result)

            payload = {
                "job_id": job_id,
                "status": doc.get("status"),
                "current_phase": doc.get("current_stage") or "UPLOADED",
                "phase": doc.get("current_stage") or "UPLOADED",
                "progress_percentage": doc.get("progress") or 0,
                "message": doc.get("error_message")
                or ((doc.get("current_stage") + "...") if doc.get("current_stage") else "Processing..."),
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
            await set_cached_fn(cache_key, payload)
            return payload
        except HTTPException:
            raise
        except DatabaseUnavailableError:
            raise HTTPException(status_code=503, detail="Database temporarily unavailable")
        except Exception as e:
            logger.error("Status check failed for job %s: %s", job_id, e)
            raise HTTPException(status_code=500, detail="Status check failed")

    async def get_document_summary(
        self,
        job_id: str,
        current_user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """Lightweight job summary for URL-based page hydration."""
        doc_service = _get_impl_symbol("DocumentService")
        extract_quality_fn = _get_impl_symbol("_extract_quality_payload", _extract_quality_payload)

        get_doc_fn = (
            doc_service.get_document
            if (doc_service and hasattr(doc_service, "get_document"))
            else self._crud.get_document
        )
        get_result_fn = (
            doc_service.get_document_result
            if (doc_service and hasattr(doc_service, "get_document_result"))
            else self._crud.get_document_result
        )

        doc = await get_doc_fn(job_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Not found")

        if doc.get("user_id") is not None:
            if not current_user or str(doc["user_id"]) != str(current_user.id):
                raise HTTPException(status_code=403, detail="Not authorized to access this document")

        status = doc.get("status")
        result = await get_result_fn(job_id) if status in _READY_FOR_EXPORT_STATUSES else None
        quality_payload = extract_quality_fn(result)
        return {
            "id": job_id,
            "status": status,
            "filename": doc.get("filename"),
            "template": doc.get("template"),
            "created_at": doc.get("created_at"),
            "output_path": doc.get("output_path") if status in _READY_FOR_EXPORT_STATUSES else None,
            "quality": quality_payload["quality"],
        }

    async def get_preview(
        self,
        job_id: str,
        current_user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """Get the structured preview data for a document."""
        doc_service = _get_impl_symbol("DocumentService")
        extract_quality_fn = _get_impl_symbol("_extract_quality_payload", _extract_quality_payload)

        get_doc_fn = (
            doc_service.get_document
            if (doc_service and hasattr(doc_service, "get_document"))
            else self._crud.get_document
        )
        get_result_fn = (
            doc_service.get_document_result
            if (doc_service and hasattr(doc_service, "get_document_result"))
            else self._crud.get_document_result
        )

        try:
            doc = await get_doc_fn(job_id)
            if not doc:
                raise HTTPException(status_code=404, detail="Document job not found")

            if doc.get("user_id") is not None:
                if not current_user or str(doc["user_id"]) != str(current_user.id):
                    raise HTTPException(status_code=403, detail="Not authorized to preview this document")

            result = await get_result_fn(job_id)
            if not result:
                raise HTTPException(status_code=404, detail="Processing results not found")

            quality_payload = extract_quality_fn(result)

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

    async def start_processing(self, doc_id: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Dispatch a document to the PipelineOrchestrator for formatting."""
        doc_service = _get_impl_symbol("DocumentService")
        get_doc_fn = (
            doc_service.get_document
            if (doc_service and hasattr(doc_service, "get_document"))
            else self._crud.get_document
        )

        doc = await get_doc_fn(doc_id)
        if doc is None:
            raise DocumentNotFoundError(doc_id)

        orchestrator_cls = _get_impl_symbol("PipelineOrchestrator", PipelineOrchestrator)
        orchestrator = orchestrator_cls()
        job = await orchestrator.dispatch(
            document_id=str(doc_id),
            options=options or {},
        )
        return {
            "document_id": str(doc_id),
            "status": "PROCESSING",
            "job": job,
        }

    async def get_processing_status(self, doc_id: str) -> List[Dict[str, Any]]:
        """Return per-phase processing statuses for a document."""
        doc_service = _get_impl_symbol("DocumentService")
        get_statuses_fn = (
            doc_service.get_processing_statuses
            if (doc_service and hasattr(doc_service, "get_processing_statuses"))
            else self._crud.get_processing_statuses
        )
        return await get_statuses_fn(doc_id)

    async def cancel_processing(self, doc_id: str) -> Dict[str, Any]:
        """Cancel an in-flight processing job for a document."""
        doc_service = _get_impl_symbol("DocumentService")
        mark_failed_fn = (
            doc_service.mark_document_failed
            if (doc_service and hasattr(doc_service, "mark_document_failed"))
            else self._crud.mark_document_failed
        )

        doc_id = str(doc_id)
        orchestrator_cls = _get_impl_symbol("PipelineOrchestrator", PipelineOrchestrator)
        orchestrator = orchestrator_cls()
        try:
            await orchestrator.cancel(document_id=doc_id)
        except Exception as exc:
            logger.warning(
                "Pipeline cancel failed for %s: %s",
                doc_id,
                exc,
                extra={"job_id": doc_id},
            )
        await mark_failed_fn(doc_id, "Processing cancelled by user.")
        return {"document_id": doc_id, "status": "CANCELLED"}

    async def get_result(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Return the stored processing result for a document."""
        doc_service = _get_impl_symbol("DocumentService")
        get_result_fn = (
            doc_service.get_document_result
            if (doc_service and hasattr(doc_service, "get_document_result"))
            else self._crud.get_document_result
        )
        result = await get_result_fn(doc_id)
        if result is None:
            raise DocumentNotFoundError(doc_id)
        return result
