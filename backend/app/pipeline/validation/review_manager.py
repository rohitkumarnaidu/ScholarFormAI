# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import logging
from typing import List, Dict, Any
from app.models.pipeline_document import PipelineDocument, ReviewStatus, ReviewMetadata

logger = logging.getLogger(__name__)

class ReviewManager:
    """
    Evaluates AI confidence scores and flags sections for Human-In-The-Loop review.
    """
    
    def __init__(self, review_threshold: float = 0.70, critical_threshold: float = 0.45):
        # Validate thresholds
        if critical_threshold >= review_threshold:
            raise ValueError(
                f"critical_threshold ({critical_threshold}) must be less than "
                f"review_threshold ({review_threshold})"
            )
        if not (0.0 <= critical_threshold <= 1.0) or not (0.0 <= review_threshold <= 1.0):
            raise ValueError("Thresholds must be between 0.0 and 1.0")
            
        self.review_threshold = review_threshold
        self.critical_threshold = critical_threshold
        logger.info(
            f"ReviewManager initialized: review_threshold={review_threshold}, "
            f"critical_threshold={critical_threshold}"
        )

    def evaluate(self, doc_obj: PipelineDocument) -> PipelineDocument:
        """Analyze document blocks and metadata to determine review status."""
        critical_flags = []
        review_flags = []
        lowest_conf = 1.0
        
        # 1. Check Block Confidences
        for b in doc_obj.blocks:
            raw_conf = (
                b.metadata.get("classification_confidence")
                if isinstance(getattr(b, "metadata", None), dict)
                else None
            )
            if raw_conf is None:
                raw_conf = getattr(b, "classification_confidence", None)
            if raw_conf is None and isinstance(getattr(b, "metadata", None), dict):
                raw_conf = b.metadata.get("nlp_confidence")

            try:
                conf = float(raw_conf)
            except (TypeError, ValueError):
                conf = 1.0
            conf = max(0.0, min(1.0, conf))

            if conf < lowest_conf:
                lowest_conf = conf

            semantic_label = (
                getattr(b, "semantic_intent", None)
                or b.metadata.get("semantic_intent", "unknown section")
            )

            if conf < self.critical_threshold:
                flag = (
                    f"CRITICAL: low confidence ({conf:.2f}) on "
                    f"{semantic_label} "
                    f"[block: {b.block_id[:8]}]"
                )
                critical_flags.append(flag)
                logger.warning(f"Threshold violation: {flag}")
            elif conf < self.review_threshold:
                flag = f"REVIEW: Ambiguous classification [block: {b.block_id[:8]}] ({conf:.2f})"
                review_flags.append(flag)
                logger.info(f"Review recommended: {flag}")

        # 2. Check Reasoning Confidence
        ai_hints = doc_obj.metadata.ai_hints
        if "semantic_advice" in ai_hints:
            advice_conf = ai_hints["semantic_advice"].get("confidence", 1.0)
            if advice_conf < lowest_conf:
                lowest_conf = advice_conf
            if advice_conf < self.review_threshold:
                flag = f"REVIEW: AI Reasoning uncertain ({advice_conf:.2f})"
                review_flags.append(flag)
                logger.info(f"Review recommended: {flag}")

        # 3. Prioritize flags: CRITICAL first, then REVIEW
        all_flags = critical_flags + review_flags
        
        # 4. Determine Final Status
        status = ReviewStatus.OK
        reason = None
        
        if lowest_conf < self.critical_threshold:
            status = ReviewStatus.CRITICAL
            reason = "Multiple sections failed automated confidence checks."
            logger.warning(
                f"Document flagged as CRITICAL: {len(critical_flags)} critical issues, "
                f"lowest_confidence={lowest_conf:.2f}"
            )
        elif lowest_conf < self.review_threshold:
            status = ReviewStatus.REVIEW
            reason = "Some sections require human verification."
            logger.info(
                f"Document flagged for REVIEW: {len(review_flags)} review items, "
                f"lowest_confidence={lowest_conf:.2f}"
            )
        else:
            logger.debug(f"Document passed review checks: lowest_confidence={lowest_conf:.2f}")
            
        doc_obj.review = ReviewMetadata(
            status=status,
            flags=all_flags[:5],  # Limit to top 5 flags (CRITICAL prioritized)
            lowest_confidence=lowest_conf,
            reason=reason
        )
        
        return doc_obj
