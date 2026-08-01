# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import pytest


@pytest.fixture
def builder():
    from app.pipeline.generation.prompt_builder import PromptBuilder
    return PromptBuilder()


class TestBuild:
    def test_academic_paper(self, builder):
        result = builder.build("academic_paper", {"title": "Test", "authors": ["Alice"]}, {"include_placeholder_content": True})
        assert "academic document generator" in result
        assert "Test" in result

    def test_resume(self, builder):
        result = builder.build("resume", {"name": "Bob", "skills": ["Python"]}, {})
        assert "resume writer" in result
        assert "Bob" in result

    def test_portfolio(self, builder):
        result = builder.build("portfolio", {"name": "Carol", "research_field": "ML"}, {})
        assert "portfolio document writer" in result
        assert "Carol" in result

    def test_report(self, builder):
        result = builder.build("report", {"title": "Tech Report", "organization": "Acme"}, {"include_placeholder_content": False})
        assert "technical report writer" in result
        assert "Tech Report" in result

    def test_thesis(self, builder):
        result = builder.build("thesis", {"title": "My Thesis", "candidate_name": "Dave", "chapter_number": 2}, {})
        assert "thesis writing assistant" in result
        assert "Dave" in result

    def test_unsupported_type_raises(self, builder):
        with pytest.raises(ValueError, match="Unsupported doc_type"):
            builder.build("novel", {}, {})


class TestJsonInstruction:
    def test_single_type(self, builder):
        result = builder._json_instruction(["BODY"])
        assert "BODY" in result
        assert "JSON array" in result

    def test_multiple_types(self, builder):
        result = builder._json_instruction(["TITLE", "HEADING_1", "BODY"])
        assert "TITLE | HEADING_1 | BODY" in result

    def test_contains_schema(self, builder):
        result = builder._json_instruction(["BODY"])
        assert '"type"' in result
        assert '"content"' in result
        assert '"level"' in result


class TestAcademicPaperPrompt:
    def test_all_fields(self, builder):
        meta = {
            "title": "Research Paper",
            "authors": ["Alice", "Bob"],
            "affiliation": "MIT",
            "abstract": "An important study",
            "keywords": ["ml", "ai"],
            "language": "English",
            "sections": [{"name": "Intro", "include": True}, {"name": "Methods", "include": True}],
        }
        result = builder._academic_paper_prompt(meta, {"include_placeholder_content": True, "word_count_target": 4000})
        assert "Research Paper" in result
        assert "Alice, Bob" in result
        assert "MIT" in result
        assert "4000" in result
        assert "Intro, Methods" in result

    def test_empty_sections_defaults(self, builder):
        meta = {"title": "Paper", "sections": []}
        result = builder._academic_paper_prompt(meta, {})
        assert "Introduction" in result

    def test_no_placeholder(self, builder):
        meta = {"title": "Paper", "sections": [{"name": "Intro", "include": True}]}
        result = builder._academic_paper_prompt(meta, {"include_placeholder_content": False})
        assert "single placeholder sentences" in result

    def test_default_word_target(self, builder):
        meta = {"title": "Paper", "sections": []}
        result = builder._academic_paper_prompt(meta, {})
        assert "3000" in result

    def test_missing_fields(self, builder):
        meta = {}
        result = builder._academic_paper_prompt(meta, {})
        assert "Untitled Paper" in result


class TestResumePrompt:
    def test_full_details(self, builder):
        meta = {
            "name": "Alice Smith",
            "email": "alice@example.com",
            "phone": "555-0100",
            "linkedin": "linkedin.com/in/alice",
            "summary": "Experienced researcher",
            "skills": ["Python", "ML"],
            "education": [{"degree": "PhD", "institution": "MIT", "year": "2024"}],
            "experience": [{"role": "Researcher", "company": "Google", "duration": "2020-2024"}],
            "certifications": ["AWS"],
        }
        result = builder._resume_prompt(meta, {})
        assert "Alice Smith" in result
        assert "alice@example.com" in result
        assert "PhD at MIT" in result

    def test_empty_education(self, builder):
        meta = {"name": "Bob", "education": []}
        result = builder._resume_prompt(meta, {})
        assert "Not provided" in result

    def test_empty_experience(self, builder):
        meta = {"name": "Bob", "experience": []}
        result = builder._resume_prompt(meta, {})
        assert "Not provided" in result

    def test_minimal(self, builder):
        meta = {}
        result = builder._resume_prompt(meta, {})
        assert "Candidate Name" in result


