

class TestAIExplainerInit:
    def test_has_explanation_map(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        explainer = AIExplainer()
        assert "missing_sections" in explainer.explanation_map
        assert "citation_format" in explainer.explanation_map
        assert "figure_captions" in explainer.explanation_map
        assert "reference_completeness" in explainer.explanation_map


class TestExplainResults:
    def test_no_errors_returns_empty(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        explainer = AIExplainer()
        result = explainer.explain_results({"errors": []})
        assert result == []

    def test_missing_section_error(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        explainer = AIExplainer()
        result = explainer.explain_results({
            "errors": ["Missing required section: Methods"]
        }, publisher="IEEE")
        assert len(result) == 1
        assert "missing" in result[0].lower()
        assert "IEEE" in result[0]

    def test_reference_error(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        explainer = AIExplainer()
        result = explainer.explain_results({
            "errors": ["Reference 'Smith2020' missing authors"]
        })
        assert len(result) == 1
        assert "reference" in result[0].lower()

    def test_general_error(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        explainer = AIExplainer()
        result = explainer.explain_results({
            "errors": ["Some random formatting issue"]
        })
        assert len(result) == 1

    def test_dict_errors(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        explainer = AIExplainer()
        result = explainer.explain_results({
            "errors": [{"category": "missing_sections", "message": "Introduction missing"}]
        })
        assert len(result) == 1

    def test_dict_unknown_category(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        explainer = AIExplainer()
        result = explainer.explain_results({
            "errors": [{"category": "unknown_category", "message": "Something went wrong"}]
        })
        assert len(result) == 1

    def test_multiple_errors(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        explainer = AIExplainer()
        result = explainer.explain_results({
            "errors": [
                "Missing required section: Methods",
                "Reference 'Smith2020' missing authors",
                "Figure fig_001 missing caption"
            ]
        })
        assert len(result) == 3

    def test_different_publisher(self):
        from app.pipeline.validation.ai_explainer import AIExplainer
        explainer = AIExplainer()
        result = explainer.explain_results({
            "errors": ["Missing required section: Methods"]
        }, publisher="APA")
        assert "APA" in result[0]
