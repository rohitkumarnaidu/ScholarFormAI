# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Parsing pipeline - Extract raw content from DOCX files."""

from .parser import DocxParser, parse_docx

__all__ = ["DocxParser", "parse_docx"]
