# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Regression checks for template DOCX assets and layout contracts.
"""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pytest
import yaml

from app.pipeline.formatting.template_renderer import TemplateRenderer

TEMPLATES_ROOT = Path("app/templates")
PIPELINE_CONTRACTS_ROOT = Path("app/pipeline/contracts")


def _contract_template_names(root: Path) -> list[str]:
    names = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        if (entry / "contract.yaml").exists():
            names.append(entry.name)
    return names


def _load_contract(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _assert_layout_block(contract: dict, source_label: str) -> None:
    layout = contract.get("layout")
    assert isinstance(layout, dict) and layout, f"{source_label} missing non-empty layout block"

    for key in ("default_columns", "margins", "section_overrides", "spacing"):
        assert key in layout, f"{source_label} layout missing '{key}'"

    margins = layout.get("margins") or {}
    for key in ("top", "bottom", "left", "right"):
        assert key in margins, f"{source_label} layout.margins missing '{key}'"


TEMPLATE_NAMES = _contract_template_names(TEMPLATES_ROOT)
PIPELINE_CONTRACT_NAMES = _contract_template_names(PIPELINE_CONTRACTS_ROOT)


def test_template_and_pipeline_contract_sets_match():
    assert set(TEMPLATE_NAMES) == set(PIPELINE_CONTRACT_NAMES)


@pytest.mark.parametrize("template_name", TEMPLATE_NAMES)
def test_template_docx_contains_jinja_markers(template_name: str):
    renderer = TemplateRenderer(templates_dir=str(TEMPLATES_ROOT))
    template_path = TEMPLATES_ROOT / template_name / "template.docx"
    assert template_path.exists(), f"Missing template DOCX: {template_path}"
    assert renderer._has_template_markers(template_path), (
        f"Template {template_name} has no detectable Jinja markers"
    )


@pytest.mark.parametrize("template_name", TEMPLATE_NAMES)
def test_template_contract_contains_layout_core(template_name: str):
    contract_path = TEMPLATES_ROOT / template_name / "contract.yaml"
    assert contract_path.exists(), f"Missing template contract: {contract_path}"
    contract = _load_contract(contract_path)
    _assert_layout_block(contract, f"app/templates/{template_name}/contract.yaml")


@pytest.mark.parametrize("template_name", PIPELINE_CONTRACT_NAMES)
def test_pipeline_contract_contains_layout_core(template_name: str):
    contract_path = PIPELINE_CONTRACTS_ROOT / template_name / "contract.yaml"
    assert contract_path.exists(), f"Missing pipeline contract: {contract_path}"
    contract = _load_contract(contract_path)
    _assert_layout_block(contract, f"app/pipeline/contracts/{template_name}/contract.yaml")


@pytest.mark.parametrize("template_name", TEMPLATE_NAMES)
def test_template_render_smoke_has_no_unresolved_jinja(template_name: str, full_doc, tmp_path):
    renderer = TemplateRenderer(templates_dir=str(TEMPLATES_ROOT))
    full_doc.metadata.title = f"Smoke Test {template_name}"
    rendered = renderer.render(full_doc, template_name=template_name)

    out_path = tmp_path / f"{template_name}_smoke.docx"
    rendered.save(str(out_path))

    with ZipFile(out_path, "r") as archive:
        for xml_name in archive.namelist():
            if not xml_name.startswith("word/") or not xml_name.endswith(".xml"):
                continue
            xml = archive.read(xml_name).decode("utf-8", errors="ignore")
            assert "{{" not in xml
            assert "{%" not in xml
