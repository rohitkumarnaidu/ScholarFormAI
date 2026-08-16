class TestGetSectionPrompt:
    def test_known_section_returns_correct_prompt(self):
        from app.pipeline.generation.section_prompts import get_section_prompt

        prompt = get_section_prompt(
            "Abstract", {"task_spec": {}, "template_rules": [], "outline": {}, "previous_sections": {}}
        )
        assert "academic abstract" in prompt.lower()
        assert "150-300" in prompt

    def test_unknown_section_returns_default(self):
        from app.pipeline.generation.section_prompts import get_section_prompt

        prompt = get_section_prompt(
            "Custom Section", {"task_spec": {}, "template_rules": [], "outline": {}, "previous_sections": {}}
        )
        assert "rigorous academic section" in prompt.lower()

    def test_includes_task_spec_in_context(self):
        from app.pipeline.generation.section_prompts import get_section_prompt

        prompt = get_section_prompt(
            "Introduction",
            {
                "task_spec": {"title": "My Paper"},
                "template_rules": [],
                "outline": {},
                "previous_sections": {},
            },
        )
        assert "My Paper" in prompt

    def test_includes_template_rules(self):
        from app.pipeline.generation.section_prompts import get_section_prompt

        prompt = get_section_prompt(
            "Methods",
            {
                "task_spec": {},
                "template_rules": [{"rule": "use APA"}],
                "outline": {},
                "previous_sections": {},
            },
        )
        assert "use APA" in prompt

    def test_includes_outline(self):
        from app.pipeline.generation.section_prompts import get_section_prompt

        prompt = get_section_prompt(
            "Results",
            {
                "task_spec": {},
                "template_rules": [],
                "outline": {"sections": [{"title": "Intro"}]},
                "previous_sections": {},
            },
        )
        assert "Intro" in prompt

    def test_previous_sections_included_when_present(self):
        from app.pipeline.generation.section_prompts import get_section_prompt

        prompt = get_section_prompt(
            "Discussion",
            {
                "task_spec": {},
                "template_rules": [],
                "outline": {},
                "previous_sections": {"Introduction": "Some intro text"},
            },
        )
        assert "Introduction" in prompt

    def test_previous_sections_omitted_when_empty(self):
        from app.pipeline.generation.section_prompts import get_section_prompt

        prompt = get_section_prompt(
            "Conclusion",
            {
                "task_spec": {},
                "template_rules": [],
                "outline": {},
                "previous_sections": {},
            },
        )
        assert "previous sections" not in prompt.lower()

    def test_long_previous_section_truncated(self):
        from app.pipeline.generation.section_prompts import get_section_prompt

        long_text = "word " * 2000
        prompt = get_section_prompt(
            "Conclusion",
            {
                "task_spec": {},
                "template_rules": [],
                "outline": {},
                "previous_sections": {"Intro": long_text},
            },
        )
        assert "..." in prompt


class TestSectionPromptsDict:
    def test_has_all_expected_keys(self):
        from app.pipeline.generation.section_prompts import SECTION_PROMPTS

        expected = {"Abstract", "Introduction", "Literature Review", "Methods", "Results", "Discussion", "Conclusion"}
        assert set(SECTION_PROMPTS.keys()) == expected
