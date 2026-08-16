# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Covers ALL remaining uncovered lines in ContentClassifier (target: 100%).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.models import Block, BlockType, DocumentMetadata, PipelineDocument
from app.pipeline.classification.classifier import ContentClassifier


@pytest.fixture
def classifier():
    return ContentClassifier()


def block(
    block_id: str, index: int, block_type=BlockType.BODY, text="", level=None, section_name="", metadata=None, **kw
):
    return Block(
        block_id=block_id,
        index=index,
        block_type=block_type,
        text=text,
        level=level,
        section_name=section_name,
        metadata=metadata or {},
        **kw,
    )


# ══════════════════════════════════════════════════════════════════════════════
# _looks_like_heading — line 85
# ══════════════════════════════════════════════════════════════════════════════


class TestLooksLikeHeadingGaps:
    def test_long_text_ending_with_colon(self, classifier):
        """Text >80 chars and ending with a colon is considered a heading."""
        b = block("b", 0, text="A" * 81 + ":")
        assert classifier._looks_like_heading(b) is True


# ══════════════════════════════════════════════════════════════════════════════
# _resolve_heading_type — lines 95, 97, 99
# ══════════════════════════════════════════════════════════════════════════════


class TestResolveHeadingTypeGaps:
    @pytest.mark.parametrize(
        "level,expected",
        [
            (2, BlockType.HEADING_2),
            (3, BlockType.HEADING_3),
            (4, BlockType.HEADING_4),
        ],
    )
    def test_level_mapping(self, classifier, level, expected):
        """Each heading level maps to the correct BlockType."""
        b = block("b", 0, metadata={"level": level}, level=level)
        result_type, _ = classifier._resolve_heading_type(b)
        assert result_type == expected


# ══════════════════════════════════════════════════════════════════════════════
# _map_llm_label — lines 113-115, 119, 121, 123, 125, 127, 133-139
# ══════════════════════════════════════════════════════════════════════════════


class TestMapScibertLabelRemainingGaps:
    def test_abstract_heading(self, classifier):
        """ABSTRACT when text equals 'abstract' → ABSTRACT_HEADING."""
        b = block("b", 0, text="abstract")
        result_type, _ = classifier._map_llm_label("ABSTRACT", b)
        assert result_type == BlockType.ABSTRACT_HEADING

    def test_abstract_body(self, classifier):
        """ABSTRACT with non-heading non-abstract text → ABSTRACT_BODY."""
        b = block("b", 0, text="This study investigates...")
        result_type, _ = classifier._map_llm_label("ABSTRACT", b)
        assert result_type == BlockType.ABSTRACT_BODY

    def test_references_long_text(self, classifier):
        """REFERENCES with long non-heading text → REFERENCE_ENTRY."""
        b = block("b", 0, text="a" * 50)
        result_type, _ = classifier._map_llm_label("REFERENCES", b)
        assert result_type == BlockType.REFERENCE_ENTRY

    def test_figure_caption_label(self, classifier):
        """FIGURE_CAPTION label maps directly."""
        b = block("b", 0)
        result_type, _ = classifier._map_llm_label("FIGURE_CAPTION", b)
        assert result_type == BlockType.FIGURE_CAPTION

    def test_table_caption_label(self, classifier):
        """TABLE_CAPTION label maps directly."""
        b = block("b", 0)
        result_type, _ = classifier._map_llm_label("TABLE_CAPTION", b)
        assert result_type == BlockType.TABLE_CAPTION

    def test_acknowledgements_label(self, classifier):
        """ACKNOWLEDGEMENTS label maps directly."""
        b = block("b", 0)
        result_type, _ = classifier._map_llm_label("ACKNOWLEDGEMENTS", b)
        assert result_type == BlockType.ACKNOWLEDGEMENTS

    def test_equation_label(self, classifier):
        """EQUATION label maps directly."""
        b = block("b", 0)
        result_type, _ = classifier._map_llm_label("EQUATION", b)
        assert result_type == BlockType.EQUATION

    def test_heading_label(self, classifier):
        """HEADING label delegates to _resolve_heading_type."""
        b = block("b", 0, metadata={"level": 2}, level=2)
        result_type, _ = classifier._map_llm_label("HEADING", b)
        assert result_type == BlockType.HEADING_2

    def test_body_label(self, classifier):
        """BODY label maps directly."""
        b = block("b", 0)
        result_type, _ = classifier._map_llm_label("BODY", b)
        assert result_type == BlockType.BODY

    def test_default_fallback(self, classifier):
        """Unrecognised label falls back to BODY."""
        b = block("b", 0)
        result_type, _ = classifier._map_llm_label("SOME_UNKNOWN_LABEL", b)
        assert result_type == BlockType.BODY


