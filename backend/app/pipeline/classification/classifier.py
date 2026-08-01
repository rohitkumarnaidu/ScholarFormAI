# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Content Classifier - Assigns semantic types to blocks.

This module determines the semantic role of each block (Title, Author,
Heading, Body, etc.) based on the structure detected in the previous stage.

Input: Document with structure metadata (headings, sections)
Output: Document with BlockType assigned
"""

import logging
import re
from datetime import UTC, datetime
from typing import Any

from app.config.settings import settings  # Import settings for dynamic thresholds
from app.models import Block, BlockType
from app.models import PipelineDocument as Document
from app.pipeline.base import PipelineStage
from app.pipeline.classification.llm_classifier import get_llm_classifier
from app.services.classification_gate import should_enable_llm_classification

logger = logging.getLogger(__name__)


class ContentClassifier(PipelineStage):
    """
    Assigns semantic BlockTypes to blocks based on structure and heuristics.

    Rules:
    - Headings identified in structure detection get HEADING_* types (or specific ones like ABSTRACT_HEADING)
    - Content between headings gets BODY type (or specific ones like ABSTRACT_BODY)
    - Front matter (before first section) is analyzed for Title, Author, Affiliation
    - References section gets REFERENCE_ENTRY types
    """

    def __init__(self):
        """Initialize the classifier."""
        # Keywords that indentify specific section types
        self.abstract_keywords = ["abstract", "summary", "resumen", "résumé"]
        self.keywords_keywords = ["keywords", "key words", "palabras clave", "mots-clés"]
        self.acknowledgements_keywords = [
            "acknowledgements",
            "acknowledgments",
            "funding",
            "conflicts of interest",
            "author contributions",
            "declaration of interest",
        ]
        self.references_keywords = {"references", "bibliography", "works cited"}

        # FEAT 49: Footnote and appendix detection patterns
        self.footnote_patterns = [
            r"^\d+\s",  # "1 Some footnote text"
            r"^\[\d+\]",  # "[1] Footnote"
            r"^ ",  # Dagger footnote marker
            r"^‡",  # Double dagger
            r"^※",  # Reference mark
            r"^\*\s",  # Asterisk footnote
        ]
        self.appendix_keywords = [
            "appendix",
            "annex",
            "annexure",
            "supplement",
            "supplementary",
            "supporting information",
            "supporting material",
        ]

        # Heuristics for affiliation detection
        self.affiliation_indicators = {
            "university",
            "college",
            "department",
            "institute",
            "school",
            "laboratory",
            "center",
            "centre",
            "hospital",
            "clinic",
            "corp",
            "inc",
            "ltd",
            "gmbh",
            "foundation",
            "limited",
            "road",
            "st.",
            "street",
            "ave",
            "avenue",
            "box",
            "email",
            "ph.",
            "fax",
            "tel",
        }

        # Keywords that exclude a block from being an AUTHOR
        self.author_exclusion_keywords = {
            "university",
            "college",
            "department",
            "institute",
            "school",
            "laboratory",
            "center",
            "centre",
            "division",
        }

        # LLM classification tuning
        self.llm_min_confidence = max(0.6, getattr(settings, "HEURISTIC_CONFIDENCE_MEDIUM", 0.6))

    def _looks_like_heading(self, block: Block) -> bool:
        text = (block.text or "").strip()
        if block.metadata.get("is_heading_candidate") or block.metadata.get("potential_heading"):
            return True
        if len(text) <= 80 and (text.isupper() or text.istitle()):
            return True
        return bool(text.endswith(":"))

    def _resolve_heading_type(self, block: Block) -> tuple[BlockType, str]:
        level = block.metadata.get("level") or block.metadata.get("heading_level") or block.level
        if level == 2:
            return BlockType.HEADING_2, "HEADING_2"
        if level == 3:
            return BlockType.HEADING_3, "HEADING_3"
        if level == 4:
            return BlockType.HEADING_4, "HEADING_4"
        return BlockType.HEADING_1, "HEADING_1"

    def _map_llm_label(self, label: str, block: Block) -> tuple[BlockType, str]:
        normalized = (label or "").strip().upper()
        text = (block.text or "").strip()

        if normalized == "TITLE":
            return BlockType.TITLE, "TITLE"
        if normalized == "AUTHOR_INFO":
            if self._is_likely_affiliation(text):
                return BlockType.AFFILIATION, "AFFILIATION"
            return BlockType.AUTHOR, "AUTHOR"
        if normalized == "ABSTRACT":
            if self._looks_like_heading(block) or text.lower() == "abstract":
                return BlockType.ABSTRACT_HEADING, "ABSTRACT_HEADING"
            return BlockType.ABSTRACT_BODY, "ABSTRACT_BODY"
        if normalized == "REFERENCES":
            if self._looks_like_heading(block) or len(text) < 50:
                return BlockType.REFERENCES_HEADING, "REFERENCES_HEADING"
            return BlockType.REFERENCE_ENTRY, "REFERENCE_ENTRY"
        if normalized == "FIGURE_CAPTION":
            return BlockType.FIGURE_CAPTION, "FIGURE_CAPTION"
        if normalized == "TABLE_CAPTION":
            return BlockType.TABLE_CAPTION, "TABLE_CAPTION"
        if normalized == "ACKNOWLEDGEMENTS":
            return BlockType.ACKNOWLEDGEMENTS, "ACKNOWLEDGEMENTS"
        if normalized == "EQUATION":
            return BlockType.EQUATION, "EQUATION"
        if normalized in {"METHODOLOGY", "CONCLUSION"}:
            if self._looks_like_heading(block):
                block_type, _ = self._resolve_heading_type(block)
                return block_type, normalized
            return BlockType.BODY, normalized
        if normalized == "HEADING":
            return self._resolve_heading_type(block)
        if normalized == "BODY":
            return BlockType.BODY, "BODY"

        # Default fallback
        return BlockType.BODY, "BODY"

    def _predict_llm_batch(self, blocks: list[Block]) -> list[dict[str, Any]] | None:
        if not should_enable_llm_classification():
            return None
        if not blocks:
            return []

        texts = [b.text or "" for b in blocks]
        try:
            classifier = get_llm_classifier()
            return classifier.classify_batch(texts)
        except Exception as exc:
            logger.warning("LLM batch inference failed (%s). Falling back to rule-based classification.", exc)
            return None

    def _apply_llm_predictions(
        self,
        blocks: list[Block],
        predictions: list[dict[str, Any]] | None,
    ) -> None:
        if not predictions:
            return

        # Persist raw predictions for observability.
        for i, block in enumerate(blocks):
            if i >= len(predictions):
                break
            pred = predictions[i] or {}
            label = pred.get("type")
            if label:
                block.metadata["llm_prediction"] = label
                block.metadata["llm_confidence"] = pred.get("confidence")

        overrides = 0
        for i, block in enumerate(blocks):
            if i >= len(predictions):
                break
            pred = predictions[i] or {}
            label = pred.get("type")
            if not label:
                continue
            try:
                confidence = float(pred.get("confidence") or 0.0)
            except (TypeError, ValueError):
                confidence = 0.0

            if confidence < self.llm_min_confidence:
                continue

            # Skip protected structural blocks
            if (
                block.metadata.get("is_header")
                or block.metadata.get("is_footer")
                or block.metadata.get("is_footnote")
                or block.metadata.get("is_endnote")
            ):
                continue

            # Only override low-specificity assignments.
            if block.block_type not in {BlockType.BODY, BlockType.UNKNOWN, BlockType.PARAGRAPH}:
                continue

            mapped_type, semantic_intent = self._map_llm_label(label, block)
            if mapped_type == BlockType.BODY and block.block_type == BlockType.BODY:
                continue

            block.block_type = mapped_type
            block.semantic_intent = semantic_intent
            block.classification_confidence = confidence
            block.metadata["semantic_intent"] = semantic_intent
            block.metadata["classification_confidence"] = confidence
            block.metadata["classification_method"] = "llm_classifier"
            overrides += 1

        if overrides:
            logger.info("LLM batch refinement applied to %d blocks.", overrides)

    def process(self, document: Document) -> Document:
        """
        Classify all blocks in the document.

        Args:
            document: Document with structure detection results

        Returns:
            Document with updated BlockTypes
        """
        start_time = datetime.now(UTC)
        try:
            return self._run_classification(document, start_time)
        except Exception as exc:
            logger.error("ContentClassifier.process failed: %s", exc, exc_info=True)
            document.add_processing_stage(
                stage_name="classification", status="error", message=f"Classification failed: {exc}"
            )
            return document

    def _run_classification(self, document: Document, start_time: datetime) -> Document:
        """Internal classification logic — called by process()."""
        blocks = document.blocks
        if not blocks:
            return document

        llm_predictions = self._predict_llm_batch(blocks)

        # 1. Identify key structural landmarks
        first_section_index = self._find_first_section_index(blocks)
        references_start_index = self._find_references_start_index(blocks)

        # State for classification logic
        title_found = False
        current_section_type = "generic"  # generic, abstract, keywords

        # 2. Main Classification Loop
        for i, block in enumerate(blocks):
            try:
                # A) HARD ISOLATION GUARD: Skip protected structural blocks
                # These must never receive semantic BlockType assignments
                if (
                    block.metadata.get("is_header")
                    or block.metadata.get("is_footer")
                    or block.metadata.get("is_footnote")
                    or block.metadata.get("is_endnote")
                ):
                    continue

                # B) PROTECTED TYPE GUARD: Title fixed per structure detector
                # TITLE is authoritative from Stage 1/Structure Detection
                if block.block_type == BlockType.TITLE:
                    block.semantic_intent = "TITLE"
                    block.classification_confidence = 1.0
                    block.metadata["classification_method"] = "structure_title_preserved"
                    if i < first_section_index:
                        title_found = True
                    continue

                text = block.text.strip() if block.text else ""
                if not text:
                    continue

                lower_text = text.lower()

                # 3️⃣ FIGURE CAPTION RULE
                if lower_text.startswith("figure ") or lower_text.startswith("fig. "):
                    block.block_type = BlockType.FIGURE_CAPTION
                    block.semantic_intent = "FIGURE_CAPTION"
                    block.classification_confidence = 1.0
                    block.metadata["semantic_intent"] = "FIGURE_CAPTION"
                    block.metadata["classification_confidence"] = 1.0
                    block.metadata["classification_method"] = "deterministic_figure_caption_rule"
                    continue

                # 4️⃣ TABLE CAPTION RULE
                if lower_text.startswith("table ") or lower_text.startswith("tab. "):
                    block.block_type = BlockType.TABLE_CAPTION
                    block.semantic_intent = "TABLE_CAPTION"
                    block.classification_confidence = 1.0
                    block.metadata["semantic_intent"] = "TABLE_CAPTION"
                    block.metadata["classification_confidence"] = 1.0
                    block.metadata["classification_method"] = "deterministic_table_caption_rule"
                    continue

                # --- ZONE 1: Front Matter ---
                if i < first_section_index:
                    # 🆕 GROBID INTEGRATION: Check for GROBID metadata first
                    # Access via ai_hints dict on DocumentMetadata model
                    grobid_data = (document.metadata.ai_hints or {}).get("grobid_metadata", {})

                    if not title_found:
                        # Prioritize GROBID title if available
                        if grobid_data and grobid_data.get("title") and text in grobid_data.get("title", ""):
                            block.block_type = BlockType.TITLE
                            block.semantic_intent = "TITLE"
                            block.classification_confidence = grobid_data.get("confidence", 0.9)
                            block.metadata["semantic_intent"] = "TITLE"
                            block.metadata["classification_confidence"] = grobid_data.get("confidence", 0.9)
                            block.metadata["classification_method"] = "grobid_title"
                            title_found = True
                            logger.debug(f"GROBID title detected: {text[:50]}")
                        else:
                            # Fallback to position-based
                            block.block_type = BlockType.TITLE
                            block.semantic_intent = "TITLE"
                            block.classification_confidence = 1.0
                            block.metadata["semantic_intent"] = "TITLE"
                            block.metadata["classification_confidence"] = 1.0
                            block.metadata["classification_method"] = "position_front_first"
                            title_found = True
                    else:
                        # 🆕 GROBID AUTHOR/AFFILIATION DETECTION
                        # Check if this block matches GROBID-extracted authors
                        if grobid_data and grobid_data.get("authors"):
                            is_grobid_author = self._match_grobid_author(text, grobid_data["authors"])
                            is_grobid_affiliation = self._match_grobid_affiliation(
                                text, grobid_data.get("affiliations", [])
                            )

                            if is_grobid_author:
                                block.block_type = BlockType.AUTHOR
                                block.semantic_intent = "AUTHOR"
                                block.classification_confidence = grobid_data.get("confidence", 0.9)
                                block.metadata["semantic_intent"] = "AUTHOR"
                                block.metadata["classification_confidence"] = grobid_data.get("confidence", 0.9)
                                block.metadata["classification_method"] = "grobid_author"
                                logger.debug(f"GROBID author detected: {text[:50]}")
                                continue

                            if is_grobid_affiliation:
                                block.block_type = BlockType.AFFILIATION
                                block.semantic_intent = "AFFILIATION"
                                block.classification_confidence = grobid_data.get("confidence", 0.9)
                                block.metadata["semantic_intent"] = "AFFILIATION"
                                block.metadata["classification_confidence"] = grobid_data.get("confidence", 0.9)
                                block.metadata["classification_method"] = "grobid_affiliation"
                                logger.debug(f"GROBID affiliation detected: {text[:50]}")
                                continue

                        # Fallback to existing regex rules if GROBID didn't match
                        # 1️⃣ AUTHOR RULE (ENHANCED - No Hard Comma Requirement)
                        # Detect based on capitalized words, with comma as confidence bonus
                        cap_words = re.findall(r"\b[A-Z][A-Za-z]*\b", text)
                        has_academic = any(kw in lower_text for kw in self.author_exclusion_keywords)

                        # Base confidence from capitalized word count
                        if 2 <= len(cap_words) <= 6 and not has_academic:
                            confidence = 0.6  # Base confidence

                            # SOFT BONUS: Comma presence increases confidence
                            if "," in text:
                                confidence += 0.1

                            block.block_type = BlockType.AUTHOR
                            block.semantic_intent = "AUTHOR"
                            block.classification_confidence = confidence
                            block.metadata["semantic_intent"] = "AUTHOR"
                            block.metadata["classification_confidence"] = confidence
                            block.metadata["classification_method"] = "regex_author_rule_enhanced"
                            continue

                        # 2️⃣ AFFILIATION RULE (LEGACY)
                        # contain keywords: University, Department, Institute, College, Laboratory
                        affiliation_keywords = ["University", "Department", "Institute", "College", "Laboratory"]
                        if any(kw in text for kw in affiliation_keywords):
                            block.block_type = BlockType.AFFILIATION
                            block.semantic_intent = "AFFILIATION"
                            block.classification_confidence = 0.7  # Lower confidence for regex
                            block.metadata["semantic_intent"] = "AFFILIATION"
                            block.metadata["classification_confidence"] = 0.7
                            block.metadata["classification_method"] = "regex_affiliation_rule"
                            continue

                        # 3️⃣ EMAIL/CORRESPONDENCE RULE (Strong Indicator)
                        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
                        if re.search(email_pattern, text):
                            # If it looks like an affiliation too, prioritize affiliation
                            if self._is_likely_affiliation(text):
                                block.block_type = BlockType.AFFILIATION
                                block.semantic_intent = "AFFILIATION"
                                block.classification_confidence = 0.9  # High confidence due to email
                                block.metadata["classification_method"] = "regex_email_affiliation"
                            else:
                                block.block_type = BlockType.AUTHOR
                                block.semantic_intent = "AUTHOR"
                                block.classification_confidence = 0.9  # High confidence due to email
                                block.metadata["classification_method"] = "regex_email_author"
                            continue

                        # Fallback for Front Matter (keep existing heuristic if no deterministic rule matches)
                        is_affiliation = self._is_likely_affiliation(text)
                        if is_affiliation:
                            block.block_type = BlockType.AFFILIATION
                            block.semantic_intent = "AFFILIATION"
                            block.metadata["semantic_intent"] = "AFFILIATION"
                            block.classification_confidence = 0.75  # Boosted slightly for zone 1
                        else:
                            block.block_type = BlockType.AUTHOR
                            block.semantic_intent = "AUTHOR"
                            block.metadata["semantic_intent"] = "AUTHOR"

                            # Boost confidence if it looks like a clean name (2-3 words, capitalized)
                            words = text.split()
                            if 1 <= len(words) <= 4 and text.istitle():
                                block.classification_confidence = 0.75
                                block.metadata["classification_method"] = "heuristic_front_name_likely"
                            else:
                                block.classification_confidence = settings.HEURISTIC_CONFIDENCE_MEDIUM

                        block.metadata["classification_confidence"] = block.classification_confidence
                        block.metadata["classification_method"] = block.metadata.get(
                            "classification_method", "heuristic_front"
                        )

                # --- ZONE 3: References ---
                elif references_start_index is not None and i >= references_start_index:
                    if i == references_start_index:
                        block.block_type = BlockType.REFERENCES_HEADING
                        block.semantic_intent = "REFERENCES_HEADING"
                        block.classification_confidence = 1.0
                        block.metadata["semantic_intent"] = "REFERENCES_HEADING"
                        block.metadata["classification_confidence"] = 1.0
                        block.metadata["classification_method"] = "structure_ref_heading"
                    else:
                        if block.metadata.get("is_heading_candidate") and block.level == 1:
                            block.block_type = BlockType.HEADING_1
                            block.semantic_intent = "HEADING_1"
                            block.classification_confidence = 1.0
                            block.metadata["semantic_intent"] = "HEADING_1"
                            block.metadata["classification_confidence"] = 1.0
                            continue

                        block.block_type = BlockType.REFERENCE_ENTRY
                        block.semantic_intent = "REFERENCE_ENTRY"
                        block.classification_confidence = settings.HEURISTIC_CONFIDENCE_HIGH
                        block.metadata["semantic_intent"] = "REFERENCE_ENTRY"
                        block.metadata["classification_confidence"] = settings.HEURISTIC_CONFIDENCE_HIGH
                        block.metadata["classification_method"] = "structure_ref_entry"

                # --- ZONE 2: Body ---
                else:
                    if block.metadata.get("is_heading_candidate"):
                        level = block.metadata.get("level", 1)
                        section_name = (block.section_name or "").lower()

                        if any(k in section_name for k in self.abstract_keywords):
                            block.block_type = BlockType.ABSTRACT_HEADING
                            block.semantic_intent = "ABSTRACT_HEADING"
                            block.metadata["semantic_intent"] = "ABSTRACT_HEADING"
                            current_section_type = "abstract"
                        elif any(k in section_name for k in self.keywords_keywords):
                            block.block_type = BlockType.KEYWORDS_HEADING
                            block.semantic_intent = "KEYWORDS_HEADING"
                            block.metadata["semantic_intent"] = "KEYWORDS_HEADING"
                            current_section_type = "keywords"
                        elif any(k in section_name for k in self.acknowledgements_keywords):
                            # Specialized classification for supplemental sections
                            text_lower = block.text.lower()
                            if "funding" in text_lower or "grant" in text_lower:
                                block.block_type = BlockType.FUNDING
                                block.semantic_intent = "FUNDING"
                                current_section_type = "funding"
                            elif "conflict" in text_lower or "interest" in text_lower:
                                block.block_type = BlockType.CONFLICT_OF_INTEREST
                                block.semantic_intent = "CONFLICT_OF_INTEREST"
                                current_section_type = "conflict"
                            else:
                                block.block_type = BlockType.ACKNOWLEDGEMENTS
                                block.semantic_intent = "ACKNOWLEDGEMENTS"
                                current_section_type = "acknowledgements"
                        # FEAT 49: Appendix detection
                        elif any(k in section_name for k in self.appendix_keywords):
                            block.block_type = BlockType.HEADING_1
                            block.semantic_intent = "APPENDIX_HEADING"
                            block.metadata["semantic_intent"] = "APPENDIX_HEADING"
                            block.metadata["is_appendix"] = True
                            current_section_type = "appendix"
                        else:
                            if level == 1:
                                block.block_type = BlockType.HEADING_1
                                block.semantic_intent = "HEADING_1"
                                block.metadata["semantic_intent"] = "HEADING_1"
                            elif level == 2:
                                block.block_type = BlockType.HEADING_2
                                block.semantic_intent = "HEADING_2"
                                block.metadata["semantic_intent"] = "HEADING_2"
                            elif level == 3:
                                block.block_type = BlockType.HEADING_3
                                block.semantic_intent = "HEADING_3"
                                block.metadata["semantic_intent"] = "HEADING_3"
                            else:
                                block.block_type = BlockType.HEADING_4
                                block.semantic_intent = "HEADING_4"
                                block.metadata["semantic_intent"] = "HEADING_4"
                            current_section_type = "generic"

                        block.classification_confidence = 1.0
                        block.metadata["classification_confidence"] = 1.0
                        block.metadata["classification_method"] = "structure_heading"
                    else:
                        # PROACTIVE FIX: Propagate Footnote status from Parser
                        if block.metadata.get("is_footnote"):
                            block.block_type = BlockType.FOOTNOTE
                            block.semantic_intent = "FOOTNOTE"
                            block.metadata["semantic_intent"] = "FOOTNOTE"
                            continue

                        if current_section_type == "abstract":
                            block.block_type = BlockType.ABSTRACT_BODY
                            block.semantic_intent = "ABSTRACT_BODY"
                            block.metadata["semantic_intent"] = "ABSTRACT_BODY"
                        elif current_section_type == "keywords":
                            block.block_type = BlockType.KEYWORDS_BODY
                            block.semantic_intent = "KEYWORDS_BODY"
                            block.metadata["semantic_intent"] = "KEYWORDS_BODY"
                        else:
                            block.block_type = BlockType.BODY
                            block.semantic_intent = "BODY"
                            block.metadata["semantic_intent"] = "BODY"
                        block.classification_confidence = settings.HEURISTIC_CONFIDENCE_HIGH
                        block.metadata["classification_confidence"] = settings.HEURISTIC_CONFIDENCE_HIGH
                        block.metadata["classification_method"] = "structure_context"

            except Exception as exc:
                logger.warning("ContentClassifier: failed to classify block %d: %s", i, exc)

        # 2.5 Optional LLM refinement (batch predictions)
        self._apply_llm_predictions(blocks, llm_predictions)

        # 3. NLP Fallback for UNKNOWNs
        self._nlp_classify_fallback(blocks)

        # 4. Enhanced NLP Fallback (Integrate Regex & SemanticParser Confidence)
        # ARCHITECTURAL INTEGRATION: Use NLP confidence to improve scoring
        # while preserving deterministic structural classification.
        for block in blocks:
            # Skip protected structural blocks
            if (
                block.metadata.get("is_header")
                or block.metadata.get("is_footer")
                or block.metadata.get("is_footnote")
                or block.metadata.get("is_endnote")
            ):
                continue

            # 4.1 Strong Regex Heuristics for Common Headings (Fix for DOCX "Low Confidence")
            text = block.text.strip()
            if not text:
                continue

            # Detect standard academic headings if not already classified as heading
            if block.block_type in [BlockType.UNKNOWN, BlockType.BODY]:
                # Numbered headings: "1. Introduction", "2. Methods"
                if re.match(r"^\d+\.\s+[A-Z][a-zA-Z\s]+$", text) and len(text) < 60:
                    block.block_type = BlockType.HEADING_1
                    block.semantic_intent = "HEADING_1"
                    block.classification_confidence = 0.85
                    block.metadata["classification_method"] = "regex_numbered_heading"
                    continue

                # Unnumbered standard headings
                std_headings = [
                    "introduction",
                    "background",
                    "methods",
                    "methodology",
                    "results",
                    "discussion",
                    "conclusion",
                    "conclusions",
                    "references",
                ]
                if text.lower() in std_headings or text.lower().replace(":", "") in std_headings:
                    block.block_type = BlockType.HEADING_1
                    block.semantic_intent = "HEADING_1"
                    block.classification_confidence = 0.9
                    block.metadata["classification_method"] = "regex_std_heading"
                    continue

            if block.block_type == BlockType.UNKNOWN:
                # Structural fallback (deterministic, unchanged)
                block.block_type = BlockType.BODY
                block.semantic_intent = "BODY"

                # CONFIDENCE INTEGRATION: Use NLP confidence if available
                # This does NOT change block_type, only improves confidence scoring
                nlp_confidence = block.metadata.get("nlp_confidence", 0.0)

                if nlp_confidence > 0:
                    # Use NLP confidence (with minimum floor of 0.5)
                    confidence = max(nlp_confidence, 0.5)
                    block.classification_confidence = confidence
                    block.metadata["classification_confidence"] = confidence
                    block.metadata["classification_method"] = "fallback_with_nlp"
                else:
                    # No NLP data available, use baseline fallback
                    block.classification_confidence = settings.HEURISTIC_CONFIDENCE_LOW
                    block.metadata["classification_confidence"] = settings.HEURISTIC_CONFIDENCE_LOW
                    block.metadata["classification_method"] = "fallback_last_resort"

        # Update processing history
        end_time = datetime.now(UTC)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        document.add_processing_stage(
            stage_name="classification",
            status="success",
            message=f"Classified {len(blocks)} blocks",
            duration_ms=duration_ms,
        )

        document.updated_at = datetime.now(UTC)
        return document

    def _find_first_section_index(self, blocks: list[Block]) -> int:
        """
        Find the index of the first heading block with safety limits.

        If no headings exist, we limit the front-matter zone to a small prefix
        or until we hit a clear body paragraph (>300 chars).
        """
        fallback_heading_keywords = {
            "abstract",
            "introduction",
            "background",
            "related work",
            "literature review",
            "methods",
            "methodology",
            "materials and methods",
            "results",
            "discussion",
            "conclusion",
            "conclusions",
            "references",
            "bibliography",
        }

        for i, block in enumerate(blocks):
            # Guard: Limit front matter search to reasonable document start
            # or until we hit something that is definitely body text.
            if i >= 30:
                break
            text = (block.text or "").strip()
            if len(text) > 300:
                break

            if block.metadata.get("is_heading_candidate"):
                # Fix: Title is not a section start, so don't let it close the front matter zone
                if block.block_type == BlockType.TITLE:
                    continue
                return i

            # Fallback heading detection: protects early major headings even when
            # structure detector is uncertain.
            cleaned = re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", text).strip().lower().rstrip(":")
            if 1 <= len(cleaned.split()) <= 12 and len(cleaned) <= 90:
                if re.match(r"^\d+(?:\.\d+)*\.?\s+[A-Z]", text):
                    return i
                if cleaned in fallback_heading_keywords:
                    return i

        # If no heading found within safety limits, return the end of
        # the potential metadata zone (not the end of the document).
        return min(12, len(blocks))

    def _find_references_start_index(self, blocks: list[Block]) -> int | None:
        """Find the index of the References heading."""
        for i, block in enumerate(blocks):
            if not block.metadata.get("is_heading_candidate"):
                continue

            # Check section name or text
            section = (block.section_name or "").lower()
            text = block.text.strip().lower()

            # Simple check
            if any(k in section for k in self.references_keywords) or any(k in text for k in self.references_keywords):
                # Verify it's not a generic sentence like "See references for more info"
                # Headings usually short.
                if len(text) < 50:
                    return i
        return None

    def _is_likely_affiliation(self, text: str) -> bool:
        """Heuristic check for affiliation content."""
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in self.affiliation_indicators)

    def _match_grobid_author(self, text: str, grobid_authors: list[dict]) -> bool:
        """
        Check if block text matches any GROBID-extracted author.

        Args:
            text: Block text to check
            grobid_authors: List of author dicts from GROBID

        Returns:
            True if text matches an author name
        """
        text_lower = text.lower()

        for author in grobid_authors:
            full_name = author.get("full_name", "").lower()
            given = author.get("given", "").lower()
            family = author.get("family", "").lower()

            # Check if author name appears in text
            if full_name and full_name in text_lower:
                return True
            if given and family and f"{given} {family}" in text_lower:
                return True
            if family and family in text_lower:
                # Check if it's not just a random word match
                if len(family) > 3:  # Avoid matching short names
                    return True

        return False

    def _match_grobid_affiliation(self, text: str, grobid_affiliations: list[str]) -> bool:
        """
        Check if block text matches any GROBID-extracted affiliation.

        Args:
            text: Block text to check
            grobid_affiliations: List of affiliation strings from GROBID

        Returns:
            True if text matches an affiliation
        """
        text_lower = text.lower()

        for affiliation in grobid_affiliations:
            if affiliation and affiliation.lower() in text_lower:
                return True
            # Also check partial matches for long affiliations
            if affiliation and len(affiliation) > 20:
                # Check if at least 70% of affiliation text appears
                affiliation_words = set(affiliation.lower().split())
                text_words = set(text_lower.split())
                overlap = len(affiliation_words & text_words)
                if affiliation_words and overlap / len(affiliation_words) > 0.7:
                    return True

        return False

    def _nlp_classify_fallback(self, blocks: list[Block]):
        """
        Simulate a lightweight BERT/fastText fallback for UNKNOWN blocks.
        Only applies if confidence is high (simulated).
        """
        for block in blocks:
            # Skip protected structural blocks from NLP fallback
            if (
                block.metadata.get("is_header")
                or block.metadata.get("is_footer")
                or block.metadata.get("is_footnote")
                or block.metadata.get("is_endnote")
            ):
                continue

            if block.block_type == BlockType.UNKNOWN:
                text = block.text.strip()
                if not text:
                    continue

                # FEAT 49: Footnote pattern detection
                is_footnote = any(re.match(pat, text) for pat in self.footnote_patterns)
                if is_footnote:
                    block.block_type = BlockType.FOOTNOTE
                    block.semantic_intent = "FOOTNOTE"
                    block.metadata["classification_method"] = "regex_footnote_pattern"
                    block.metadata["confidence"] = 0.85
                    continue

                # NLP Simulation: Check for Equation-like content
                if re.search(r"[=+\-]{2,}|\\sum|\\alpha", text):
                    # FORENSIC FIX: Enable BlockType.EQUATION support
                    block.block_type = BlockType.EQUATION
                    block.semantic_intent = "EQUATION"
                    block.metadata["classification_method"] = "nlp_bert_high_confidence"
                    block.metadata["confidence"] = 0.92

                # NLP Simulation: Check for Table-like tab structures
                elif text.count("\t") > 2 or text.count("|") > 2:
                    block.block_type = BlockType.BODY
                    block.metadata["classification_method"] = "nlp_bert_high_confidence"
                    block.metadata["confidence"] = 0.88


# Convenience function
def classify_content(document: Document) -> Document:
    """
    Classify content in a structured document.

    Args:
        document: Document to classify

    Returns:
        Document with classified blocks
    """
    classifier = ContentClassifier()
    return classifier.process(document)
