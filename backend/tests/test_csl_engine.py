# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Unit tests for CSL reference formatting engine.
"""

from app.models import Reference, ReferenceType
from app.pipeline.contracts.loader import ContractLoader
from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
from app.pipeline.services.csl_engine import CSLEngine


def _sample_reference(reference_id: str, index: int, title_suffix: str = "") -> Reference:
    suffix = f" {title_suffix}" if title_suffix else ""
    return Reference(
        reference_id=reference_id,
        citation_key=f"ref_{index + 1}",
        raw_text=f"[{index + 1}] J. Smith, A. Doe, Deep Learning for Signals{suffix}, 2024.",
        reference_type=ReferenceType.JOURNAL_ARTICLE,
        authors=["Smith, John", "Doe, Alice"],
        title=f"Deep Learning for Signals{suffix}",
        journal="IEEE Transactions on Signal Processing",
        year=2024,
        volume="72",
        issue="4",
        pages="100-110",
        doi="10.1109/TSP.2024.1234567",
        index=index,
    )


def test_csl_engine_formats_ieee_reference():
    engine = CSLEngine()
    ref = _sample_reference("ref_001", 0)

    formatted = engine.format_reference(ref, style="ieee")

    assert isinstance(formatted, str)
    assert formatted.strip()
    assert "Deep Learning for Signals" in formatted
    assert "2024" in formatted


def test_csl_engine_formats_apa_reference():
    engine = CSLEngine()
    ref = _sample_reference("ref_001", 0)

    formatted = engine.format_reference(ref, style="apa")

    assert isinstance(formatted, str)
    assert formatted.strip()
    assert "Deep Learning for Signals" in formatted
    assert "2024" in formatted
    assert "Smith" in formatted


def test_csl_engine_formats_multiple_references():
    engine = CSLEngine()
    refs = [
        _sample_reference("ref_001", 0, title_suffix="A"),
        _sample_reference("ref_002", 1, title_suffix="B"),
    ]

    formatted = engine.format_references(refs, style="ieee")

    assert len(formatted) == 2
    assert all(entry.strip() for entry in formatted)
    assert "Signals A" in formatted[0]
    assert "Signals B" in formatted[1]


def test_reference_formatter_engine_uses_csl_wrapper():
    loader = ContractLoader(contracts_dir="app/pipeline/contracts")
    formatter_engine = ReferenceFormatterEngine(contract_loader=loader, csl_engine=CSLEngine())
    refs = [_sample_reference("ref_001", 0)]

    formatted_refs = formatter_engine.format_all(refs, publisher="ieee")

    assert len(formatted_refs) == 1
    assert formatted_refs[0].formatted_text is not None
    assert "Deep Learning for Signals" in formatted_refs[0].formatted_text


def test_csl_engine_reports_10k_plus_style_support():
    engine = CSLEngine()
    capabilities = engine.get_capabilities()

    assert capabilities["supports_external_csl_files"] is True
    assert capabilities["estimated_available_styles"] >= 10_000
    assert engine.supports_10k_plus_styles() is True


def test_builtin_ieee_and_apa_csl_files_exist():
    engine = CSLEngine()

    assert engine.resolve_style_path("ieee").is_file()
    assert engine.resolve_style_path("apa").is_file()
