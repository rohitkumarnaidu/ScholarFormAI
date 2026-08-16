# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Expanded RAG ground truth dataset — additional 30 queries (for 50+ total)."""

import pytest

# ---------------------------------------------------------------------------
# Expanded Ground Truth Dataset — 30 additional queries
# ---------------------------------------------------------------------------

EXPANDED_GROUND_TRUTH = [
    # === Vancouver, Numeric, Harvard, Chicago, MLA (5 queries) ===
    {
        "query": "What is the correct Vancouver style for citing a journal article with more than six authors?",
        "relevant_docs": [
            {"text": "Vancouver style lists the first six authors followed by et al.", "relevance": 3},
            {"text": "Vancouver: author names are formatted as Surname Initials separated by commas.", "relevance": 2},
            {"text": "Vancouver style uses sequential numbering in square brackets.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "APA uses author-date format without numbered references.", "relevance": 0},
        ],
    },
    {
        "query": "How does Chicago style format footnote citations for repeated sources?",
        "relevant_docs": [
            {"text": "Chicago style uses shortened citations after the first full citation.", "relevance": 3},
            {"text": "Chicago footnotes use author last name and short title for repeated references.", "relevance": 3},
            {"text": "Chicago style allows ibid. for consecutive same-source citations.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "MLA uses in-text parenthetical citations, not footnotes.", "relevance": 0},
        ],
    },
    {
        "query": "MLA 9th edition in-text citation rules for indirect sources",
        "relevant_docs": [
            {"text": "MLA 9th edition uses qtd. in to cite indirect sources.", "relevance": 3},
            {"text": "MLA in-text citations use author's last name and page number.", "relevance": 2},
            {"text": "MLA style prefers citing the original source whenever possible.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "APA uses as cited in for secondary source citations.", "relevance": 0},
        ],
    },
    {
        "query": "How does Harvard style format corporate author citations?",
        "relevant_docs": [
            {
                "text": "Harvard style abbreviates commonly known corporate author names after first mention.",
                "relevance": 3,
            },
            {"text": "Harvard style: corporate authors are cited by organisation name.", "relevance": 2},
            {"text": "Harvard referencing uses author-date format for all sources.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "Vancouver style never abbreviates corporate author names.", "relevance": 0},
        ],
    },
    {
        "query": "Numeric citation style guidelines for consecutive reference numbering",
        "relevant_docs": [
            {"text": "Numeric style uses consecutive numbers in order of first citation.", "relevance": 3},
            {"text": "Numeric citation: consecutive references use en-dash or comma separation.", "relevance": 2},
            {"text": "Numeric style resets numbering for each chapter in some publications.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "Author-year styles like APA do not use sequential numbering.", "relevance": 0},
        ],
    },
    # === Edge case queries (5 queries) ===
    {
        "query": "DPI",
        "relevant_docs": [
            {"text": "Elsevier requires figures at minimum 300 DPI resolution.", "relevance": 3},
            {"text": "IEEE requires 600 DPI for line art figures.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "Nature journals accept any resolution for digital-only figures.", "relevance": 0},
        ],
    },
    {
        "query": "What are the specific formatting requirements for supplementary materials in academic journal submissions across all major publishers including margin specifications, font sizes, file formats, naming conventions, cover letter contents, and ORCID iD registration policies for corresponding authors as of the 2025 guidelines?",
        "relevant_docs": [
            {
                "text": "Most major publishers accept supplementary materials as PDF, DOCX, or ZIP files.",
                "relevance": 3,
            },
            {"text": "Supplementary material naming conventions vary by publisher: Suppl., S1, etc.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "MLA formatting guidelines do not address supplementary materials.", "relevance": 0},
        ],
    },
    {
        "query": "figure resolution & table formatting && (Elsevier || IEEE) !Springer",
        "relevant_docs": [
            {"text": "Elsevier requires figures at minimum 300 DPI resolution.", "relevance": 3},
            {"text": "IEEE requires 600 DPI for line art figures, 300 DPI for photographs.", "relevance": 3},
            {"text": "Elsevier tables should be numbered consecutively with Arabic numerals.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "Springer tables use Roman numerals in some template variants.", "relevance": 0},
        ],
    },
    {
        "query": "σ-πίνακας μορφοποίηση (Greek: table formatting)",
        "relevant_docs": [
            {"text": "Tables should be formatted consistently regardless of display language.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "Greek language manuscripts follow the same structural rules.", "relevance": 0},
        ],
    },
    {
        "query": "0 === 0",
        "relevant_docs": [
            {"text": "Mathematical equality symbols should not be used in standard queries.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "Boolean operators are used for advanced search syntax.", "relevance": 0},
        ],
    },
    # === Multi-intent queries — cross-publisher (5 queries) ===
    {
        "query": "What are the abstract length limits for Nature compared to Elsevier and PLOS ONE?",
        "relevant_docs": [
            {"text": "Nature abstract word limit is 150 words for Articles.", "relevance": 3},
            {"text": "Elsevier journals typically allow 300-word abstracts.", "relevance": 3},
            {"text": "PLOS ONE requires abstracts up to 300 words with structured format.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "IEEE abstracts are typically 150-250 words for conference papers.", "relevance": 0},
        ],
    },
    {
        "query": "Compare figure resolution requirements between IEEE, Elsevier, and Springer",
        "relevant_docs": [
            {"text": "Elsevier requires figures at minimum 300 DPI resolution.", "relevance": 3},
            {"text": "IEEE requires 600 DPI for line art and 300 DPI for photographs.", "relevance": 3},
            {"text": "Springer recommends 400-600 DPI for figures in print publications.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "ACM does not specify DPI requirements for figures.", "relevance": 0},
        ],
    },
    {
        "query": "How do citation styles differ between ACS, AMA, and Chicago for the same reference?",
        "relevant_docs": [
            {"text": "ACS uses superscript numbers for citations in chemistry publications.", "relevance": 3},
            {"text": "AMA citation style uses superscript numbers outside punctuation.", "relevance": 2},
            {"text": "Chicago style uses footnotes or author-date depending on the discipline.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "Vancouver style is used primarily in biomedical journals.", "relevance": 0},
        ],
    },
    {
        "query": "What are the corresponding author policies across SAGE, Taylor & Francis, and De Gruyter?",
        "relevant_docs": [
            {"text": "SAGE requires corresponding author to submit the manuscript.", "relevance": 3},
            {"text": "Taylor & Francis designates one corresponding author for each submission.", "relevance": 2},
            {"text": "De Gruyter allows multiple corresponding authors with shared responsibility.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "IEEE corresponding authors are responsible for all co-author approvals.", "relevance": 0},
        ],
    },
    {
        "query": "Compare open access policies and APC waivers between ACM, PLOS, and Frontiers journals",
        "relevant_docs": [
            {"text": "ACM offers author-pays open access with ACM member discounts.", "relevance": 3},
            {"text": "PLOS uses a flat APC with automatic waivers for low-income countries.", "relevance": 3},
            {"text": "Frontiers has a tiered APC system with institutional membership discounts.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "Nature APC is determined on a per-journal basis by Springer Nature.", "relevance": 0},
        ],
    },
    # === Section-specific queries (5 queries) ===
    {
        "query": "How should complex tables with merged cells be formatted for Springer journals?",
        "relevant_docs": [
            {"text": "Springer tables should be numbered consecutively with Arabic numerals.", "relevance": 3},
            {"text": "Springer table headers can span multiple columns with merged cells.", "relevance": 2},
            {
                "text": "Springer formatting: tables must be in editable Word format with clear row/column structure.",
                "relevance": 2,
            },
        ],
        "irrelevant_docs": [
            {"text": "Taylor & Francis prefers tables as separate image files.", "relevance": 0},
        ],
    },
    {
        "query": "What are the figure caption formatting requirements for multi-panel figures in Elsevier journals?",
        "relevant_docs": [
            {"text": "Elsevier figure captions should be placed below the figure.", "relevance": 3},
            {"text": "Elsevier multi-panel figures use A, B, C labels for sub-figures.", "relevance": 2},
            {"text": "Elsevier requires each sub-figure panel to have its own label in the caption.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "IEEE captions are placed above the figure.", "relevance": 0},
        ],
    },
    {
        "query": "How should inline and displayed equations be numbered in IMRaD-structured papers?",
        "relevant_docs": [
            {"text": "Equations are numbered sequentially in parentheses (1), (2) within each paper.", "relevance": 3},
            {
                "text": "In IMRaD papers, equation numbers appear on the right side of displayed equations.",
                "relevance": 2,
            },
            {"text": "AMS style uses section-based equation numbering like (1.1), (1.2).", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "Figure and table numbering use independent sequences.", "relevance": 0},
        ],
    },
    {
        "query": "What is the correct format for the references section in ACM conference papers?",
        "relevant_docs": [
            {"text": "ACM references use numbered format matching the citation order in text.", "relevance": 3},
            {"text": "ACM reference list headings vary by template: References or Bibliography.", "relevance": 2},
            {"text": "ACM requires DOI and URL in all reference entries when available.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "ACM does not use author-year citation format.", "relevance": 0},
        ],
    },
    {
        "query": "What information must be included in a data availability statement for PLOS ONE?",
        "relevant_docs": [
            {
                "text": "PLOS ONE requires data availability statements including repository names and DOIs.",
                "relevance": 3,
            },
            {"text": "PLOS ONE data policy mandates all underlying data be freely available.", "relevance": 2},
            {"text": "PLOS ONE data availability statements must explain any restrictions on access.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "Elsevier data availability statements follow the CRediT taxonomy.", "relevance": 0},
        ],
    },
    # === Template-specific queries (5 queries) ===
    {
        "query": "What sections should a professional academic resume/CV template include for science faculty positions?",
        "relevant_docs": [
            {
                "text": "Academic CVs include Education, Research Experience, Publications, and References.",
                "relevance": 3,
            },
            {
                "text": "Science faculty CVs include a Research Statement and Teaching Philosophy section.",
                "relevance": 2,
            },
            {"text": "Academic resumes typically list publications in reverse chronological order.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "Corporate resumes focus on skills and work experience over publications.", "relevance": 0},
        ],
    },
    {
        "query": "How do you structure a grant proposal template for NIH funding applications?",
        "relevant_docs": [
            {
                "text": "NIH grant proposals require Specific Aims, Research Strategy, and Budget sections.",
                "relevance": 3,
            },
            {
                "text": "NIH Research Strategy includes Significance, Innovation, and Approach subsections.",
                "relevance": 2,
            },
            {"text": "NIH requires biographical sketches for all key personnel.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {
                "text": "NSF proposals use a different format with Intellectual Merit and Broader Impacts.",
                "relevance": 0,
            },
        ],
    },
    {
        "query": "What are the standard sections in a PhD thesis template across UK and US universities?",
        "relevant_docs": [
            {
                "text": "PhD thesis structure: Abstract, Acknowledgements, TOC, Introduction, Literature Review, Methods, Results, Discussion, Conclusion, References, Appendices.",
                "relevance": 3,
            },
            {"text": "UK theses often include a Declaration of Originality and Impact Statement.", "relevance": 2},
            {
                "text": "US dissertations typically include a single comprehensive literature review chapter.",
                "relevance": 1,
            },
        ],
        "irrelevant_docs": [
            {"text": "Master's theses are typically shorter and may omit a full literature review.", "relevance": 0},
        ],
    },
    {
        "query": "What formatting does a Springer Nature proceedings paper template require?",
        "relevant_docs": [
            {"text": "Springer LNCS proceedings use the Lecture Notes in Computer Science template.", "relevance": 3},
            {"text": "Springer proceedings require structured abstract, keywords, and references.", "relevance": 2},
            {
                "text": "Springer Nature proceedings templates enforce strict page limits and font sizes.",
                "relevance": 1,
            },
        ],
        "irrelevant_docs": [
            {"text": "Springer journal articles use a different template from proceedings papers.", "relevance": 0},
        ],
    },
    {
        "query": "How do industry report templates differ from academic manuscript templates?",
        "relevant_docs": [
            {"text": "Industry reports use Executive Summary format with bullet-point findings.", "relevance": 3},
            {"text": "Academic manuscripts follow IMRaD structure with formal citation styles.", "relevance": 2},
            {
                "text": "Industry report templates prioritise visual data presentation over textual analysis.",
                "relevance": 1,
            },
        ],
        "irrelevant_docs": [
            {"text": "Both formats require table of contents and references sections.", "relevance": 0},
        ],
    },
    # === Negative queries (5 queries — clearly irrelevant to any publisher) ===
    {
        "query": "What is the best recipe for chocolate chip cookies?",
        "relevant_docs": [
            {"text": "Academic formatting guidelines do not include cooking recipes.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "IEEE style uses numbered brackets for citation ordering.", "relevance": 0},
            {"text": "Nature abstract word limit is 150 words.", "relevance": 0},
        ],
    },
    {
        "query": "How to change a flat tyre on a 2024 Toyota Camry?",
        "relevant_docs": [
            {"text": "Academic manuscript formatting does not cover automotive maintenance.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "Elsevier requires 300 DPI figure resolution.", "relevance": 0},
            {"text": "MLA uses author-page in-text citations.", "relevance": 0},
        ],
    },
    {
        "query": "Best practices for indoor hydroponic tomato cultivation",
        "relevant_docs": [
            {"text": "Agricultural research paper formatting may include plant science studies.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "ACM requires 1-inch margins on all sides.", "relevance": 0},
            {"text": "ICMJE Vancouver citation style for biomedical journals.", "relevance": 0},
        ],
    },
    {
        "query": "How to train a golden retriever puppy to sit and stay",
        "relevant_docs": [
            {"text": "Animal behaviour studies may follow APA style in psychology journals.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "Springer table formatting guidelines for academic papers.", "relevance": 0},
            {"text": "SAGE Harvard citation style for social sciences.", "relevance": 0},
        ],
    },
    {
        "query": "Best budget smartphones under 300 dollars in 2025",
        "relevant_docs": [
            {"text": "Consumer electronics reviews are not covered by academic formatting standards.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "IEEE citation style in computer science conference papers.", "relevance": 0},
            {"text": "Nature research articles on mobile technology innovations.", "relevance": 0},
        ],
    },
]


# ---------------------------------------------------------------------------
# Fixtures for expanded dataset
# ---------------------------------------------------------------------------


@pytest.fixture
def expanded_ground_truth_data():
    """Provide the expanded ground truth for querying."""
    return EXPANDED_GROUND_TRUTH


# ---------------------------------------------------------------------------
# Dataset Integrity Tests
# ---------------------------------------------------------------------------


class TestExpandedGroundTruthDataset:
    """Verify the expanded ground truth dataset is internally consistent."""

    @pytest.mark.ai_quality
    @pytest.mark.rag
    def test_expanded_dataset_has_correct_number_of_queries(self):
        assert len(EXPANDED_GROUND_TRUTH) == 30, "Expanded ground truth must have exactly 30 queries"

    @pytest.mark.ai_quality
    @pytest.mark.rag
    def test_all_expanded_queries_have_relevant_and_irrelevant_docs(self):
        for i, item in enumerate(EXPANDED_GROUND_TRUTH):
            assert item["query"], f"Query {i} is empty"
            assert len(item["relevant_docs"]) >= 1, f"Query {i} has no relevant docs"
            assert len(item["irrelevant_docs"]) >= 1, f"Query {i} has no irrelevant docs"

    @pytest.mark.ai_quality
    @pytest.mark.rag
    def test_expanded_relevance_scores_in_range(self):
        for item in EXPANDED_GROUND_TRUTH:
            for doc in item["relevant_docs"]:
                assert 1 <= doc["relevance"] <= 3, f"Relevance out of range: {doc['relevance']}"
            for doc in item["irrelevant_docs"]:
                assert doc["relevance"] == 0, "Irrelevant doc has non-zero relevance"

    @pytest.mark.ai_quality
    @pytest.mark.rag
    def test_all_expanded_queries_have_unique_text(self):
        all_texts = []
        for item in EXPANDED_GROUND_TRUTH:
            for doc in item["relevant_docs"] + item["irrelevant_docs"]:
                all_texts.append(doc["text"])
        assert len(set(all_texts)) == len(all_texts), "Duplicate texts found in expanded ground truth"

    @pytest.mark.ai_quality
    @pytest.mark.rag
    def test_negative_queries_have_minimal_relevance(self):
        for item in EXPANDED_GROUND_TRUTH:
            query = item["query"].lower()
            for doc in item["relevant_docs"]:
                if (
                    "recipe" in query
                    or "tyre" in query
                    or "hydroponic" in query
                    or "puppy" in query
                    or "smartphone" in query
                ):
                    assert doc["relevance"] == 1, "Negative query should have relevance=1"

    @pytest.mark.ai_quality
    @pytest.mark.rag
    def test_combined_dataset_reaches_fifty_plus(self):
        from test_rag_ground_truth import GROUND_TRUTH as GT

        combined = GT + EXPANDED_GROUND_TRUTH
        assert len(combined) >= 50, f"Combined dataset has {len(combined)} queries, expected >= 50"
