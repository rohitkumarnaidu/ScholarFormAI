# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Dedicated tests for the Equation model.

Covers construction, serialization, content representations, and defaults.
"""

from __future__ import annotations


class TestEquationMinimumFields:
    def test_creation_with_minimum_fields(self):
        from app.models.equation import Equation

        eq = Equation(equation_id="eqn_min", index=5)
        assert eq.equation_id == "eqn_min"
        assert eq.index == 5
        assert eq.text is None
        assert eq.mathml is None
        assert eq.omml is None
        assert eq.is_block is True

    def test_default_number_is_none(self):
        from app.models.equation import Equation

        eq = Equation(equation_id="eqn_def", index=0)
        assert eq.number is None
        assert eq.get_display_number() == ""

    def test_default_block_id_is_none(self):
        from app.models.equation import Equation

        eq = Equation(equation_id="eqn_def", index=0)
        assert eq.block_id is None

    def test_default_referenced_by_is_empty(self):
        from app.models.equation import Equation

        eq = Equation(equation_id="eqn_def", index=0)
        assert eq.referenced_by == []

    def test_default_metadata_is_empty(self):
        from app.models.equation import Equation

        eq = Equation(equation_id="eqn_def", index=0)
        assert eq.metadata == {}


class TestEquationAllFields:
    def test_creation_with_all_fields(self):
        from app.models.equation import Equation

        eq = Equation(
            equation_id="eqn_full",
            number="(42)",
            text="E = mc^2",
            mathml="<math><mi>E</mi><mo>=</mo><mi>m</mi><msup><mi>c</mi><mn>2</mn></msup></math>",
            omml="<m:oMath><m:r><m:t>E=mc^2</m:t></m:r></m:oMath>",
            is_block=False,
            index=1,
            block_id="blk_eq_001",
            referenced_by=["blk_001", "blk_002"],
            metadata={"font_size": 12, "style": "italic"},
        )
        assert eq.equation_id == "eqn_full"
        assert eq.number == "(42)"
        assert eq.text == "E = mc^2"
        assert eq.mathml is not None
        assert eq.omml is not None
        assert eq.is_block is False
        assert eq.index == 1
        assert eq.block_id == "blk_eq_001"
        assert eq.referenced_by == ["blk_001", "blk_002"]
        assert eq.metadata["font_size"] == 12


class TestEquationSerialization:
    def test_serialization_roundtrip(self):
        from app.models.equation import Equation

        eq = Equation(
            equation_id="eqn_ser",
            number="(7)",
            text="x = y",
            mathml="<math><mi>x</mi><mo>=</mo><mi>y</mi></math>",
            index=2,
        )
        data = eq.model_dump(mode="json")
        restored = Equation(**data)
        assert restored.equation_id == eq.equation_id
        assert restored.number == eq.number
        assert restored.text == eq.text
        assert restored.mathml == eq.mathml
        assert restored.index == eq.index
        assert restored.is_block == eq.is_block

    def test_serialization_includes_metadata(self):
        from app.models.equation import Equation

        eq = Equation(
            equation_id="eqn_meta",
            index=3,
            metadata={"source": "latex", "confidence": 0.98},
        )
        data = eq.model_dump(mode="json")
        assert data["metadata"]["source"] == "latex"
        assert data["metadata"]["confidence"] == 0.98


class TestEquationContent:
    def test_with_mathml_content(self):
        from app.models.equation import Equation

        eq = Equation(
            equation_id="eqn_mml",
            mathml="<math><mrow><mi>a</mi><mo>+</mo><mi>b</mi><mo>=</mo><mi>c</mi></mrow></math>",
            index=4,
        )
        assert eq.has_content() is True
        assert eq.text is None

    def test_with_omml_content(self):
        from app.models.equation import Equation

        eq = Equation(
            equation_id="eqn_omml",
            omml="<m:oMath><m:r><m:t>a+b</m:t></m:r></m:oMath>",
            index=5,
        )
        assert eq.has_content() is True
        assert eq.mathml is None

    def test_with_empty_text(self):
        from app.models.equation import Equation

        eq = Equation(
            equation_id="eqn_empty",
            text="",
            index=6,
        )
        assert eq.has_content() is False

    def test_with_all_three_representations(self):
        from app.models.equation import Equation

        eq = Equation(
            equation_id="eqn_all",
            text="x=1",
            mathml="<math><mi>x</mi><mo>=</mo><mn>1</mn></math>",
            omml="<m:oMath><m:r><m:t>x=1</m:t></m:r></m:oMath>",
            index=7,
        )
        assert eq.has_content() is True
        assert eq.text == "x=1"
        assert eq.mathml is not None
        assert eq.omml is not None

    def test_no_content_at_all(self):
        from app.models.equation import Equation

        eq = Equation(equation_id="eqn_none", index=8)
        assert eq.has_content() is False


class TestEquationMethods:
    def test_get_display_number_with_number(self):
        from app.models.equation import Equation

        eq = Equation(equation_id="eqn_dn", number="(1)", index=0)
        assert eq.get_display_number() == "(1)"

    def test_get_display_number_empty_default(self):
        from app.models.equation import Equation

        eq = Equation(equation_id="eqn_dn2", index=0)
        assert eq.get_display_number() == ""

    def test_is_block_defaults_true(self):
        from app.models.equation import Equation

        eq = Equation(equation_id="eqn_block", index=0)
        assert eq.is_block is True

    def test_is_block_false_for_inline(self):
        from app.models.equation import Equation

        eq = Equation(equation_id="eqn_inline", index=0, is_block=False)
        assert eq.is_block is False
