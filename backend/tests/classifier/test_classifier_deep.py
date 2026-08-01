# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.models import Block, BlockType, DocumentMetadata, PipelineDocument
from app.pipeline.classification.classifier import ContentClassifier, classify_content

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def classifier():
    return ContentClassifier()


def block(block_id: str, index: int, block_type=BlockType.BODY, text="",
           level=None, section_name="", metadata=None, **kw):
    return Block(
        block_id=block_id, index=index, block_type=block_type, text=text,
        level=level, section_name=section_name, metadata=metadata or {}, **kw,
    )


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

class TestInit:
    def test_sets_keyword_sets(self, classifier):
        assert classifier.abstract_keywords
        assert classifier.references_keywords
        assert classifier.acknowledgements_keywords
        assert classifier.affiliation_indicators
        assert classifier.footnote_patterns
        assert classifier.appendix_keywords


# ---------------------------------------------------------------------------
# _looks_like_heading
# ---------------------------------------------------------------------------

class TestLooksLikeHeading:
    def test_is_heading_candidate_meta(self, classifier):
        assert classifier._looks_like_heading(block("b", 0, metadata={"is_heading_candidate": True})) is True

    def test_potential_heading_meta(self, classifier):
        assert classifier._looks_like_heading(block("b", 0, metadata={"potential_heading": True})) is True

    def test_uppercase_short(self, classifier):
        assert classifier._looks_like_heading(block("b", 0, text="INTRODUCTION")) is True

    def test_title_case_short(self, classifier):
        assert classifier._looks_like_heading(block("b", 0, text="Related Work")) is True

    def test_long_text_not_heading(self, classifier):
        assert classifier._looks_like_heading(block("b", 0, text="A" * 200)) is False

    def test_empty_not_heading(self, classifier):
        assert classifier._looks_like_heading(block("b", 0, text="")) is False


# ---------------------------------------------------------------------------
# _resolve_heading_type
# ---------------------------------------------------------------------------

class TestResolveHeadingType:
    def test_level_1(self, classifier):
        assert classifier._resolve_heading_type(block("b", 0, level=1))[0] == BlockType.HEADING_1

    def test_level_4(self, classifier):
        assert classifier._resolve_heading_type(block("b", 0, level=4))[0] == BlockType.HEADING_4

    def test_heading_level_meta(self, classifier):
        assert classifier._resolve_heading_type(block("b", 0, metadata={"heading_level": 2}))[0] == BlockType.HEADING_2


# ---------------------------------------------------------------------------
# _map_scibert_label
# ---------------------------------------------------------------------------

class TestMapScibertLabel:
    def test_title(self, classifier):
        assert classifier._map_scibert_label("TITLE", block("b", 0))[0] == BlockType.TITLE

    def test_abstract_heading(self, classifier):
        b = block("b", 0, text="Abstract", metadata={"is_heading_candidate": True})
        assert classifier._map_scibert_label("ABSTRACT", b)[0] == BlockType.ABSTRACT_HEADING

    def test_abstract_body(self, classifier):
        b = block("b", 0, text="This paper presents...")
        assert classifier._map_scibert_label("ABSTRACT", b)[0] == BlockType.ABSTRACT_BODY

    def test_references_heading(self, classifier):
        b = block("b", 0, text="References", metadata={"is_heading_candidate": True})
        assert classifier._map_scibert_label("REFERENCES", b)[0] == BlockType.REFERENCES_HEADING

    def test_references_entry(self, classifier):
        b = block("b1", 0, text="[1] Author, J. (2024). A very long paper title indeed that exceeds the fifty character minimum threshold.")
        assert classifier._map_scibert_label("REFERENCES", b)[0] == BlockType.REFERENCE_ENTRY

    def test_figure_caption(self, classifier):
        assert classifier._map_scibert_label("FIGURE_CAPTION", block("b", 0))[0] == BlockType.FIGURE_CAPTION

    def test_table_caption(self, classifier):
        assert classifier._map_scibert_label("TABLE_CAPTION", block("b", 0))[0] == BlockType.TABLE_CAPTION

    def test_acknowledgements(self, classifier):
        assert classifier._map_scibert_label("ACKNOWLEDGEMENTS", block("b", 0))[0] == BlockType.ACKNOWLEDGEMENTS

    def test_equation(self, classifier):
        assert classifier._map_scibert_label("EQUATION", block("b", 0))[0] == BlockType.EQUATION

    def test_methodology_heading(self, classifier):
        b = block("b", 0, text="Methodology", metadata={"is_heading_candidate": True})
        assert classifier._map_scibert_label("METHODOLOGY", b)[0] == BlockType.HEADING_1

    def test_methodology_body(self, classifier):
        b = block("b", 0, text="We used a transformer-based approach.")
        assert classifier._map_scibert_label("METHODOLOGY", b)[0] == BlockType.BODY

    def test_heading(self, classifier):
        assert classifier._map_scibert_label("HEADING", block("b", 0))[0] == BlockType.HEADING_1

    def test_body(self, classifier):
        assert classifier._map_scibert_label("BODY", block("b", 0))[0] == BlockType.BODY

    def test_unknown_falls_to_body(self, classifier):
        assert classifier._map_scibert_label("UNKNOWN", block("b", 0))[0] == BlockType.BODY


