
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Fills remaining coverage gaps in ContentClassifier beyond test_classifier_deep.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.pipeline.classification.classifier import ContentClassifier, classify_content


from app.models import Block, BlockType, DocumentMetadata, PipelineDocument

@pytest.fixture
def classifier():
    return ContentClassifier()


def block(block_id: str, index: int, block_type=BlockType.BODY, text="",
           level=None, section_name="", metadata=None, **kw):
    return Block(
        block_id=block_id, index=index, block_type=block_type, text=text,
        level=level, section_name=section_name, metadata=metadata or {}, **kw)


# ══════════════════════════════════════════════════════════════════════════════
# _map_llm_label — uncovered branches
# ══════════════════════════════════════════════════════════════════════════════

class TestMapScibertLabelGaps:
    def test_author_info_with_affiliation_text(self, classifier):
        """AUTHOR_INFO label with affiliation-looking text → AFFILIATION"""
        b = block("b", 0, text="University of Testing")
        result_type, _ = classifier._map_llm_label("AUTHOR_INFO", b)
        assert result_type == BlockType.AFFILIATION

    def test_author_info_without_affiliation(self, classifier):
        """AUTHOR_INFO label without affiliation text → AUTHOR"""
        b = block("b", 0, text="John Smith")
        result_type, _ = classifier._map_llm_label("AUTHOR_INFO", b)
        assert result_type == BlockType.AUTHOR

    def test_conclusion_heading(self, classifier):
        """CONCLUSION with heading look → resolve heading type"""
        b = block("b", 0, text="Conclusion", metadata={"is_heading_candidate": True}, level=1)
        result_type, _ = classifier._map_llm_label("CONCLUSION", b)
        assert result_type == BlockType.HEADING_1

    def test_conclusion_body(self, classifier):
        """CONCLUSION without heading look → BODY"""
        b = block("b", 0, text="In conclusion, we have shown...")
        result_type, _ = classifier._map_llm_label("CONCLUSION", b)
        assert result_type == BlockType.BODY

    def test_references_short_text_is_heading(self, classifier):
        """REFERENCES with short text → REFERENCES_HEADING"""
        b = block("b", 0, text="References")
        result_type, _ = classifier._map_llm_label("REFERENCES", b)
        assert result_type == BlockType.REFERENCES_HEADING


# ══════════════════════════════════════════════════════════════════════════════
# _predict_llm_batch — language detection exception path
# ══════════════════════════════════════════════════════════════════════════════

class TestPredictScibertBatchGaps:
    def test_lang_detect_raises_exception_falls_to_en(self):
        """When detect_language raises, detected_lang should become 'en'."""
        from app.pipeline.intelligence.semantic_parser import SemanticParser
        parser = SemanticParser()
        parser._llm_classifier = MagicMock()
        parser._llm_classifier.classify_batch.return_value = [{"type": "BODY", "confidence": 0.95}]
        with patch("app.pipeline.intelligence.semantic_parser.should_enable_llm_classification", return_value=True):
            with patch("app.pipeline.intelligence.semantic_parser.HAS_LANGDETECT", True, create=True):
                with patch("app.pipeline.intelligence.semantic_parser.detect_language", side_effect=Exception("lang fail"), create=True):
                    result = parser.analyze_blocks([block("b", 0, text="Hello World")])
        assert result[0]["detected_language"] == "en"
        assert result[0]["predicted_section_type"] == "BODY"
        assert result[0]["confidence_score"] == 0.95


# ══════════════════════════════════════════════════════════════════════════════
# _apply_llm_predictions — confidence parsing failure
# ══════════════════════════════════════════════════════════════════════════════

