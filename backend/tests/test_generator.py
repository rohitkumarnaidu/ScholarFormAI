# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

# -*- coding: utf-8 -*-
"""
Backend tests for the Document Generator pipeline.
Tests: PromptBuilder, ContentParser, DocumentGenerator, and the generator router.
"""
from __future__ import annotations

import json
import pytest


# ─── PromptBuilder tests ────────────────────────────────────────────────────

class TestPromptBuilder:
    def setup_method(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        self.pb = PromptBuilder()

    def test_academic_paper_contains_title(self):
        metadata = {
            "title": "Deep Learning for Document Formatting",
            "authors": ["Jane Doe"],
            "abstract": "We present a new method.",
            "sections": [{"name": "Introduction", "include": True}],
        }
        prompt = self.pb.build("academic_paper", metadata, {})
        assert "Deep Learning for Document Formatting" in prompt

    def test_academic_paper_contains_sections(self):
        metadata = {
            "title": "Test",
            "sections": [
                {"name": "Introduction", "include": True},
                {"name": "Methodology", "include": True},
                {"name": "Conclusion", "include": False},
            ],
        }
        prompt = self.pb.build("academic_paper", metadata, {})
        assert "Introduction" in prompt
        assert "Methodology" in prompt
        assert "Conclusion" not in prompt

    def test_resume_contains_candidate_name(self):
        metadata = {"name": "John Smith", "email": "john@example.com", "skills": ["Python"]}
        prompt = self.pb.build("resume", metadata, {})
        assert "John Smith" in prompt

    def test_portfolio_prompt_built(self):
        metadata = {"name": "Dr. Alice", "research_field": "AI", "bio": "AI researcher."}
        prompt = self.pb.build("portfolio", metadata, {})
        assert "Dr. Alice" in prompt
        assert isinstance(prompt, str) and len(prompt) > 100

    def test_report_contains_title(self):
        metadata = {"title": "Annual Security Report", "authors": ["Team A"]}
        prompt = self.pb.build("report", metadata, {})
        assert "Annual Security Report" in prompt

    def test_thesis_contains_chapter_info(self):
        metadata = {
            "title": "PhD Thesis",
            "chapter_number": 2,
            "chapter_title": "Literature Review",
        }
        prompt = self.pb.build("thesis", metadata, {})
        assert "2" in prompt
        assert "Literature Review" in prompt

    def test_invalid_doc_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported doc_type"):
            self.pb.build("invalid_type", {}, {})


# ─── ContentParser tests ─────────────────────────────────────────────────────

class TestContentParser:
    def setup_method(self):
        from app.pipeline.generation.content_parser import ContentParser
        self.cp = ContentParser()

    def test_parse_plain_json(self):
        raw = json.dumps([
            {"type": "TITLE", "content": "My Paper", "level": 0},
            {"type": "BODY", "content": "Introduction text.", "level": 0},
        ])
        blocks = self.cp.parse(raw, "academic_paper")
        assert len(blocks) == 2
        assert blocks[0]["type"] == "TITLE"
        assert blocks[0]["content"] == "My Paper"

    def test_parse_json_with_code_fences(self):
        raw = '```json\n[{"type": "TITLE", "content": "Test Title", "level": 0}]\n```'
        blocks = self.cp.parse(raw, "academic_paper")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "TITLE"

    def test_parse_type_alias_h1(self):
        raw = json.dumps([{"type": "H1", "content": "Introduction", "level": 1}])
        blocks = self.cp.parse(raw, "academic_paper")
        assert blocks[0]["type"] == "HEADING_1"

    def test_parse_unknown_type_falls_back_to_body(self):
        raw = json.dumps([{"type": "UNKNOWN_WEIRD_TYPE", "content": "text", "level": 0}])
        blocks = self.cp.parse(raw, "academic_paper")
        assert blocks[0]["type"] == "BODY"

    def test_parse_empty_content_blocks_kept(self):
        raw = json.dumps([{"type": "BODY", "content": "", "level": 0}])
        blocks = self.cp.parse(raw, "academic_paper")
        assert len(blocks) == 1
        assert blocks[0]["content"] == ""

    def test_parse_malformed_json_raises_value_error(self):
        with pytest.raises(ValueError):
            self.cp.parse("this is not json at all", "academic_paper")

    def test_parse_non_array_json_raises(self):
        with pytest.raises(ValueError):
            self.cp.parse('{"key": "value"}', "academic_paper")


# ─── DocumentGenerator unit tests ────────────────────────────────────────────

class TestDocumentGenerator:
    def setup_method(self):
        from unittest.mock import patch
        from app.pipeline.generation.document_generator import DocumentGenerator
        self._ds_patch = patch("app.pipeline.generation.document_generator.DocumentService")
        self._ds_mock = self._ds_patch.start()
        self._ds_mock.create_document.return_value = {"id": "test"}
        self._ds_mock.get_document.return_value = None
        self._ds_mock.get_document_result.return_value = None
        self._ds_mock.upsert_document_result.return_value = None
        self._supa_patch = patch("app.pipeline.generation.document_generator.get_supabase_client", return_value=None)
        self._supa_patch.start()
        self.dg = DocumentGenerator()

    def teardown_method(self):
        import unittest.mock
        unittest.mock.patch.stopall()

    @pytest.mark.asyncio
    async def test_start_job_returns_uuid(self):
        job_id = await self.dg.start_job(
            doc_type="academic_paper",
            template="ieee",
            metadata={"title": "Test"},
            options={"include_placeholder_content": True},
            user_id="test-user",
        )
        assert isinstance(job_id, str)
        assert len(job_id) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_get_status_for_valid_job(self):
        job_id = await self.dg.start_job(
            doc_type="resume", template="none",
            metadata={"name": "Test User"},
            options={}, user_id="user1",
        )
        status = self.dg.get_status(job_id)
        assert status["job_id"] == job_id
        assert status["status"] in ("pending", "processing", "done", "failed")

    def test_get_status_unknown_job_raises(self):
        with pytest.raises(KeyError, match="not found"):
            self.dg.get_status("non-existent-job-id-xyz")

    def test_rule_based_skeleton_returns_valid_json(self):
        skeleton = self.dg._rule_based_skeleton("academic_paper", {"title": "Fallback Test"})
        blocks = json.loads(skeleton)
        assert isinstance(blocks, list)
        assert len(blocks) >= 2
        assert blocks[0]["type"] == "TITLE"
        assert "Fallback Test" in blocks[0]["content"]


# ─── Router schema validation tests ──────────────────────────────────────────

class TestGeneratorSchemas:
    def test_generate_request_valid(self):
        from app.schemas.document import GenerateRequest, GenerationOptions
        req = GenerateRequest(
            doc_type="academic_paper",
            template="ieee",
            metadata={"title": "Schema Test"},
            options=GenerationOptions(include_placeholder_content=True, word_count_target=2000),
        )
        assert req.doc_type == "academic_paper"
        assert req.options.word_count_target == 2000

    def test_generate_request_defaults(self):
        from app.schemas.document import GenerateRequest
        req = GenerateRequest(
            doc_type="resume",
            template="none",
            metadata={"name": "Jane"},
        )
        assert req.options.include_placeholder_content is True
        assert req.options.word_count_target == 3000

    def test_generate_response_shape(self):
        from app.schemas.document import GenerateResponse
        resp = GenerateResponse(job_id="abc-123", status="pending", message="Queued")
        assert resp.job_id == "abc-123"
        assert resp.status == "pending"
