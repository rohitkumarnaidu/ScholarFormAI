# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import logging
import re
from typing import Any

from app.models import Block
from app.pipeline.classification.llm_classifier import get_llm_classifier
from app.pipeline.safety import safe_function
from app.services.classification_gate import should_enable_llm_classification
from app.utils.singleton import get_or_create

try:
    from langdetect import detect as detect_language

    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False
    detect_language = None

logger = logging.getLogger(__name__)


class SemanticParser:
    """
    NLP semantic layer for manuscript block classification.

    Execution order:
    1) LLM-based classifier (when enabled)
    2) Deterministic heuristics
    """

    def __init__(self):
        self._llm_classifier = None

    @property
    def llm_classifier(self):
        if self._llm_classifier is None:
            self._llm_classifier = get_llm_classifier()
        return self._llm_classifier

    def detect_boundaries(self, blocks: list[Block]) -> list[Block]:
        try:
            return self._repair_fragmented_headings(blocks)
        except Exception as exc:
            logger.warning(
                "SemanticParser Guard: detect_boundaries failed: %s. Returning original blocks.",
                exc,
            )
            return blocks

    def reconcile_fragmented_headings(self, blocks: list[Block]) -> list[Block]:
        try:
            return self._repair_fragmented_headings(blocks)
        except Exception as exc:
            logger.warning(
                "SemanticParser Guard: reconcile_fragmented_headings failed: %s. Returning original blocks.",
                exc,
            )
            return blocks

    @safe_function(fallback_value=[], error_message="SemanticParser.analyze_blocks failed")
    def analyze_blocks(
        self,
        blocks: list[Block],
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        llm_enabled = should_enable_llm_classification()

        semantic_blocks: list[dict[str, Any]] = []
        combined_text = " ".join(b.text for b in blocks[:10] if b.text)[:500]
        detected_lang = "en"
        if HAS_LANGDETECT and combined_text.strip():
            try:
                detected_lang = detect_language(combined_text)
            except Exception:
                detected_lang = "en"

        use_llm = llm_enabled and detected_lang == "en"
        if not use_llm and detected_lang != "en":
            logger.warning(
                "Non-English document detected (%s). Using heuristic-only mode.",
                detected_lang,
            )

        repaired_blocks = self._repair_fragmented_headings(blocks)
        texts = [block.text or "" for block in repaired_blocks]
        if use_llm:
            predictions = self._predict_block_types_batch(texts, user_id=user_id)
        else:
            predictions = [self._heuristic_classify(text) for text in texts]

        for i, block in enumerate(repaired_blocks):
            prediction = predictions[i] if i < len(predictions) else self._heuristic_classify(block.text)
            semantic_block = {
                "block_id": i,
                "raw_text": block.text,
                "predicted_section_type": prediction["type"],
                "confidence_score": prediction["confidence"],
                "detected_language": detected_lang,
            }
            semantic_blocks.append(semantic_block)

        return semantic_blocks

    def _predict_block_type(
        self,
        text: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        if should_enable_llm_classification():
            return self.llm_classifier.classify_block(text, user_id=user_id)
        return self._heuristic_classify(text)

    def _predict_block_types_batch(
        self,
        texts: list[str],
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if not texts:
            return []
        if should_enable_llm_classification():
            predictions = self.llm_classifier.classify_batch(texts, user_id=user_id)
            if predictions:
                return predictions
        return [self._heuristic_classify(text) for text in texts]

    def predict_blocks_batch(
        self,
        texts: list[str],
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._predict_block_types_batch(texts, user_id=user_id)

    def _heuristic_classify(self, text: str) -> dict[str, Any]:
        prediction = {"type": "BODY", "confidence": 0.5}
        text = (text or "").strip()
        upper_text = text.upper()

        if len(text) < 150:
            if upper_text.startswith("ABSTRACT"):
                prediction = {"type": "ABSTRACT", "confidence": 0.8}
            elif upper_text.startswith("REFERENCES") or upper_text.startswith("BIBLIOGRAPHY"):
                prediction = {"type": "REFERENCES", "confidence": 0.8}
            elif re.match(r"^\[\d+\]", text) or re.match(r"^\d+\.\s+[A-Z]", text):
                prediction = {"type": "REFERENCES", "confidence": 0.75}
            elif upper_text.startswith("ACKNOWLEDGEMENTS") or upper_text.startswith("ACKNOWLEDGMENTS"):
                prediction = {"type": "ACKNOWLEDGEMENTS", "confidence": 0.8}
            elif upper_text.startswith("METHODOLOGY") or upper_text.startswith("METHODS"):
                prediction = {"type": "METHODOLOGY", "confidence": 0.8}
            elif upper_text.startswith("CONCLUSION") or upper_text.startswith("CONCLUSIONS"):
                prediction = {"type": "CONCLUSION", "confidence": 0.8}
            elif upper_text.startswith("INTRODUCTION") or upper_text.startswith("RESULTS") or upper_text.startswith("DISCUSSION"):
                prediction = {"type": "HEADING", "confidence": 0.8}
            elif text.startswith("Figure") or text.startswith("Fig."):
                prediction = {"type": "FIGURE_CAPTION", "confidence": 0.7}
            elif text.startswith("Table") or text.startswith("Tab."):
                prediction = {"type": "TABLE_CAPTION", "confidence": 0.7}
            elif text and text[0].isupper() and len(text) < 80:
                prediction = {"type": "HEADING", "confidence": 0.6}
        return prediction

    def classify_block(
        self,
        text: str,
        use_transformer: bool = True,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        if should_enable_llm_classification() and use_transformer:
            return self._predict_block_type(text, user_id=user_id)
        return self._heuristic_classify(text)

    def _repair_fragmented_headings(self, blocks: list[Block]) -> list[Block]:
        repaired = []
        i = 0
        while i < len(blocks):
            current = blocks[i]
            if i + 1 < len(blocks):
                next_block = blocks[i + 1]
                if current.text.isdigit() and next_block.text and next_block.text[0].islower():
                    current.text = f"{current.text}. {next_block.text}"
                    repaired.append(current)
                    i += 2
                    continue
            repaired.append(current)
            i += 1
        return repaired


_semantic_parser = None


def get_semantic_parser() -> SemanticParser:
    global _semantic_parser
    _semantic_parser = get_or_create(_semantic_parser, SemanticParser)
    return _semantic_parser
