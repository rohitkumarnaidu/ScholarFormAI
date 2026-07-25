# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.services.llm_service import generate_with_fallback
from app.services.llm_fallback_service import LLMUnavailableError

logger = logging.getLogger(__name__)

CLASSIFICATION_LABELS = [
    "HEADING", "ABSTRACT", "BODY", "REFERENCES", "FIGURE_CAPTION",
    "TABLE_CAPTION", "ACKNOWLEDGEMENTS", "EQUATION", "METHODOLOGY",
    "CONCLUSION", "AUTHOR_INFO", "TITLE",
]

CLASSIFICATION_PROMPT = """You are an expert academic document classifier. Given a text block from a scholarly paper, classify it into one of these categories:
- HEADING: Section or subsection title
- ABSTRACT: Abstract content
- BODY: Regular body paragraph
- REFERENCES: Reference/citation entry
- FIGURE_CAPTION: Figure caption
- TABLE_CAPTION: Table caption
- ACKNOWLEDGEMENTS: Acknowledgements or funding statement
- EQUATION: Mathematical equation
- METHODOLOGY: Methodology description
- CONCLUSION: Conclusion section
- AUTHOR_INFO: Author name or affiliation information
- TITLE: Paper title

Text block:
{text}

Respond with ONLY the category label and a confidence score between 0 and 1 in this JSON format:
{{"type": "CATEGORY", "confidence": 0.95}}"""

BATCH_CLASSIFICATION_PROMPT = """You are an expert academic document classifier. Given a list of text blocks from a scholarly paper, classify each one into one of these categories:
- HEADING: Section or subsection title
- ABSTRACT: Abstract content
- BODY: Regular body paragraph
- REFERENCES: Reference/citation entry
- FIGURE_CAPTION: Figure caption
- TABLE_CAPTION: Table caption
- ACKNOWLEDGEMENTS: Acknowledgements or funding statement
- EQUATION: Mathematical equation
- METHODOLOGY: Methodology description
- CONCLUSION: Conclusion section
- AUTHOR_INFO: Author name or affiliation information
- TITLE: Paper title

For each text block, respond with the category label and a confidence score between 0 and 1.

Text blocks:
{texts}

Respond with ONLY a JSON array in this format:
[{{"type": "CATEGORY", "confidence": 0.95}}, ...]"""


class LLMClassifier:
    """Classifies academic paper text blocks using an LLM."""

    def classify_block(
        self,
        text: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not text or not text.strip():
            return {"type": "BODY", "confidence": 0.5}
        return self._classify_text(text, user_id=user_id)

    def classify_batch(
        self,
        texts: List[str],
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not texts:
            return []
        return self._classify_texts_batch(texts, user_id=user_id)

    def _classify_text(self, text: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        llm_enabled = getattr(settings, "LLM_CLASSIFICATION_ENABLED", True)
        if not llm_enabled:
            return self._heuristic_classify(text)

        prompt = CLASSIFICATION_PROMPT.format(text=text[:2000])
        messages = [{"role": "user", "content": prompt}]

        try:
            result = generate_with_fallback(
                messages=messages,
                temperature=0.1,
                max_tokens=128,
                user_id=user_id,
            )
            raw = result.get("text", "")
            parsed = self._parse_response(raw)
            if parsed:
                return parsed
        except (LLMUnavailableError, Exception) as exc:
            logger.warning("LLM classification failed: %s. Using heuristic fallback.", exc)

        if getattr(settings, "LLM_CLASSIFICATION_FALLBACK_TO_RULES", True):
            return self._heuristic_classify(text)
        return {"type": "BODY", "confidence": 0.5}

    def _classify_texts_batch(self, texts: List[str], user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        llm_enabled = getattr(settings, "LLM_CLASSIFICATION_ENABLED", True)
        if not llm_enabled:
            return [self._heuristic_classify(t) for t in texts]

        numbered = "\n".join(f"[{i}] {t[:500]}" for i, t in enumerate(texts))
        prompt = BATCH_CLASSIFICATION_PROMPT.format(texts=numbered)
        messages = [{"role": "user", "content": prompt}]

        try:
            result = generate_with_fallback(
                messages=messages,
                temperature=0.1,
                max_tokens=256 + len(texts) * 64,
                user_id=user_id,
            )
            raw = result.get("text", "")
            parsed = self._parse_batch_response(raw)
            if len(parsed) == len(texts):
                return parsed
        except (LLMUnavailableError, Exception) as exc:
            logger.warning("LLM batch classification failed: %s. Using heuristic fallback.", exc)

        if getattr(settings, "LLM_CLASSIFICATION_FALLBACK_TO_RULES", True):
            return [self._heuristic_classify(t) for t in texts]
        return [{"type": "BODY", "confidence": 0.5} for _ in texts]

    def _parse_response(self, raw: str) -> Optional[Dict[str, Any]]:
        match = re.search(r'\{[^}]+\}', raw)
        if match:
            try:
                data = json.loads(match.group())
                label = str(data.get("type", "BODY")).strip().upper()
                confidence = float(data.get("confidence", 0.5))
                if label not in CLASSIFICATION_LABELS:
                    label = "BODY"
                return {"type": label, "confidence": max(0.0, min(1.0, confidence))}
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        for label in CLASSIFICATION_LABELS:
            if label in raw.upper():
                return {"type": label, "confidence": 0.7}
        return None

    def _parse_batch_response(self, raw: str) -> List[Dict[str, Any]]:
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                results = []
                for item in data:
                    label = str(item.get("type", "BODY")).strip().upper()
                    confidence = float(item.get("confidence", 0.5))
                    if label not in CLASSIFICATION_LABELS:
                        label = "BODY"
                    results.append({"type": label, "confidence": max(0.0, min(1.0, confidence))})
                return results
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        return []

    def _heuristic_classify(self, text: str) -> Dict[str, Any]:
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
            elif upper_text.startswith("INTRODUCTION"):
                prediction = {"type": "HEADING", "confidence": 0.8}
            elif upper_text.startswith("RESULTS") or upper_text.startswith("DISCUSSION"):
                prediction = {"type": "HEADING", "confidence": 0.8}
            elif text.startswith("Figure") or text.startswith("Fig."):
                prediction = {"type": "FIGURE_CAPTION", "confidence": 0.7}
            elif text.startswith("Table") or text.startswith("Tab."):
                prediction = {"type": "TABLE_CAPTION", "confidence": 0.7}
            elif text and text[0].isupper() and len(text) < 80:
                prediction = {"type": "HEADING", "confidence": 0.6}
        return prediction

    @staticmethod
    def labels() -> List[str]:
        return list(CLASSIFICATION_LABELS)


_classifier_instance = None


def get_llm_classifier() -> LLMClassifier:
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = LLMClassifier()
    return _classifier_instance
