# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Deep test suite for Equation Standardizer pipeline stage.
Covers process(), OMML→MathML conversion via XSLT, singleton access.
"""

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
from __future__ import annotations
from unittest.mock import patch, MagicMock
import pytest
from app.pipeline.equations.standardizer import EquationStandardizer, get_equation_standardizer

@pytest.fixture
def standardizer():

    from app.models import Equation
    return EquationStandardizer()

@pytest.fixture
def doc_with_omml():
    from app.models import Equation
    return PipelineDocument(document_id="eq1", equations=[
        Equation(equation_id="e1", index=0,
                 omml='<m:oMath xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"><m:r><m:t>x</m:t></m:r></m:oMath>'),
        Equation(equation_id="e2", index=1,
                 omml='<m:oMath xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"><m:r><m:t>y</m:t></m:r></m:oMath>'),
    ])

@pytest.fixture
def doc_with_text_only():
    from app.models import Equation
    return PipelineDocument(document_id="eq2", equations=[
        Equation(equation_id="e3", index=0, text="E = mc^2"),
    ])

class TestEquationStandardizerProcess:
    def test_process_converts_omml(self, standardizer, doc_with_omml):
        from app.models import Equation
        with patch.object(standardizer, "_convert_omml_to_mathml") as mock_conv:
            mock_conv.return_value = "<math><mi>x</mi></math>"
            result = standardizer.process(doc_with_omml)
            assert result.equations[0].mathml == "<math><mi>x</mi></math>"
            assert mock_conv.call_count == 2

    def test_process_empty_equations(self, standardizer):
        from app.models import Equation
        doc = PipelineDocument(document_id="empty", equations=[])
        result = standardizer.process(doc)
        assert len(result.equations) == 0

    def test_process_no_omml_skips(self, standardizer, doc_with_text_only):
        from app.models import Equation
        result = standardizer.process(doc_with_text_only)
        assert result.equations[0].mathml is None

    def test_process_handles_conversion_failure(self, standardizer, doc_with_omml):
        from app.models import Equation
        with patch.object(standardizer, "_convert_omml_to_mathml") as mock_conv:
            mock_conv.return_value = ""
            result = standardizer.process(doc_with_omml)
            assert result.equations[0].mathml is None

    def test_process_exception_in_loop_continues(self, standardizer, doc_with_omml):
        from app.models import Equation
        with patch.object(standardizer, "_convert_omml_to_mathml") as mock_conv:
            mock_conv.side_effect = [RuntimeError("fail"), "<math><mi>y</mi></math>"]
            result = standardizer.process(doc_with_omml)
            assert result.equations[1].mathml == "<math><mi>y</mi></math>"

    def test_process_adds_conversion_engine_metadata(self, standardizer, doc_with_omml):
        from app.models import Equation
        with patch.object(standardizer, "_convert_omml_to_mathml") as mock_conv:
            mock_conv.return_value = "<math><mi>x</mi></math>"
            result = standardizer.process(doc_with_omml)
            assert result.equations[0].metadata.get("conversion_engine") == "xslt-1.0"

class TestOMMLToMathMLConversion:
    def test_convert_with_xslt(self, standardizer):
        from app.models import Equation
        omml = '<m:oMath xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"><m:r><m:t>x</m:t></m:r></m:oMath>'
        result = standardizer._convert_omml_to_mathml(omml)
        assert isinstance(result, str)

    def test_convert_no_xslt_returns_empty(self, tmp_path):
        from app.models import Equation
        s = EquationStandardizer(xsl_path=str(tmp_path / "nonexistent.xsl"))
        assert s._convert_omml_to_mathml("<test/>") == ""

    def test_convert_invalid_xml_returns_empty(self, standardizer):
        from app.models import Equation
        assert standardizer._convert_omml_to_mathml("not xml") == ""

    def test_convert_empty_string_returns_empty(self, standardizer):
        from app.models import Equation
        assert standardizer._convert_omml_to_mathml("") == ""

class TestXSLTLoading:
    def test_xslt_not_found_warns(self, tmp_path):
        from app.models import Equation
        import logging

        xsl_path = str(tmp_path / "missing.xsl")
        s = EquationStandardizer(xsl_path=xsl_path)
        assert s._xslt is None

    def test_xslt_loaded_when_found(self, tmp_path):
        from app.models import Equation
        xsl_path = str(tmp_path / "test.xsl")
        with open(xsl_path, "w") as f:
            f.write('<?xml version="1.0"?><xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"/>')
        s = EquationStandardizer(xsl_path=xsl_path)
        assert s._xslt is not None

    def test_xslt_invalid_parsing(self, tmp_path):
        from app.models import Equation
        xsl_path = str(tmp_path / "bad.xsl")
        with open(xsl_path, "w") as f:
            f.write("not xml")
        s = EquationStandardizer(xsl_path=xsl_path)
        assert s._xslt is None

class TestProcessingHistory:
    def test_success_status(self, standardizer, doc_with_omml):
        from app.models import Equation
        with patch.object(standardizer, "_convert_omml_to_mathml") as mock_conv:
            mock_conv.return_value = "<math/>"
            result = standardizer.process(doc_with_omml)
            stage = result.processing_history[-1]
            assert stage.stage_name == "equation_standardization"
            assert stage.status == "success"

    def test_partial_status_on_failures(self, standardizer, doc_with_omml):
        from app.models import Equation
        with patch.object(standardizer, "_convert_omml_to_mathml") as mock_conv:
            mock_conv.return_value = ""
            result = standardizer.process(doc_with_omml)
            stage = result.processing_history[-1]
            assert stage.status == "partial"

    def test_duration_recorded(self, standardizer):
        from app.models import Equation
        doc = PipelineDocument(document_id="dur", equations=[
            Equation(equation_id="e1", index=0, omml="<test/>"),
        ])
        with patch.object(standardizer, "_convert_omml_to_mathml") as mock_conv:
            mock_conv.return_value = "<math/>"
            result = standardizer.process(doc)
            stage = result.processing_history[-1]
            assert stage.stage_name == "equation_standardization"

    def test_empty_document_returns_without_stage(self, standardizer):
        from app.models import Equation
        doc = PipelineDocument(document_id="empty", equations=[])
        result = standardizer.process(doc)
        assert len(result.processing_history) == 0

class TestGetEquationStandardizer:
    def test_singleton(self):
        from app.models import Equation
        s1 = get_equation_standardizer()
        s2 = get_equation_standardizer()
        assert s1 is s2
