# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

# -*- coding: utf-8 -*-
"""
PromptBuilder -- constructs LLM prompts for each supported document type.

Supported doc_types:
  academic_paper | resume | portfolio | report | thesis
"""
from __future__ import annotations


class PromptBuilder:
    """Builds structured LLM prompts for document generation."""

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def build(self, doc_type: str, metadata: dict, options: dict) -> str:
        builders = {
            "academic_paper": self._academic_paper_prompt,
            "resume":         self._resume_prompt,
            "portfolio":      self._portfolio_prompt,
            "report":         self._report_prompt,
            "thesis":         self._thesis_prompt,
        }
        fn = builders.get(doc_type)
        if fn is None:
            raise ValueError(f"Unsupported doc_type: '{doc_type}'")
        return fn(metadata, options)

    # ------------------------------------------------------------------
    # Shared instruction block
    # ------------------------------------------------------------------
    @staticmethod
    def _json_instruction(block_types: list[str]) -> str:
        types_str = " | ".join(block_types)
        return (
            f"\nReturn ONLY a valid JSON array. No extra text, no markdown prose outside the array.\n"
            f"Each element must follow this exact schema:\n"
            f'{{\n'
            f'  "type": "{types_str}",\n'
            f'  "content": "<text content>",\n'
            f'  "level": 0\n'
            f'}}\n'
            f'("level" is only meaningful for HEADING_1 / HEADING_2 / HEADING_3.)\n'
        )

    # ------------------------------------------------------------------
    # Academic Paper
    # ------------------------------------------------------------------
    def _academic_paper_prompt(self, metadata: dict, options: dict) -> str:
        title      = metadata.get("title", "Untitled Paper")
        authors    = ", ".join(metadata.get("authors", []))
        affil      = metadata.get("affiliation", "")
        abstract   = metadata.get("abstract", "")
        keywords   = ", ".join(metadata.get("keywords", []))
        language   = metadata.get("language", "English")
        sections   = [
            s["name"] for s in metadata.get("sections", []) if s.get("include", True)
        ]
        if not sections:
            sections = ["Introduction", "Methodology", "Results",
                        "Discussion", "Conclusion", "References"]
        placeholder = options.get("include_placeholder_content", True)
        content_instr = (
            "Write 3-5 detailed placeholder paragraphs for every body section."
            if placeholder
            else "Include section headings but leave body paragraphs as single placeholder sentences."
        )
        word_target = options.get("word_count_target", 3000)

        block_types = [
            "TITLE", "AUTHOR_INFO", "AFFILIATION", "ABSTRACT",
            "KEYWORDS", "HEADING_1", "HEADING_2", "BODY",
            "FIGURE_CAPTION", "TABLE_CAPTION", "REFERENCE_ENTRY",
        ]

        return (
            f"You are an expert academic document generator.\n"
            f"Generate a complete, publication-quality academic paper as a JSON array of document blocks.\n\n"
            f"=== Paper Details ===\n"
            f"Title:       {title}\n"
            f"Authors:     {authors}\n"
            f"Affiliation: {affil}\n"
            f"Abstract:    {abstract}\n"
            f"Keywords:    {keywords}\n"
            f"Language:    {language}\n"
            f"Sections:    {', '.join(sections)}\n"
            f"Target words:{word_target}\n\n"
            f"=== Instructions ===\n"
            f"- Start with TITLE, then AUTHOR_INFO, AFFILIATION, ABSTRACT, KEYWORDS blocks.\n"
            f"- Then produce HEADING_1 for each requested section.\n"
            f"- {content_instr}\n"
            f"- End with a HEADING_1 'References' followed by 8-12 REFERENCE_ENTRY blocks "
            f"  formatted as APA-style placeholder citations.\n"
            f"- Use academic English. Do not include any JSON outside the top-level array.\n"
            + self._json_instruction(block_types)
        )

    # ------------------------------------------------------------------
    # Resume / CV
    # ------------------------------------------------------------------
    def _resume_prompt(self, metadata: dict, options: dict) -> str:
        name    = metadata.get("name", "Candidate Name")
        email   = metadata.get("email", "")
        phone   = metadata.get("phone", "")
        linkedin = metadata.get("linkedin", "")
        summary = metadata.get("summary", "")
        skills  = ", ".join(metadata.get("skills", []))
        edu     = metadata.get("education", [])
        exp     = metadata.get("experience", [])
        certs   = ", ".join(metadata.get("certifications", []))

        edu_str = "; ".join(
            f"{e.get('degree','Degree')} at {e.get('institution','Institution')} ({e.get('year','')})"
            for e in edu
        ) if edu else "Not provided"

        exp_str = "; ".join(
            f"{e.get('role','Role')} at {e.get('company','Company')} ({e.get('duration','')})"
            for e in exp
        ) if exp else "Not provided"

        block_types = [
            "TITLE", "CONTACT_INFO", "SUMMARY",
            "HEADING_1", "HEADING_2", "BODY", "BULLET",
        ]

        return (
            f"You are a professional resume writer.\n"
            f"Generate a complete professional resume/CV as a JSON array of document blocks.\n\n"
            f"=== Candidate Details ===\n"
            f"Name:           {name}\n"
            f"Email:          {email}\n"
            f"Phone:          {phone}\n"
            f"LinkedIn:       {linkedin}\n"
            f"Summary:        {summary}\n"
            f"Skills:         {skills}\n"
            f"Education:      {edu_str}\n"
            f"Experience:     {exp_str}\n"
            f"Certifications: {certs}\n\n"
            f"=== Instructions ===\n"
            f"- Start with TITLE (candidate name), then CONTACT_INFO, then SUMMARY.\n"
            f"- Sections in order: Skills, Experience, Education, Certifications, Publications (if applicable).\n"
            f"- Use HEADING_1 for each section, BODY for entries, BULLET for achievements.\n"
            f"- Keep content concise, action-verb-led, professional.\n"
            + self._json_instruction(block_types)
        )

    # ------------------------------------------------------------------
    # Portfolio
    # ------------------------------------------------------------------
    def _portfolio_prompt(self, metadata: dict, options: dict) -> str:
        name    = metadata.get("name", "Researcher Name")
        field   = metadata.get("research_field", "")
        bio     = metadata.get("bio", "")
        projects = metadata.get("projects", [])
        pubs    = metadata.get("publications", [])

        proj_str = "; ".join(
            f"{p.get('title','Project')} ({p.get('year','')}): {p.get('description','')}"
            for p in projects
        ) if projects else "Not provided"

        pub_str = "; ".join(
            f"{p.get('title','Paper')} - {p.get('venue','')}" for p in pubs
        ) if pubs else "Not provided"

        block_types = [
            "TITLE", "AUTHOR_INFO", "ABSTRACT", "HEADING_1",
            "HEADING_2", "BODY", "BULLET", "FIGURE_CAPTION",
        ]

        return (
            f"You are a professional portfolio document writer for researchers.\n"
            f"Generate a comprehensive researcher portfolio as a JSON array of document blocks.\n\n"
            f"=== Portfolio Details ===\n"
            f"Name:           {name}\n"
            f"Research Field: {field}\n"
            f"Bio:            {bio}\n"
            f"Projects:       {proj_str}\n"
            f"Publications:   {pub_str}\n\n"
            f"=== Instructions ===\n"
            f"- Start with TITLE (researcher name + role), AUTHOR_INFO, then ABSTRACT (research statement).\n"
            f"- Include sections: About, Research Interests, Key Projects, Publications, Achievements, Contact.\n"
            f"- Use HEADING_1 for major sections, HEADING_2 for project/paper titles, BODY for descriptions, BULLET for highlights.\n"
            f"- Tone: professional, academic, engaging.\n"
            + self._json_instruction(block_types)
        )

    # ------------------------------------------------------------------
    # Technical Report
    # ------------------------------------------------------------------
    def _report_prompt(self, metadata: dict, options: dict) -> str:
        title     = metadata.get("title", "Technical Report")
        authors   = ", ".join(metadata.get("authors", []))
        org       = metadata.get("organization", "")
        abstract  = metadata.get("abstract", "")
        sections  = [
            s["name"] for s in metadata.get("sections", []) if s.get("include", True)
        ]
        if not sections:
            sections = [
                "Executive Summary", "Introduction", "Background",
                "Methodology", "Findings", "Recommendations", "Conclusion", "References",
            ]
        placeholder = options.get("include_placeholder_content", True)
        content_instr = (
            "Write 2-4 paragraphs of detailed placeholder content per section."
            if placeholder else "Include headings and single-sentence placeholders only."
        )

        block_types = [
            "TITLE", "AUTHOR_INFO", "ABSTRACT", "KEYWORDS",
            "HEADING_1", "HEADING_2", "HEADING_3", "BODY",
            "BULLET", "TABLE_CAPTION", "REFERENCE_ENTRY",
        ]

        return (
            f"You are a professional technical report writer.\n"
            f"Generate a well-structured technical report as a JSON array of document blocks.\n\n"
            f"=== Report Details ===\n"
            f"Title:        {title}\n"
            f"Authors:      {authors}\n"
            f"Organization: {org}\n"
            f"Abstract:     {abstract}\n"
            f"Sections:     {', '.join(sections)}\n\n"
            f"=== Instructions ===\n"
            f"- Start with TITLE, AUTHOR_INFO, then ABSTRACT.\n"
            f"- Use HEADING_1 for each section, HEADING_2 for subsections.\n"
            f"- {content_instr}\n"
            f"- End with a REFERENCE_ENTRY section with 5-8 placeholder references.\n"
            + self._json_instruction(block_types)
        )

    # ------------------------------------------------------------------
    # Thesis Chapter
    # ------------------------------------------------------------------
    def _thesis_prompt(self, metadata: dict, options: dict) -> str:
        title       = metadata.get("title", "Thesis Chapter")
        candidate   = metadata.get("candidate_name", "")
        university  = metadata.get("university", "")
        degree      = metadata.get("degree", "")
        chapter_num = metadata.get("chapter_number", 1)
        chapter_title = metadata.get("chapter_title", "Introduction")
        abstract    = metadata.get("abstract", "")
        sections    = [
            s["name"] for s in metadata.get("sections", []) if s.get("include", True)
        ]
        if not sections:
            sections = [
                "Introduction", "Literature Review",
                "Research Gap", "Objectives", "Summary",
            ]

        block_types = [
            "TITLE", "AUTHOR_INFO", "ABSTRACT", "HEADING_1",
            "HEADING_2", "HEADING_3", "BODY", "BULLET",
            "FIGURE_CAPTION", "TABLE_CAPTION", "REFERENCE_ENTRY",
        ]

        return (
            f"You are a thesis writing assistant.\n"
            f"Generate Chapter {chapter_num} of a thesis as a JSON array of document blocks.\n\n"
            f"=== Thesis Details ===\n"
            f"Full Thesis Title:   {title}\n"
            f"Candidate:          {candidate}\n"
            f"University:         {university}\n"
            f"Degree:             {degree}\n"
            f"Chapter Number:     {chapter_num}\n"
            f"Chapter Title:      {chapter_title}\n"
            f"Research Summary:   {abstract}\n"
            f"Sections:           {', '.join(sections)}\n\n"
            f"=== Instructions ===\n"
            f"- Start with a TITLE block for the chapter title (e.g. 'Chapter {chapter_num}: {chapter_title}').\n"
            f"- Include AUTHOR_INFO and ABSTRACT at the top if chapter_number == 1, otherwise skip.\n"
            f"- Use HEADING_1 for each section, HEADING_2 for subsections.\n"
            f"- Write 3-5 academic paragraphs per section.\n"
            f"- End with 'References' section and 8-10 REFERENCE_ENTRY blocks.\n"
            + self._json_instruction(block_types)
        )
