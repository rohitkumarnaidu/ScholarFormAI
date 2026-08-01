# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
External service integrations for document processing pipeline.

This module provides clients for industry-standard tools:
- GROBID: Metadata extraction (title, authors, affiliations)
- Docling: Layout analysis (bounding boxes, visual structure)
- CrossRef: Citation validation and DOI lookup
- CSL: Citation formatting engine
"""

from .crossref_client import CrossRefClient
from .csl_engine import CSLEngine
from .grobid_client import GROBIDClient

__all__ = ["GROBIDClient", "CSLEngine", "CrossRefClient"]