# ---------------------------------------------------------------------------
# _predict_scibert_batch
# ---------------------------------------------------------------------------

class TestPredictScibertBatch:
    def test_disabled_returns_none(self, classifier):
        with patch("app.pipeline.classification.classifier.should_enable_scibert", return_value=False):
            assert classifier._predict_scibert_batch([]) is None

    def test_empty_blocks_returns_list(self, classifier):
        with patch("app.pipeline.classification.classifier.should_enable_scibert", return_value=True):
            assert classifier._predict_scibert_batch([]) == []

    def test_non_english_returns_none(self, classifier):
        mock_parser = MagicMock()
        mock_parser.predict_blocks_batch.return_value = []
        with patch("app.pipeline.classification.classifier.should_enable_scibert", return_value=True):
            with patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser", return_value=mock_parser):
                with patch("app.pipeline.intelligence.semantic_parser.HAS_LANGDETECT", True, create=True):
                    with patch("app.pipeline.intelligence.semantic_parser.detect_language", return_value="fr", create=True):
                        result = classifier._predict_scibert_batch([block("b", 0, text="Bonjour")])
        assert result is None

    def test_successful_prediction(self, classifier):
        mock_parser = MagicMock()
        mock_parser.model = MagicMock()
        mock_parser.tokenizer = MagicMock()
        mock_parser.predict_blocks_batch.return_value = [{"type": "BODY", "confidence": 0.95}]
        with patch("app.pipeline.classification.classifier.should_enable_scibert", return_value=True):
            with patch("app.pipeline.intelligence.semantic_parser.HAS_LANGDETECT", False, create=True):
                with patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser", return_value=mock_parser):
                    result = classifier._predict_scibert_batch([block("b", 0, text="Hello")])
        assert result == [{"type": "BODY", "confidence": 0.95}]

    def test_exception_caught(self, classifier):
        with patch("app.pipeline.classification.classifier.should_enable_scibert", return_value=True):
            with patch("app.pipeline.intelligence.semantic_parser.HAS_LANGDETECT", False, create=True):
                with patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser", side_effect=ImportError("no module")):
                    assert classifier._predict_scibert_batch([block("b", 0)]) is None

    def test_no_model_returns_none(self, classifier):
        mock_parser = MagicMock()
        mock_parser.model = None
        mock_parser.tokenizer = None
        with patch("app.pipeline.classification.classifier.should_enable_scibert", return_value=True):
            with patch("app.pipeline.intelligence.semantic_parser.HAS_LANGDETECT", False, create=True):
                with patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser", return_value=mock_parser):
                    assert classifier._predict_scibert_batch([block("b", 0)]) is None


# ---------------------------------------------------------------------------
# _apply_scibert_predictions
# ---------------------------------------------------------------------------

