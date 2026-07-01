import pytest


class TestPromptBuilderBuild:
    def test_academic_paper(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        result = builder.build("academic_paper", {"title": "Test"}, {})
        assert "JSON array" in result
        assert "TITLE" in result
        assert "BODY" in result
        assert "Test" in result

    def test_resume(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        result = builder.build("resume", {"name": "Alice"}, {})
        assert "JSON array" in result
        assert "TITLE" in result
        assert "BULLET" in result
        assert "Alice" in result

    def test_portfolio(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        result = builder.build("portfolio", {"name": "Bob"}, {})
        assert "JSON array" in result
        assert "FIGURE_CAPTION" in result

    def test_report(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        result = builder.build("report", {"title": "Report"}, {})
        assert "Executive Summary" in result
        assert "REFERENCE_ENTRY" in result

    def test_thesis(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        result = builder.build("thesis", {"chapter_number": 1}, {})
        assert "Chapter 1" in result
        assert "HEADING_1" in result

    def test_unsupported_doc_type(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        with pytest.raises(ValueError, match="Unsupported"):
            builder.build("unknown", {}, {})

    def test_academic_with_custom_sections(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        result = builder.build("academic_paper", {
            "title": "ML Paper",
            "authors": ["Alice", "Bob"],
            "sections": [{"name": "Intro", "include": True}],
            "keywords": ["ML"],
        }, {"word_count_target": 5000})
        assert "ML Paper" in result
        assert "Alice, Bob" in result
        assert "Intro" in result

    def test_resume_with_full_details(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        result = builder.build("resume", {
            "name": "Alice",
            "email": "a@b.com",
            "skills": ["Python", "ML"],
            "education": [{"degree": "PhD", "institution": "MIT", "year": "2025"}],
            "experience": [{"role": "Researcher", "company": "Lab", "duration": "3y"}],
        }, {})
        assert "a@b.com" in result
        assert "PhD at MIT" in result
        assert "Researcher at Lab" in result

    def test_report_placeholder_false(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        result = builder.build("report", {}, {"include_placeholder_content": False})
        assert "single-sentence" in result

    def test_thesis_chapter_2(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        result = builder.build("thesis", {
            "chapter_number": 2,
            "chapter_title": "Methods",
        }, {})
        assert "Chapter 2" in result
        assert "headerSlot" not in result  # placeholder only


class TestJsonInstruction:
    def test_single_type(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        result = PromptBuilder._json_instruction(["TITLE"])
        assert "TITLE" in result
        assert "JSON array" in result

    def test_multiple_types(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        result = PromptBuilder._json_instruction(["HEADING_1", "BODY"])
        assert "HEADING_1 | BODY" in result
