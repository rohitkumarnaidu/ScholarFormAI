# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
LLM-based PDF parser that replaces Nougat + Docling HF Space services.

Tier 1: Vision API (GPT-4o, Claude 3.5, Gemini 2.0) — best quality
Tier 2: PyMuPDF text extraction + LLM structure analysis — fallback
Tier 3: Raw PyMuPDF text extraction — last resort
"""

from __future__ import annotations

import logging
import os
import re
import base64
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.models import (
    Block,
    BlockType,
    DocumentMetadata,
    PipelineDocument as Document,
    TextStyle,
)
from app.pipeline.parsing.base_parser import BaseParser
from app.services.llm_service import generate_with_model
from app.utils.id_generator import generate_block_id

logger = logging.getLogger(__name__)

LITELLM_AVAILABLE = False
try:
    from litellm import completion as litellm_completion

    LITELLM_AVAILABLE = True
except ImportError:
    pass


def _has_vision_capability(model_name: str) -> bool:
    """Check if a model name suggests vision capability."""
    if not model_name:
        return False
    vision_prefixes = {
        "gpt-4o",
        "gpt-4-vision",
        "gpt-4-turbo",
        "claude-3",
        "claude-3.5",
        "claude-3-opus",
        "claude-3-sonnet",
        "claude-3-haiku",
        "claude-3.5-sonnet",
        "claude-3.5-haiku",
        "gemini-2.0",
        "gemini-2.5",
        "gemini-1.5",
        "gemini-pro-vision",
    }
    model_lower = model_name.lower()
    return any(model_lower.startswith(p) for p in vision_prefixes)


def _pdf_to_images(file_path: str, dpi: int = 200) -> list:
    import fitz
    from PIL import Image

    images = []
    pdf_doc = fitz.open(file_path)
    for page in pdf_doc:
        pix = page.get_pixmap(dpi=dpi)
        images.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
    pdf_doc.close()
    return images


def _image_to_base64(image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _classify_llm_line(line: str) -> BlockType:
    stripped = line.strip()
    if not stripped:
        return BlockType.UNKNOWN

    if stripped.startswith("### "):
        return BlockType.HEADING_3
    if stripped.startswith("## "):
        return BlockType.HEADING_2
    if stripped.startswith("# "):
        return BlockType.HEADING_1

    if stripped.lower().startswith("abstract"):
        return BlockType.ABSTRACT

    if stripped.lower() in ("references", "bibliography"):
        return BlockType.HEADING_1

    if stripped.startswith("- ") or stripped.startswith("* ") or re.match(r"^\d+\.\s", stripped):
        return BlockType.LIST_ITEM

    if "|" in stripped and stripped.count("|") >= 2:
        return BlockType.UNKNOWN

    return BlockType.BODY


class LLMPDFParser(BaseParser):
    """
    Replaces Nougat + Docling HF Spaces with provider-based LLM parsing.

    Tier 1: Vision API (GPT-4o, Claude 3.5, Gemini 2.0) — best quality
    Tier 2: PyMuPDF text extraction + LLM structure analysis — fallback
    Tier 3: Raw PyMuPDF text extraction — last resort
    """

    def __init__(self):
        self.block_counter = 0

    def supports_format(self, file_extension: str) -> bool:
        return file_extension.lower() == ".pdf"

    def parse(self, file_path: str, document_id: str) -> Document:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        document = self._new_document(file_path, document_id)

        if self._vision_available():
            try:
                return self._parse_via_vision(file_path, document_id)
            except Exception as exc:
                logger.warning("LLM PDF Vision API parsing failed: %s", exc)
                document.add_processing_stage(
                    stage_name="parsing",
                    status="warning",
                    message=f"Vision API failed, trying text+LLM fallback: {exc}",
                )

        try:
            return self._parse_via_text_llm(file_path, document_id)
        except Exception as exc:
            logger.warning("LLM text+structure parsing failed: %s", exc)
            document.add_processing_stage(
                stage_name="parsing",
                status="warning",
                message=f"LLM text parsing failed, using raw extraction: {exc}",
            )

        return self._parse_via_raw_pymupdf(file_path, document_id)

    def _new_document(self, file_path: str, document_id: str) -> Document:
        now = datetime.now(timezone.utc)
        document = Document(
            document_id=str(document_id),
            original_filename=Path(file_path).name,
            source_path=file_path,
            created_at=now,
            updated_at=now,
        )
        document.metadata = DocumentMetadata()
        return document

    def _vision_available(self) -> bool:
        if not settings.LLM_PDF_PARSER_VISION_API_ENABLED:
            return False
        for provider_attr in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"):
            if getattr(settings, provider_attr, None):
                return True
        return False

    def _get_vision_model(self) -> Optional[str]:
        if getattr(settings, "OPENAI_API_KEY", None):
            return "gpt-4o"
        if getattr(settings, "ANTHROPIC_API_KEY", None):
            return "claude-3.5-sonnet"
        if getattr(settings, "GOOGLE_API_KEY", None):
            return "gemini-2.0-flash"
        return None

    def _call_vision_api(self, messages: List[Dict[str, Any]]) -> str:
        """Call a vision-capable model, handling multimodal content."""
        model_name = self._get_vision_model()
        if not model_name:
            raise RuntimeError("No vision-capable provider configured")

        if LITELLM_AVAILABLE:
            api_key = None
            api_base = None
            if model_name.startswith("gpt"):
                api_key = settings.OPENAI_API_KEY
            elif model_name.startswith("claude"):
                api_key = settings.ANTHROPIC_API_KEY
                api_base = "https://api.anthropic.com"
            elif model_name.startswith("gemini"):
                api_key = settings.GOOGLE_API_KEY

            kwargs = {
                "model": model_name,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 4096,
            }
            if api_key:
                kwargs["api_key"] = api_key
            if api_base:
                kwargs["api_base"] = api_base

            response = litellm_completion(**kwargs)
            choices = response.choices
            if choices and choices[0].message.content:
                return choices[0].message.content
            return ""

        raise RuntimeError("LiteLLM unavailable for vision API calls")

    def _parse_via_vision(self, file_path: str, document_id: str) -> Document:
        import fitz
        from PIL import Image

        document = self._new_document(file_path, document_id)
        model_name = self._get_vision_model()
        logger.info("LLMPDFParser: Tier 1 Vision API using %s", model_name)

        pdf_doc = fitz.open(file_path)
        num_pages = len(pdf_doc)
        all_blocks: List[Block] = []
        self.block_counter = 0

        for page_num in range(num_pages):
            page = pdf_doc[page_num]
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            b64_image = _image_to_base64(img)

            prompt = (
                "You are an academic PDF parser. Extract ALL text from this page image "
                "and return it as clean Markdown. Preserve the document structure:\n"
                "- Use # for main title, ## for section headings, ### for subsection headings\n"
                "- Preserve paragraph breaks\n"
                "- Convert tables to Markdown table format\n"
                "- Wrap equations in $$...$$\n"
                "- Preserve list formatting with - or 1.\n"
                "Return ONLY the extracted Markdown text, no explanations."
            )

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_image}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ]

            try:
                page_text = self._call_vision_api(messages).strip()
                if page_text:
                    page_blocks = self._parse_llm_output(page_text)
                    all_blocks.extend(page_blocks)
            except Exception as exc:
                logger.warning("LLM Vision page %d failed: %s", page_num + 1, exc)

        pdf_doc.close()

        document.blocks = all_blocks
        document.figures = []
        document.add_processing_stage(
            stage_name="parsing",
            status="success",
            message=(f"Parsed PDF with LLM Vision API ({model_name}): {len(all_blocks)} blocks from {num_pages} pages"),
        )
        document.metadata.ai_hints = document.metadata.ai_hints or {}
        document.metadata.ai_hints["parser"] = "llm_vision"
        document.metadata.ai_hints["llm_model"] = model_name
        return document

    def _parse_via_text_llm(self, file_path: str, document_id: str) -> Document:
        import fitz

        document = self._new_document(file_path, document_id)

        pdf_doc = fitz.open(file_path)
        num_pages = len(pdf_doc)
        page_texts: List[str] = []

        for page_num in range(num_pages):
            page = pdf_doc[page_num]
            text = page.get_text("text") or ""
            page_texts.append(text)
        pdf_doc.close()

        full_text = "\n\n--- Page Break ---\n\n".join(page_texts)

        try:
            structured_markdown = self._llm_structure_text(full_text)
            blocks = self._parse_llm_output(structured_markdown)
        except Exception as exc:
            logger.warning("LLM structure analysis failed, using raw text: %s", exc)
            blocks = self._parse_llm_output(full_text)

        document.blocks = blocks
        document.figures = []
        document.add_processing_stage(
            stage_name="parsing",
            status="success",
            message=(f"Parsed PDF with LLM text+structure analysis: {len(blocks)} blocks"),
        )
        document.metadata.ai_hints = document.metadata.ai_hints or {}
        document.metadata.ai_hints["parser"] = "llm_text"
        return document

    def _llm_structure_text(self, raw_text: str) -> str:
        prompt = (
            "You are an academic document structure analyzer. Given raw text extracted from a PDF, "
            "reorganize it into clean Markdown that preserves the document's structure:\n"
            "- Use # for the document title\n"
            "- Use ## for major section headings\n"
            "- Use ### for subsection headings\n"
            "- Preserve paragraph breaks\n"
            "- Convert tables to Markdown table format\n"
            "- Wrap equations in $$...$$\n"
            "- Preserve list formatting with - or 1.\n"
            "Return ONLY the structured Markdown, no explanations.\n\n"
            f"Raw text:\n\n{raw_text[:150000]}"
        )

        messages = [{"role": "user", "content": prompt}]
        result = generate_with_model(
            messages=messages,
            model_name="gpt-4o-mini",
            temperature=0.1,
            max_tokens=8192,
        )
        return result.get("text", "")

    def _parse_via_raw_pymupdf(self, file_path: str, document_id: str) -> Document:
        import fitz

        document = self._new_document(file_path, document_id)
        pdf_doc = fitz.open(file_path)
        all_blocks: List[Block] = []
        self.block_counter = 0

        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            text = page.get_text("text") or ""
            if text.strip():
                block_id = generate_block_id(self.block_counter)
                self.block_counter += 1
                all_blocks.append(
                    Block(
                        block_id=block_id,
                        text=text.strip(),
                        index=self.block_counter * 100,
                        block_type=BlockType.BODY,
                        page_number=page_num + 1,
                    )
                )
        pdf_doc.close()

        document.blocks = all_blocks
        document.figures = []
        document.add_processing_stage(
            stage_name="parsing",
            status="success",
            message=(f"Parsed PDF with raw PyMuPDF extraction: {len(all_blocks)} blocks"),
        )
        document.metadata.ai_hints = document.metadata.ai_hints or {}
        document.metadata.ai_hints["parser"] = "pymupdf_raw"
        return document

    def _parse_llm_output(self, text: str) -> List[Block]:
        blocks: List[Block] = []
        if not text:
            return blocks

        raw_blocks = re.split(r"\n{2,}", text)
        for raw in raw_blocks:
            raw = raw.strip()
            if not raw:
                continue

            block_type = _classify_llm_line(raw)
            clean_text = raw
            heading_level = 0
            if raw.startswith("### "):
                clean_text = raw[4:]
                heading_level = 3
            elif raw.startswith("## "):
                clean_text = raw[3:]
                heading_level = 2
            elif raw.startswith("# "):
                clean_text = raw[2:]
                heading_level = 1

            block_id = generate_block_id(self.block_counter)
            self.block_counter += 1
            style = TextStyle(bold=(heading_level > 0))
            block = Block(
                block_id=block_id,
                text=clean_text,
                index=self.block_counter * 100,
                block_type=block_type,
                style=style,
            )

            if heading_level > 0:
                block.metadata["heading_level"] = heading_level
                block.metadata["potential_heading"] = True
            if "\\[" in raw or "$$" in raw or "\\begin{" in raw:
                block.metadata["has_equation"] = True
            if "|" in raw and raw.count("|") >= 2:
                block.metadata["is_table"] = True

            block.metadata["parser"] = "llm_pdf"
            blocks.append(block)

        return blocks

    def analyze_layout(self, file_path: str) -> Dict[str, Any]:
        """
        Replace Docling layout analysis with LLM-based structure analysis.
        Returns the same format as DoclingClient.analyze_layout().
        """
        import fitz

        try:
            pdf_doc = fitz.open(file_path)
            num_pages = len(pdf_doc)
            page_texts = []
            for page_num in range(min(num_pages, 5)):
                page = pdf_doc[page_num]
                text = page.get_text("text") or ""
                page_texts.append(f"--- Page {page_num + 1} ---\n{text}")
            pdf_doc.close()

            sample_text = "\n\n".join(page_texts)

            prompt = (
                "You are a document layout analyzer. Given the extracted text from a PDF, "
                "identify the document's structural elements. For each element, determine:\n"
                "- type: one of 'title', 'section_header', 'subsection_header', 'paragraph', 'table', 'figure', 'list', 'equation', 'header', 'footer', 'abstract'\n"
                "- text: the element text\n"
                "- level: heading level (1-4) for headers, 0 otherwise\n"
                "- confidence: 0.0 to 1.0\n\n"
                "Return a JSON object with an 'elements' array. Example:\n"
                '{"elements": [{"type": "title", "text": "Paper Title", "level": 0, "confidence": 0.95}]}\n\n'
                f"Document text:\n\n{sample_text[:100000]}"
            )

            messages = [{"role": "user", "content": prompt}]
            result = generate_with_model(
                messages=messages,
                model_name="gpt-4o-mini",
                temperature=0.1,
                max_tokens=4096,
            )
            response_text = result.get("text", "")

            try:
                layout_data = json.loads(response_text)
            except json.JSONDecodeError:
                json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response_text)
                if json_match:
                    layout_data = json.loads(json_match.group(1))
                else:
                    raise

            return {
                "elements": layout_data.get("elements", []),
                "headers": layout_data.get("headers", []),
                "footers": layout_data.get("footers", []),
                "tables": layout_data.get("tables", []),
                "figures": layout_data.get("figures", []),
                "confidence": layout_data.get("confidence", 0.85),
                "pages": num_pages,
            }
        except Exception as exc:
            logger.warning("LLM layout analysis failed: %s", exc)
            return {
                "elements": [],
                "headers": [],
                "footers": [],
                "tables": [],
                "figures": [],
                "confidence": 0.0,
                "pages": 0,
            }