class TestApplyScibertPredictions:
    def test_no_predictions_noop(self, classifier):
        b = block("b1", 0, block_type=BlockType.BODY)
        classifier._apply_scibert_predictions([b], None)
        assert b.block_type == BlockType.BODY

    def test_stores_raw_metadata(self, classifier):
        b = block("b1", 0, block_type=BlockType.BODY)
        preds = [{"type": "ABSTRACT", "confidence": 0.95}]
        classifier._apply_scibert_predictions([b], preds)
        assert b.metadata.get("scibert_prediction") == "ABSTRACT"

    def test_skips_non_body_types(self, classifier):
        b = block("b1", 0, block_type=BlockType.TITLE)
        preds = [{"type": "BODY", "confidence": 0.95}]
        classifier._apply_scibert_predictions([b], preds)
        assert b.block_type == BlockType.TITLE

    def test_overrides_body(self, classifier):
        b = block("b1", 0, block_type=BlockType.BODY)
        preds = [{"type": "ABSTRACT", "confidence": 0.95}]
        classifier._apply_scibert_predictions([b], preds)
        assert b.block_type == BlockType.ABSTRACT_BODY

    def test_low_confidence_skipped(self, classifier):
        classifier.scibert_min_confidence = 0.8
        b = block("b1", 0, block_type=BlockType.BODY)
        preds = [{"type": "ABSTRACT", "confidence": 0.3}]
        classifier._apply_scibert_predictions([b], preds)
        assert b.block_type == BlockType.BODY

    def test_skips_header_blocks(self, classifier):
        b = block("b1", 0, block_type=BlockType.BODY, metadata={"is_header": True})
        preds = [{"type": "ABSTRACT", "confidence": 0.95}]
        classifier._apply_scibert_predictions([b], preds)
        assert b.block_type == BlockType.BODY

    def test_body_to_body_skipped(self, classifier):
        b = block("b1", 0, block_type=BlockType.BODY)
        preds = [{"type": "BODY", "confidence": 0.99}]
        classifier._apply_scibert_predictions([b], preds)
        assert b.block_type == BlockType.BODY
        assert b.metadata.get("classification_method") != "scibert_batch"


# ---------------------------------------------------------------------------
# _is_likely_affiliation
# ---------------------------------------------------------------------------

class TestIsLikelyAffiliation:
    def test_university(self, classifier):
        assert classifier._is_likely_affiliation("University of Wonderland") is True

    def test_institute(self, classifier):
        assert classifier._is_likely_affiliation("Institute for Advanced Study") is True

    def test_email(self, classifier):
        assert classifier._is_likely_affiliation("alice@mit.edu") is True

    def test_department(self, classifier):
        assert classifier._is_likely_affiliation("Department of Physics") is True

    def test_plain_name_not_affiliation(self, classifier):
        assert classifier._is_likely_affiliation("Alice Johnson") is False


# ---------------------------------------------------------------------------
# _match_grobid_author
# ---------------------------------------------------------------------------

class TestMatchGrobidAuthor:
    def test_matches_full_name(self, classifier):
        authors = [{"full_name": "Alice Johnson"}]
        assert classifier._match_grobid_author("Alice Johnson", authors) is True

    def test_matches_given_family(self, classifier):
        authors = [{"given": "Alice", "family": "Johnson"}]
        assert classifier._match_grobid_author("Alice Johnson", authors) is True

    def test_family_short_skipped(self, classifier):
        authors = [{"family": "Li"}]
        assert classifier._match_grobid_author("Li", authors) is False

    def test_no_match(self, classifier):
        assert classifier._match_grobid_author("Alice", [{"full_name": "Bob"}]) is False

    def test_empty(self, classifier):
        assert classifier._match_grobid_author("Alice", []) is False


# ---------------------------------------------------------------------------
# _match_grobid_affiliation
# ---------------------------------------------------------------------------

