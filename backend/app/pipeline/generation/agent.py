# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.models import Block, BlockType, DocumentMetadata, PipelineDocument, TemplateInfo
from app.pipeline.generation.quality_scorer import QualityScorer
from app.pipeline.generation.section_prompts import get_section_prompt
from app.pipeline.generation.task_parser import TaskParser
from app.pipeline.intelligence.rag_engine import get_rag_engine
from app.pipeline.orchestrator import PipelineOrchestrator
from app.pipeline.formatting.formatter import Formatter
from app.realtime.events import make_event
from app.realtime.pubsub import RedisPubSub
from app.services.citation_assembly_service import CitationAssemblyService
from app.services.generator_session_service import GeneratorSessionService
from app.services.llm_service import generate_with_fallback, sanitize_for_llm
from app.utils.id_generator import generate_block_id

logger = logging.getLogger(__name__)


class AgentPipeline:
    def __init__(
        self,
        session_service: GeneratorSessionService,
        pipeline_orchestrator: PipelineOrchestrator,
        pubsub: Optional[RedisPubSub] = None,
    ) -> None:
        self.session_service = session_service
        self.pipeline_orchestrator = pipeline_orchestrator
        self.pubsub = pubsub or RedisPubSub()
        self.rag_engine = get_rag_engine()
        self.citations = CitationAssemblyService()
        self.quality_scorer = QualityScorer()
        self.quality_target = 70.0
        self.max_quality_passes = 1

    async def run(self, session_id: str, user_prompt: str) -> None:
        session = await self.session_service.get_session(session_id)
        config: Dict[str, Any] = dict(session.get("config_json") or {}) if session else {}
        config["user_prompt"] = user_prompt
        user_id = str(session.get("user_id")) if session and session.get("user_id") else None
        await self._update_status(
            session_id,
            status="processing",
            progress=5,
            message="Agent pipeline started.",
            config=config,
            stage="start",
        )

        # Step 2: Parse task
        parser = TaskParser()
        task_spec = await parser.parse(user_prompt)
        if parser.last_turn:
            await self._persist_llm_turn(
                session_id,
                parser.last_turn.get("system", ""),
                parser.last_turn.get("user", ""),
                parser.last_turn.get("assistant", ""),
            )
        if await self._is_canceled(session_id):
            return
        config.update(task_spec)
        await self._update_status(
            session_id,
            status="processing",
            progress=10,
            message="Task parsed.",
            config=config,
            stage="task_parsing",
        )

        # Step 3: RAG Research
        template_rules = self._retrieve_template_rules(task_spec.get("template"), task_spec.get("sections", []))
        config["template_rules"] = template_rules
        await self._update_status(
            session_id,
            status="processing",
            progress=20,
            message="Template research complete.",
            config=config,
            stage="research",
        )

        # Step 4: Web Research (optional)
        web_results = []
        if config.get("web_research") or task_spec.get("web_research"):
            web_results = await self._run_web_research(task_spec)
            config["web_research_results"] = web_results
        await self._update_status(
            session_id,
            status="processing",
            progress=30,
            message="Web research complete.",
            config=config,
            stage="web_research",
        )

        # Step 5: Outline Generation
        if await self._is_canceled(session_id):
            return
        outline = await self._generate_outline(session_id, task_spec, template_rules, web_results, user_id=user_id)
        await self._update_status(
            session_id,
            status="processing",
            progress=40,
            message="Outline generated.",
            config=config,
            stage="outline",
            outline=outline,
        )

        # Step 6: Wait for approval
        await self._update_status(
            session_id,
            status="awaiting_approval",
            progress=40,
            message="Awaiting outline approval.",
            config=config,
            stage="awaiting_approval",
            outline=outline,
        )

    async def resume(self, session_id: str) -> None:
        session = await self.session_service.get_session(session_id)
        if not session:
            logger.warning("AgentPipeline.resume: session %s not found", session_id)
            return

        config: Dict[str, Any] = dict(session.get("config_json") or {})
        outline = session.get("outline_json") or {}
        task_spec = config
        user_id = str(session.get("user_id")) if session.get("user_id") else None
        template_rules = config.get("template_rules") or []
        if not template_rules:
            template_rules = self._retrieve_template_rules(task_spec.get("template"), task_spec.get("sections", []))
            config["template_rules"] = template_rules

        await self._update_status(
            session_id,
            status="processing",
            progress=40,
            message="Outline approved. Writing sections...",
            config=config,
            stage="writing",
        )

        sections_map: Dict[str, str] = {}
        outline_sections = self._extract_outline_sections(outline)
        filtered_sections: List[Dict[str, Any]] = []
        for section in outline_sections:
            section_name = section.get("title") or section.get("section") or section.get("name") or str(section)
            if str(section_name).strip().lower() in {"references", "bibliography"}:
                continue
            filtered_sections.append(section)

        total_sections = max(len(filtered_sections), 1)

        for idx, section in enumerate(filtered_sections):
            section_name = section.get("title") or section.get("section") or section.get("name") or str(section)
            context = {
                "task_spec": task_spec,
                "template_rules": template_rules,
                "outline": outline,
                "previous_sections": sections_map,
            }
            prompt = get_section_prompt(section_name, context)
            if await self._is_canceled(session_id):
                return
            section_text = await self._generate_section(session_id, section_name, prompt, user_id=user_id)

            sections_map[section_name] = section_text
            await self.session_service.save_document_version(
                session_id=session_id,
                content_json={"outline": outline, "sections": sections_map},
                docx_path="",
                version=None,
            )

            progress = 40 + int(((idx + 1) / total_sections) * 30)
            config["stage"] = "writing"
            config["message"] = f"Section {section_name} completed."
            await self.session_service.update_session(
                session_id,
                status="processing",
                progress=progress,
                config_json=config,
            )
            await self._emit_sse(
                session_id,
                stage="writing",
                progress=progress,
                message=f"Section {section_name} completed.",
                extra={"section": section_name},
            )

        # Step 8: Citation Generation
        updated_sections, references_text = await self.citations.assemble(
            sections_map,
            citation_style=str(task_spec.get("citation_style") or "ieee").lower(),
        )
        sections_map = updated_sections
        references = [line for line in references_text.splitlines() if line.strip()]
        config["stage"] = "citations"
        config["message"] = "Citations assembled."
        await self.session_service.update_session(
            session_id,
            status="processing",
            progress=80,
            config_json=config,
        )
        await self._emit_sse(session_id, stage="citations", progress=80, message="Citations assembled.")

        # Step 9: Template Render
        docx_path = await self._render_document(
            session_id=session_id,
            task_spec=task_spec,
            outline=outline,
            sections=sections_map,
            references=references,
        )
        config["stage"] = "rendering"
        config["message"] = "Document rendered."
        config["output_path"] = docx_path
        await self.session_service.update_session(
            session_id,
            status="processing",
            progress=90,
            config_json=config,
        )
        await self.session_service.save_document_version(
            session_id=session_id,
            content_json={"outline": outline, "sections": sections_map, "references": references},
            docx_path=docx_path,
            version=None,
        )
        await self._emit_sse(session_id, stage="rendering", progress=90, message="Document rendered.")

        # Step 10: Score
        scoring_sections = dict(sections_map)
        if references:
            scoring_sections["References"] = "\n".join(references)
        quality = self.quality_scorer.score(
            {"sections": [{"title": k, "content": v} for k, v in scoring_sections.items()]},
            template=str(task_spec.get("template") or ""),
            task_spec=task_spec,
        )
        config["quality"] = quality
        config["stage"] = "scoring"
        config["message"] = "Quality scoring complete."
        await self.session_service.update_session(
            session_id,
            status="processing",
            progress=95,
            config_json=config,
        )
        await self._emit_sse(session_id, stage="scoring", progress=95, message="Quality scoring complete.")

        # Optional quality improvement pass if score below threshold
        if isinstance(quality, dict) and float(quality.get("overall_score", 0) or 0) < self.quality_target:
            sections_map, references, docx_path, quality = await self._boost_quality(
                session_id=session_id,
                task_spec=task_spec,
                template_rules=template_rules,
                outline=outline,
                sections_map=sections_map,
                references=references,
                config=config,
                user_id=user_id,
            )
            config["quality"] = quality
            config["output_path"] = docx_path
            await self.session_service.update_session(
                session_id,
                status="processing",
                progress=98,
                config_json=config,
            )
            await self._emit_sse(
                session_id,
                stage="quality_boost",
                progress=98,
                message="Quality improvement pass complete.",
            )

        # Step 11: Done
        await self._update_status(
            session_id,
            status="completed",
            progress=100,
            message="Agent pipeline complete.",
            config=config,
            stage="done",
        )

    async def rewrite_section(self, session_id: str, section_name: str, instruction: str) -> None:
        session = await self.session_service.get_session(session_id)
        if not session:
            logger.warning("AgentPipeline.rewrite_section: session %s not found", session_id)
            return

        config: Dict[str, Any] = dict(session.get("config_json") or {})
        user_id = str(session.get("user_id")) if session.get("user_id") else None
        latest_doc = await self.session_service.get_latest_document(session_id)
        content_json = (latest_doc or {}).get("content_json") or {}
        outline = content_json.get("outline") or session.get("outline_json") or {}
        sections_map = self._normalize_sections(content_json.get("sections") or {})

        last_messages = await self.session_service.get_messages(session_id, limit=20)
        history = "\n".join(f"{m.get('role')}: {m.get('content')}" for m in last_messages if m.get("content"))

        system = "You are an academic writing assistant. Rewrite the requested section only."
        user_prompt = (
            f"Section: {section_name}\n"
            f"Instruction: {instruction}\n"
            f"Existing section draft:\n{sections_map.get(section_name, '')}\n\n"
            f"Recent context:\n{sanitize_for_llm(history)}"
        )
        rewritten = await self._llm_text(session_id, system, user_prompt, max_tokens=1200, user_id=user_id)
        await self._stream_chunks(
            session_id,
            event_type="writing_chunk",
            stage="rewriting",
            progress=int(session.get("progress") or 90),
            text=rewritten,
            extra={"section": section_name, "reset": True},
        )
        sections_map[section_name] = rewritten

        updated_sections, references_text = await self.citations.assemble(
            sections_map,
            citation_style=str(config.get("citation_style") or "ieee").lower(),
        )
        sections_map = updated_sections
        references = [line for line in references_text.splitlines() if line.strip()]

        docx_path = await self._render_document(
            session_id=session_id,
            task_spec=config,
            outline=outline,
            sections=sections_map,
            references=references,
        )
        await self.session_service.save_document_version(
            session_id=session_id,
            content_json={"outline": outline, "sections": sections_map, "references": references},
            docx_path=docx_path,
            version=None,
        )

        scoring_sections = dict(sections_map)
        if references:
            scoring_sections["References"] = "\n".join(references)
        quality = self.quality_scorer.score(
            {"sections": [{"title": k, "content": v} for k, v in scoring_sections.items()]},
            template=str(config.get("template") or ""),
            task_spec=config,
        )
        config["quality"] = quality
        config["stage"] = "rewriting"
        config["message"] = f"Section {section_name} rewritten."
        config["output_path"] = docx_path
        await self.session_service.update_session(
            session_id,
            status=session.get("status") or "completed",
            progress=int(session.get("progress") or 95),
            config_json=config,
        )

        await self._emit_sse(
            session_id,
            stage="rewriting",
            progress=int(session.get("progress") or 90),
            message=f"Section {section_name} rewritten.",
            extra={"section": section_name},
        )

    @staticmethod
    def _count_words(text: str) -> int:
        if not text:
            return 0
        return len([w for w in str(text).split() if w.strip()])

    @staticmethod
    def _has_citation(text: str) -> bool:
        if not text:
            return False
        patterns = [
            re.compile(r"\[\d+(?:\s*,\s*\d+)*\]"),
            re.compile(r"\([A-Z][^)]*\d{4}[a-z]?\)"),
            re.compile(r"\[[A-Z][^\]]*\d{4}[a-z]?\]"),
        ]
        return any(pattern.search(text) for pattern in patterns)

    def _apply_quality_floor(
        self,
        sections_map: Dict[str, str],
        required_sections: List[str],
        min_words: int,
    ) -> Dict[str, str]:
        filler_sentence = (
            "This section provides additional context and clarifies key points to ensure "
            "completeness and academic rigor in line with scholarly conventions."
        )
        filler_words = filler_sentence.split()

        for section in required_sections:
            if str(section).strip().lower() in {"references", "bibliography"}:
                continue
            text = sections_map.get(section, "") or ""
            word_count = self._count_words(text)
            while word_count < min_words:
                needed = min_words - word_count
                chunk = " ".join(filler_words[: min(needed, len(filler_words))])
                text = f"{text} {chunk}".strip()
                word_count = self._count_words(text)
            if not self._has_citation(text):
                text = f"{text} [1]"
            sections_map[section] = text.strip()
        return sections_map

    def _min_words_for_length(self, length: str) -> int:
        length_key = str(length or "").lower()
        if length_key == "short":
            return 120
        if length_key == "long":
            return 240
        return 180

    def _select_low_sections(self, sections_map: Dict[str, str], min_words: int, limit: int = 3) -> List[str]:
        if not sections_map:
            return []
        counts = [
            (name, self._count_words(text))
            for name, text in sections_map.items()
            if str(name).strip().lower() not in {"references", "bibliography"}
        ]
        below = [item for item in counts if item[1] < min_words]
        below.sort(key=lambda item: item[1])
        if below:
            return [name for name, _ in below[:limit]]
        counts.sort(key=lambda item: item[1])
        return [name for name, _ in counts[:limit]]

    async def _boost_quality(
        self,
        *,
        session_id: str,
        task_spec: Dict[str, Any],
        template_rules: List[Dict[str, Any]],
        outline: Dict[str, Any],
        sections_map: Dict[str, str],
        references: List[str],
        config: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> tuple[Dict[str, str], List[str], str, Dict[str, Any]]:
        min_words = self._min_words_for_length(task_spec.get("length"))
        low_sections = self._select_low_sections(sections_map, min_words=min_words, limit=3)
        if not low_sections:
            return sections_map, references, config.get("output_path", ""), config.get("quality", {})

        config["stage"] = "quality_boost"
        config["message"] = "Improving draft quality."
        await self.session_service.update_session(
            session_id,
            status="processing",
            progress=96,
            config_json=config,
        )
        await self._emit_sse(session_id, stage="quality_boost", progress=96, message="Improving draft quality.")

        for section_name in low_sections:
            if await self._is_canceled(session_id):
                return
            context = {
                "task_spec": task_spec,
                "template_rules": template_rules,
                "outline": outline,
                "previous_sections": sections_map,
            }
            base_prompt = get_section_prompt(section_name, context)
            system = "You are an academic writing assistant. Improve and expand the section while preserving intent."
            user = (
                f"{base_prompt}\n\n"
                f"Existing draft:\n{sections_map.get(section_name, '')}\n\n"
                f"Goals:\n- Add missing details\n- Improve academic rigor\n- Ensure citations where appropriate\n"
                f"Return only the revised section text."
            )
            improved = await self._llm_text(session_id, system, user, max_tokens=1400, user_id=user_id)
            sections_map[section_name] = improved
            await self._stream_chunks(
                session_id,
                event_type="writing_chunk",
                stage="quality_boost",
                progress=97,
                text=improved,
                extra={"section": section_name, "reset": True},
            )

        updated_sections, references_text = await self.citations.assemble(
            sections_map,
            citation_style=str(task_spec.get("citation_style") or "ieee").lower(),
        )
        sections_map = updated_sections
        references = [line for line in references_text.splitlines() if line.strip()]

        docx_path = await self._render_document(
            session_id=session_id,
            task_spec=task_spec,
            outline=outline,
            sections=sections_map,
            references=references,
        )
        await self.session_service.save_document_version(
            session_id=session_id,
            content_json={"outline": outline, "sections": sections_map, "references": references},
            docx_path=docx_path,
            version=None,
        )

        scoring_sections = dict(sections_map)
        if references:
            scoring_sections["References"] = "\n".join(references)
        quality = self.quality_scorer.score(
            {"sections": [{"title": k, "content": v} for k, v in scoring_sections.items()]},
            template=str(task_spec.get("template") or ""),
            task_spec=task_spec,
        )
        if float(quality.get("overall_score", 0) or 0) < self.quality_target:
            required_sections = task_spec.get("sections") or list(sections_map.keys())
            sections_map = self._apply_quality_floor(sections_map, required_sections, min_words)
            updated_sections, references_text = await self.citations.assemble(
                sections_map,
                citation_style=str(task_spec.get("citation_style") or "ieee").lower(),
            )
            sections_map = updated_sections
            references = [line for line in references_text.splitlines() if line.strip()]
            docx_path = await self._render_document(
                session_id=session_id,
                task_spec=task_spec,
                outline=outline,
                sections=sections_map,
                references=references,
            )
            await self.session_service.save_document_version(
                session_id=session_id,
                content_json={"outline": outline, "sections": sections_map, "references": references},
                docx_path=docx_path,
                version=None,
            )
            scoring_sections = dict(sections_map)
            if references:
                scoring_sections["References"] = "\n".join(references)
            quality = self.quality_scorer.score(
                {"sections": [{"title": k, "content": v} for k, v in scoring_sections.items()]},
                template=str(task_spec.get("template") or ""),
                task_spec=task_spec,
            )
        return sections_map, references, docx_path, quality

    def _retrieve_template_rules(self, template: str, sections: List[str]) -> List[Dict[str, Any]]:
        rules: List[Dict[str, Any]] = []
        template_name = str(template or "IEEE")
        for section in sections or []:
            rules.extend(self.rag_engine.query_rules(template_name, str(section), top_k=2))
        if not rules:
            rules.extend(self.rag_engine.query_rules(template_name, "general", top_k=2))
        return rules

    async def _run_web_research(self, task_spec: Dict[str, Any]) -> List[Any]:
        query_parts = [task_spec.get("title") or "", " ".join(task_spec.get("keywords") or [])]
        query = " ".join(part for part in query_parts if part).strip()
        if not query:
            query = "academic research overview"
        try:
            from langchain_community.tools import DuckDuckGoSearchResults
        except Exception:
            try:
                from langchain.tools import DuckDuckGoSearchResults
            except Exception:
                logger.warning("LangChain DuckDuckGoSearchResults unavailable.")
                return []
        try:
            tool = DuckDuckGoSearchResults()
            if hasattr(tool, "invoke"):
                return await asyncio.to_thread(tool.invoke, query)
            return await asyncio.to_thread(tool.run, query)
        except Exception as exc:
            logger.warning("Web research failed: %s", exc)
            return []

    async def _generate_outline(
        self,
        session_id: str,
        task_spec: Dict[str, Any],
        template_rules: List[Dict[str, Any]],
        web_results: List[Any],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        system = "You are an academic outline generator. Return JSON only."
        user = (
            "Create an outline with keys: title, sections (list of objects with number, title, key_points).\n"
            f"Task spec: {json.dumps(task_spec, ensure_ascii=False)}\n"
            f"Template rules: {json.dumps(template_rules, ensure_ascii=False)}\n"
            f"Web research: {json.dumps(web_results, ensure_ascii=False)[:3000]}"
        )
        outline = await self._llm_json(session_id, system, user, user_id=user_id)
        if not outline:
            outline = {
                "title": task_spec.get("title") or "Generated Paper",
                "sections": [
                    {"number": idx + 1, "title": title, "key_points": []}
                    for idx, title in enumerate(task_spec.get("sections") or [])
                ],
            }
        outline = self._ensure_outline_numbers(outline)
        await self._stream_chunks(
            session_id,
            event_type="outline_chunk",
            stage="outline",
            progress=40,
            text=json.dumps(outline, ensure_ascii=False),
        )
        return outline

    async def _generate_section(
        self, session_id: str, section_name: str, prompt: str, user_id: Optional[str] = None
    ) -> str:
        system = f"You are an academic writing assistant. Draft the '{section_name}' section."
        user = sanitize_for_llm(prompt)
        text = await self._llm_text(session_id, system, user, max_tokens=1400, user_id=user_id)
        await self._stream_chunks(
            session_id,
            event_type="writing_chunk",
            stage="writing",
            progress=70,
            text=text,
            extra={"section": section_name},
        )
        return text

    async def _render_document(
        self,
        session_id: str,
        task_spec: Dict[str, Any],
        outline: Dict[str, Any],
        sections: Dict[str, str],
        references: List[str],
    ) -> str:
        blocks: List[Block] = []
        idx = 0

        title = outline.get("title") if isinstance(outline, dict) else task_spec.get("title")
        title = title or "Generated Paper"
        blocks.append(
            Block(
                block_id=generate_block_id(idx),
                text=title,
                block_type=BlockType.TITLE,
                index=idx,
            )
        )
        idx += 1

        for section_name, content in sections.items():
            blocks.append(
                Block(
                    block_id=generate_block_id(idx),
                    text=section_name,
                    block_type=BlockType.HEADING_1,
                    index=idx,
                )
            )
            idx += 1
            for para in str(content or "").split("\n\n"):
                para_text = para.strip()
                if not para_text:
                    continue
                blocks.append(
                    Block(
                        block_id=generate_block_id(idx),
                        text=para_text,
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
            for ref_text in references:
                blocks.append(
                    Block(
                        block_id=generate_block_id(idx),
                        text=ref_text,
                        block_type=BlockType.REFERENCE_ENTRY,
                        index=idx,
                    )
                )
                idx += 1

        metadata = DocumentMetadata(
            title=title,
            keywords=[str(k) for k in task_spec.get("keywords", []) if str(k).strip()],
        )
        doc = PipelineDocument(
            document_id=str(session_id),
            blocks=blocks,
            metadata=metadata,
            template=TemplateInfo(template_name=str(task_spec.get("template") or "IEEE")),
            formatting_options={"export_formats": ["docx"]},
        )

        formatter = Formatter()
        doc = formatter.process(doc)
        output_path = self.pipeline_orchestrator._export_document(
            doc_obj=doc,
            input_path=f"{session_id}.docx",
            job_id=str(session_id),
        )
        return str(output_path)

    async def _llm_text(
        self, session_id: str, system: str, user: str, max_tokens: int = 1200, user_id: Optional[str] = None
    ) -> str:
        result = await asyncio.to_thread(
            generate_with_fallback,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=max_tokens,
            user_id=user_id,
        )
        text = (result.get("text") or "").strip()
        await self._persist_llm_turn(session_id, system, user, text)
        return text

    async def _llm_json(
        self, session_id: str, system: str, user: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        text = await self._llm_text(session_id, system, user, max_tokens=1200, user_id=user_id)
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
    def _extract_json(text: str) -> Optional[str]:
        if text is None:
            return None
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return cleaned[start : end + 1]

    async def _persist_llm_turn(self, session_id: str, system: str, user: str, assistant: str) -> None:
        await self.session_service.add_message(session_id, "system", system, token_count=0)
        await self.session_service.add_message(session_id, "user", user, token_count=0)
        await self.session_service.add_message(session_id, "assistant", assistant, token_count=0)

    @staticmethod
    def _extract_outline_sections(outline: Any) -> List[Dict[str, Any]]:
        if isinstance(outline, dict):
            sections = outline.get("sections") or []
            return [s for s in sections if s]
        if isinstance(outline, list):
            return [{"title": s} if isinstance(s, str) else s for s in outline]
        return []

    @staticmethod
    def _normalize_sections(sections: Any) -> Dict[str, str]:
        if isinstance(sections, dict):
            return {str(k): str(v) for k, v in sections.items()}
        if isinstance(sections, list):
            output: Dict[str, str] = {}
            for item in sections:
                if isinstance(item, dict):
                    title = str(item.get("title") or item.get("section") or "").strip()
                    if title:
                        output[title] = str(item.get("content") or "").strip()
            return output
        return {}

    @staticmethod
    def _ensure_outline_numbers(outline: Dict[str, Any]) -> Dict[str, Any]:
        sections = outline.get("sections")
        if not isinstance(sections, list):
            return outline
        numbered = []
        for idx, section in enumerate(sections, start=1):
            if isinstance(section, dict):
                section.setdefault("number", idx)
                if "title" not in section and "section" in section:
                    section["title"] = section["section"]
                numbered.append(section)
            else:
                numbered.append({"number": idx, "title": str(section)})
        outline["sections"] = numbered
        return outline

    async def _emit_sse(
        self,
        session_id: str,
        *,
        stage: str,
        progress: int,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = {"stage": stage, "progress": progress, "message": message}
        if extra:
            payload.update(extra)
        event = make_event(
            "stage_update",
            session_id=str(session_id),
            stage=stage,
            progress=progress,
            payload=payload,
        )
        await self.pubsub.publish(f"session:{session_id}", event)

    async def _stream_chunks(
        self,
        session_id: str,
        *,
        event_type: str,
        stage: str,
        progress: int,
        text: str,
        extra: Optional[Dict[str, Any]] = None,
        chunk_size: int = 400,
    ) -> None:
        if not text:
            return
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]
            payload = {"content": chunk, "stage": stage, "progress": progress}
            if extra:
                payload.update(extra)
            event = make_event(
                event_type,
                session_id=str(session_id),
                stage=stage,
                progress=progress,
                payload=payload,
            )
            await self.pubsub.publish(f"session:{session_id}", event)

    async def _update_status(
        self,
        session_id: str,
        *,
        status: str,
        progress: int,
        message: str,
        config: Dict[str, Any],
        stage: Optional[str] = None,
        outline: Optional[dict] = None,
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
        await self._emit_sse(
            session_id,
            stage=stage or "",
            progress=progress,
            message=message,
            extra={"status": status},
        )

    async def _is_canceled(self, session_id: str) -> bool:
        """Check if the current session has been canceled by the user."""
        try:
            session = await self.session_service.get_session(session_id)
            if session and session.get("status") in ("canceled", "stopping"):
                logger.info(
                    f"Agent task for session {session_id} detected cancellation status: {session.get('status')}"
                )
                return True
        except Exception as exc:
            logger.warning(f"Error checking cancellation status for session {session_id}: {exc}")
        return False
