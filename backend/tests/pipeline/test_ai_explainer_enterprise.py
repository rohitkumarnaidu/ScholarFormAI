# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
import pytest


class TestAIExplainer:
    def test_init(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        exp = AIExplainer()
        assert "missing_sections" in exp.explanation_map
        assert "citation_format" in exp.explanation_map

    def test_empty_errors(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        exp = AIExplainer()
        result = exp.explain_results({"errors": []})
        assert result == []

    def test_missing_sections_error(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        exp = AIExplainer()
        result = exp.explain_results({"errors": ["The document is missing the Introduction section"]})
        assert len(result) == 1
        assert "missing" in result[0].lower()
        assert "IEEE" in result[0]

    def test_reference_error(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        exp = AIExplainer()
        result = exp.explain_results({"errors": ["Reference [1] has no DOI"]})
        assert len(result) == 1
        assert "reference" in result[0].lower()

    def test_custom_publisher(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        exp = AIExplainer()
        result = exp.explain_results({"errors": ["missing sections"]}, publisher="ACM")
        assert "ACM" in result[0]

    def test_dict_error(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        exp = AIExplainer()
        result = exp.explain_results({"errors": [{"category": "figure_captions", "message": "Fig 1 missing caption"}]})
        assert len(result) == 1
        assert "Figures" in result[0]

    def test_dict_error_unknown_category(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        exp = AIExplainer()
        result = exp.explain_results({"errors": [{"category": "unknown_cat", "message": "test"}]})
        assert len(result) == 1

    def test_mixed_errors(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        exp = AIExplainer()
        result = exp.explain_results({
            "errors": [
                "missing Abstract section",
                {"category": "citation_format", "message": "Wrong style"},
            ]
        })
        assert len(result) == 2

    def test_general_error_fallback(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        exp = AIExplainer()
        result = exp.explain_results({"errors": ["Some random formatting issue"]})
        assert len(result) == 1