class TestPortfolioPrompt:
    def test_full_details(self, builder):
        meta = {
            "name": "Dr. Smith",
            "research_field": "Machine Learning",
            "bio": "Expert in AI",
            "projects": [{"title": "Graphix", "year": "2024", "description": "A graph tool"}],
            "publications": [{"title": "Deep Learning", "venue": "NeurIPS"}],
        }
        result = builder._portfolio_prompt(meta, {})
        assert "Dr. Smith" in result
        assert "Machine Learning" in result
        assert "Graphix" in result
        assert "Deep Learning" in result

    def test_empty_projects(self, builder):
        meta = {"name": "Bob", "projects": []}
        result = builder._portfolio_prompt(meta, {})
        assert "Not provided" in result

    def test_empty_publications(self, builder):
        meta = {"name": "Bob", "publications": []}
        result = builder._portfolio_prompt(meta, {})
        assert "Not provided" in result

    def test_minimal(self, builder):
        meta = {}
        result = builder._portfolio_prompt(meta, {})
        assert "Researcher Name" in result


class TestReportPrompt:
    def test_full_details(self, builder):
        meta = {
            "title": "Annual Report",
            "authors": ["Alice"],
            "organization": "Acme Corp",
            "abstract": "Summary",
            "sections": [{"name": "Executive Summary", "include": True}],
        }
        result = builder._report_prompt(meta, {"include_placeholder_content": True})
        assert "Annual Report" in result
        assert "Acme Corp" in result
        assert "Executive Summary" in result

    def test_empty_sections_defaults(self, builder):
        meta = {"title": "Report", "sections": []}
        result = builder._report_prompt(meta, {"include_placeholder_content": True})
        assert "Executive Summary" in result

    def test_no_placeholder(self, builder):
        meta = {"title": "Report", "sections": [{"name": "Intro", "include": True}]}
        result = builder._report_prompt(meta, {"include_placeholder_content": False})
        assert "single-sentence placeholders" in result

    def test_minimal(self, builder):
        meta = {}
        result = builder._report_prompt(meta, {})
        assert "Technical Report" in result


class TestThesisPrompt:
    def test_full_details(self, builder):
        meta = {
            "title": "PhD Thesis",
            "candidate_name": "Dave",
            "university": "MIT",
            "degree": "PhD",
            "chapter_number": 3,
            "chapter_title": "Methodology",
            "abstract": "This chapter describes methods",
            "sections": [{"name": "Design", "include": True}],
        }
        result = builder._thesis_prompt(meta, {})
        assert "Dave" in result
        assert "MIT" in result
        assert "Chapter 3" in result
        assert "Methodology" in result

    def test_chapter_one_includes_author(self, builder):
        meta = {"chapter_number": 1, "sections": []}
        result = builder._thesis_prompt(meta, {})
        assert "AUTHOR_INFO" in result or "Abstract" in result

    def test_empty_sections_defaults(self, builder):
        meta = {"title": "Thesis", "sections": []}
        result = builder._thesis_prompt(meta, {})
        assert "Literature Review" in result

    def test_minimal(self, builder):
        meta = {}
        result = builder._thesis_prompt(meta, {})
        assert "Thesis Chapter" in result

    def test_chapter_title_included(self, builder):
        meta = {"chapter_number": 2, "chapter_title": "Literature Review", "sections": []}
        result = builder._thesis_prompt(meta, {})
        assert "Chapter 2" in result
        assert "Literature Review" in result
