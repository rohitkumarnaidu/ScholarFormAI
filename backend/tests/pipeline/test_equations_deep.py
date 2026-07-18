# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
from unittest.mock import MagicMock, patch, mock_open
import pytest
pytestmark = [pytest.mark.pipeline]


class TestEquationStandardizer:
    def test_init_default_xsl_path(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        import os
        with patch("os.path.exists", return_value=False):
            s = EquationStandardizer()
            assert s.xsl_path is not None
            assert s._xslt is None

    def test_init_with_custom_path(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        with patch("os.path.exists", return_value=True):
            with patch("lxml.etree.parse") as mock_parse:
                mock_xslt = MagicMock()
                mock_parse.return_value = mock_xslt
                from lxml import etree
                with patch.object(etree, "XSLT") as mock_xslt_cls:
                    mock_xslt_cls.return_value = MagicMock()
                    s = EquationStandardizer(xsl_path="/custom/omml2mml.xsl")
                    assert s._xslt is not None

    def test_init_xslt_load_failure(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        with patch("os.path.exists", return_value=True):
            with patch("lxml.etree.parse", side_effect=Exception("Parse error")):
                s = EquationStandardizer(xsl_path="/bad/path.xsl")
                assert s._xslt is None

    def test_init_xslt_not_found(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        with patch("os.path.exists", return_value=False):
            s = EquationStandardizer(xsl_path="/nonexistent.xsl")
            assert s._xslt is None

    def test_process_no_equations(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        from app.models.pipeline_document import PipelineDocument
        doc = PipelineDocument(document_id="test")
        s = EquationStandardizer()
        with patch.object(s, "_convert_omml_to_mathml"):
            result = s.process(doc)
            assert result is doc

    def test_process_with_equations(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        from app.models.pipeline_document import PipelineDocument
        from app.models.equation import Equation
        doc = PipelineDocument(
            document_id="test",
            equations=[Equation(equation_id="e1", omml="<m:oMath>...</m:oMath>", index=0)]
        )
        s = EquationStandardizer()
        with patch.object(s, "_convert_omml_to_mathml", return_value="<math>converted</math>"):
            result = s.process(doc)
            assert result.equations[0].mathml == "<math>converted</math>"
            assert result.equations[0].metadata["conversion_engine"] == "xslt-1.0"

    def test_process_conversion_failure(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        from app.models.pipeline_document import PipelineDocument
        from app.models.equation import Equation
        doc = PipelineDocument(
            document_id="test",
            equations=[Equation(equation_id="e1", omml="<bad>", index=0)]
        )
        s = EquationStandardizer()
        with patch.object(s, "_convert_omml_to_mathml", return_value=""):
            result = s.process(doc)
            assert result.equations[0].mathml is None

    def test_process_exception(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        from app.models.pipeline_document import PipelineDocument
        from app.models.equation import Equation
        doc = PipelineDocument(
            document_id="test",
            equations=[Equation(equation_id="e1", omml="<m:oMath>...</m:oMath>", index=0)]
        )
        s = EquationStandardizer()
        with patch.object(s, "_convert_omml_to_mathml", side_effect=Exception("Convert error")):
            result = s.process(doc)
            assert result.equations[0].mathml is None

    def test_process_partial_failure(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        from app.models.pipeline_document import PipelineDocument
        from app.models.equation import Equation
        doc = PipelineDocument(
            document_id="test",
            equations=[
                Equation(equation_id="e1", omml="<m:oMath>ok</m:oMath>", index=0),
                Equation(equation_id="e2", omml="<m:oMath>bad</m:oMath>", index=1),
            ]
        )
        s = EquationStandardizer()
        with patch.object(s, "_convert_omml_to_mathml", side_effect=["<math>ok</math>", ""]):
            result = s.process(doc)
            assert result.equations[0].mathml == "<math>ok</math>"
            assert result.equations[1].mathml is None

    def test_convert_omml_to_mathml_no_xslt(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        s = EquationStandardizer()
        s._xslt = None
        result = s._convert_omml_to_mathml("<m:oMath>test</m:oMath>")
        assert result == ""

    def test_convert_omml_to_mathml_success(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        from lxml import etree

        mock_xslt = MagicMock()
        mock_result = MagicMock()
        mock_result.__str__.return_value = "<math>result</math>"
        mock_xslt.return_value = mock_result
        from lxml import etree as _real_etree

        s = EquationStandardizer()
        s._xslt = mock_xslt
        with patch("lxml.etree.fromstring") as mock_fromstring:
            mock_dom = MagicMock()
            mock_dom.nsmap = {None: "http://schemas.openxmlformats.org/officeDocument/2006/math"}
            mock_fromstring.return_value = mock_dom
            with patch("lxml.etree.tostring", return_value="<math>result</math>"):
                result = s._convert_omml_to_mathml("<m:oMath>test</m:oMath>")
                assert result == "<math>result</math>"

    def test_convert_omml_to_mathml_xml_syntax_error(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        s = EquationStandardizer()
        s._xslt = MagicMock()
        from lxml.etree import XMLSyntaxError
        with patch("lxml.etree.fromstring", side_effect=XMLSyntaxError("bad xml", None, 0, 0)):
            result = s._convert_omml_to_mathml("<bad>")
            assert result == ""

    def test_convert_omml_to_mathml_general_exception(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        s = EquationStandardizer()
        s._xslt = MagicMock()
        with patch("lxml.etree.fromstring", side_effect=Exception("General error")):
            result = s._convert_omml_to_mathml("<test/>")
            assert result == ""

    def test_convert_omml_no_default_ns(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        s = EquationStandardizer()
        mock_xslt = MagicMock()
        mock_result = MagicMock()
        mock_result.__str__.return_value = "<math>result</math>"
        mock_xslt.return_value = mock_result
        s._xslt = mock_xslt

        with patch("lxml.etree.fromstring") as mock_fromstring:
            mock_dom = MagicMock()
            mock_dom.nsmap = {"m": "http://some/other/ns"}
            mock_fromstring.return_value = mock_dom
            with patch("lxml.etree.tostring", return_value="<math>result</math>"):
                result = s._convert_omml_to_mathml("<m:oMath>test</m:oMath>")
                assert result == "<math>result</math>"

    def test_get_equation_standardizer(self):
        from app.pipeline.equations.standardizer import get_equation_standardizer, _standardizer
        _standardizer = None
        s = get_equation_standardizer()
        assert s is not None
        s2 = get_equation_standardizer()
        assert s is s2

    def test_convert_omml_to_mathml_with_omml_ns(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        s = EquationStandardizer()
        mock_xslt = MagicMock()
        mock_result = MagicMock()
        mock_result.__str__.return_value = "<math>result</math>"
        mock_xslt.return_value = mock_result
        s._xslt = mock_xslt

        with patch("lxml.etree.fromstring") as mock_fromstring:
            mock_dom = MagicMock()
            mock_dom.nsmap = {None: "http://schemas.openxmlformats.org/officeDocument/2006/math"}
            mock_fromstring.return_value = mock_dom
            with patch("lxml.etree.tostring", return_value="<math>result</math>"):
                result = s._convert_omml_to_mathml("<m:oMath>test</m:oMath>")
                assert result is not None

    def test_process_no_omml(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        from app.models.pipeline_document import PipelineDocument
        from app.models.equation import Equation
        doc = PipelineDocument(
            document_id="test",
            equations=[Equation(equation_id="e1", omml=None, index=0)]
        )
        s = EquationStandardizer()
        result = s.process(doc)
        assert result.equations[0].mathml is None