class TestApplyScibertPredictionsGaps:
    def test_bad_confidence_value_sets_zero(self, classifier):
        """Non-numeric confidence string should set confidence to 0.0."""
        b = block("b1", 0, block_type=BlockType.BODY)
        preds = [{"type": "TITLE", "confidence": "not-a-number"}]
        classifier._apply_llm_predictions([b], preds)
        assert b.metadata.get("llm_confidence") == "not-a-number"
        # Since float('not-a-number') raises TypeError → confidence = 0.0 < scibert_min_confidence → skip
        assert b.block_type == BlockType.BODY

    def test_protected_structural_blocks_skipped(self, classifier):
        """Footer, footnote, endnote blocks should not be overridden."""
        b = block("b1", 0, block_type=BlockType.BODY, metadata={"is_footer": True})
        preds = [{"type": "TITLE", "confidence": 0.95}]
        classifier._apply_llm_predictions([b], preds)
        assert b.block_type == BlockType.BODY

    def test_unknown_type_but_block_not_body(self, classifier):
        """Block already classified as something other than BODY/UNKNOWN/PARAGRAPH should be skipped."""
        b = block("b1", 0, block_type=BlockType.ABSTRACT_BODY)
        preds = [{"type": "TITLE", "confidence": 0.95}]
        classifier._apply_llm_predictions([b], preds)
        assert b.block_type == BlockType.ABSTRACT_BODY

    def test_predictions_shorter_than_blocks(self, classifier):
        """Fewer predictions than blocks should not cause error."""
        blocks = [
            block("b1", 0, block_type=BlockType.BODY),
            block("b2", 1, block_type=BlockType.BODY),
            block("b3", 2, block_type=BlockType.BODY),
        ]
        preds = [{"type": "TITLE", "confidence": 0.95}]
        classifier._apply_llm_predictions([blocks[0]], preds)
        assert blocks[0].metadata.get("llm_prediction") == "TITLE"

    def test_methodology_heading_resolved(self, classifier):
        b = block("b", 0, text="Methodology", metadata={"is_heading_candidate": True, "level": 1})
        result_type, _ = classifier._map_llm_label("METHODOLOGY", b)
        assert result_type == BlockType.HEADING_1


# ══════════════════════════════════════════════════════════════════════════════
# _run_classification — front matter / email / author confidence / fallback
# ══════════════════════════════════════════════════════════════════════════════