class TestMatchGrobidAffiliation:
    def test_exact_match(self, classifier):
        assert classifier._match_grobid_affiliation("MIT", ["MIT"]) is True

    def test_substring_match(self, classifier):
        assert classifier._match_grobid_affiliation("Massachusetts Institute of Technology", ["MIT"]) is False

    def test_partial_long_affiliation(self, classifier):
        affs = ["Massachusetts Institute of Technology Cambridge"]
        assert classifier._match_grobid_affiliation("Massachusetts Institute of Technology", affs) is True

    def test_empty_affs(self, classifier):
        assert classifier._match_grobid_affiliation("MIT", []) is False


# ---------------------------------------------------------------------------
# _find_first_section_index
# ---------------------------------------------------------------------------

class TestFindFirstSectionIndex:
    def test_finds_first_heading(self, classifier):
        blocks = [
            block("b1", 0, BlockType.TITLE, text="Title"),
            block("b2", 100, BlockType.BODY, text="Author", metadata={"is_heading_candidate": True}),
        ]
        assert classifier._find_first_section_index(blocks) == 1

    def test_skips_title_blocks(self, classifier):
        blocks = [
            block("b1", 0, BlockType.TITLE, text="Title", metadata={"is_heading_candidate": True}),
            block("b2", 100, BlockType.BODY, text="Intro", metadata={"is_heading_candidate": True}),
        ]
        assert classifier._find_first_section_index(blocks) == 1

    def test_long_text_breaks(self, classifier):
        blocks = [
            block("b1", 0, BlockType.TITLE, text="Title"),
            block("b2", 100, BlockType.BODY, text="A" * 301),
        ]
        assert classifier._find_first_section_index(blocks) == 2

    def test_fallback_numbered_heading(self, classifier):
        blocks = [block("b1", 0, BlockType.BODY, text="1. Introduction")]
        assert classifier._find_first_section_index(blocks) == 0

    def test_fallback_keyword_heading(self, classifier):
        blocks = [block("b1", 0, BlockType.BODY, text="Abstract")]
        assert classifier._find_first_section_index(blocks) == 0

    def test_empty_returns_0(self, classifier):
        assert classifier._find_first_section_index([]) == 0


# ---------------------------------------------------------------------------
# _find_references_start_index
# ---------------------------------------------------------------------------

class TestFindReferencesStartIndex:
    def test_finds_by_text(self, classifier):
        blocks = [
            block("b1", 0, BlockType.BODY, text="References",
                  metadata={"is_heading_candidate": True}),
        ]
        assert classifier._find_references_start_index(blocks) == 0

    def test_finds_by_section_name(self, classifier):
        blocks = [
            block("b1", 0, BlockType.BODY, text="Refs", section_name="references",
                  metadata={"is_heading_candidate": True}),
        ]
        assert classifier._find_references_start_index(blocks) == 0

    def test_not_heading_candidate_skipped(self, classifier):
        blocks = [
            block("b1", 0, BlockType.BODY, text="References", section_name="references"),
        ]
        assert classifier._find_references_start_index(blocks) is None

    def test_long_text_skipped(self, classifier):
        blocks = [
            block("b1", 0, BlockType.BODY, text="References and related literature... " + "A" * 50,
                  metadata={"is_heading_candidate": True}),
        ]
        assert classifier._find_references_start_index(blocks) is None

    def test_no_references(self, classifier):
        assert classifier._find_references_start_index([block("b1", 0)]) is None


# ---------------------------------------------------------------------------
# Deterministic captions
# ---------------------------------------------------------------------------

