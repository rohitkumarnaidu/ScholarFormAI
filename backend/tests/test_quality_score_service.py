class TestNormalize:
    def test_lower_strips_and_compacts(self):
        from app.services.quality_score_service import _normalize

        assert _normalize("  Hello   WORLD ") == "hello world"

    def test_none_returns_empty(self):
        from app.services.quality_score_service import _normalize

        assert _normalize(None) == ""

    def test_empty_string(self):
        from app.services.quality_score_service import _normalize

        assert _normalize("") == ""


class TestFlattenAliases:
    def test_flattens_and_sorts(self):
        from app.services.quality_score_service import _flatten_aliases

        result = _flatten_aliases([{"z", "a"}, {"m"}])
        assert result == ["a", "z", "m"]


class TestDisplaySectionName:
    def test_returns_first_alias_capitalized(self):
        from app.services.quality_score_service import _display_section_name

        result = _display_section_name({"work experience", "experience"})
        assert result == "Experience"

    def test_empty_set_returns_section(self):
        from app.services.quality_score_service import _display_section_name

        assert _display_section_name(set()) == "Section"


class TestDedupePreserveOrder:
    def test_removes_duplicates(self):
        from app.services.quality_score_service import _dedupe_preserve_order

        result = _dedupe_preserve_order(["Introduction", "Methods", "Introduction", "Results"])
        assert result == ["Introduction", "Methods", "Results"]

    def test_removes_empty(self):
        from app.services.quality_score_service import _dedupe_preserve_order

        result = _dedupe_preserve_order(["A", "", "B"])
        assert result == ["A", "B"]

    def test_all_empty_returns_empty(self):
        from app.services.quality_score_service import _dedupe_preserve_order

        assert _dedupe_preserve_order(["", " ", None]) == []


class TestInferProviderFromModel:
    def test_groq(self):
        from app.services.quality_score_service import _infer_provider_from_model

        assert _infer_provider_from_model("groq/llama") == "groq"

    def test_nvidia(self):
        from app.services.quality_score_service import _infer_provider_from_model

        assert _infer_provider_from_model("nvidia/llama 3.3 70b") == "nvidia"

    def test_ollama(self):
        from app.services.quality_score_service import _infer_provider_from_model

        assert _infer_provider_from_model("ollama/deepseek-r1") == "ollama"

    def test_deepseek_via_ollama(self):
        from app.services.quality_score_service import _infer_provider_from_model

        assert _infer_provider_from_model("deepseek-coder") == "ollama"

    def test_openai(self):
        from app.services.quality_score_service import _infer_provider_from_model

        assert _infer_provider_from_model("gpt-4o") == "openai"
        assert _infer_provider_from_model("openai/gpt-4") == "openai"

    def test_anthropic(self):
        from app.services.quality_score_service import _infer_provider_from_model

        assert _infer_provider_from_model("claude-3-opus") == "anthropic"
        assert _infer_provider_from_model("anthropic/claude") == "anthropic"

    def test_rule_based(self):
        from app.services.quality_score_service import _infer_provider_from_model

        assert _infer_provider_from_model("rule_based") == "rule_based"
        assert _infer_provider_from_model("rule based system") == "rule_based"

    def test_none_or_empty(self):
        from app.services.quality_score_service import _infer_provider_from_model

        assert _infer_provider_from_model(None) is None
        assert _infer_provider_from_model("") is None

    def test_unknown_returns_none(self):
        from app.services.quality_score_service import _infer_provider_from_model

        assert _infer_provider_from_model("unknown-model") is None


class TestExtractMissingSections:
    def test_extracts_from_errors_and_warnings(self):
        from app.services.quality_score_service import _extract_missing_sections

        result = _extract_missing_sections(
            {
                "errors": ["missing required section: Introduction", "some other error"],
                "warnings": ["missing required section: References"],
            }
        )
        assert result == ["Introduction", "References"]

    def test_empty_results_returns_empty(self):
        from app.services.quality_score_service import _extract_missing_sections

        assert _extract_missing_sections({}) == []

    def test_ignores_non_string_items(self):
        from app.services.quality_score_service import _extract_missing_sections

        result = _extract_missing_sections(
            {
                "errors": [123, "missing required section: Results"],
            }
        )
        assert result == ["Results"]


class TestExtractLLMProvider:
    def test_direct_provider(self):
        from app.services.quality_score_service import _extract_llm_provider

        result = _extract_llm_provider({"llm_provider_used": "openai"})
        assert result == "openai"

    def test_semantic_audit_provider(self):
        from app.services.quality_score_service import _extract_llm_provider

        result = _extract_llm_provider(
            {
                "ai_semantic_audit": {"llm_provider": "anthropic"},
            }
        )
        assert result == "anthropic"

    def test_model_inference(self):
        from app.services.quality_score_service import _extract_llm_provider

        result = _extract_llm_provider(
            {
                "ai_semantic_audit": {"model": "gpt-4o"},
            }
        )
        assert result == "openai"

    def test_none_when_unavailable(self):
        from app.services.quality_score_service import _extract_llm_provider

        assert _extract_llm_provider({}) is None


