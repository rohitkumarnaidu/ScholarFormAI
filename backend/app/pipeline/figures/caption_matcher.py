# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Caption Matcher - Links figures to their captions.

This module detects caption blocks (e.g., "Figure 1: ...") and associates
them with the nearest Figure object.
"""

import logging
import re
import os
from typing import List, Tuple, Dict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from app.pipeline.base import PipelineStage
from app.models import PipelineDocument as Document, Block, Figure


class CaptionMatcher(PipelineStage):
    """
    Links figures to their captions based on proximity and text patterns.

    Logic:
    1. Identify caption candidates using regex (BlockType is usually BODY).
    2. Identify figures (already extracted).
    3. Match each caption to the nearest figure, preferring the one immediately
       ABOVE the caption (standard academic style).
    4. Link them:
       - Figure gets `caption_text` and `caption_block_id`.
       - Block gets `BlockType.FIGURE_CAPTION` (if semantic update is allowed/safe).
    """

    def __init__(self, max_distance: int = 2, enable_vision: bool = False):
        """
        Initialize the matcher.

        Args:
            max_distance: Max number of blocks between figure and caption to consider a match.
            enable_vision: Whether to use NVIDIA Vision for caption enhancement.
        """
        self.max_distance = max_distance
        self.enable_vision = enable_vision

        # Regex for common caption patterns (case-insensitive)
        # Matches: "Figure 1.", "Fig. 2:", "Figure 3-a"
        self.caption_pattern = re.compile(r"^(?:Figure|Fig\.?)\s+\d+[a-zA-Z0-9\.]*", re.IGNORECASE)

        # Initialize vision client if enabled
        self.vision_client = None
        if self.enable_vision:
            try:
                from app.services.nvidia_client import get_nvidia_client

                self.vision_client = get_nvidia_client()
                if self.vision_client:
                    logger.info("Vision analysis enabled for figure captions.")
            except Exception as exc:
                logger.warning("Vision analysis unavailable: %s", exc)
                self.vision_client = None

    def process(self, document: Document) -> Document:
        """
        Match specific figures to captions in the document.
        """
        start_time = datetime.now(timezone.utc)

        try:
            blocks = document.blocks
            figures = document.figures

            if not figures:
                return document

            # 1. Detect Caption Candidates
            caption_candidates = self._find_caption_candidates(blocks)

            # 2. Match Figures to Captions
            matches = self._match_candidates(blocks, figures, caption_candidates)

            # 3. Apply Links
            match_count = 0
            vision_enhanced = 0

            for fig, cap_block in matches:
                # Update Figure
                fig.caption_text = cap_block.text.strip()
                fig.caption_block_id = cap_block.block_id

                # Update Block metadata
                cap_block.metadata["is_figure_caption"] = True
                cap_block.metadata["linked_figure_id"] = fig.figure_id
                match_count += 1

            # 4. Vision Analysis Enhancement
            if self.enable_vision and self.vision_client:
                vision_enhanced = self._enhance_captions_with_vision(figures)
        except Exception as exc:
            logger.error("Caption matching failed: %s", exc)
            document.add_processing_stage(
                stage_name="figure_linking", status="error", message=f"Caption matching failed: {exc}"
            )
            return document

        # Update processing history
        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        message = f"Linked {match_count} captions to figures"
        if vision_enhanced > 0:
            message += f", enhanced {vision_enhanced} with vision analysis"

        document.add_processing_stage(
            stage_name="figure_linking", status="success", message=message, duration_ms=duration_ms
        )

        document.updated_at = datetime.now(timezone.utc)

        return document

    def _enhance_captions_with_vision(self, figures: List[Figure]) -> int:
        """
        Use NVIDIA Llama 3.2 Vision to enhance figure captions.

        Args:
            figures: List of figures to analyze

        Returns:
            Number of figures enhanced
        """
        enhanced_count = 0

        for figure in figures:
            # Skip if no image path
            if not figure.export_path or not os.path.exists(figure.export_path):
                continue

            try:
                # Analyze figure with vision model
                vision_description = self.vision_client.analyze_figure(
                    image_path=figure.export_path, caption=figure.caption_text
                )

                if vision_description:
                    # Store vision analysis in metadata
                    figure.metadata["vision_analysis"] = vision_description

                    # If no caption exists, use vision analysis as caption
                    if not figure.caption_text or figure.caption_text.strip() == "":
                        figure.caption_text = f"Figure {figure.figure_id}: {vision_description}"
                        figure.metadata["caption_source"] = "vision_generated"
                        logger.info("Generated caption for Figure %s using vision.", figure.figure_id)
                    else:
                        # Caption exists, just store analysis for reference
                        figure.metadata["caption_source"] = "manual_with_vision"
                        logger.info("Enhanced Figure %s with vision analysis.", figure.figure_id)

                    enhanced_count += 1

            except Exception as exc:
                logger.warning("Vision analysis failed for Figure %s: %s", figure.figure_id, exc)
                continue

        return enhanced_count

    def _find_caption_candidates(self, blocks: List[Block]) -> List[int]:
        """
        Find parser indices of blocks that look like captions.
        """
        candidates = []
        for block in blocks:
            # Captions are usually BODY or UNKNOWN (if missed), but rarely HEADINGS.
            # We skip headings to reduce false positives (e.g. "Figure 1 Analysis" as a section title).
            if block.is_heading():
                continue

            text = block.text.strip()
            if self.caption_pattern.match(text):
                candidates.append(block.index)
        return candidates

    def _match_candidates(
        self, blocks: List[Block], figures: List[Figure], candidate_indices: List[int]
    ) -> List[Tuple[Figure, Block]]:
        """
        Match detected caption blocks to figures.
        """
        matches = []
        assigned_figures: Dict[str, bool] = {}  # Keep track of matched figures

        # Create block_map for O(1) lookup by parser index
        block_map: Dict[int, Block] = {block.index: block for block in blocks}

        # Create a list index map to calculate "Logical Distance" (number of blocks between)
        # This makes the matcher resilient to arbitrary index steps (e.g. 100)
        list_index_map: Dict[int, int] = {block.index: i for i, block in enumerate(blocks)}

        # Sort candidates to handle document flow
        candidate_indices.sort()

        for cap_idx in candidate_indices:
            caption_block = block_map.get(cap_idx)
            if not caption_block or cap_idx not in list_index_map:
                continue

            best_figure = None
            min_distance = float("inf")

            cap_list_idx = list_index_map[cap_idx]

            for figure in figures:
                if figure.figure_id in assigned_figures:
                    continue

                fig_block_idx = figure.metadata.get("block_index")
                if fig_block_idx is None or fig_block_idx not in list_index_map:
                    continue

                # Logical distance = caption_list_pos - figure_list_pos
                distance = cap_list_idx - list_index_map[fig_block_idx]

                # Check absolute distance against max_distance (threshold in blocks)
                if abs(distance) <= self.max_distance:
                    current_dist_abs = abs(distance)

                    if current_dist_abs < min_distance:
                        min_distance = current_dist_abs
                        best_figure = figure
                    elif current_dist_abs == min_distance:
                        # Tie-breaker: Prefer figure ABOVE the caption (distance > 0)
                        if distance > 0:
                            best_figure = figure

            if best_figure:
                matches.append((best_figure, caption_block))
                assigned_figures[best_figure.figure_id] = True

        return matches


# Convenience function
def link_figures(document: Document, enable_vision: bool = True) -> Document:
    matcher = CaptionMatcher(enable_vision=enable_vision)
    return matcher.process(document)
