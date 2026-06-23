# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Heading Detection Rules - Text and style heuristics for identifying headings.

This module contains rule-based logic to detect heading candidates based on:
- Keyword matching (common section names)
- Numbering patterns (1., 1.1, I., etc.)
- Font size (outliers compared to body text)
- Text styling (bold, font size)
- Text properties (short lines, capitalization)
"""

import re
from typing import Optional, Dict, Any, Tuple, List
from app.models import Block
from app.config.settings import settings  # Import settings for dynamic thresholds


# Common academic section headings (case-insensitive)
COMMON_SECTION_KEYWORDS = {
    # Front matter
    "abstract", "keywords", "key words", "summary",
    
    # Main sections (level 1)
    "introduction", "background", "related work", "literature review",
    "methods", "methodology", "materials and methods", "experimental setup",
    "results", "findings", "experimental results",
    "discussion", "results and discussion",
    "conclusion", "conclusions",
    "acknowledgments", "acknowledgements", "acknowledgment", "acknowledgement",
    "funding", "funding information", "financial support",
    "references", "bibliography", "works cited",
    "appendix", "appendices", "supplementary material",
    
    # Compliance / Meta
    "conflict of interest", "conflicts of interest", "disclosure",
    "declaration of interest", "declarations of interest",
    "competing interests", "competing interest",
    "author contributions", "authors' contributions",
    "data availability", "data availability statement",
    "ethics statement", "ethics approval",
    "abbreviations",
}


def detect_numbering_pattern(text: str) -> Optional[Dict[str, Any]]:
    """
    Detect if text starts with a heading numbering pattern.
    """
    text = text.strip()
    if not text:
        return None
        
    # Decimal numbering: 1., 1.1, 1.1.1, etc.
    # Also support "1 Introduction" (no dot) if followed by Capital Letter
    # Regex: ^(\d+(?:\.\d+)*)\.?\s+([A-Z].+)$
    decimal_match = re.match(r'^(\d+(?:\.\d+)*)\.?\s+([A-Z].*)$', text)
    if decimal_match:
        number = decimal_match.group(1)
        remainder = decimal_match.group(2)
        level = number.count('.') + 1
        
        return {
            "pattern_type": "decimal",
            "number": number,
            "level": level,
            "remainder": remainder
        }
    
    # Roman numerals: I. Introduction
    roman_match = re.match(r'^([IVX]+)\.?\s+([A-Z].*)$', text)
    if roman_match:
        number = roman_match.group(1)
        remainder = roman_match.group(2)
        return {
            "pattern_type": "roman",
            "number": number,
            "level": 1,
            "remainder": remainder
        }
    
    return None


def detect_title(block: Block, all_blocks: list) -> bool:
    """
    STRICT Title Detection.
    Rules:
    - ONLY the first non-empty block in the document.
    - Length between 5 and 200 chars.
    - Not a numbered heading.
    """
    text = block.text.strip()
    if not text or len(text) < 5 or len(text) > 200:
        return False
        
    # Find all non-empty body blocks (ignore parser-marked headers/footers)
    non_empty = [
        b for b in all_blocks
        if b.text.strip()
        and not b.metadata.get("is_header")
        and not b.metadata.get("is_footer")
    ]
    if not non_empty:
        return False
        
    # Rule: MUST be the very first non-empty block
    if block.block_id != non_empty[0].block_id:
        return False
        
    # Rule: TITLE must NEVER be a numbered heading
    if detect_numbering_pattern(text):
        return False
        
    return True


def matches_section_keyword(text: str) -> bool:
    """
    Check if text matches a common section heading keyword.
    Strictly enforce short length for keywords.
    """
    text_clean = text.strip().lower()
    
    # HARD GUARD: Headings matching keywords are rarely long.
    # "Abstract" etc. are usually < 40 chars.
    if len(text_clean) > 50:
        return False
        
    # Remove leading numbering
    text_clean = re.sub(r'^\d+(?:\.\d+)*\.?\s*', '', text_clean)
    text_clean = re.sub(r'^[IVX]+\.?\s*', '', text_clean)
    
    # Check exact match
    if text_clean in COMMON_SECTION_KEYWORDS:
        return True
    
    # Check for small variations like "1. Introduction" (number already removed)
    # But do NOT allow "Abstract publishing requires..."
    # We only allow trailing text if it's very short (e.g., "Abstract - Summer 2023")
    if any(text_clean.startswith(f"{kw}") for kw in COMMON_SECTION_KEYWORDS):
        if len(text_clean) < 30: # Tight limit for prefix matches
            return True
            
    return False


def is_likely_heading_by_style(block: Block, avg_font_size: Optional[float] = None) -> Tuple[bool, float]:
    """
    Determine if a block is likely a heading based on styling.
    """
    text = block.text.strip()
    
    # Minimum length guard (keep as reasonable sanity check)
    if len(text) < 2:
        return False, 0.0
        
    score = 0.0
    
    # SOFT PENALTY: Long text is less likely to be a heading
    # But don't reject outright - reduce confidence instead
    if len(text) > 260:
        score -= 0.4  # Strong penalty for extremely long text
    elif len(text) > 200:
        score -= 0.3  # Strong penalty for very long text
    elif len(text) > 120:
        score -= 0.1  # Keep long headings possible while still penalizing
    
    # Font size outliers are strong signals
    if block.style.font_size and avg_font_size:
        if block.style.font_size > avg_font_size * 1.2:
            score += 0.5
        elif block.style.font_size > avg_font_size:
            score += 0.2
            
    if block.style.bold:
        score += 0.3
        
    if text.isupper():
        score += 0.2
        
    # Negative signal: Ends with period
    if text.endswith('.'):
        score -= 0.3
        
    return score >= settings.HEADING_STYLE_THRESHOLD, min(score, 1.0)  # Dynamic threshold


def infer_heading_level(block: Block, numbering_info: Optional[Dict] = None) -> int:
    """
    Infer heading level (1-4).
    TITLE = 0 (handled by detect_title)
    Abstract/Intro/Methods/References/Conclusion = 1
    Numbering depth (1.1 = 2)
    """
    text = block.text.strip().lower()
    
    # Major sections are always Level 1
    major_sections = {
        "abstract", "introduction", "methods", "methodology", 
        "results", "discussion", "conclusion", "conclusions", 
        "references", "bibliography", "summary", "keywords"
    }
    
    # Remove leading numbering for keyword check
    clean_text = re.sub(r'^\d+(?:\.\d+)*\.?\s*', '', text)
    if clean_text in major_sections:
        return 1
        
    # Use numbering depth
    if numbering_info and "level" in numbering_info:
        return min(numbering_info["level"], 4)
        
    return 1 # Default to level 1 for other heading candidates


def get_capitalization_ratio(text: str) -> float:
    """Calculate ratio of capitalized words for Title Case detection."""
    words = text.split()
    if not words:
        return 0.0
    # Common small words in Title Case
    small_words = {"a", "an", "the", "and", "but", "or", "for", "nor", "on", "at", "to", "from", "by", "of", "with"}
    
    meaningful_words = [w for w in words if w.lower() not in small_words]
    if not meaningful_words:
        return 1.0 # If only small words, assume it's okay (rare for headings)
        
    capped = [w for w in meaningful_words if w[0].isupper() or any(c.isupper() for c in w)]
    return len(capped) / len(meaningful_words)


def analyze_heading_candidate(
    block: Block,
    all_blocks: List[Block],
    block_index: int,
    avg_font_size: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """
    Unified analysis with ABSOLUTE SENIOR HARD GUARDS.
    These guards override ALL keyword/style matches.
    """
    text = block.text.strip()
    if not text:
        return None

    # Note: Length penalties applied in style scoring, not hard rejection
        
    # Check for numbering
    num_info = detect_numbering_pattern(text)
    
    # HARD GUARD 2: Sentence punctuation without numbering
    # Actual headings rarely end in . ? ! unless they are very short (e.g. "Q&A.")
    if not num_info and text.endswith(('.', '?', '!')):
        if len(text.split()) > 4: # If it's more than a few words, it's a sentence
            return None
        
    # HARD GUARD 3: Multiple sentences
    # Presence of period followed by space and capital letter suggests a paragraph
    if not num_info and re.search(r'\.[ \t]+[A-Z]', text):
        return None
        
    # HARD GUARD 4: Starts with paragraph-typical markers (ABSOLUTE REJECTION)
    pronoun_starters = ("this paper", "the proposed", "we propose", "our system", "it is", "in this", "we present", "this study")
    if text.lower().startswith(pronoun_starters):
        return None
        
    # HARD GUARD 5: Figure and Table captions (ABSOLUTE REJECTION)
    caption_starters = ("figure ", "fig. ", "table ", "tab. ", "box ")
    if text.lower().startswith(caption_starters):
        return None

    # SOFT GUARD: Sentence-like structure reduces confidence
    # Long text with multiple sentences is less likely a heading
    # But we don't reject outright - let confidence scoring handle it
    if not num_info and (re.search(r'[\.\?\!]\s+[A-Z]', text) or len(text.split()) > 15):
        # This will be caught by confidence threshold later
        pass

    # HARD GUARD 7: Numbered but looks like sentence (e.g. Reference entry)
    # "1. Smith, J. Title."
    if num_info:
        remainder = num_info["remainder"].strip()
        # If the remainder contains sentence-ending punctuation followed by space+Cap
        # AND it's not super short (like "Q. A.")
        # AND it looks like a list/reference (contains comma or "et al")
        if re.search(r'[\.\?\!]\s+[A-Z]', remainder) and len(remainder) > 20:
             if ',' in remainder or " et al" in remainder.lower():
                 return None


    # ABSTRACT SAFETY GUARD (ABSOLUTE)
    # If we have recently seen an "Abstract" keyword heading, all following blocks
    # are body until we see a strong new section (numbered or major keyword).
    
    # 1. Scan backward to find the most recent "heading" or keyword
    lookback_index = block_index - 1
    recent_abstract_found = False
    
    while lookback_index >= 0:
        prev_block = all_blocks[lookback_index]
        prev_text = prev_block.text.strip().lower()
        
        # If we hit an "Abstract" keyword alone or as a heading
        if prev_text == "abstract":
            recent_abstract_found = True
            break
            
        # If we hit ANY other clear heading (numbered), the abstract block has likely ended
        if detect_numbering_pattern(prev_block.text):
            break
            
        # If we hit a major section name (excluding Abstract)
        major_keywords = {"introduction", "methods", "results", "discussion", "conclusion", "references"}
        if prev_text in major_keywords:
            break
            
        lookback_index -= 1
        
    if recent_abstract_found:
        # If we found an abstract heading recently, this current block is body
        # UNLESS it's a very clear next heading (but we already checked those in the while loop if they were prev)
        # Actually, if the current block IS a major keyword or numbered, it's allowed.
        # But if it's just a "likely style" match or fallback, reject it.
        if not num_info and not matches_section_keyword(text):
            return None

    reasons = []
    confidence = 0.0
    
    # Priority 1: Numbering
    if num_info:
        reasons.append(f"Numbering: {num_info['number']}")
        confidence += 0.8
        
    # Priority 2: Keyword
    if matches_section_keyword(text):
        reasons.append("Section Keyword")
        confidence += 0.5
        
    # Priority 3: Style
    style_likely, style_score = is_likely_heading_by_style(block, avg_font_size)
    if style_likely:
        reasons.append("Heading Style")
        confidence += style_score * 0.4

    # Priority 4: Parser heading hint (PDF/Doc parser signal)
    parser_heading_hint = False
    parser_heading_level = None
    if isinstance(getattr(block, "metadata", None), dict):
        parser_heading_hint = bool(block.metadata.get("potential_heading"))
        parser_heading_level = block.metadata.get("heading_level")
    if parser_heading_hint:
        reasons.append("Parser Heading Signal")
        confidence += 0.45

    # FALLBACK LOGIC: Keyword-Independent Heading Heuristic
    # If we haven't crossed threshold but it's short, isolated, and Title Case
    if confidence < 0.4:
        # Check isolation using sequential block_index (not sparse Document index)
        # This replaces the old index-gap heuristic that over-fired with Step-100 gaps.
        # Now uses content-aware adjacency: empty neighbours = isolated block.
        is_isolated = (
            block_index > 0
            and block_index < len(all_blocks) - 1
            and not all_blocks[block_index - 1].text.strip()
            and not all_blocks[block_index + 1].text.strip()
        )
        
        cap_ratio = get_capitalization_ratio(text)
        
        if len(text) <= 60 and cap_ratio >= 0.7 and is_isolated:
            confidence = settings.HEADING_FALLBACK_CONFIDENCE  # Dynamic fallback confidence
            reasons.append("Fallback: Short, Isolated, Title Case")
            
    if confidence < settings.HEADING_STYLE_THRESHOLD:  # Dynamic threshold
        return None
        
    # Level Inference
    level = infer_heading_level(block, num_info)
    if parser_heading_level in {1, 2, 3, 4} and not num_info:
        level = int(parser_heading_level)
    if not num_info and not matches_section_keyword(text):
        # Default level 2 for fallback headings
        level = 2
        # Promote to Level 1 if near start or isolated + large font
        if block_index < 5 or (style_score > 0.4 and avg_font_size and block.style.font_size and block.style.font_size > avg_font_size):
            level = 1
        
    return {
        "is_heading": True,
        "confidence": min(confidence, 1.0),
        "level": level,
        "has_numbering": num_info is not None,
        "numbering_info": num_info,
        "reasons": reasons
    }
