# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
NLP Content Analyzer - Enriches document with AI/NLP hints (Read-Only).
"""

import importlib.util
import json
import logging
import re

from app.models import Block, BlockType
from app.models import PipelineDocument as Document
from app.services.llm_service import generate_with_fallback
from app.utils.singleton import get_or_create_safe

logger = logging.getLogger(__name__)

try:
    YAKE_AVAILABLE = importlib.util.find_spec("yake") is not None
except Exception:
    YAKE_AVAILABLE = False

# KeyBERT import is heavy; defer to runtime to avoid startup OOM on low-memory deploys.
KEYBERT_AVAILABLE = False

NLP_AVAILABLE = YAKE_AVAILABLE or KEYBERT_AVAILABLE
_KEYBERT_MODEL = None

from app.pipeline.base import PipelineStage


class ContentAnalyzer(PipelineStage):
    """
    Analyzes document content to provide advisory hints.
    Does NOT modify content or block types.
    """

    def __init__(self):
        self.nlp = None

    def process(self, document: Document) -> Document:
        """
        Run analysis on the document blocks.
        Populates block.metadata["ai_hints"].
        """
        # Load model if strictly needed here, or use initialized one

        for block in document.blocks:
            hints = {}

            # 1. Section Confidence Estimation
            # Simple heuristic + Entity analysis if available
            section_conf = self._estimate_section_confidence(block)
            if section_conf:
                hints["predicted_section"] = section_conf["section"]
                hints["confidence"] = section_conf["confidence"]
                hints["notes"] = section_conf["notes"]

            # 2. Caption Quality
            # If block might be a caption (starts with Fig/Table)
            if self._is_potential_caption(block.text):
                quality = self._evaluate_caption_quality(block.text)
                hints["caption_quality"] = quality

            # 3. Readability (Abstract)
            # If we think it's abstract body
            if block.block_type == BlockType.ABSTRACT_BODY or methods_detect_abstract(block.text):
                readability = self._check_readability(block.text)
                hints["readability"] = readability

            # Attach hints if any
            if hints:
                if not block.metadata:
                    block.metadata = {}
                block.metadata["ai_hints"] = hints

        return document

    def _estimate_section_confidence(self, block: Block) -> dict:
        """Estimate if block is a section header."""
        text = block.text.strip().lower()
        if not text:
            return None

        # Rules
        headers = {
            "abstract": 0.95,
            "introduction": 0.9,
            "methods": 0.8,
            "methodology": 0.8,
            "results": 0.8,
            "discussion": 0.8,
            "conclusion": 0.8,
            "references": 0.95,
            "bibliography": 0.95,
        }

        # Exact match (ignoring numbering "1. Introduction")
        clean = re.sub(r"^[\d\.]+\s*", "", text)
        if clean in headers:
            return {"section": clean.title(), "confidence": headers[clean], "notes": ["Keyword match"]}

        return None

    def _is_potential_caption(self, text: str) -> bool:
        return text.lstrip().lower().startswith(("fig", "table", "chart"))

    def _evaluate_caption_quality(self, text: str) -> str:
        """Rate caption: Good, Short, Vague."""
        words = text.split()
        if len(words) < 5:
            return "Short"

        vague_words = ["image", "chart", "diagram", "below", "above"]
        if any(w in text.lower() for w in vague_words) and len(words) < 10:
            return "Possibly Vague"

        return "Good"

    def _check_readability(self, text: str) -> str:
        """Simple readability check."""
        # Sentence length
        sentences = re.split(r"[.!?]+", text)
        sentences = [s for s in sentences if s.strip()]
        if not sentences:
            return "N/A"

        avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
        if avg_len > 30:
            return "Complex (Long Sentences)"
        elif avg_len < 8:
            return "Simple (Short Sentences)"
        return "Standard"


def methods_detect_abstract(text: str) -> bool:
    """Helper to detect abstract-like text."""
    # Heuristic
    return "background" in text.lower() and "results" in text.lower() and len(text) > 200


def _get_keybert_model():
    global _KEYBERT_MODEL
    if _KEYBERT_MODEL is None:
        try:
            if importlib.util.find_spec("keybert") is None:
                return None
            from keybert import KeyBERT  # local import to avoid startup cost
        except Exception as exc:
            logger.warning("KeyBERT import failed: %s", exc)
            return None
        _KEYBERT_MODEL = get_or_create_safe(
            _KEYBERT_MODEL,
            KeyBERT,
            logger=logger,
            name="KeyBERT model",
            log_level="warning",
        )
    return _KEYBERT_MODEL


def extract_keywords(text: str, top_k: int = 8) -> list[str]:
    """
    Enhancement-aware keyword extraction with strict fallback order.
    Default order: keybert -> yake -> basic.
    """
    text = (text or "").strip()
    if not text:
        return []

    def basic_fallback() -> list[str]:
        # Ultimate fallback: deterministic token frequency heuristic.
        tokens = [t.strip(".,;:!?()[]{}").lower() for t in text.split()]
        tokens_local = [t for t in tokens if len(t) > 3]
        freq: dict[str, int] = {}
        for token in tokens_local:
            freq[token] = freq.get(token, 0) + 1
        return [tok for tok, _count in sorted(freq.items(), key=lambda item: item[1], reverse=True)[:top_k]]

    backend_order = ["keybert", "yake", "basic"]
    try:
        from app.services.enhancement_manager import enhancement_manager

        profile = enhancement_manager.profile
        if profile.enabled and profile.keyword_enabled:
            backend_order = enhancement_manager.get_keyword_backends()
        else:
            backend_order = ["basic"]
    except Exception as exc:
        logger.debug("Enhancement profile unavailable for keyword extraction: %s", exc)

    yake_candidates: list[str] = []
    for backend in backend_order:
        if backend == "keyllm":
            try:
                llm_keywords = _extract_keywords_with_keyllm(text, top_k=top_k)
                if llm_keywords:
                    return llm_keywords
            except Exception as exc:
                logger.warning("KeyLLM extraction failed: %s", exc)

        if backend == "yake":
            if not YAKE_AVAILABLE:
                continue
            try:
                import yake

                extractor = yake.KeywordExtractor(lan="en", n=2, top=max(top_k * 2, 10))
                yake_candidates = [kw for kw, _score in extractor.extract_keywords(text) if kw]
                if yake_candidates:
                    return yake_candidates[:top_k]
            except Exception as exc:
                logger.warning("YAKE extraction failed: %s", exc)

        elif backend == "keybert":
            keybert_model = _get_keybert_model()
            if keybert_model is None:
                continue
            try:
                if not yake_candidates and YAKE_AVAILABLE:
                    import yake

                    extractor = yake.KeywordExtractor(lan="en", n=2, top=max(top_k * 2, 10))
                    yake_candidates = [kw for kw, _score in extractor.extract_keywords(text) if kw]

                kw = keybert_model.extract_keywords(
                    text,
                    candidates=yake_candidates or None,
                    top_n=top_k,
                    stop_words="english",
                )
                keywords = [item[0] for item in kw if item and item[0]]
                if keywords:
                    return keywords
            except Exception as exc:
                logger.warning("KeyBERT extraction failed: %s", exc)

        elif backend == "basic":
            return basic_fallback()

    # Safety fallback: never fail keyword extraction.
    if yake_candidates:
        return yake_candidates[:top_k]
    tokens = [t.strip(".,;:!?()[]{}").lower() for t in text.split()]
    tokens = [t for t in tokens if len(t) > 3]
    freq: dict[str, int] = {}
    for token in tokens:
        freq[token] = freq.get(token, 0) + 1
    return [tok for tok, _count in sorted(freq.items(), key=lambda item: item[1], reverse=True)[:top_k]]


def _parse_keyword_payload(raw: str, top_k: int) -> list[str]:
    if not raw:
        return []
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = cleaned.rstrip("`").strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start == -1 or end <= start:
            return []
        try:
            payload = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return []

    if isinstance(payload, dict):
        payload = payload.get("keywords") or payload.get("items") or []
    if not isinstance(payload, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in payload:
        token = str(item or "").strip()
        if not token:
            continue
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(token)
        if len(normalized) >= top_k:
            break
    return normalized


def _extract_keywords_with_keyllm(text: str, top_k: int) -> list[str]:
    prompt = (
        f"Extract the top {max(1, top_k)} semantic keywords from this academic text. "
        "Return strict JSON as an array of keyword strings only."
    )
    result = generate_with_fallback(
        [
            {"role": "system", "content": "You extract semantic keywords for research indexing."},
            {"role": "user", "content": f"{prompt}\n\n{text[:3500]}"},
        ],
        temperature=0.0,
        max_tokens=200,
    )
    response_text = str((result or {}).get("text") or "").strip()
    return _parse_keyword_payload(response_text, top_k=top_k)