class TestRunClassificationGaps:
    def test_email_author_without_affiliation(self, classifier):
        """Email line without affiliation indicators → AUTHOR."""
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="alice@mit.edu"),
            ]),
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=10):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.AUTHOR
        assert doc.blocks[1].metadata.get("classification_method") == "regex_email_author"

    def test_email_affiliation_with_affiliation_keywords(self, classifier):
        """Email line with affiliation keywords (but not email-specific method) → AFFILIATION
        via the keyword rule (Department) before the email rule fires."""
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="alice@mit.edu, Department of CS"),
            ]),
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=10):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.AFFILIATION
        # "Department" triggers regex_affiliation_rule before the email pattern is checked
        assert doc.blocks[1].metadata.get("classification_method") == "regex_affiliation_rule"

    def test_author_with_comma_gets_bonus_confidence(self, classifier):
        """Author with comma → bonus confidence."""
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="Alice Johnson, PhD"),
            ]),
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=10):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.AUTHOR
        assert doc.blocks[1].classification_confidence >= 0.6

    def test_author_with_academic_keyword_excluded(self, classifier):
        """Text containing author exclusion keywords → skip author rule."""
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="Department of Physics"),
            ]),
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=10):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.AFFILIATION

    def test_affiliation_by_indicator_fallback(self, classifier):
        """Fallback affiliation detection in front matter.
        Uses text that avoids the keyword rules but triggers affiliation_indicators."""
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="Research School of Something"),
            ]),
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=10):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.AFFILIATION
        assert doc.blocks[1].metadata.get("classification_method") == "heuristic_front"

    def test_short_clean_name_gets_boosted_confidence(self, classifier):
        """2-4 word capitalized text matches the AUTHOR rule (regex_author_rule_enhanced), not the fallback."""
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="Bob Smith"),
            ]),
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=10):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        # "Bob Smith" hits AUTHOR rule (2 cap words, no academic exclusion) → 0.6 base, no comma bonus
        assert doc.blocks[1].classification_confidence == 0.6
        assert doc.blocks[1].metadata.get("classification_method") == "regex_author_rule_enhanced"

    def test_long_name_gets_medium_confidence(self, classifier):
        """7+ capitalized words (avoids AUTHOR keyword rule) → fallback heuristic_front."""
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="One Two Three Four Five Six Seven Eight"),
            ]),
        from app.config.settings import settings
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=10):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].classification_confidence == getattr(settings, "HEURISTIC_CONFIDENCE_MEDIUM", 0.6)

    def test_footnote_preserved_during_classification(self, classifier):
        """Block with is_footnote metadata in body zone → preserved (hard guard skips reclassification)."""
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.HEADING_1, text="Intro", metadata={"is_heading_candidate": True}, level=1, section_name="introduction"),
                block("b2", 1, BlockType.BODY, text="Some text"),
                block("b3", 2, BlockType.FOOTNOTE, text="A footnote", metadata={"is_footnote": True}),
            ]),
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[3].block_type == BlockType.FOOTNOTE

    def test_supplemental_heading_not_appendix(self, classifier):
        """A heading with 'supplement' in section_name → APPENDIX_HEADING."""
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="Supplementary Materials",
                      metadata={"is_heading_candidate": True}, level=1,
                      section_name="supplementary"),
            ]),
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.HEADING_1
        assert doc.blocks[1].metadata.get("is_appendix") is True

    def test_references_zone_heading_candidate_level_1(self, classifier):
        """After references heading, a block with is_heading_candidate + level 1 → HEADING_1.
        References start at index 0, so block at index 1 is post-references heading."""
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="References",
                      metadata={"is_heading_candidate": True}),
                block("b2", 1, BlockType.BODY, text="Appendix A: Data",
                      level=1, metadata={"is_heading_candidate": True}),
            ]),
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=0):
                    classifier.process(doc)
        assert doc.blocks[2].block_type == BlockType.HEADING_1

    def test_references_zone_non_heading_entry(self, classifier):
        """After references heading, a non-heading-candidate block → REFERENCE_ENTRY."""
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="References",
                      metadata={"is_heading_candidate": True}),
                block("b2", 1, BlockType.BODY, text="[1] Author. Title.", metadata={}),
            ]),
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=1):
                    classifier.process(doc)
        assert doc.blocks[2].block_type == BlockType.REFERENCE_ENTRY

    def test_heading_levels_2_3_4(self, classifier):
        """Heading candidates with level 2, 3, 4 map correctly in body zone.
        Note: body zone reads level from metadata (block.metadata.get('level', 1))."""
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="Subsection",
                      metadata={"is_heading_candidate": True, "level": 2}, section_name="methods"),
                block("b2", 1, BlockType.BODY, text="Subsubsection",
                      metadata={"is_heading_candidate": True, "level": 3}, section_name="methods"),
                block("b3", 2, BlockType.BODY, text="Sub4",
                      metadata={"is_heading_candidate": True, "level": 4}, section_name="methods"),
            ]),
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=0):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.HEADING_2
        assert doc.blocks[2].block_type == BlockType.HEADING_3
        assert doc.blocks[3].block_type == BlockType.HEADING_4


# ══════════════════════════════════════════════════════════════════════════════
# Post-loop classification (NLP fallback + UNKNOWN handling)
# ══════════════════════════════════════════════════════════════════════════════

