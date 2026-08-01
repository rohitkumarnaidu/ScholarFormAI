from unittest.mock import MagicMock, patch


class TestEquationStandardizer:
    def test_omml_xml_syntax_error_returns_empty(self):
        with patch("app.pipeline.equations.standardizer.os.path.exists", return_value=True):
            with patch("app.pipeline.equations.standardizer.etree.XSLT"):
                from app.pipeline.equations.standardizer import EquationStandardizer
                es = EquationStandardizer(xsl_path="/fake/omml2mml.xsl")
                es._xslt = MagicMock()
                result = es._convert_omml_to_mathml("<invalid>")
                assert result == ""

    def test_no_xslt_returns_empty(self):
        with patch("app.pipeline.equations.standardizer.os.path.exists", return_value=False):
            from app.pipeline.equations.standardizer import EquationStandardizer
            es = EquationStandardizer(xsl_path="/fake/omml2mml.xsl")
            es._xslt = None
            result = es._convert_omml_to_mathml("<m:oMath></m:oMath>")
            assert result == ""

    def test_process_empty_equations(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        es = EquationStandardizer(xsl_path="/fake/omml2mml.xsl")
        doc = MagicMock()
        doc.equations = []
        result = es.process(doc)
        assert result is doc

    def test_process_no_xslt_does_not_crash(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        es = EquationStandardizer(xsl_path="/fake/omml2mml.xsl")
        es._xslt = None
        doc = MagicMock()
        eq = MagicMock()
        eq.omml = "<m:oMath></m:oMath>"
        doc.equations = [eq]
        result = es.process(doc)
        assert result is doc

    def test_get_equation_standardizer_singleton(self):
        with patch("app.pipeline.equations.standardizer.get_or_create") as mock_goc:
            from app.pipeline.equations.standardizer import get_equation_standardizer
            get_equation_standardizer()
            mock_goc.assert_called_once()