# ══════════════════════════════════════════════════════════════════════════════
# _predict_llm_batch — lines 143, 145, 155->169, 157->168, 175-177
# ══════════════════════════════════════════════════════════════════════════════


class TestPredictScibertBatchRemainingGaps:
    def test_scibert_disabled(self, classifier):
        """When SciBERT is disabled, return None."""
        with patch("app.pipeline.classification.classifier.should_enable_llm_classification", return_value=False):
            result = classifier._predict_llm_batch([block("b", 0)])
        assert result is None

    def test_empty_blocks_list(self, classifier):
        """When blocks list is empty and SciBERT enabled, return []."""
        with patch("app.pipeline.classification.classifier.should_enable_llm_classification", return_value=True):
            result = classifier._predict_llm_batch([])
        assert result == []

    def test_exception_during_inference(self, classifier):
        """Exception during model inference is caught and returns None."""
        with patch("app.pipeline.classification.classifier.should_enable_llm_classification", return_value=True):
            with patch("app.pipeline.classification.classifier.get_llm_classifier") as mock_get_llm:
                mock_llm = MagicMock()
                mock_llm.classify_batch.side_effect = Exception("Model error")
                mock_get_llm.return_value = mock_llm
                result = classifier._predict_llm_batch([block("b", 0, text="hello")])
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# _apply_llm_predictions — lines 190, 193->188, 200, 204, 228
# ══════════════════════════════════════════════════════════════════════════════


class TestApplyScibertPredictionsRemainingGaps:
    def test_first_loop_break(self, classifier):
        """First loop breaks when predictions are shorter than blocks."""
        blocks = [block("b1", 0), block("b2", 1)]
        preds = [{"type": "TITLE", "confidence": 0.95}]
        classifier._apply_llm_predictions(blocks, preds)
        assert blocks[0].metadata.get("llm_prediction") == "TITLE"

    def test_falsy_label_in_first_loop(self, classifier):
        """Falsy label in first loop skips metadata persistence."""
        b = block("b1", 0)
        classifier._apply_llm_predictions([b], [{"type": None}])
        assert "llm_prediction" not in b.metadata

    def test_second_loop_break(self, classifier):
        """Second loop breaks when predictions are shorter than blocks."""
        blocks = [block("b1", 0, block_type=BlockType.BODY), block("b2", 1)]
        preds = [{"type": "TITLE", "confidence": 0.95}]
        classifier._apply_llm_predictions(blocks, preds)
        assert blocks[1].block_type == BlockType.BODY

    def test_no_label_continue(self, classifier):
        """Second loop skips when label is missing."""
        b = block("b1", 0, block_type=BlockType.BODY)
        classifier._apply_llm_predictions([b], [{"type": None, "confidence": 0.95}])
        assert b.block_type == BlockType.BODY

    def test_same_body_type_skip(self, classifier):
        """Skip override when mapped type is BODY and block is already BODY."""
        b = block("b1", 0, block_type=BlockType.BODY)
        classifier._apply_llm_predictions([b], [{"type": "BODY", "confidence": 0.95}])
        assert b.block_type == BlockType.BODY


