# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
from __future__ import annotations
from unittest.mock import MagicMock, patch
import pytest


class TestPipelineStage:
    def test_abstract_cannot_instantiate(self):
        from app.pipeline.base import PipelineStage
        with pytest.raises(TypeError):
            PipelineStage()

    def test_concrete_implementation(self):
        from app.pipeline.base import PipelineStage
        class ConcreteStage(PipelineStage):
            def process(self, document):
                document.processed = True
                return document
        doc = MagicMock()
        result = ConcreteStage().process(doc)
        assert result.processed is True