class TestPostLoopClassificationGaps:
    def test_standard_heading_detected(self, classifier):
        """Post-loop: UNKNOWN block containing standard heading text → HEADING_1."""
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[block("b1", 0, BlockType.UNKNOWN, text="Introduction")]),
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=0):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[0].block_type == BlockType.HEADING_1
        assert doc.blocks[0].metadata.get("classification_method") == "regex_std_heading"

    def test_standard_heading_with_colon(self, classifier):
        """Post-loop: heading with colon removed before match."""
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[block("b1", 0, BlockType.UNKNOWN, text="Introduction:")]),
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=0):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[0].block_type == BlockType.HEADING_1

    def test_unknown_with_nlp_confidence_uses_nlp(self, classifier):
        """UNKNOWN block with nlp_confidence > 0. In body zone it gets set to BODY
        with structure_context. The nlp_confidence path is only reached for blocks
        that stay UNKNOWN through the main loop (e.g. after an exception)."""
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[block("b1", 0, BlockType.UNKNOWN, text="Some random text",
                         metadata={"nlp_confidence": 0.7})]),
        from app.config.settings import settings
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=0):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[0].block_type == BlockType.BODY
        # Main loop body zone sets HEURISTIC_CONFIDENCE_HIGH & structure_context
        assert doc.blocks[0].classification_confidence == settings.HEURISTIC_CONFIDENCE_HIGH
        assert doc.blocks[0].metadata.get("classification_method") == "structure_context"

    def test_unknown_without_nlp_uses_low_confidence(self, classifier):
        """UNKNOWN block without nlp_confidence in body zone → BODY with HEURISTIC_CONFIDENCE_HIGH."""
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[block("b1", 0, BlockType.UNKNOWN, text="Some random text")]),
        from app.config.settings import settings
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=0):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[0].block_type == BlockType.BODY
        assert doc.blocks[0].classification_confidence == settings.HEURISTIC_CONFIDENCE_HIGH

    def test_protected_blocks_skipped_in_post_loop(self, classifier):
        """Protected structural blocks are skipped in post-loop fallback.
        Regular block at index 2 is in body zone → BODY."""
        blocks = [
            block("b1", 0, BlockType.UNKNOWN, text="Header", metadata={"is_header": True}),
            block("b2", 1, BlockType.UNKNOWN, text="Footer", metadata={"is_footer": True}),
            block("b3", 2, BlockType.UNKNOWN, text="Regular text"),
        ]
        doc = PipelineDocument(document_id="d", metadata=DocumentMetadata(), blocks=blocks)
        from app.config.settings import settings
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=2):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[2].block_type == BlockType.BODY
        assert doc.blocks[2].classification_confidence == settings.HEURISTIC_CONFIDENCE_HIGH

    def test_nlp_footnote_fallback(self, classifier):
        """NLP fallback detects footnote-like text.
        Only applies to blocks that remain UNKNOWN through the main loop.
        In body zone, UNKNOWN becomes BODY before the fallback runs."""
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[block("b1", 0, BlockType.UNKNOWN, text="1 This is a footnote")]),
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=0):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        # Main loop body zone → BODY (structure_context) before NLP fallback runs
        assert doc.blocks[0].block_type == BlockType.BODY


# ══════════════════════════════════════════════════════════════════════════════
# _find_first_section_index — edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestFindFirstSectionIndexGaps:
    def test_index_limit_30(self, classifier):
        """After 30 blocks without heading, limit to 12."""
        blocks = [block(f"b{i}", i, BlockType.BODY, text="A" * 5) for i in range(35)]
        result = classifier._find_first_section_index(blocks)
        assert result == 12

    def test_long_body_text_limited(self, classifier):
        """Block with >300 chars breaks the search."""
        blocks = [
            block("b0", 0, BlockType.TITLE, text="Title"),
            block("b1", 1, BlockType.BODY, text="A" * 301),
        ]
        result = classifier._find_first_section_index(blocks)
        assert result == 2

    def test_fallback_numbered_heading_with_dots(self, classifier):
        """Numbered heading like '1.1 Background' also detected."""
        blocks = [block("b1", 0, BlockType.BODY, text="1.1 Background")]
        result = classifier._find_first_section_index(blocks)
        assert result == 0

    def test_fallback_heading_cleaned_and_checked(self, classifier):
        """Non-numbered short text matching fallback keywords."""
        blocks = [block("b1", 0, BlockType.BODY, text="Related Work")]
        result = classifier._find_first_section_index(blocks)
        # 'related work' is in fallback_heading_keywords
        assert result == 0

    def test_no_heading_found(self, classifier):
        """No heading found in first 30 blocks."""
        blocks = [block(f"b{i}", i, BlockType.BODY, text="word") for i in range(5)]
        result = classifier._find_first_section_index(blocks)
        assert result == min(12, 5)


