# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
from unittest.mock import MagicMock
import pytest


class TestAIExplainer:
    def test_explain_string_errors(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        e = AIExplainer()
        results = e.explain_results({
            "errors": ["missing section: references", "bad reference format"]
        }, publisher="IEEE")
        assert len(results) == 2
        assert "missing" in results[0].lower()
        assert "reference" in results[1].lower()

    def test_explain_dict_errors(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        e = AIExplainer()
        results = e.explain_results({
            "errors": [
                {"category": "missing_sections", "message": "Methods section missing"},
                {"category": "figure_captions", "message": "No captions on figures"}
            ]
        }, publisher="Nature")
        assert len(results) == 2
        assert "Methods" in results[0] or "methods" in results[0]

    def test_explain_unknown_string_category(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        e = AIExplainer()
        results = e.explain_results({
            "errors": ["something unknown happened"]
        })
        assert len(results) == 1
        assert "formatting error" in results[0]

    def test_explain_unknown_dict_category(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        e = AIExplainer()
        results = e.explain_results({
            "errors": [{"category": "unknown_type", "message": "Something broke"}]
        })
        assert len(results) == 1
        assert "formatting error" in results[0]

    def test_no_errors(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        e = AIExplainer()
        results = e.explain_results({"errors": []})
        assert results == []

    def test_publisher_is_used(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        e = AIExplainer()
        results = e.explain_results({
            "errors": ["missing section: conclusion"]
        }, publisher="ACM")
        assert "ACM" in results[0] or "acm" in results[0].lower()