# ══════════════════════════════════════════════════════════════════════════════
# process — lines 254-261
# ══════════════════════════════════════════════════════════════════════════════


class TestProcessGaps:
    def test_process_exception_recovery(self, classifier):
        """Exception in _run_classification is caught, stage is recorded as error."""
        doc = PipelineDocument(document_id="d", metadata=DocumentMetadata(), blocks=[])
        with patch.object(classifier, "_run_classification", side_effect=ValueError("simulated failure")):
            result = classifier.process(doc)
        assert result is doc
        assert result.processing_history[-1].status == "error"


# ══════════════════════════════════════════════════════════════════════════════
# _run_classification — lines 302, 335-342, 356-377, 419-422, 445-446,
#                       486-489, 491-494, 497-509, 542-545, 548-550, 552-554,
#                       563-564
# ══════════════════════════════════════════════════════════════════════════════


class TestRunClassificationRemainingGaps:
    def test_empty_text_continue(self, classifier):
        """Block with empty text is skipped (stays UNKNOWN)."""
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(), blocks=[block("b0", 0, BlockType.UNKNOWN, text="")]
        )
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=0):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[0].block_type == BlockType.UNKNOWN

    def test_grobid_title_classification(self, classifier):
        """Front-matter block matching GROBID title gets GROBID classification."""
        doc = PipelineDocument(
            document_id="d",
            metadata=DocumentMetadata(ai_hints={"grobid_metadata": {"title": "My Paper", "confidence": 0.95}}),
            blocks=[block("b0", 0, BlockType.BODY, text="My Paper")],
        )
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=10):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[0].block_type == BlockType.TITLE
        assert doc.blocks[0].metadata.get("classification_method") == "grobid_title"

    def test_grobid_author_classification(self, classifier):
        """Front-matter block matching GROBID author gets AUTHOR type."""
        doc = PipelineDocument(
            document_id="d",
            metadata=DocumentMetadata(
                ai_hints={
                    "grobid_metadata": {"authors": [{"full_name": "John Smith"}], "confidence": 0.9},
                }
            ),
            blocks=[
                block("b0", 0, BlockType.TITLE, text="Title"),
                block("b1", 1, BlockType.BODY, text="John Smith"),
            ],
        )
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=10):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.AUTHOR
        assert doc.blocks[1].metadata.get("classification_method") == "grobid_author"

    def test_grobid_affiliation_classification(self, classifier):
        """Front-matter block matching GROBID affiliation gets AFFILIATION type."""
        doc = PipelineDocument(
            document_id="d",
            metadata=DocumentMetadata(
                ai_hints={
                    "grobid_metadata": {
                        "authors": [{"full_name": "Jane Doe"}],
                        "affiliations": ["MIT University"],
                        "confidence": 0.9,
                    },
                }
            ),
            blocks=[
                block("b0", 0, BlockType.TITLE, text="Title"),
                block("b1", 1, BlockType.BODY, text="MIT University"),
            ],
        )
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=10):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.AFFILIATION
        assert doc.blocks[1].metadata.get("classification_method") == "grobid_affiliation"

    def test_email_with_affiliation(self, classifier):
        """Email line with affiliation indicator text → AFFILIATION via email rule."""
        doc = PipelineDocument(
            document_id="d",
            metadata=DocumentMetadata(),
            blocks=[
                block("b0", 0, BlockType.TITLE, text="Title"),
                block("b1", 1, BlockType.BODY, text="alice@school.edu"),
            ],
        )
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=10):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.AFFILIATION
        assert doc.blocks[1].metadata.get("classification_method") == "regex_email_affiliation"

    def test_short_name_fallback_confidence(self, classifier):
        """Short istitle name (1-4 words) in fallback gets boosted confidence."""
        doc = PipelineDocument(
            document_id="d",
            metadata=DocumentMetadata(),
            blocks=[
                block("b0", 0, BlockType.TITLE, text="Title"),
                block("b1", 1, BlockType.BODY, text="Testing"),
            ],
        )
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=10):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].classification_confidence == 0.75
        assert doc.blocks[1].metadata.get("classification_method") == "heuristic_front_name_likely"

    def test_abstract_heading_in_body_zone(self, classifier):
        """Heading with 'abstract' in section_name → ABSTRACT_HEADING."""
        doc = PipelineDocument(
            document_id="d",
            metadata=DocumentMetadata(),
            blocks=[
                block("b0", 0, BlockType.TITLE, text="Title"),
                block(
                    "b1",
                    1,
                    BlockType.BODY,
                    text="Abstract",
                    metadata={"is_heading_candidate": True},
                    level=1,
                    section_name="abstract",
                ),
            ],
        )
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.ABSTRACT_HEADING

    def test_keywords_heading_in_body_zone(self, classifier):
        """Heading with 'key words' in section_name → KEYWORDS_HEADING."""
        doc = PipelineDocument(
            document_id="d",
            metadata=DocumentMetadata(),
            blocks=[
                block("b0", 0, BlockType.TITLE, text="Title"),
                block(
                    "b1",
                    1,
                    BlockType.BODY,
                    text="Keywords",
                    metadata={"is_heading_candidate": True},
                    level=1,
                    section_name="key words",
                ),
            ],
        )
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.KEYWORDS_HEADING

    @pytest.mark.parametrize(
        "section,text,expected_type,expected_intent",
        [
            ("acknowledgements", "Funding provided by NSF", BlockType.FUNDING, "FUNDING"),
            ("acknowledgements", "No conflict of interest", BlockType.CONFLICT_OF_INTEREST, "CONFLICT_OF_INTEREST"),
            ("acknowledgements", "We thank our colleagues", BlockType.ACKNOWLEDGEMENTS, "ACKNOWLEDGEMENTS"),
        ],
    )
    def test_acknowledgements_heading_types(self, classifier, section, text, expected_type, expected_intent):
        """Acknowledgements heading text triggers FUNDING / CONFLICT_OF_INTEREST / ACKNOWLEDGEMENTS."""
        doc = PipelineDocument(
            document_id="d",
            metadata=DocumentMetadata(),
            blocks=[
                block("b0", 0, BlockType.TITLE, text="Title"),
                block(
                    "b1",
                    1,
                    BlockType.BODY,
                    text=text,
                    metadata={"is_heading_candidate": True},
                    level=1,
                    section_name=section,
                ),
            ],
        )
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == expected_type
        assert doc.blocks[1].semantic_intent == expected_intent

    def test_footnote_propagation_in_body_zone(self, classifier):
        """Block with is_footnote metadata in body zone → FOOTNOTE type."""

        class FickleMeta:
            def __init__(self):
                self._store = {}
                self._fc = 0

            def get(self, key, default=None):
                if key == "is_footnote":
                    self._fc += 1
                    if self._fc == 1:
                        return None
                    return True
                return self._store.get(key, default)

            def __getitem__(self, key):
                return self._store[key]

            def __setitem__(self, key, value):
                self._store[key] = value

            def __contains__(self, key):
                return key in self._store

        b2 = block("b2", 2, BlockType.BODY, text="footnote text", metadata={})
        b2.metadata = FickleMeta()
        doc = PipelineDocument(
            document_id="d",
            metadata=DocumentMetadata(),
            blocks=[
                block("b0", 0, BlockType.TITLE, text="Title"),
                block(
                    "b1",
                    1,
                    BlockType.BODY,
                    text="Intro",
                    metadata={"is_heading_candidate": True},
                    level=1,
                    section_name="introduction",
                ),
                b2,
            ],
        )
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[2].block_type == BlockType.FOOTNOTE

    def test_abstract_body_section(self, classifier):
        """Non-heading block after abstract heading → ABSTRACT_BODY."""
        doc = PipelineDocument(
            document_id="d",
            metadata=DocumentMetadata(),
            blocks=[
                block("b0", 0, BlockType.TITLE, text="Title"),
                block(
                    "b1",
                    1,
                    BlockType.BODY,
                    text="Abstract",
                    metadata={"is_heading_candidate": True},
                    level=1,
                    section_name="abstract",
                ),
                block("b2", 2, BlockType.BODY, text="This is the abstract"),
            ],
        )
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[2].block_type == BlockType.ABSTRACT_BODY
        assert doc.blocks[2].semantic_intent == "ABSTRACT_BODY"

    def test_keywords_body_section(self, classifier):
        """Non-heading block after keywords heading → KEYWORDS_BODY."""
        doc = PipelineDocument(
            document_id="d",
            metadata=DocumentMetadata(),
            blocks=[
                block("b0", 0, BlockType.TITLE, text="Title"),
                block(
                    "b1",
                    1,
                    BlockType.BODY,
                    text="Keywords",
                    metadata={"is_heading_candidate": True},
                    level=1,
                    section_name="key words",
                ),
                block("b2", 2, BlockType.BODY, text="kw1, kw2"),
            ],
        )
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[2].block_type == BlockType.KEYWORDS_BODY
        assert doc.blocks[2].semantic_intent == "KEYWORDS_BODY"

    def test_main_loop_exception_handling(self, classifier):
        """Exception in main loop is caught; block stays UNKNOWN then handled by post-loop."""
        blocks = [
            block(
                "b0",
                0,
                BlockType.BODY,
                text="Introduction",
                metadata={"is_heading_candidate": True},
                level=1,
                section_name="introduction",
            ),
            block(
                "b1",
                1,
                BlockType.UNKNOWN,
                text="some text",
                metadata={"is_heading_candidate": True, "level": 1},
                section_name="test",
            ),
        ]
        object.__setattr__(blocks[1], "section_name", 123)
        doc = PipelineDocument(document_id="d", metadata=DocumentMetadata(), blocks=blocks)
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=0):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.BODY


