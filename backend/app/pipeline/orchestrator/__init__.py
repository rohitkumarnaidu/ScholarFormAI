# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Pipeline Orchestrator package.

Refactored from a 1350-line god class into a modular package:
  __init__.py    — Backward-compatible re-exports
  orchestrator.py — Slim coordination class
  stages.py       — Individual pipeline stage implementations
  contracts.py    — Stage contract Protocol interfaces
  errors.py       — Stage-specific error types
  metrics.py      — Stage metrics collection
  events.py       — Stage event emission for SSE
"""

import logging
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)

from app.config.settings import settings
from app.db.supabase_client import get_supabase_client
from app.pipeline.services import GROBIDClient, DoclingClient
from app.pipeline.input_conversion.converter import InputConverter
from app.pipeline.nlp.analyzer import ContentAnalyzer, extract_keywords
from app.pipeline.contracts.loader import ContractLoader
from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
from app.utils.serialization import build_structured_data, safe_model_dump
from app.utils.singleton import resolve_optional_callable
from app.pipeline.parsing.parser_factory import ParserFactory
from app.pipeline.structure_detection.detector import StructureDetector
from app.pipeline.classification.classifier import ContentClassifier
from app.pipeline.figures.caption_matcher import CaptionMatcher
from app.pipeline.tables.caption_matcher import TableCaptionMatcher
from app.pipeline.references.parser import ReferenceParser
from app.pipeline.validation import DocumentValidator, validate_document
from app.pipeline.validation.ai_explainer import AIExplainer
from app.pipeline.formatting.formatter import Formatter
from app.pipeline.export.exporter import Exporter
from app.pipeline.normalization.normalizer import Normalizer as TextNormalizer
from app.services.quality_score_service import compute_quality_score
from app.pipeline.equations.standardizer import get_equation_standardizer
from app.pipeline.safety import safe_execution
from app.pipeline.safety.retry_guard import execute_with_retry, retry_with_backoff
from app.models import Block, BlockType, TemplateInfo, PipelineDocument, DocumentMetadata
from app.services.quality_score_service import compute_quality_score

# Ensure the orchestrator module is importable before we use PipelineOrchestrator
from app.pipeline.orchestrator.orchestrator import (
    PipelineOrchestrator,
    _MAX_CONCURRENT_JOBS,
    _pipeline_semaphore,
    _ACQUIRE_TIMEOUT_SECONDS,
    get_rag_engine,
    get_reasoning_engine,
)

# Re-export figure analyzer helpers from stages
from app.pipeline.orchestrator.stages import _get_figure_analyzer, _figure_analyzer_instance

# Re-export phase implementations
from app.pipeline.orchestrator.phases import PipelinePhases

# Backward-compatible aliases for tests that import the old variable names
_MAX_CONCURRENCY = _MAX_CONCURRENT_JOBS
_ACQUIRE_TIMEOUT = _ACQUIRE_TIMEOUT_SECONDS

__all__ = [
    "PipelineOrchestrator",
    "PipelinePhases",
    "logger",
    "_MAX_CONCURRENT_JOBS",
    "_pipeline_semaphore",
    "_ACQUIRE_TIMEOUT_SECONDS",
    "_get_figure_analyzer",
    "_figure_analyzer_instance",
    "get_rag_engine",
    "get_reasoning_engine",
    "build_structured_data",
    "safe_model_dump",
    "get_supabase_client",
    "settings",
    "GROBIDClient",
    "DoclingClient",
    "InputConverter",
    "ContentAnalyzer",
    "ContractLoader",
    "ReferenceFormatterEngine",
    "resolve_optional_callable",
]
