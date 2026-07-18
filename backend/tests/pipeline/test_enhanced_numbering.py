# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
from unittest.mock import MagicMock, Mock
import pytest
pytestmark = [pytest.mark.pipeline]


class TestNumberingEnginePerSection:
    """Test per-section equation numbering."""

    def test_per_section_equation_numbering(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        engine = NumberingEngine(scope="per_section")
        blocks = [
            Mock(block_id="s1", block_type="heading_1", text="Section 1", section_number=1),
            Mock(block_id="e1", block_type="equation", text="x=1", section_number=1),
            Mock(block_id="e2", block_type="equation", text="y=2", section_number=1),
            Mock(block_id="s2", block_type="heading_1", text="Section 2", section_number=2),
            Mock(block_id="e3", block_type="equation", text="z=3", section_number=2),
        ]
        result = engine.number_equations(blocks)
        assert result[1].number == "(1.1)"
        assert result[2].number == "(1.2)"
        assert result[4].number == "(2.1)"

    def test_per_section_single_section(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        engine = NumberingEngine(scope="per_section")
        blocks = [
            Mock(block_id="s1", block_type="heading_1", text="Section 1", section_number=1),
            Mock(block_id="e1", block_type="equation", text="x=1", section_number=1),
        ]
        result = engine.number_equations(blocks)
        assert result[1].number == "(1.1)"

    def test_per_section_no_headings(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        engine = NumberingEngine(scope="per_section")
        blocks = [
            Mock(block_id="e1", block_type="equation", text="x=1"),
            Mock(block_id="e2", block_type="equation", text="y=2"),
        ]
        result = engine.number_equations(blocks)
        assert result[0].number == "(1.1)"
        assert result[1].number == "(1.2)"

    def test_set_scope_method(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        engine = NumberingEngine(scope="global")
        assert engine.scope == "global"
        engine.set_scope("per_section")
        assert engine.scope == "per_section"

    def test_equation_numbering_with_body_blocks(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        engine = NumberingEngine(scope="per_section")
        blocks = [
            Mock(block_id="s1", block_type="heading_1", text="Intro", section_number=1),
            Mock(block_id="b1", block_type="body", text="Some text..."),
            Mock(block_id="e1", block_type="equation", text="x=1"),
            Mock(block_id="b2", block_type="body", text="More text..."),
            Mock(block_id="e2", block_type="equation", text="y=2"),
        ]
        result = engine.number_equations(blocks)
        assert result[2].number == "(1.1)"
        assert result[4].number == "(1.2)"


class TestNumberingEngineTableNumbering:
    """Test hierarchical table numbering."""

    def test_global_table_numbering(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        engine = NumberingEngine()
        blocks = [
            Mock(block_id="t1", block_type="table_caption", text="Table caption 1"),
            Mock(block_id="t2", block_type="table_caption", text="Table caption 2"),
        ]
        result = engine.number_tables(blocks, scope="global")
        assert result[0].number == "Table 1"
        assert result[1].number == "Table 2"

    def test_per_section_table_numbering(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        engine = NumberingEngine(scope="per_section")
        blocks = [
            Mock(block_id="s1", block_type="heading_1", text="Results", section_number=1),
            Mock(block_id="t1", block_type="table_caption", text="Table caption"),
            Mock(block_id="s2", block_type="heading_1", text="Discussion", section_number=2),
            Mock(block_id="t2", block_type="table_caption", text="Table caption"),
        ]
        result = engine.number_tables(blocks, scope="per_section")
        assert result[1].number == "Table 1.1"
        assert result[3].number == "Table 2.1"

    def test_table_numbering_with_heading_text(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        engine = NumberingEngine(scope="per_section")
        blocks = [
            Mock(block_id="s1", block_type="heading_1", text="1 Results", section_number=1),
            Mock(block_id="t1", block_type="table_caption", text="Table"),
        ]
        result = engine.number_tables(blocks, scope="per_section")
        assert result[1].number == "Table 1.1"

    def test_empty_blocks_table_numbering(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        engine = NumberingEngine()
        result = engine.number_tables([], scope="global")
        assert result == []


class TestCrossReferenceEngineAutoResolve:
    """Test cross-reference auto-resolution."""

    def test_auto_resolve_flag(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine
        engine = CrossReferenceEngine(auto_resolve=True)
        assert engine.auto_resolve is True
        engine2 = CrossReferenceEngine()
        assert engine2.auto_resolve is False

    def test_resolve_equation_references(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine
        engine = CrossReferenceEngine()
        blocks = [
            Mock(block_id="b1", text="See Equation (3) for details"),
            Mock(block_id="b2", text="Refer to Eq. (5) above"),
        ]
        equation_map = {3: "(2.1)", 5: "(3.4)"}
        result = engine.resolve_references(blocks, equation_map=equation_map)
        assert "Equation (2.1)" in result[0].text
        assert "Eq. (3.4)" in result[1].text

    def test_resolve_figure_references(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine
        engine = CrossReferenceEngine()
        blocks = [
            Mock(block_id="b1", text="See Figure 1 below"),
            Mock(block_id="b2", text="As shown in Fig. 2"),
        ]
        figure_map = {1: "1", 2: "2"}
        result = engine.resolve_references(blocks, figure_map=figure_map)
        assert "Figure 1" in result[0].text
        assert "Fig. 2" in result[1].text

    def test_resolve_table_references(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine
        engine = CrossReferenceEngine()
        blocks = [
            Mock(block_id="b1", text="See Table 1.2 for data"),
        ]
        table_map = {2: "2.1"}
        result = engine.resolve_references(blocks, table_map=table_map)
        assert "Table 2.1" in result[0].text

    def test_resolve_no_maps(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine
        engine = CrossReferenceEngine()
        blocks = [Mock(block_id="b1", text="Some text")]
        result = engine.resolve_references(blocks)
        assert result[0].text == "Some text"

    def test_resolve_multiple_maps(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine
        engine = CrossReferenceEngine()
        blocks = [
            Mock(
                block_id="b1",
                text="See Equation (1), Figure 3, and Table 5",
            ),
        ]
        equation_map = {1: "(1.1)"}
        figure_map = {3: "3"}
        table_map = {5: "2.3"}
        result = engine.resolve_references(
            blocks,
            equation_map=equation_map,
            figure_map=figure_map,
            table_map=table_map,
        )
        text = result[0].text
        assert "Equation (1.1)" in text
        assert "Figure 3" in text
        assert "Table 2.3" in text

    def test_no_change_when_map_missing(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine
        engine = CrossReferenceEngine()
        blocks = [Mock(block_id="b1", text="See Equation (99)")]
        equation_map = {1: "(1)"}
        result = engine.resolve_references(blocks, equation_map=equation_map)
        assert result[0].text == "See Equation (99)"


class TestCSLEngineExpanded:
    """Test CSL engine expanded style map."""

    def test_all_styles_in_map(self):
        from app.pipeline.services.csl_engine import CSLEngine
        expected = {"ieee", "apa", "vancouver", "mla", "chicago", "harvard",
                    "nature", "springer", "acm", "elsevier", "numeric"}
        assert expected.issubset(set(CSLEngine.DEFAULT_STYLE_MAP.keys()))

    def test_get_capabilities_lists_builtins(self):
        from app.pipeline.services.csl_engine import CSLEngine
        engine = CSLEngine()
        caps = engine.get_capabilities()
        assert "built_in_styles" in caps
        assert len(caps["built_in_styles"]) >= 11

    def test_resolve_style_apa(self):
        from app.pipeline.services.csl_engine import CSLEngine
        engine = CSLEngine()
        result = engine.resolve_style("apa")
        assert result["style"] == "apa"
        assert "csl_xml" in result
        assert result["source"] in ("file", "fallback", "cache")

    def test_resolve_style_ieee(self):
        from app.pipeline.services.csl_engine import CSLEngine
        engine = CSLEngine()
        result = engine.resolve_style("ieee")
        assert result["style"] == "ieee"
        assert "csl_xml" in result

    def test_resolve_style_vancouver(self):
        from app.pipeline.services.csl_engine import CSLEngine
        engine = CSLEngine()
        result = engine.resolve_style("vancouver")
        assert result["style"] == "vancouver"
        assert "csl_xml" in result

    def test_resolve_style_numeric_default(self):
        from app.pipeline.services.csl_engine import CSLEngine
        engine = CSLEngine()
        result = engine.resolve_style("unknown_style")
        assert result["style"] == "unknown_style"
        assert "csl_xml" in result

    def test_caching(self):
        from app.pipeline.services.csl_engine import CSLEngine
        engine = CSLEngine()
        result1 = engine.resolve_style("apa")
        result2 = engine.resolve_style("apa")
        assert result2["source"] == "cache"

    def test_fallback_formatters_all_styles(self):
        from app.models import Reference
        from app.pipeline.services.csl_engine import CSLEngine
        engine = CSLEngine()
        ref = Reference(
            reference_id="r1",
            citation_key="test2020",
            raw_text="Test, A. (2020). Title. Journal.",
            authors=["Test, A."],
            title="Title",
            journal="Journal",
            year=2020,
            volume="10",
            issue="2",
            pages="50-60",
            index=0,
        )
        for style in ["ieee", "apa", "vancouver", "mla", "chicago", "harvard"]:
            result = engine._format_fallback(ref, style=style)
            assert result, f"Fallback failed for style: {style}"
            assert isinstance(result, str)