class TestDeterministicCaptions:
    def test_figure_caption(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[block("b1", 0, BlockType.BODY, text="Figure 1: Results")],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[0].block_type == BlockType.FIGURE_CAPTION

    def test_table_caption(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[block("b1", 0, BlockType.BODY, text="Table 1: Data")],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[0].block_type == BlockType.TABLE_CAPTION


# ---------------------------------------------------------------------------
# Front matter
# ---------------------------------------------------------------------------

class TestFrontMatter:
    def test_title_position_first(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[block("b1", 0, BlockType.BODY, text="My Paper")],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=10):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[0].block_type == BlockType.TITLE

    def test_grobid_title(self, classifier):
        doc = PipelineDocument(
            document_id="d",
            metadata=DocumentMetadata(ai_hints={"grobid_metadata": {"title": "My Paper"}}),
            blocks=[block("b1", 0, BlockType.BODY, text="My Paper")],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=10):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[0].block_type == BlockType.TITLE

    def test_grobid_author(self, classifier):
        doc = PipelineDocument(
            document_id="d",
            metadata=DocumentMetadata(ai_hints={
                "grobid_metadata": {"authors": [{"full_name": "Alice Johnson"}]}
            }),
            blocks=[
                block("b1", 0, BlockType.TITLE, text="Title"),
                block("b2", 100, BlockType.BODY, text="Alice Johnson"),
            ],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=10):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.AUTHOR

    def test_grobid_affiliation(self, classifier):
        doc = PipelineDocument(
            document_id="d",
            metadata=DocumentMetadata(ai_hints={
                "grobid_metadata": {
                    "authors": [{"full_name": "Alice Johnson"}],
                    "affiliations": ["Massachusetts Institute of Technology"]
                }
            }),
            blocks=[
                block("b1", 0, BlockType.TITLE, text="Title"),
                block("b2", 100, BlockType.AUTHOR, text="Alice Johnson"),
                block("b3", 200, BlockType.BODY, text="Massachusetts Institute of Technology"),
            ],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=10):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[2].block_type == BlockType.AFFILIATION

    def test_regex_author_rule(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b1", 0, BlockType.TITLE, text="Title"),
                block("b2", 100, BlockType.BODY, text="Alice Johnson"),
            ],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=10):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.AUTHOR

    def test_affiliation_by_keyword(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b1", 0, BlockType.TITLE, text="Title"),
                block("b2", 100, BlockType.AUTHOR, text="Alice Johnson"),
                block("b3", 200, BlockType.BODY, text="University of Wonderland"),
            ],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=10):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[2].block_type == BlockType.AFFILIATION


# ---------------------------------------------------------------------------
# Body zone headings
# ---------------------------------------------------------------------------

class TestBodyZone:
    def test_heading_candidate(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="Introduction",
                      metadata={"is_heading_candidate": True}, level=1),
            ],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.HEADING_1

    def test_abstract_heading(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="Abstract",
                      metadata={"is_heading_candidate": True}, level=1,
                      section_name="abstract"),
            ],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.ABSTRACT_HEADING

    def test_abstract_body(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="Abstract",
                      metadata={"is_heading_candidate": True}, level=1,
                      section_name="abstract"),
                block("b2", 100, BlockType.BODY, text="This paper presents..."),
            ],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[2].block_type == BlockType.ABSTRACT_BODY

    def test_keywords_heading(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="Keywords",
                      metadata={"is_heading_candidate": True}, level=1,
                      section_name="keywords"),
            ],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.KEYWORDS_HEADING

    def test_keywords_body(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="Keywords",
                      metadata={"is_heading_candidate": True}, level=1,
                      section_name="keywords"),
                block("b2", 100, BlockType.BODY, text="machine learning, NLP"),
            ],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[2].block_type == BlockType.KEYWORDS_BODY

    def test_acknowledgements_heading(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="Acknowledgements",
                      metadata={"is_heading_candidate": True}, level=1,
                      section_name="acknowledgements"),
            ],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.ACKNOWLEDGEMENTS

    def test_funding_heading(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="Funding",
                      metadata={"is_heading_candidate": True}, level=1,
                      section_name="acknowledgements"),
            ],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.FUNDING

    def test_conflict_of_interest_heading(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="Conflicts of Interest",
                      metadata={"is_heading_candidate": True}, level=1,
                      section_name="acknowledgements"),
            ],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.CONFLICT_OF_INTEREST

    def test_appendix_heading(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="Appendix",
                      metadata={"is_heading_candidate": True}, level=1,
                      section_name="appendix"),
            ],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.HEADING_1
        assert doc.blocks[1].metadata.get("is_appendix") is True


