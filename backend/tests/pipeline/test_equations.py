# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
from __future__ import annotations
from unittest.mock import patch, MagicMock
import pytest
from app.utils.id_generator import generate_equation_id

class TestEquationStandardizer:
    @pytest.fixture
    def standardizer(self):

        from app.models import PipelineDocument, Equation
        with patch("app.pipeline.equations.standardizer.etree") as mock_etree:
            mock_etree.parse.return_value = MagicMock()
            mock_etree.XSLT.return_value = MagicMock()
            from app.pipeline.equations.standardizer import EquationStandardizer
            yield EquationStandardizer(xsl_path="/fake/omml2mml.xsl")

    def test_process_no_equations(self, standardizer):
        from app.models import PipelineDocument, Equation
        doc = PipelineDocument(document_id="t", )
        result = standardizer.process(doc)
        assert result is doc

    def test_process_omml_conversion_success(self, standardizer):
        from app.models import PipelineDocument, Equation
        standardizer._convert_omml_to_mathml = MagicMock(return_value="<math>result</math>")
        eq = Equation(equation_id=generate_equation_id(1), index=1, omml="<m:oMath>...</m:oMath>")
        doc = PipelineDocument(document_id="t", equations=[eq])
        result = standardizer.process(doc)
        assert result.equations[0].mathml == "<math>result</math>"

    def test_process_omml_conversion_failure(self, standardizer):
        from app.models import PipelineDocument, Equation
        standardizer._convert_omml_to_mathml = MagicMock(return_value="")
        eq = Equation(equation_id=generate_equation_id(1), index=1, omml="<bad>xml</bad>")
        doc = PipelineDocument(document_id="t", equations=[eq])
        result = standardizer.process(doc)
        assert result.equations[0].mathml != "<math>result</math>"

    def test_process_adds_stage_info(self, standardizer):
        from app.models import PipelineDocument, Equation
        standardizer._convert_omml_to_mathml = MagicMock(return_value="<math>ok</math>")
        eq = Equation(equation_id=generate_equation_id(1), index=1, omml="<m:oMath>x</m:oMath>")
        doc = PipelineDocument(document_id="t", equations=[eq])
        result = standardizer.process(doc)
        stages = [s.stage_name for s in result.processing_history]
        assert "equation_standardization" in stages

    def test_convert_no_xslt(self):
        from app.models import PipelineDocument, Equation
        with patch("app.pipeline.equations.standardizer.etree") as mock_etree:
            mock_etree.parse.return_value = MagicMock()
            mock_etree.XSLT.side_effect = Exception("no xslt")
            from app.pipeline.equations.standardizer import EquationStandardizer
            s = EquationStandardizer(xsl_path="/fake/omml2mml.xsl")
            assert s._xslt is None

    def test_convert_xslt_not_found(self):
        from app.models import PipelineDocument, Equation
        from app.pipeline.equations.standardizer import EquationStandardizer
        s = EquationStandardizer(xsl_path="/nonexistent/omml2mml.xsl")
        result = s._convert_omml_to_mathml("<xml/>")
        assert result == ""

    def test_convert_xml_syntax_error(self, standardizer):
        from app.models import PipelineDocument, Equation
        standardizer._xslt = MagicMock()
        class FakeXMLSyntaxError(Exception):
            pass
        with patch("app.pipeline.equations.standardizer.etree") as mock_etree:
            mock_etree.XMLSyntaxError = FakeXMLSyntaxError
            mock_etree.fromstring.side_effect = FakeXMLSyntaxError("bad xml")
            result = standardizer._convert_omml_to_mathml("<bad>xml")
        assert result == ""

    def test_process_exception_handled(self, standardizer):
        from app.models import PipelineDocument, Equation
        standardizer._convert_omml_to_mathml = MagicMock(side_effect=Exception("unexpected"))
        eq = Equation(equation_id=generate_equation_id(1), index=1, omml="<m:oMath>x</m:oMath>")
        doc = PipelineDocument(document_id="t", equations=[eq])
        result = standardizer.process(doc)
        stages = [s.stage_name for s in result.processing_history]
        assert "equation_standardization" in stages

    def test_get_equation_standardizer_singleton(self):
        from app.models import PipelineDocument, Equation
        with patch("app.pipeline.equations.standardizer.etree") as mock_etree:
            mock_etree.parse.return_value = MagicMock()
            mock_etree.XSLT.return_value = MagicMock()
            from app.pipeline.equations.standardizer import get_equation_standardizer
            s1 = get_equation_standardizer()
            s2 = get_equation_standardizer()
            assert s1 is s2
