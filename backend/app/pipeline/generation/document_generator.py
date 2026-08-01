# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

# -*- coding: utf-8 -*-
"""
DocumentGenerator -- orchestrator for generate-from-scratch jobs.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config.settings import settings
from app.db.supabase_client import get_supabase_client
from app.models.block import Block, BlockType
from app.models.pipeline_document import DocumentMetadata, PipelineDocument, TemplateInfo
from app.pipeline.export.exporter import Exporter
from app.pipeline.formatting.formatter import Formatter
from app.pipeline.generation.content_parser import ContentParser
from app.pipeline.generation.prompt_builder import PromptBuilder

from app.services.document_service import DocumentService
from app.utils.singleton import get_or_create

logger = logging.getLogger(__name__)

GENERATED_DIR = Path(settings.GENERATED_OUTPUT_DIR)

_BLOCK_TYPE_MAP: dict[str, BlockType] = {
    "TITLE": BlockType.TITLE,
    "AUTHOR_INFO": BlockType.AUTHOR,
    "AUTHOR": BlockType.AUTHOR,
    "AFFILIATION": BlockType.AFFILIATION,
    "ABSTRACT": BlockType.ABSTRACT_BODY,
    "SUMMARY": BlockType.BODY,
    "KEYWORDS": BlockType.KEYWORDS_BODY,
    "HEADING_1": BlockType.HEADING_1,
    "HEADING_2": BlockType.HEADING_2,
    "HEADING_3": BlockType.HEADING_3,
    "BODY": BlockType.BODY,
    "BULLET": BlockType.LIST_ITEM,
    "BULLET_LIST": BlockType.LIST_ITEM,
    "REFERENCE_ENTRY": BlockType.REFERENCE_ENTRY,
    "FIGURE_CAPTION": BlockType.FIGURE_CAPTION,
    "TABLE_CAPTION": BlockType.TABLE_CAPTION,
}


class DocumentGenerator:
    """Orchestrates document generation from metadata."""

    def __init__(self) -> None:
        # Volatile fallback only used when Supabase is unavailable in local/test mode.
        self._volatile_sessions: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _normalize_status(raw_status: str | None) -> str:
        mapping = {
            "PENDING": "pending",
            "PROCESSING": "processing",
            "COMPLETED": "done",
            "COMPLETED_WITH_WARNINGS": "done",
            "FAILED": "failed",
            "CANCELLED": "failed",
            "pending": "pending",
            "processing": "processing",
            "done": "done",
            "failed": "failed",
        }
        return mapping.get(str(raw_status or "").strip(), "processing")

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()

    def _default_session_config(
        self,
        *,
        doc_type: str,
        template: str,
        metadata: dict[str, Any],
        options: dict[str, Any],
        user_id: str,
    ) -> dict[str, Any]:
        return {
            "doc_type": doc_type,
            "template": template,
            "metadata": metadata,
            "options": options,
            "user_id": user_id,
            "stage": "queued",
            "message": "Generation job queued.",
            "error": None,
            "output_path": None,
        }

    def _session_record_to_status(self, session: dict[str, Any], *, include_outline: bool = True) -> dict[str, Any]:
        config = session.get("config_json") or {}
        status = self._normalize_status(str(session.get("status") or config.get("status") or "pending"))
        progress = int(session.get("progress") or config.get("progress") or 0)
        stage = str(config.get("stage") or "queued")
        message = str(config.get("message") or "Generation in progress...")
        error = config.get("error")
        output_path = config.get("output_path")
        outline = session.get("outline_json") if include_outline else []
        if not isinstance(outline, list):
            outline = []
        outline = [str(item).strip() for item in outline if str(item).strip()]
        return {
            "job_id": str(session.get("id")),
            "status": status,
            "stage": stage,
            "progress": int(max(0, min(100, progress))),
            "message": message,
            "error": str(error) if error else None,
            "output_path": str(output_path) if output_path else None,
            "outline": outline,
        }

    def _get_session_record(self, job_id: str) -> dict[str, Any] | None:
        sb = get_supabase_client()
        if sb is not None:
            try:
                result = sb.table("generator_sessions").select("*").eq("id", str(job_id)).maybe_single().execute()
                if result.data:
                    return result.data
            except Exception as exc:
                logger.warning("Failed to fetch generator session %s from DB: %s", job_id, exc)
        return self._volatile_sessions.get(str(job_id))

    def get_session(self, job_id: str) -> dict[str, Any] | None:
        return self._get_session_record(job_id)

    def update_status(
        self,
        job_id: str,
        *,
        status: str,
        progress: int,
        stage: str | None = None,
        message: str | None = None,
        error: str | None = None,
        output_path: str | None = None,
        outline: list[str] | None = None,
    ) -> None:
        record = self._get_session_record(job_id) or {"id": str(job_id)}
        config = dict(record.get("config_json") or {})
        config["status"] = status
        config["progress"] = int(max(0, min(100, progress)))
        if stage is not None:
            config["stage"] = stage
        if message is not None:
            config["message"] = message
        if error is not None:
            config["error"] = error
        if output_path is not None:
            config["output_path"] = output_path

        payload: dict[str, Any] = {
            "status": status,
            "progress": int(max(0, min(100, progress))),
            "config_json": config,
            "updated_at": self._now_iso(),
        }
        if outline is not None:
            payload["outline_json"] = [str(item).strip() for item in outline if str(item).strip()]

        sb = get_supabase_client()
        if sb is not None:
            try:
                sb.table("generator_sessions").update(payload).eq("id", str(job_id)).execute()
            except Exception as exc:
                logger.warning("Failed to update generator session %s in DB: %s", job_id, exc)

        merged = dict(record)
        merged.update(payload)
        self._volatile_sessions[str(job_id)] = merged

    async def start_job(
        self,
        doc_type: str,
        template: str,
        metadata: dict,
        options: dict,
        user_id: str,
    ) -> str:
        job_id = str(uuid.uuid4())
        generated_filename = f"generated_{doc_type}_{job_id[:8]}.docx"
        config_json = self._default_session_config(
            doc_type=doc_type,
            template=template,
            metadata=metadata,
            options=options,
            user_id=user_id,
        )
        formatting_options = {
            "generation": True,
            "doc_type": doc_type,
            "include_placeholder_content": bool(options.get("include_placeholder_content", True)),
            "word_count_target": int(options.get("word_count_target", 3000)),
            "export_formats": ["docx", "pdf"],
        }

        db_created = DocumentService.create_document(
            doc_id=job_id,
            user_id=str(user_id) if user_id else None,
            filename=generated_filename,
            template=template,
            formatting_options=formatting_options,
        )
        if db_created is None:
            logger.warning("Generation job %s created in memory only (DB unavailable).", job_id)

        session_payload = {
            "id": job_id,
            "user_id": str(user_id) if user_id else None,
            "session_type": "agent",
            "status": "pending",
            "progress": 0,
            "config_json": config_json,
            "outline_json": [],
            "created_at": self._now_iso(),
            "updated_at": self._now_iso(),
        }

        sb = get_supabase_client()
        if sb is not None:
            try:
                sb.table("generator_sessions").insert(session_payload).execute()
            except Exception as exc:
                logger.warning("Failed to persist generator session %s to DB: %s", job_id, exc)
                self._volatile_sessions[job_id] = session_payload
        else:
            self._volatile_sessions[job_id] = session_payload

        self._emit(
            job_id, phase="QUEUED", status="PENDING", message="Generation job queued.", progress=0, stage="queued"
        )
        return job_id

    async def run_pipeline(self, job_id: str) -> None:
        state = self._get_session_record(job_id)
        if not state:
            logger.error("run_pipeline: generation job '%s' not found", job_id)
            return

        config = state.get("config_json") or {}
        doc_type = str(config.get("doc_type") or "academic_paper")
        template = str(config.get("template") or "none")
        metadata = config.get("metadata") or {}
        options = config.get("options") or {}

        try:
            self._update(job_id, "generating", 10, "Building LLM prompt...")
            prompt_builder = PromptBuilder()
            prompt = prompt_builder.build(doc_type, metadata, options)

            self._update(job_id, "generating", 30, "AI writing document content...")
            llm_response = await self._llm_generate(prompt, job_id)

            self._update(job_id, "structuring", 50, "Structuring AI output into blocks...")
            parser = ContentParser()
            raw_blocks = parser.parse(llm_response, doc_type)
            outline = self._extract_outline(raw_blocks)
            self.update_status(
                job_id,
                status="processing",
                progress=50,
                stage="structuring",
                message="Structuring AI output into blocks...",
                outline=outline,
            )

            DocumentService.upsert_document_result(
                job_id,
                structured_data={
                    "doc_type": doc_type,
                    "template": template,
                    "blocks": raw_blocks,
                    "outline": outline,
                    "generated_at": datetime.now(UTC).isoformat(),
                },
                validation_results={},
            )

            self._update(job_id, "formatting", 75, f"Applying {template.upper()} template...")
            output_path = await self._format_and_export(
                raw_blocks=raw_blocks,
                template=template,
                job_id=job_id,
                metadata=metadata,
                doc_type=doc_type,
            )

            try:
                output_hash = self._compute_sha256(output_path)
                DocumentService.update_output_hash(job_id, output_hash)
            except Exception as exc:
                logger.warning("Failed to persist output hash for generation job %s: %s", job_id, exc)

            raw_text = "\n\n".join(
                block.get("content", "").strip() for block in raw_blocks if str(block.get("content", "")).strip()
            )
            DocumentService.mark_document_completed(job_id, str(output_path), raw_text=raw_text)
            self._update(job_id, "done", 100, "Document ready for download!", output_path=str(output_path))
            logger.info("Generation job %s completed: %s", job_id, output_path)
        except Exception as exc:
            logger.exception("Generation job %s failed: %s", job_id, exc)
            DocumentService.mark_document_failed(job_id, str(exc))
            self._update(job_id, "error", 0, str(exc), error=str(exc))

    def get_status(self, job_id: str) -> dict[str, Any]:
        state = self._get_session_record(job_id)
        if state:
            status_payload = self._session_record_to_status(state)
            if not status_payload["outline"]:
                result = DocumentService.get_document_result(job_id)
                if result and isinstance(result.get("structured_data"), dict):
                    raw_outline = result["structured_data"].get("outline") or []
                    if isinstance(raw_outline, list):
                        status_payload["outline"] = [str(item).strip() for item in raw_outline if str(item).strip()]
            return status_payload

        doc = DocumentService.get_document(job_id)
        if not doc:
            raise KeyError(f"generation job not found: '{job_id}'")

        db_status = str(doc.get("status") or "PENDING").upper()
        mapped_status = {
            "PENDING": "pending",
            "PROCESSING": "processing",
            "COMPLETED": "done",
            "COMPLETED_WITH_WARNINGS": "done",
            "FAILED": "failed",
            "CANCELLED": "failed",
        }.get(db_status, "processing")
        stage = str(doc.get("current_stage") or "QUEUED").lower()
        progress = int(doc.get("progress") or 0)
        message = doc.get("error_message") or f"{stage}..."
        error = doc.get("error_message") if mapped_status == "failed" else None
        output_path = doc.get("output_path")

        outline: list[str] = []
        result = DocumentService.get_document_result(job_id)
        if result and isinstance(result.get("structured_data"), dict):
            raw_outline = result["structured_data"].get("outline") or []
            if isinstance(raw_outline, list):
                outline = [str(item).strip() for item in raw_outline if str(item).strip()]

        return {
            "job_id": str(job_id),
            "status": mapped_status,
            "stage": stage,
            "progress": progress,
            "message": str(message),
            "error": error,
            "output_path": output_path,
            "outline": outline,
        }

    def get_download_path(self, job_id: str) -> Path | None:
        state = self._get_session_record(job_id)
        if state:
            status_payload = self._session_record_to_status(state, include_outline=False)
            if status_payload.get("status") == "done" and status_payload.get("output_path"):
                return Path(str(status_payload["output_path"]))

        doc = DocumentService.get_document(job_id)
        if not doc:
            return None
        status = str(doc.get("status") or "").upper()
        if status not in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}:
            return None
        output_path = doc.get("output_path")
        return Path(output_path) if output_path else None

    def _update(
        self,
        job_id: str,
        stage: str,
        progress: int,
        message: str,
        output_path: str | None = None,
        error: str | None = None,
    ) -> None:
        status = (
            "failed"
            if stage == "error"
            else ("done" if progress >= 100 else ("pending" if stage == "queued" else "processing"))
        )
        self.update_status(
            job_id,
            status=status,
            progress=int(max(0, min(100, progress))),
            stage=stage,
            message=str(message),
            error=error,
            output_path=output_path,
        )

        doc_status = "FAILED" if status == "failed" else ("COMPLETED" if status == "done" else "PROCESSING")
        updates: dict[str, Any] = {
            "status": doc_status,
            "current_stage": stage.upper(),
            "progress": int(max(0, min(100, progress))),
        }
        if error:
            updates["error_message"] = error
        if output_path:
            updates["output_path"] = output_path
        DocumentService.update_document(job_id, updates)

        phase_status = (
            "FAILED" if doc_status == "FAILED" else ("COMPLETED" if doc_status == "COMPLETED" else "PROCESSING")
        )
        DocumentService.upsert_processing_status(
            job_id,
            phase=stage.upper(),
            status=phase_status,
            progress_percentage=int(max(0, min(100, progress))),
            message=message,
        )

        self._emit(
            job_id,
            phase=stage.upper(),
            status=phase_status,
            message=message,
            progress=int(max(0, min(100, progress))),
            stage=stage,
            output_path=output_path,
            error=error,
        )

    def _emit(self, job_id: str, **payload: Any) -> None:
        try:
            from app.routers.v1.stream import emit_event
            emit_event(job_id, "status_update", payload)
        except Exception as exc:
            logger.debug("SSE emission failed for generation job %s: %s", job_id, exc)

    async def _llm_generate(self, prompt: str, job_id: str) -> str:
        """
        Call the LLM via existing service fallbacks.
        """
        try:
            from app.services.llm_service import LLM_NVIDIA

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: LLM_NVIDIA.complete(prompt, max_tokens=4096, temperature=0.3),
            )
            if response and response.strip():
                logger.info("Generation job %s: NVIDIA Tier 1 LLM succeeded", job_id)
                return response
        except Exception as exc:
            logger.warning("Generation job %s: NVIDIA Tier 1 failed (%s), trying DeepSeek", job_id, exc)

        try:
            from app.services.llm_service import LLM_DEEPSEEK

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: LLM_DEEPSEEK.complete(prompt, max_tokens=4096, temperature=0.3),
            )
            if response and response.strip():
                logger.info("Generation job %s: DeepSeek Tier 2 LLM succeeded", job_id)
                return response
        except Exception as exc:
            logger.warning("Generation job %s: DeepSeek Tier 2 failed (%s), using rule fallback", job_id, exc)

        logger.warning("Generation job %s: all LLMs unavailable, using rule-based skeleton", job_id)
        state = self._get_session_record(job_id) or {}
        config = state.get("config_json") or {}
        return self._rule_based_skeleton(
            str(config.get("doc_type", "academic_paper")),
            config.get("metadata") or {},
        )

    @staticmethod
    def _rule_based_skeleton(doc_type: str, metadata: dict) -> str:
        import json

        title = metadata.get("title") or metadata.get("name") or "Document Title"
        blocks = [
            {"type": "TITLE", "content": title, "level": 0},
            {"type": "ABSTRACT", "content": metadata.get("abstract", "Abstract placeholder."), "level": 0},
            {"type": "HEADING_1", "content": "Introduction", "level": 1},
            {"type": "BODY", "content": "This section will be completed once AI services are available.", "level": 0},
            {"type": "HEADING_1", "content": "Conclusion", "level": 1},
            {"type": "BODY", "content": "Conclusion placeholder.", "level": 0},
        ]
        if doc_type == "resume":
            blocks = [
                {"type": "TITLE", "content": title, "level": 0},
                {"type": "HEADING_1", "content": "Professional Summary", "level": 1},
                {"type": "BODY", "content": metadata.get("summary", "Summary placeholder."), "level": 0},
                {"type": "HEADING_1", "content": "Experience", "level": 1},
                {"type": "BODY", "content": "Experience placeholder.", "level": 0},
            ]
        return json.dumps(blocks)

    async def _format_and_export(
        self,
        raw_blocks: list[dict[str, Any]],
        template: str,
        job_id: str,
        metadata: dict[str, Any],
        doc_type: str,
    ) -> Path:
        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        output_path = (GENERATED_DIR / f"{job_id}.docx").resolve()

        pipeline_blocks: list[Block] = []
        for index, raw_block in enumerate(raw_blocks):
            text = str(raw_block.get("content", "")).strip()
            if not text:
                continue
            raw_type = str(raw_block.get("type", "BODY")).upper().strip()
            block_type = _BLOCK_TYPE_MAP.get(raw_type, BlockType.BODY)
            level = raw_block.get("level")
            try:
                level_value = int(level) if level is not None else None
            except Exception:
                level_value = None
            pipeline_blocks.append(
                Block(
                    block_id=f"{job_id}-{index}",
                    text=text,
                    block_type=block_type,
                    index=index,
                    level=level_value,
                    metadata=raw_block.get("metadata") or {},
                )
            )

        doc_metadata = DocumentMetadata(
            title=metadata.get("title") or metadata.get("name"),
            authors=[str(author) for author in metadata.get("authors", []) if str(author).strip()],
            abstract=metadata.get("abstract"),
            keywords=[str(keyword) for keyword in metadata.get("keywords", []) if str(keyword).strip()],
        )
        pipeline_doc = PipelineDocument(
            document_id=job_id,
            original_filename=f"generated_{job_id[:8]}.docx",
            blocks=pipeline_blocks,
            metadata=doc_metadata,
            template=TemplateInfo(template_name=template),
            formatting_options={
                "generation": True,
                "doc_type": doc_type,
                "export_formats": ["docx", "pdf"],
                "cover_page": False,
                "toc": False,
            },
            output_path=str(output_path),
        )

        formatter = Formatter()
        pipeline_doc = formatter.process(pipeline_doc)
        if not getattr(pipeline_doc, "generated_doc", None):
            raise RuntimeError("Formatting failed: no document artifact generated.")

        exporter = Exporter()
        pipeline_doc = exporter.process(pipeline_doc)
        if not output_path.exists():
            raise RuntimeError("Export failed: generated DOCX file not found.")

        return output_path

    @staticmethod
    def _extract_outline(raw_blocks: list[dict[str, Any]]) -> list[str]:
        outline: list[str] = []
        for block in raw_blocks:
            block_type = str(block.get("type", "")).upper()
            if block_type.startswith("HEADING") or block_type in {"TITLE", "ABSTRACT"}:
                content = str(block.get("content", "")).strip()
                if content:
                    outline.append(content)
        deduped: list[str] = []
        seen: set[str] = set()
        for item in outline:
            normalized = item.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(item)
        return deduped[:50]

    @staticmethod
    def _compute_sha256(filepath: Path) -> str:
        digest = hashlib.sha256()
        with open(filepath, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


_generator_singleton: DocumentGenerator | None = None


def get_generator() -> DocumentGenerator:
    global _generator_singleton
    _generator_singleton = get_or_create(_generator_singleton, DocumentGenerator)
    return _generator_singleton
