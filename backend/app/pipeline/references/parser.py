# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Reference Parser - Semantic extraction of reference fields.

Parses unstructured reference strings into structured metadata.
"""

import logging
import re
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

from app.models import BlockType, Reference, ReferenceType
from app.models import PipelineDocument as Document
from app.pipeline.base import PipelineStage
from app.utils.id_generator import generate_reference_id

from .normalizer import clean_author_name, clean_title


class ReferenceParser(PipelineStage):
    """
    Parses reference blocks into structured Reference objects.

    Primary Focus: IEEE style (numeric).
    [1] A. B. Author, "Title," Venue, Year.
    """

    def __init__(self):
        # Regex components
        self.year_pattern = re.compile(r"\b(19|20)\d{2}\b")
        self.citation_key_pattern = re.compile(r"^\[([\w\-]+)\]")
        self.doi_pattern = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
        self.url_pattern = re.compile(r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+")

        # IEEE style author split (comma separated, followed by quote)
        # Conservative: Authors are usually at the start.

    def process(self, document: Document) -> Document:
        """
        Extract and parse references from the document.
        """
        start_time = datetime.now(UTC)

        try:
            blocks = document.get_blocks_by_type(BlockType.REFERENCE_ENTRY)
            if not blocks:
                # Fallback: check Section "References" if not typed
                document.get_blocks_in_section("References")
                # We stick to BlockType.REFERENCE_ENTRY as per contract.
                pass

            parsed_count = 0
            references = []

            for i, block in enumerate(blocks):
                text = (block.text or "").strip()
                if not text:
                    continue

                try:
                    # Parse individual reference
                    ref_obj = self._parse_single_reference(text, i)
                    ref_obj.block_id = block.block_id
                    references.append(ref_obj)
                    parsed_count += 1
                except Exception as exc:
                    logger.warning("Failed to parse reference block %s: %s", block.block_id, exc)

            document.references = references
        except Exception as exc:
            logger.error("Reference parsing failed: %s", exc)
            document.add_processing_stage(
                stage_name="reference_parsing", status="error", message=f"Reference parsing failed: {exc}"
            )
            return document

        # Log
        end_time = datetime.now(UTC)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        document.add_processing_stage(
            stage_name="reference_parsing",
            status="success",
            message=f"Parsed {parsed_count} references",
            duration_ms=duration_ms,
        )

        return document

    def _parse_single_reference(self, text: str, index: int) -> Reference:
        """
        Parse a single reference string.
        """

        # 1. Extract Citation Key
        match_key = self.citation_key_pattern.match(text)
        citation_key = match_key.group(1) if match_key else str(index + 1)

        # Remove key from text for further processing
        remainder = text[match_key.end() :].strip() if match_key else text

        # 2. Extract Year
        years = self.year_pattern.findall(remainder)
        year = int(years[-1]) if years else None  # Assume last year mentions is publication year

        # 3. Extract DOI/URL
        doi_match = self.doi_pattern.search(remainder)
        doi = doi_match.group(0) if doi_match else None

        url_match = self.url_pattern.search(remainder)
        url = url_match.group(0) if url_match else None

        # 4. Extract Title and Authors (Heuristic)
        # IEEE: Authors, "Title", Venue, ...
        # If quotes exist, assume title is in quotes.

        title = None
        authors = []
        venue = None

        # Look for quoted title
        quote_start = remainder.find('"')
        quote_end = remainder.find('"', quote_start + 1)

        if quote_start != -1 and quote_end != -1:
            # Found quoted title
            part_authors = remainder[:quote_start].strip().strip(",.")
            part_title = remainder[quote_start : quote_end + 1]  # Include quotes for cleaning
            part_rest = remainder[quote_end + 1 :].strip()

            title = clean_title(part_title)
            authors = self._parse_authors(part_authors)

            # Venue is likely in part_rest
            # Clean venue: remove year, pages if possible, or just Dump it.
            # heuristic: part_rest usually starts with ", Journal Name,"
            venue = part_rest.strip(",. ")

            # refine venue
            # remove year
            if year:
                venue = venue.replace(str(year), "").strip(",. ")
            if "pp." in venue:
                # split pages?
                pass

        else:
            # No quotes. fallback by dot separators?
            # Author1, Author2. Title. Venue. Year.
            parts = remainder.split(".")
            if len(parts) >= 3:
                # Heuristic: [0]=Authors, [1]=Title, [2]=Venue
                authors = self._parse_authors(parts[0])
                title = clean_title(parts[1])
                venue = parts[2].strip()
            else:
                # Fallback: Whole string is title?
                title = remainder

        # 5. Determine Type (Simple)
        ref_type = ReferenceType.UNKNOWN
        if venue and ("Conf" in venue or "Proc" in venue or "Symposium" in venue):
            ref_type = ReferenceType.CONFERENCE_PAPER
        elif venue and ("Journal" in venue or "Trans" in venue):
            ref_type = ReferenceType.JOURNAL_ARTICLE
        elif doi:
            ref_type = ReferenceType.JOURNAL_ARTICLE  # Likely

        # Construct Object
        ref_id = generate_reference_id(index)

        return Reference(
            reference_id=ref_id,
            index=index,
            number=(index + 1) if citation_key.isdigit() else None,
            citation_key=citation_key if match_key else f"ref_{index + 1}",
            raw_text=text,
            reference_type=ref_type,
            authors=authors,
            title=title,
            year=year,
            journal=venue if ref_type == ReferenceType.JOURNAL_ARTICLE else None,
            conference=venue if ref_type == ReferenceType.CONFERENCE_PAPER else None,
            doi=doi,
            url=url,
        )

    def _parse_authors(self, author_str: str) -> list[str]:
        """Parse author string into list."""
        if not author_str:
            return []
        # Split by comma or 'and'
        # IEEE: "A. B. Name, C. Name, and D. Name"

        # Remove 'and'
        normalized = author_str.replace(" and ", ", ")

        parts = normalized.split(",")
        authors = [clean_author_name(p) for p in parts if p.strip()]
        return authors


# Convenience
def parse_references(document: Document) -> Document:
    parser = ReferenceParser()
    return parser.process(document)
