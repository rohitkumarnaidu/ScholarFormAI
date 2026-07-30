# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
from __future__ import annotations
from unittest.mock import MagicMock
import pytest


class TestBaseParser:
    def test_abstract_cannot_instantiate(self):
        from app.pipeline.parsing.base_parser import BaseParser
        with pytest.raises(TypeError):
            BaseParser()

    def test_concrete_parser(self):
        from app.pipeline.parsing.base_parser import BaseParser
        class TestParser(BaseParser):
            def parse(self, file_path, document_id):
                return file_path + document_id
            def supports_format(self, file_extension):
                return file_extension == ".xyz"
        p = TestParser()
        assert p.parse("a", "b") == "ab"
        assert p.supports_format(".xyz") is True
        assert p.supports_format(".pdf") is False