class TestCollectPresentSections:
    def test_from_metadata_abstract(self):
        from app.services.quality_score_service import _collect_present_sections

        data = {"metadata": {"abstract": "This is the abstract"}}
        result = _collect_present_sections(data)
        assert "abstract" in result

    def test_from_references(self):
        from app.services.quality_score_service import _collect_present_sections

        data = {"references": [{"id": "1"}]}
        result = _collect_present_sections(data)
        assert "references" in result

    def test_from_headings(self):
        from app.services.quality_score_service import _collect_present_sections

        data = {"headings": [{"text": "Introduction"}, {"text": "Methods"}]}
        result = _collect_present_sections(data)
        assert "introduction" in result
        assert "methods" in result

    def test_empty_data(self):
        from app.services.quality_score_service import _collect_present_sections

        assert _collect_present_sections({}) == set()


class TestSectionHasContent:
    def test_abstract_in_metadata(self):
        from app.services.quality_score_service import _section_has_content

        assert _section_has_content({"abstract"}, {"metadata": {"abstract": "Text"}}) is True

    def test_references_in_data(self):
        from app.services.quality_score_service import _section_has_content

        assert _section_has_content({"references"}, {"references": [{"id": "1"}]}) is True

    def test_content_in_blocks(self):
        from app.services.quality_score_service import _section_has_content

        data = {
            "blocks": [
                {"block_type": "text", "section_name": "Introduction", "text": "Some intro text"},
            ]
        }
        assert _section_has_content({"introduction"}, data) is True

    def test_heading_blocks_skipped(self):
        from app.services.quality_score_service import _section_has_content

        data = {
            "blocks": [
                {"block_type": "heading_1", "section_name": "Introduction", "text": "Introduction"},
            ]
        }
        assert _section_has_content({"introduction"}, data) is False

    def test_no_text_returns_false(self):
        from app.services.quality_score_service import _section_has_content

        data = {"blocks": [{"block_type": "text", "section_name": "Methods", "text": ""}]}
        assert _section_has_content({"methods"}, data) is False

    def test_empty_data_returns_false(self):
        from app.services.quality_score_service import _section_has_content

        assert _section_has_content({"abstract"}, {}) is False


class TestComputeQualityScore:
    def test_ieee_full_compliance(self):
        from app.services.quality_score_service import compute_quality_score

        data = {
            "metadata": {"abstract": "An abstract"},
            "references": [{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}, {"id": "5"}],
            "headings": [
                {"text": "Introduction"},
                {"text": "Methods"},
                {"text": "Results"},
                {"text": "Conclusion"},
            ],
            "blocks": [
                {"block_type": "text", "section_name": "Introduction", "text": "Intro text"},
                {"block_type": "text", "section_name": "Methods", "text": "Methods text"},
                {"block_type": "text", "section_name": "Results", "text": "Results text"},
                {"block_type": "text", "section_name": "Conclusion", "text": "Conclusion text"},
            ],
        }
        result = compute_quality_score(data, "ieee", {})
        assert result["template_compliance_pct"] == 100.0
        assert result["content_completeness_pct"] == 100.0
        assert result["citation_count"] == 5
        assert result["overall_score"] == 100.0
        assert result["missing_sections"] == []
        assert result["llm_provider_used"] is None

    def test_ieee_partial_compliance(self):
        from app.services.quality_score_service import compute_quality_score

        data = {
            "metadata": {"abstract": "An abstract"},
            "references": [{"id": "1"}],
            "headings": [{"text": "Introduction"}],
        }
        result = compute_quality_score(data, "ieee", {})
        assert 0 < result["template_compliance_pct"] < 100
        assert result["citation_count"] == 1
        assert "Methods" in result["missing_sections"] or "Methodology" in result["missing_sections"]

    def test_unknown_template_falls_back(self):
        from app.services.quality_score_service import compute_quality_score

        data = {
            "metadata": {"abstract": "Text"},
            "references": [{"id": "1"}],
        }
        result = compute_quality_score(data, "unknown_template", {})
        assert "abstract" in str(result["required_sections"])
        assert "references" in str(result["required_sections"])

    def test_includes_provider(self):
        from app.services.quality_score_service import compute_quality_score

        result = compute_quality_score(
            {},
            "apa",
            {"llm_provider_used": "nvidia"},
        )
        assert result["llm_provider_used"] == "nvidia"

    def test_empty_structured_data(self):
        from app.services.quality_score_service import compute_quality_score

        result = compute_quality_score({}, "ieee", {"citation_target": 5})
        assert result["template_compliance_pct"] == 0.0
        assert result["citation_count"] == 0