# ══════════════════════════════════════════════════════════════════════════════
# Post-loop inline — lines 587, 611-628
# ══════════════════════════════════════════════════════════════════════════════


class TestPostLoopRemainingGaps:
    def test_empty_text_skipped_in_post_loop(self, classifier):
        """Empty-text UNKNOWN block is skipped in post-loop (line 587)."""
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(), blocks=[block("b0", 0, BlockType.UNKNOWN, text="")]
        )
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=0):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[0].block_type == BlockType.UNKNOWN

    def test_unknown_without_nlp_in_post_loop(self, classifier):
        """UNKNOWN block with no nlp_confidence → BODY + HEURISTIC_CONFIDENCE_LOW."""
        from app.config.settings import settings

        blocks = [
            block(
                "b0",
                0,
                BlockType.BODY,
                text="Intro",
                metadata={"is_heading_candidate": True},
                level=1,
                section_name="introduction",
            ),
            block(
                "b1",
                1,
                BlockType.UNKNOWN,
                text="some text",
                metadata={"is_heading_candidate": True, "level": 1},
                section_name="test",
            ),
        ]
        object.__setattr__(blocks[1], "section_name", 123)
        doc = PipelineDocument(document_id="d", metadata=DocumentMetadata(), blocks=blocks)
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=0):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.BODY
        assert doc.blocks[1].classification_confidence == settings.HEURISTIC_CONFIDENCE_LOW
        assert doc.blocks[1].metadata.get("classification_method") == "fallback_last_resort"

    def test_unknown_with_nlp_in_post_loop(self, classifier):
        """UNKNOWN block with nlp_confidence > 0 → BODY with NLP confidence."""
        blocks = [
            block(
                "b0",
                0,
                BlockType.BODY,
                text="Intro",
                metadata={"is_heading_candidate": True},
                level=1,
                section_name="introduction",
            ),
            block(
                "b1",
                1,
                BlockType.UNKNOWN,
                text="some text",
                metadata={"is_heading_candidate": True, "level": 1, "nlp_confidence": 0.7},
                section_name="test",
            ),
        ]
        object.__setattr__(blocks[1], "section_name", 123)
        doc = PipelineDocument(document_id="d", metadata=DocumentMetadata(), blocks=blocks)
        with patch.object(classifier, "_predict_llm_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=0):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.BODY
        assert doc.blocks[1].classification_confidence == max(0.7, 0.5)
        assert doc.blocks[1].metadata.get("classification_method") == "fallback_with_nlp"


# ══════════════════════════════════════════════════════════════════════════════
# _find_first_section_index — lines 679-681, 686->668
# ══════════════════════════════════════════════════════════════════════════════


class TestFindFirstSectionIndexRemainingGaps:
    def test_title_heading_candidate_skipped(self, classifier):
        """TITLE block with is_heading_candidate is skipped; next heading found."""
        blocks = [
            block("b0", 0, BlockType.TITLE, text="Title", metadata={"is_heading_candidate": True}),
            block("b1", 1, BlockType.BODY, text="Introduction", metadata={"is_heading_candidate": True}),
        ]
        result = classifier._find_first_section_index(blocks)
        assert result == 1

    def test_fallback_too_long_skipped(self, classifier):
        """Fallback detection skips text with >12 words (line 686→668)."""
        blocks = [
            block(
                "b0", 0, BlockType.BODY, text="one two three four five six seven eight nine ten eleven twelve thirteen"
            ),
        ]
        result = classifier._find_first_section_index(blocks)
        assert result == 1  # no heading found, min(12, 1)


# ══════════════════════════════════════════════════════════════════════════════
# _nlp_classify_fallback — lines 793-818
# ══════════════════════════════════════════════════════════════════════════════


class TestNlpClassifyFallbackGaps:
    def test_skip_protected_block(self, classifier):
        """Protected structural blocks are skipped by NLP fallback."""
        b = block("b1", 0, BlockType.UNKNOWN, text="1 A footnote", metadata={"is_footnote": True})
        classifier._nlp_classify_fallback([b])
        assert b.block_type == BlockType.UNKNOWN

    def test_empty_text_skip(self, classifier):
        """Empty text UNKNOWN block is skipped (line 794-795)."""
        b = block("b1", 0, BlockType.UNKNOWN, text="")
        classifier._nlp_classify_fallback([b])
        assert b.block_type == BlockType.UNKNOWN

    def test_footnote_pattern_detected(self, classifier):
        """UNKNOWN block starting with digit+space → FOOTNOTE."""
        b = block("b1", 0, BlockType.UNKNOWN, text="1 This is a footnote")
        classifier._nlp_classify_fallback([b])
        assert b.block_type == BlockType.FOOTNOTE

    def test_equation_pattern_detected(self, classifier):
        """UNKNOWN block with equation syntax → EQUATION."""
        b = block("b1", 0, BlockType.UNKNOWN, text=r"x = \sum_{i=1}^{n} y_i")
        classifier._nlp_classify_fallback([b])
        assert b.block_type == BlockType.EQUATION

    def test_table_pattern_detected(self, classifier):
        """UNKNOWN block with tab characters → BODY with table metadata."""
        b = block("b1", 0, BlockType.UNKNOWN, text="a\tb\tc\td")
        classifier._nlp_classify_fallback([b])
        assert b.block_type == BlockType.BODY
        assert b.metadata.get("classification_method") == "nlp_bert_high_confidence"

    def test_no_match_unchanged(self, classifier):
        """UNKNOWN block matching no pattern stays unchanged."""
        b = block("b1", 0, BlockType.UNKNOWN, text="just some regular text")
        classifier._nlp_classify_fallback([b])
        assert b.block_type == BlockType.UNKNOWN
