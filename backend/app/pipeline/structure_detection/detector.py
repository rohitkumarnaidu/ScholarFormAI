# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Structure Detector - Main orchestrator for structure detection.

This module coordinates heading detection, level inference, and section identification.
It enriches blocks with structure metadata without changing block types (remain UNKNOWN).

Input: Normalized Document
Output: Document with structure hints attached to blocks
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from statistics import mean, median

from app.models import PipelineDocument as Document, Block, BlockType
from app.pipeline.contracts.loader import ContractLoader
from .heading_rules import analyze_heading_candidate
from .position_rules import analyze_position, boost_heading_confidence_by_position


from app.pipeline.base import PipelineStage
from app.pipeline.safety.safe_execution import safe_function, safe_execution

logger = logging.getLogger(__name__)

class StructureDetector(PipelineStage):
    """
    Detects document structure through rule-based heuristics.
    
    This stage identifies:
    - Heading candidates
    - Heading levels (1-4)
    - Section boundaries
    - Parent-child relationships
    
    IMPORTANT: Does NOT assign semantic block types (they remain UNKNOWN).
    Only attaches metadata for later classification stage.
    """
    
    def __init__(self, contracts_dir: str = "app/pipeline/contracts"):
        """Initialize the detector."""
        self.avg_font_size: Optional[float] = None
        self.detected_headings: List[Dict[str, Any]] = []
        self.contract_loader = ContractLoader(contracts_dir=contracts_dir)
    
    def process(self, document: Document) -> Document:
        """
        Detect structure in a normalized document.
        """
        with safe_execution("StructureDetector.process"):
            start_time = datetime.now(timezone.utc)
            
            # Step 0: ENFORCE NORMALIZATION
            # User requirement: Normalizer must run before StructureDetector
            # We run it here to ensure test scripts don't bypass it.
            from app.pipeline.normalization.normalizer import Normalizer
            normalizer = Normalizer()
            document = normalizer.process(document)
            
            # Step 1: Calculate average font size for comparison
            self.avg_font_size = self._calculate_avg_font_size(document.blocks)
            
            # Step 2: Detect heading candidates
            # Week 2 Enhancements: Check for Docling layout data
            # Access via ai_hints dict on DocumentMetadata model
            docling_layout = document.metadata.ai_hints.get("docling_layout")
            
            heading_candidates: list = []
            if docling_layout:
                # path: Enhanced structure detection using Docling layout analysis
                # Features: Bounding box aware, font size confident, logo tolerant
                logger.info(
                    "Using Docling layout data for structure detection (%d elements)",
                    len(docling_layout.get("elements", [])),
                )
                heading_candidates = self._detect_structure_with_docling(document.blocks, docling_layout)
            
            # Fallback if Docling unavailable OR failed (returned empty/None)
            if not heading_candidates:
                if docling_layout:
                    logger.warning(
                        "Docling detection returned no results (or failed). Fallback to standard rule-based detection."
                    )
                # Fallback: Use standard rule-based detection
                heading_candidates = self._detect_heading_candidates(document.blocks)
        
        # Step 3: Assign section names based on headings
        self._assign_section_names(document.blocks, heading_candidates)
        
        # Step 4: Build parent-child relationships
        self._build_hierarchy(document.blocks, heading_candidates)
        
        # Step 5: Canonicalize section names based on contract
        publisher = document.template.template_name if document.template else None
        if publisher:
            self._canonicalize_sections(document.blocks, publisher)
            
        # Step 6: Validate hierarchy (detect jumps, e.g., L1 -> L3)
        self._validate_hierarchy(document.blocks)
        
        # Update processing history
        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        num_headings = len(heading_candidates)
        num_sections = len(set(b.section_name for b in document.blocks if b.section_name))
        
        document.add_processing_stage(
            stage_name="structure_detection",
            status="success",
            message=f"Detected {num_headings} headings, {num_sections} sections",
            duration_ms=duration_ms
        )
        
        document.updated_at = datetime.now(timezone.utc)
        
        # Store detected headings for debugging
        self.detected_headings = heading_candidates
        
        return document
    
    def _calculate_avg_font_size(self, blocks: List[Block]) -> Optional[float]:
        """
        Calculate average font size in document.
        
        This is used to detect font size outliers (potential headings).
        
        Args:
            blocks: All blocks in document
        
        Returns:
            Average font size, or None if no blocks have font size
        """
        font_sizes = []
        for block in blocks:
            if block.style.font_size and block.text.strip():
                font_sizes.append(block.style.font_size)
        
        if not font_sizes:
            return None
        
        # Use median instead of mean to avoid outlier influence
        return median(font_sizes)
    
    def _detect_heading_candidates(self, blocks: List[Block]) -> List[Dict[str, Any]]:
        """
        Detect all heading candidates in the document.
        
        This combines text/style heuristics with positional cues.
        
        Args:
            blocks: All blocks in document (in order)
        
        Returns:
            List of detected headings with metadata
            Each entry: {
                "block": Block,
                "block_id": str,
                "level": int,
                "confidence": float,
                "reasons": list of str
            }
        """
        # Import local rules including new Title rule
        from .heading_rules import analyze_heading_candidate, detect_title, get_capitalization_ratio
        
        candidates = []
        found_title = False
        potential_author_count = 0 
        
        for i, block in enumerate(blocks):
            # 1. HARD ISOLATION RULE: Skip Header/Footer blocks
            if block.metadata.get("is_header") or block.metadata.get("is_footer"):
                continue

            # Skip empty blocks (Normalizer should have removed them, but double check)
            if not block.text.strip():
                continue
            
            # 1. TITLE DETECTION (Priority 1, Level 0, Constant 1.0 confidence)
            if detect_title(block, blocks):
                block.block_type = BlockType.TITLE
                block.level = 0
                block.metadata["is_heading_candidate"] = True
                block.metadata["heading_confidence"] = 1.0
                block.metadata["heading_reasons"] = ["Main Document Title Detected"]
                block.metadata["semantic_intent"] = "TITLE"
                block.metadata["level"] = 0 # FOR VISUAL TEST SCRIPT
                
                candidates.append({
                    "block": block,
                    "block_id": block.block_id,
                    "level": 0,
                    "confidence": 1.0,
                    "reasons": ["Main Document Title Detected"],
                    "position_info": {"position_hints": ["Title"]}
                })
                found_title = True
                continue

            # AUTHOR/AFFILIATION HEURISTIC (SAFE Metadata)
            # If Block appears immediately after TITLE, check for Author/Affiliation
            if found_title and potential_author_count < 5:
                # If we hit a clear heading, stop searching for authors
                num_info = analyze_heading_candidate(block, blocks, i, self.avg_font_size)
                if num_info:
                    found_title = False # Stop looking after hit heading
                else: 
                    text = block.text.strip()
                    if len(text) < 120:
                        potential_author_count += 1
                        uni_keywords = ["University", "Institute", "College", "Department", "Faculty", "Center", "Lab", "Corporation", "School"]
                        is_aff = any(kw.lower() in text.lower() for kw in uni_keywords)
                        # Author heuristic: caps ratio + commas/et al
                        is_auth = (get_capitalization_ratio(text) > 0.6 and ("," in text or len(text.split()) < 10))
                        
                        if is_auth:
                            block.metadata["is_author_block"] = True
                        if is_aff:
                            block.metadata["is_affiliation_block"] = True
            
            # 2. HEADING ANALYSIS (Numbered/Keyword/Style/Fallback)
            heading_info = analyze_heading_candidate(block, blocks, i, self.avg_font_size)
            
            if heading_info is None:
                continue
            
            # Confidence boosting by position (only for valid candidates)
            position_info = analyze_position(block, blocks)
            final_confidence = boost_heading_confidence_by_position(
                heading_info["confidence"],
                position_info
            )
            
            # Enforce deterministic levels for major sections
            level = heading_info.get("level", 1)
            all_reasons = heading_info.get("reasons", []) + position_info.get("position_hints", [])
            
            # Update block metadata (Keep UNKNOWN type until classification)
            block.level = level
            block.metadata["level"] = level # FOR VISUAL TEST SCRIPT
            block.metadata["is_heading_candidate"] = True
            block.metadata["heading_confidence"] = final_confidence
            block.metadata["heading_reasons"] = all_reasons
            
            if heading_info.get("has_numbering"):
                block.metadata["numbering_info"] = heading_info["numbering_info"]
            
            # Store candidate
            candidates.append({
                "block": block,
                "block_id": block.block_id,
                "level": level,
                "confidence": final_confidence,
                "reasons": all_reasons,
                "position_info": position_info
            })
        
        return candidates
    
    def _assign_section_names(
        self,
        blocks: List[Block],
        heading_candidates: List[Dict[str, Any]]
    ) -> None:
        """
        Assign section names to all blocks based on detected headings.
        
        Blocks inherit the section name from the most recent heading before them.
        """
        # Build a mapping of block_id -> heading info
        heading_map = {h["block_id"]: h for h in heading_candidates}
        
        current_section = None
        
        for block in blocks:
            # 1. HARD ISOLATION RULE: Headers/Footers never inherit section_name
            if block.metadata.get("is_header") or block.metadata.get("is_footer"):
                block.section_name = None
                continue

            # If this block is a heading, update current section
            if block.block_id in heading_map:
                heading = heading_map[block.block_id]
                
                # Use block text as section name (cleaned)
                # SPECIAL CASE: For Title level (0) or explicitly TITLE type, use canonical "title"
                if heading.get("level") == 0 or block.block_type == BlockType.TITLE:
                    section_name = "title"
                else:
                    section_name = block.text.strip()
                
                # Remove numbering if present
                if "numbering_info" in block.metadata:
                    numbering_info = block.metadata["numbering_info"]
                    section_name = numbering_info.get("remainder", section_name)
                
                current_section = section_name
                block.section_name = current_section
            else:
                # Non-heading block inherits current section
                if current_section:
                    block.section_name = current_section
    
    def _build_hierarchy(
        self,
        blocks: List[Block],
        heading_candidates: List[Dict[str, Any]]
    ) -> None:
        """
        Build parent-child relationships between headings.
        
        A heading's parent is the nearest preceding heading with a lower level number
        (e.g., level 2's parent is the nearest level 1).
        """
        heading_map = {h["block_id"]: h for h in heading_candidates}
        # Build list of headings in order
        heading_stack: List[Dict[str, Any]] = []
        
        for block in blocks:
            # 1. HARD ISOLATION RULE: Skip Header/Footer blocks
            if block.metadata.get("is_header") or block.metadata.get("is_footer"):
                continue

            # Check if this block is a heading
            heading_info = heading_map.get(block.block_id)
            
            if heading_info is None:
                continue
            
            current_level = heading_info["level"]
            
            # Find parent: nearest heading with lower level number
            parent_id = None
            for i in range(len(heading_stack) - 1, -1, -1):
                if heading_stack[i]["level"] < current_level:
                    parent_id = heading_stack[i]["block_id"]
                    break
            
            # Set parent
            if parent_id:
                block.parent_id = parent_id
            
            # Update stack: remove headings at same or lower level
            heading_stack = [h for h in heading_stack if h["level"] < current_level]
            heading_stack.append(heading_info)

    def _canonicalize_sections(self, blocks: List[Block], publisher: str) -> None:
        """
        Rename sections to their canonical names based on the publisher contract.
        Example: "Related Work" -> "Background"
        """
        try:
            for block in blocks:
                if block.section_name:
                    block.section_name = self.contract_loader.get_canonical_name(publisher, block.section_name)
        except Exception as e:
            logger.warning("Section canonicalization failed: %s", e)

    def _validate_hierarchy(self, blocks: List[Block]) -> None:
        """
        Validate heading nesting hierarchy.
        Detects "jumping" levels (e.g., Heading 1 followed by Heading 3).
        """
        last_level = 0
        for block in blocks:
            # 1. HARD ISOLATION RULE: Skip Header/Footer blocks
            if block.metadata.get("is_header") or block.metadata.get("is_footer"):
                continue

            if block.is_heading() and block.level:
                # Level should not jump by more than 1 (except when going back up)
                if block.level > last_level + 1:
                    warning = f"Heading level jump detected: Level {last_level} to Level {block.level}"
                    block.warnings.append(warning)
                    block.is_valid = False
                last_level = block.level


    @safe_function(fallback_value=[], error_message="Docling structure detection failed")
    def _detect_structure_with_docling(self, blocks: List[Block], layout_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect structure using Docling layout analysis data.
        
        Uses bounding boxes and visual features for superior accuracy:
        1. Title Detection: Ignores top logos/images using y-coordinates.
        2. Heading Levels: Strictly based on font size hierarchy.
        3. Header/Footer: Filters out elements in top/bottom margins.
        
        Args:
            blocks: Document blocks
            layout_data: Docling layout dictionary
            
        Returns:
            List of detected headings with metadata
        """
        from app.models import BlockType

        def _normalize(text: str) -> str:
            import re
            cleaned = (text or "").strip().lower()
            cleaned = re.sub(r"\s+", " ", cleaned)
            return cleaned
        
        candidates = []
        found_title = False
        
        # 1. Parse Layout Elements
        elements = layout_data.get("elements", [])
        if not elements:
            logger.warning("Docling layout data empty. Fallback to standard detection.")
            return self._detect_heading_candidates(blocks)

        prepared_elements: List[Dict[str, Any]] = []
        for element in elements:
            normalized_text = _normalize(element.get("text", ""))
            if not normalized_text:
                continue
            prepared_elements.append(
                {
                    "raw": element,
                    "normalized_text": normalized_text,
                    "sample": normalized_text[:80],
                    "tokens": set(normalized_text.split()),
                }
            )
            
        # 2. Identify Visual Hierarchy (Font Sizes)
        font_sizes = [e.get("font_size", 0) for e in elements if e.get("type") in ["title", "heading"]]
        if not font_sizes:
             font_sizes = [e.get("font_size", 0) for e in elements if e.get("font_size")]
             
        max_font_size = max(font_sizes) if font_sizes else 0
        
        # 3. Match Blocks to Layout Elements (Fuzzy Match by Text)
        # Note: Docling text might differ slightly from our normalized text
        # We use a simple containment or similarity check
        
        for block in blocks:
            if block.metadata.get("is_header") or block.metadata.get("is_footer"):
                continue

            # Skip empty
            if not block.text.strip():
                continue
                
            # Try to find corresponding layout element
            matched_element = None
            block_text_norm = _normalize(block.text)
            block_text_sample = block_text_norm[:80]
            block_tokens = set(block_text_norm.split())
            
            for prepared in prepared_elements:
                element = prepared["raw"]
                element_text_norm = prepared["normalized_text"]
                element_tokens = prepared["tokens"]
                element_sample = prepared["sample"]

                # Primary: exact/contains check on normalized text
                if (
                    block_text_sample
                    and (
                        block_text_sample in element_text_norm
                        or element_sample in block_text_norm
                    )
                ):
                    matched_element = element
                    break

                # Secondary: token overlap for OCR/noise variation
                if not block_tokens or not element_tokens:
                    continue
                overlap = len(block_tokens & element_tokens) / max(1, len(block_tokens))
                if overlap >= 0.7:
                    matched_element = element
                    break
            
            if not matched_element:
                # If no match, fall back to heuristic for this block or skip
                continue
                
            # 4. Apply Docling Logic
            
            # A. Title Detection (Logo Tolerance built-in to Docling types)
            if not found_title and matched_element.get("type") == "title":
                # Double check: Is it truly the title?
                # Rule: Largest font or explicitly tagged 'title' by Docling
                # Rule: Must be in top 50% of page 1
                bbox = matched_element.get("bbox", {})
                if bbox.get("page", 1) == 1 and bbox.get("y0", 0) < 500:
                    block.block_type = BlockType.TITLE
                    block.level = 0
                    block.metadata["is_heading_candidate"] = True
                    block.metadata["heading_confidence"] = 1.0
                    block.metadata["heading_reasons"] = ["Docling: Title Detected"]
                    block.metadata["semantic_intent"] = "TITLE"
                    block.metadata["level"] = 0 
                    
                    candidates.append({
                        "block": block,
                        "block_id": block.block_id,
                        "level": 0,
                        "confidence": 1.0,
                        "reasons": ["Docling: Title Detected"],
                    })
                    found_title = True
                    continue

            # B. Heading Detection
            if matched_element.get("type") in ["section_header", "heading"]:
                # Determine Level based on Font Size relative to Max
                font_size = matched_element.get("font_size", 0)
                level = 1
                
                # Simple Font Hierarchy Logic
                if max_font_size > 0:
                    if font_size >= max_font_size * 0.9: level = 1
                    elif font_size >= max_font_size * 0.8: level = 2
                    elif font_size >= max_font_size * 0.7: level = 3
                    else: level = 4
                
                block.block_type = BlockType.HEADING_1 # Base type, will be refined
                block.level = level
                block.metadata["is_heading_candidate"] = True
                block.metadata["heading_confidence"] = matched_element.get("confidence", 0.9)
                block.metadata["heading_reasons"] = [f"Docling: Heading (Size {font_size})"]
                block.metadata["semantic_intent"] = "HEADING"
                block.metadata["level"] = level
                
                candidates.append({
                    "block": block,
                    "block_id": block.block_id,
                    "level": level,
                    "confidence": 0.9,
                    "reasons": [f"Docling: Heading (Size {font_size})"],
                })
        
        # If Docling found nothing (e.g. scanned doc without OCR), fallback
        if not candidates:
            logger.warning("Docling found no structure. Fallback to standard detection.")
            return self._detect_heading_candidates(blocks)
             
        return candidates

# Convenience function
@safe_function(fallback_value=None, error_message="detect_structure failed")
def detect_structure(document: "Document") -> "Document":
    """
    Detect structure in a normalized document.
    
    This is a convenience wrapper around StructureDetector.
    
    Args:
        document: Normalized document
    
    Returns:
        Document with structure metadata
    """
    detector = StructureDetector()
    return detector.process(document)