# ---------------------------------------------------------------------------
# References zone
# ---------------------------------------------------------------------------

class TestReferencesZone:
    def test_heading_and_entry(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[
                block("b0", -1, BlockType.TITLE, text="Title"),
                block("b1", 0, BlockType.BODY, text="References",
                      metadata={"is_heading_candidate": True}),
                block("b2", 100, BlockType.BODY, text="[1] Author. Title."),
            ],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=1):
                    classifier.process(doc)
        assert doc.blocks[1].block_type == BlockType.REFERENCES_HEADING
        assert doc.blocks[2].block_type == BlockType.REFERENCE_ENTRY


# ---------------------------------------------------------------------------
# NLP fallback
# ---------------------------------------------------------------------------

class TestNlpFallback:
    def test_footnote_pattern(self, classifier):
        b = block("b1", 0, BlockType.UNKNOWN, text="1 A footnote text here")
        classifier._nlp_classify_fallback([b])
        assert b.block_type == BlockType.FOOTNOTE

    def test_equation_pattern(self, classifier):
        b = block("b1", 0, BlockType.UNKNOWN, text="x == y")
        classifier._nlp_classify_fallback([b])
        assert b.block_type == BlockType.EQUATION

    def test_table_pattern(self, classifier):
        b = block("b1", 0, BlockType.UNKNOWN, text="A\tB\tC\n1\t2\t3")
        classifier._nlp_classify_fallback([b])
        assert b.block_type == BlockType.BODY

    def test_skips_non_unknown(self, classifier):
        b = block("b1", 0, BlockType.BODY, text="1A footnote")
        classifier._nlp_classify_fallback([b])
        assert b.block_type == BlockType.BODY


# ---------------------------------------------------------------------------
# process
# ---------------------------------------------------------------------------

class TestProcess:
    def test_returns_document(self, classifier):
        doc = PipelineDocument(document_id="d", metadata=DocumentMetadata(), blocks=[])
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=0):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    result = classifier.process(doc)
        assert result is doc

    def test_adds_processing_stage(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[block("b1", 0, BlockType.BODY, text="Hello")],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=0):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert len(doc.processing_history) >= 1

    def test_handles_exception(self, classifier):
        doc = PipelineDocument(document_id="d", metadata=DocumentMetadata(), blocks=[])
        with patch.object(classifier, "_run_classification", side_effect=ValueError("boom")):
            result = classifier.process(doc)
        assert result is doc

    def test_skips_header_blocks(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[block("b1", 0, BlockType.BODY, text="Header", metadata={"is_header": True})],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[0].block_type == BlockType.BODY

    def test_preserves_title(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[block("b1", 0, BlockType.TITLE, text="My Paper")],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=1):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[0].block_type == BlockType.TITLE

    def test_body_default(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[block("b1", 0, BlockType.BODY, text="Regular paragraph.")],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=0):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[0].block_type == BlockType.BODY

    def test_post_loop_numbered_heading(self, classifier):
        doc = PipelineDocument(
            document_id="d", metadata=DocumentMetadata(),
            blocks=[block("b1", 0, BlockType.UNKNOWN, text="1. Introduction")],
        )
        with patch.object(classifier, "_predict_scibert_batch", return_value=None):
            with patch.object(classifier, "_find_first_section_index", return_value=0):
                with patch.object(classifier, "_find_references_start_index", return_value=None):
                    classifier.process(doc)
        assert doc.blocks[0].block_type == BlockType.HEADING_1


# ---------------------------------------------------------------------------
# classify_content convenience
# ---------------------------------------------------------------------------

class TestClassifyContent:
    def test_returns_document(self):
        doc = PipelineDocument(document_id="d", metadata=DocumentMetadata(), blocks=[])
        with patch.object(ContentClassifier, "_predict_scibert_batch", return_value=None):
            with patch.object(ContentClassifier, "_find_first_section_index", return_value=0):
                with patch.object(ContentClassifier, "_find_references_start_index", return_value=None):
                    result = classify_content(doc)
        assert result is doc
