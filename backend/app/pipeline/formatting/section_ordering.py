# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


from app.models import PipelineDocument as Document
from app.pipeline.contracts.loader import ContractLoader


class SectionOrderValidator:
    """
    Validates the sequence of sections against contract rules.
    """

    def __init__(self, contract_loader: ContractLoader):
        self.contract_loader = contract_loader

    def validate_order(self, document: Document, publisher: str) -> list[str]:
        """
        Identify out-of-order or missing sections.
        """
        contract = self.contract_loader.load(publisher)
        expected_order = contract.get("sections", {}).get("order", [])

        found_sections = []
        for block in document.blocks:
            if block.is_heading() and block.section_name:
                normalized_name = block.section_name.lower()
                if normalized_name not in found_sections:
                    found_sections.append(normalized_name)

        violations = []
        # Check for missing required sections
        required = contract.get("sections", {}).get("required", [])
        for req in required:
            if req.lower() not in found_sections:
                violations.append(f"Missing required section: {req}")

        # Check order (relative positions)
        last_index = -1
        for section in found_sections:
            if section in [s.lower() for s in expected_order]:
                current_index = [s.lower() for s in expected_order].index(section)
                if current_index < last_index:
                    violations.append(f"Section out of order: {section.title()}")
                last_index = current_index

        return violations