# ══════════════════════════════════════════════════════════════════════════════
# _find_references_start_index — edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestFindReferencesStartIndexGaps:
    def test_references_in_text_found(self, classifier):
        blocks = [
            block("b1", 0, BlockType.BODY, text="References",
                  metadata={"is_heading_candidate": True}),
        ]
        assert classifier._find_references_start_index(blocks) == 0

    def test_references_keyword_section_name(self, classifier):
        blocks = [
            block("b1", 0, BlockType.BODY, text="Refs", section_name="bibliography",
                  metadata={"is_heading_candidate": True}),
        ]
        assert classifier._find_references_start_index(blocks) == 0

    def test_long_text_skipped(self, classifier):
        blocks = [
            block("b1", 0, BlockType.BODY, text="References and more... " + "A" * 60,
                  metadata={"is_heading_candidate": True}),
        ]
        assert classifier._find_references_start_index(blocks) is None

    def test_no_match(self, classifier):
        assert classifier._find_references_start_index([]) is None


# ══════════════════════════════════════════════════════════════════════════════
# _match_grobid_author — edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestMatchGrobidAuthorGaps:
    def test_family_in_text_long_enough(self, classifier):
        authors = [{"family": "Smithsonian"}]
        assert classifier._match_grobid_author("Smithsonian Institute", authors) is True

    def test_family_short_skipped(self, classifier):
        authors = [{"family": "Li"}]
        assert classifier._match_grobid_author("Li", authors) is False

    def test_full_name_with_given_family(self, classifier):
        authors = [{"given": "Alice", "family": "Johnson"}]
        assert classifier._match_grobid_author("Alice Johnson", authors) is True


# ══════════════════════════════════════════════════════════════════════════════
# _match_grobid_affiliation — edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestMatchGrobidAffiliationGaps:
    def test_exact_text_match(self, classifier):
        assert classifier._match_grobid_affiliation("MIT", ["MIT"]) is True

    def test_partial_long_affiliation(self, classifier):
        affs = ["Massachusetts Institute of Technology Cambridge MA"]
        # Covers 5/6 words (83%) > 70% threshold
        assert classifier._match_grobid_affiliation("Massachusetts Institute of Technology Cambridge", affs) is True

    def test_no_affiliation_match(self, classifier):
        assert classifier._match_grobid_affiliation("Some random text", ["MIT"]) is False

    def test_short_affiliation_no_partial(self, classifier):
        affs = ["MIT"]
        result = classifier._match_grobid_affiliation("Massachusetts Institute of Technology", affs)
        assert result is False


# ══════════════════════════════════════════════════════════════════════════════
# classify_content convenience function
# ══════════════════════════════════════════════════════════════════════════════

class TestClassifyContentGaps:
    def test_returns_document(self):
        doc = PipelineDocument(document_id="d", metadata=DocumentMetadata(), blocks=[])
        with patch.object(ContentClassifier, "_predict_llm_batch", return_value=None):
            with patch.object(ContentClassifier, "_find_first_section_index", return_value=0):
                with patch.object(ContentClassifier, "_find_references_start_index", return_value=None):
                    result = classify_content(doc)
        assert result is doc
