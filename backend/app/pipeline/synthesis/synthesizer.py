# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.models import Block, BlockType, PipelineDocument, Reference, TemplateInfo
from app.pipeline.orchestrator import PipelineOrchestrator
from app.pipeline.parsing.parser_factory import ParserFactory
from app.pipeline.services.csl_engine import CSLEngine
from app.realtime.events import make_event
from app.realtime.pubsub import RedisPubSub
from app.routers.v1.documents_impl import ACCEPTED_EXTENSIONS, _validate_magic_bytes
from app.services.crossref_client import get_crossref_client
from app.services.generator_session_service import GeneratorSessionService
from app.services.llm_service import generate_with_fallback, sanitize_for_llm
from app.services.session_vector_store import SessionVectorStore
from app.utils.id_generator import generate_block_id, generate_reference_id

logger = logging.getLogger(__name__)

_REF_PATTERN = re.compile(r"\[REF:(.+?)\]")


class _FakeUpload:
    def __init__(self, filename: str) -> None:
        self.filename = filename

    async def read(self) -> bytes:
        return b""


class MultiDocSynthesizer:
    def __init__(
        self,
        session_service: GeneratorSessionService,
        vector_store: SessionVectorStore,
        llm_service: Any,
        pipeline_orchestrator: PipelineOrchestrator,
        pubsub: RedisPubSub | None = None,
    ) -> None:
        self.session_service = session_service
        self.vector_store = vector_store
        self.llm_service = llm_service
        self.pipeline_orchestrator = pipeline_orchestrator
        self.pubsub = pubsub or RedisPubSub()
        self.crossref = get_crossref_client()
        self.csl_engine = CSLEngine()

    async def run(self, session_id: str, file_paths: list[str], template: str) -> str:
        session = await self.session_service.get_session(session_id)
        config: dict[str, Any] = dict(session.get("config_json") or {}) if session else {}
        try:
            await self._update_status(session_id, "processing", 5, "Synthesis pipeline started.", config)

            # Stage 1: Upload Validate
            valid_files, warnings = await self._validate_files(file_paths)
            if warnings:
                config.setdefault("warnings", []).extend(warnings)
            config["files"] = valid_files
            warning_msg = ""
            if warnings:
                warning_msg = f" Warnings: {'; '.join(warnings)}"
            await self._update_status(
                session_id,
                "processing",
                12,
                f"Upload validation complete.{warning_msg}",
                config,
                stage="upload_validate",
            )

            # Stage 2: Per-Doc Extract
            extracted_docs = await self._extract_documents(session_id, valid_files)
            config["extracted_docs"] = [
                {"filename": doc["filename"], "section_count": len(doc.get("sections", []))} for doc in extracted_docs
            ]
            await self._update_status(
                session_id,
                "processing",
                25,
                "Extraction complete.",
                config,
                stage="extraction",
            )

            # Stage 3: Embed
            self.vector_store.create_collection(session_id)
            chunks = self._build_chunks(extracted_docs)
            self.vector_store.add_chunks(session_id, chunks)
            await self._update_status(
                session_id,
                "processing",
                37,
                "Embedding complete.",
                config,
                stage="embedding",
            )

            # Stage 4: Cross-Doc Analysis
            analysis = await self._cross_doc_analysis(extracted_docs)
            config["analysis"] = analysis
            await self._update_status(
                session_id,
                "processing",
                50,
                "Cross-document analysis complete.",
                config,
                stage="analysis",
            )

            # Stage 5: Synthesis Plan
            outline = await self._generate_outline(session_id, analysis, template)
            await self._update_status(
                session_id,
                "processing",
                62,
                "Outline generated.",
                config,
                stage="outline",
                outline=outline,
            )

            # Stage 6: Content Generation
            sections = await self._generate_sections(outline, session_id)
            config["sections"] = [{"title": s["title"], "length": len(s["content"])} for s in sections]
            await self._update_status(
                session_id,
                "processing",
                75,
                "Draft content generated.",
                config,
                stage="writing",
            )

            # Stage 7: Citation Insertion
            citations_payload = self._insert_citations(sections, template)
            sections = citations_payload["sections"]
            references = citations_payload["references"]
            config["citations"] = citations_payload["citations"]
            await self._update_status(
                session_id,
                "processing",
                87,
                "Citations inserted.",
                config,
                stage="citations",
            )

            # Stage 8: Template Render
            output_path = self._render_document(session_id, template, outline, sections, references)
            config["output_path"] = output_path
            config["docx_path"] = output_path

            content_json = {
                "outline": outline,
                "sections": sections,
                "references": references,
                "analysis": analysis,
            }
            await self.session_service.save_document_version(
                session_id=session_id,
                content_json=content_json,
                docx_path=output_path,
                version=None,
            )
            await self._update_status(
                session_id,
                "done",
                100,
                "Synthesis complete.",
                config,
                stage="rendering",
            )
            return output_path
        except Exception as exc:
            logger.exception("Synthesis pipeline failed for %s: %s", session_id, exc)
            await self._update_status(
                session_id,
                "failed",
                0,
                f"Synthesis failed: {exc}",
                config,
                stage="error",
                event_type="error",
            )
            raise

    async def _emit_event(
        self,
        session_id: str,
        event_type: str,
        stage: str | None,
        progress: int | None,
        message: str | None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        event_payload = payload or {}
        if stage:
            event_payload.setdefault("stage", stage)
        if progress is not None:
            event_payload.setdefault("progress", progress)
        if message:
            event_payload.setdefault("message", message)
        event = make_event(
            event_type,
            session_id=str(session_id),
            stage=stage,
            progress=progress,
            payload=event_payload,
        )
        await self.pubsub.publish(f"session:{session_id}", event)

    async def _update_status(
        self,
        session_id: str,
        status: str,
        progress: int,
        message: str,
        config: dict[str, Any],
        *,
        stage: str | None = None,
        outline: dict | None = None,
        event_type: str = "stage_update",
    ) -> None:
        if stage:
            config["stage"] = stage
        config["message"] = message
        update_fields = {
            "status": status,
            "progress": int(max(0, min(100, progress))),
            "config_json": config,
        }
        if outline is not None:
            update_fields["outline_json"] = outline
        await self.session_service.update_session(session_id, **update_fields)
        await self._emit_event(session_id, event_type, stage, progress, message, payload={"status": status})

    async def _validate_files(self, file_entries: list[Any]) -> tuple[list[dict[str, Any]], list[str]]:
        if not (2 <= len(file_entries) <= 6):
            raise HTTPException(status_code=422, detail="Upload between 2 and 6 files.")
        warnings: list[str] = []
        seen_hashes: set[str] = set()
        valid_files: list[dict[str, Any]] = []

        for entry in file_entries:
            if isinstance(entry, str):
                path = entry
                filename = Path(entry).name
            else:
                path = entry.get("path")
                filename = entry.get("filename") or Path(path).name
            ext = Path(filename).suffix.lower()
            if ext not in ACCEPTED_EXTENSIONS:
                raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'.")
            content = Path(path).read_bytes()
            await _validate_magic_bytes(_FakeUpload(filename), content=content, file_ext=ext)
            sha = hashlib.sha256(content).hexdigest()
            if sha in seen_hashes:
                warnings.append(f"Duplicate file skipped: {filename}")
                continue
            seen_hashes.add(sha)
            valid_files.append(
                {
                    "path": path,
                    "filename": filename,
                    "hash": sha,
                    "size": len(content),
                }
            )

        if len(valid_files) < 2:
            raise HTTPException(status_code=422, detail="Need at least 2 unique files after deduplication.")
        return valid_files, warnings

    async def _extract_documents(self, session_id: str, files: list[dict[str, Any]]) -> list[dict[str, Any]]:
        async def _extract_one(file_meta: dict[str, Any]) -> dict[str, Any]:
            file_path = file_meta["path"]
            ext = Path(file_path).suffix.lower()
            factory = ParserFactory()
            doc_obj = await asyncio.to_thread(
                self.pipeline_orchestrator._run_extraction_stage,
                factory,
                file_path,
                session_id,
                {},
                ext,
            )
            text = "\n".join([b.text for b in doc_obj.blocks if b.text])
            sections = [b.section_name for b in doc_obj.blocks if b.section_name]
            return {
                **file_meta,
                "doc_obj": doc_obj,
                "text": text,
                "sections": sections,
            }

        tasks = [asyncio.create_task(_extract_one(meta)) for meta in files]
        results: list[dict[str, Any]] = []
        for task in asyncio.as_completed(tasks):
            item = await task
            results.append(item)
            await self._emit_event(
                session_id,
                "stage_update",
                "extraction",
                25,
                f"Extracted {item.get('filename')}",
            )
        return results

    def _build_chunks(self, extracted_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        for doc in extracted_docs:
            doc_obj: PipelineDocument = doc["doc_obj"]
            buffer = ""
            current_section = None
            current_page = None
            for block in doc_obj.blocks:
                text = (block.text or "").strip()
                if not text:
                    continue
                section = block.section_name or current_section or "Unknown"
                page = block.page_number or current_page
                if current_section is None:
                    current_section = section
                if section != current_section or len(buffer) > 1000:
                    chunks.extend(self._chunk_text(buffer, doc["filename"], current_section, current_page))
                    buffer = ""
                    current_section = section
                buffer = f"{buffer}\n{text}".strip()
                current_page = page
            if buffer:
                chunks.extend(self._chunk_text(buffer, doc["filename"], current_section or "Unknown", current_page))
        return chunks

    def _chunk_text(
        self,
        text: str,
        source_doc: str,
        section: str,
        page: int | None,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunk = text[start:end].strip()
            if chunk:
                output.append(
                    {
                        "text": chunk,
                        "source_doc": source_doc,
                        "section": section,
                        "page": page,
                    }
                )
            if end == len(text):
                break
            start = max(0, end - overlap)
        return output

    async def _cross_doc_analysis(self, extracted_docs: list[dict[str, Any]]) -> dict[str, Any]:
        summaries = []
        for doc in extracted_docs:
            snippet = (doc.get("text") or "")[:1800]
            summaries.append({"filename": doc.get("filename"), "summary": snippet})

        system = "You are a research synthesis analyst. Return JSON only."
        user = (
            "Given these document summaries, return JSON with keys: "
            "overlaps (list), gaps (list), unique_points (dict keyed by filename).\n\n"
            f"{json.dumps(summaries, ensure_ascii=False)}"
        )
        result = await self._llm_json(system, user)
        if result:
            return result
        return {"overlaps": [], "gaps": [], "unique_points": {s["filename"]: [] for s in summaries}}

    async def _generate_outline(self, session_id: str, analysis: dict[str, Any], template: str) -> dict[str, Any]:
        system = "You are an academic outline generator. Return JSON only."
        user = (
            "Create a synthesis outline with keys: title, sections (list of objects with title and key_points).\n"
            f"Template: {template}\nAnalysis:\n{json.dumps(analysis, ensure_ascii=False)}"
        )
        result = await self._llm_json(system, user)
        if result is None:
            result = {
                "title": "Synthesized Report",
                "sections": [
                    {"title": "Introduction", "key_points": []},
                    {"title": "Methods", "key_points": []},
                    {"title": "Results", "key_points": []},
                    {"title": "Discussion", "key_points": []},
                    {"title": "Conclusion", "key_points": []},
                ],
            }
        await self._stream_chunks(
            session_id,
            "outline_chunk",
            "outline",
            62,
            json.dumps(result, ensure_ascii=False),
        )
        return result

    async def _generate_sections(self, outline: dict[str, Any], session_id: str) -> list[dict[str, Any]]:
        sections: list[dict[str, Any]] = []
        if isinstance(outline, dict):
            outline_sections = outline.get("sections") or []
        elif isinstance(outline, list):
            outline_sections = outline
        else:
            outline_sections = []
        for section in outline_sections:
            title = section["title"] if isinstance(section, dict) else str(section)
            sources = self.vector_store.query(session_id, title, top_k=4)
            context = "\n\n".join(f"[{s.get('source_doc')} - {s.get('section')}] {s.get('text')}" for s in sources)
            system = (
                "You are a synthesis engine. Use the provided sources and include citations "
                "as [REF: query] for factual claims. Return plain text."
            )
            user = (
                f"Section: {title}\n"
                f"Sources:\n{sanitize_for_llm(context)}\n"
                f"Key points: {section.get('key_points') if isinstance(section, dict) else ''}"
            )
            text = await self._llm_text(system, user, max_tokens=1200)
            await self._stream_chunks(
                session_id,
                "writing_chunk",
                "writing",
                75,
                text,
                extra={"section": title},
            )
            sections.append({"title": title, "content": text})
        return sections

    def _insert_citations(self, sections: list[dict[str, Any]], template: str) -> dict[str, Any]:
        queries: list[str] = []
        for section in sections:
            queries.extend([q.strip() for q in _REF_PATTERN.findall(section["content"] or "")])

        unique_queries: list[str] = []
        for q in queries:
            if q and q not in unique_queries:
                unique_queries.append(q)

        references: list[Reference] = []
        formatted_refs: list[str] = []
        query_to_num: dict[str, int] = {}
        for idx, query in enumerate(unique_queries, start=1):
            result = self.crossref.validate_citation(query)
            authors = []
            raw_authors = result.get("authors") or ""
            if raw_authors:
                authors = [a.strip() for a in raw_authors.split(",") if a.strip()]
            ref = Reference(
                reference_id=generate_reference_id(idx - 1),
                citation_key=f"[{idx}]",
                raw_text=query,
                index=idx - 1,
                authors=authors,
                title=result.get("title"),
                doi=result.get("doi"),
                url=result.get("url"),
            )
            references.append(ref)
            query_to_num[query] = idx

        if references:
            try:
                formatted_refs = self.csl_engine.format_references(references, style=self._template_to_csl(template))
            except Exception as exc:
                logger.warning("CSL formatting failed; using raw references: %s", exc)
                formatted_refs = [r.raw_text for r in references]

        for section in sections:

            def _replace(match):
                query = match.group(1).strip()
                num = query_to_num.get(query)
                return f"[{num}]" if num else ""

            section["content"] = _REF_PATTERN.sub(_replace, section["content"])

        return {
            "sections": sections,
            "references": formatted_refs,
            "citations": [{"query": q, "number": query_to_num[q]} for q in query_to_num],
        }

    def _template_to_csl(self, template: str) -> str:
        key = (template or "ieee").strip().lower()
        if not key or key == "none":
            return "ieee"
        return key

    def _render_document(
        self,
        session_id: str,
        template: str,
        outline: dict[str, Any],
        sections: list[dict[str, Any]],
        references: list[str],
    ) -> str:
        from app.pipeline.export.exporter import Exporter
        from app.pipeline.formatting.formatter import Formatter

        blocks: list[Block] = []
        idx = 0

        title = outline.get("title") if isinstance(outline, dict) else None
        title = title or "Synthesized Report"
        blocks.append(
            Block(
                block_id=generate_block_id(idx),
                text=title,
                block_type=BlockType.TITLE,
                index=idx,
            )
        )
        idx += 1

        for section in sections:
            blocks.append(
                Block(
                    block_id=generate_block_id(idx),
                    text=section["title"],
                    block_type=BlockType.HEADING_1,
                    index=idx,
                )
            )
            idx += 1
            for para in (section["content"] or "").split("\n\n"):
                para = para.strip()
                if not para:
                    continue
                blocks.append(
                    Block(
                        block_id=generate_block_id(idx),
                        text=para,
                        block_type=BlockType.BODY,
                        index=idx,
                    )
                )
                idx += 1

        if references:
            blocks.append(
                Block(
                    block_id=generate_block_id(idx),
                    text="References",
                    block_type=BlockType.HEADING_1,
                    index=idx,
                )
            )
            idx += 1

            for _ref_idx, ref_text in enumerate(references):
                block_id = generate_block_id(idx)
                blocks.append(
                    Block(
                        block_id=block_id,
                        text=ref_text,
                        block_type=BlockType.REFERENCE_ENTRY,
                        index=idx,
                    )
                )
                idx += 1

        doc = PipelineDocument(
            document_id=str(session_id),
            blocks=blocks,
            template=TemplateInfo(template_name=template),
            formatting_options={"export_formats": ["docx"]},
        )

        formatter = Formatter()
        exporter = Exporter()
        doc = formatter.process(doc)
        output_dir = Path("generated_outputs") / "synthesis" / str(session_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "synthesized.docx"
        doc.output_path = str(output_path.resolve())
        exporter.process(doc)
        return str(output_path.resolve())

    async def _llm_text(self, system: str, user: str, max_tokens: int = 1200) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": sanitize_for_llm(user)},
        ]
        result = await asyncio.to_thread(generate_with_fallback, messages, temperature=0.3, max_tokens=max_tokens)
        return (result.get("text") or "").strip()

    async def _llm_json(self, system: str, user: str) -> dict[str, Any] | None:
        text = await self._llm_text(system, user, max_tokens=1200)
        if not text:
            return None
        json_text = self._extract_json(text)
        if not json_text:
            return None
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _extract_json(text: str) -> str | None:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
            cleaned = cleaned.rstrip("```").strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return cleaned[start : end + 1]

    async def _stream_chunks(
        self,
        session_id: str,
        event_type: str,
        stage: str,
        progress: int,
        text: str,
        extra: dict[str, Any] | None = None,
        chunk_size: int = 400,
    ) -> None:
        if not text:
            return
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]
            payload = {"content": chunk, "stage": stage, "progress": progress}
            if extra:
                payload.update(extra)
            await self._emit_event(
                session_id=session_id,
                event_type=event_type,
                stage=stage,
                progress=progress,
                message=None,
                payload=payload,
            )
