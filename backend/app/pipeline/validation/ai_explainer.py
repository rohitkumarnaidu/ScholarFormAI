# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from typing import Dict, Any, List

class AIExplainer:
    """
    Provides natural language explanations for validation results.
    Complies with safety guidelines: Non-destructive, Explanation ONLY.
    """
    
    def __init__(self):
        # In a real app, this would use an LLM prompt
        self.explanation_map = {
            "missing_sections": "It looks like your manuscript is missing some mandatory sections required by {publisher}. Specifically, {details} should be included to meet the submission standards.",
            "citation_format": "The citations in your document don't match the {publisher} style. We recommend using numerical brackets like [1] for IEEE, or Author-Year for APA.",
            "figure_captions": "Figures detected in your document are missing properly formatted captions. Every figure should have a 'Fig. N' label below it.",
            "reference_completeness": "Some references appear to have incomplete metadata (missing DOI or Year). Providing full metadata improves the credibility of your scientific work."
        }

    def explain_results(self, validation_results: Dict[str, Any], publisher: str = "IEEE") -> List[str]:
        """
        Generate a list of helpful explanations based on JSON validation results.
        """
        explanations = []
        errors = validation_results.get("errors", [])
        
        for error in errors:
            if isinstance(error, str):
                # Simple heuristic for string errors
                category = "general"
                if "missing" in error.lower() or "section" in error.lower():
                    category = "missing_sections"
                elif "reference" in error.lower():
                    category = "reference_completeness"
                
                template = self.explanation_map.get(category, "There is a formatting error: {details}")
                explanations.append(template.format(publisher=publisher, details=error))
            else:
                # Handle dictionary errors if any
                category = error.get("category", "general")
                template = self.explanation_map.get(category, "There is a formatting error in your {category} section.")
                explanations.append(template.format(
                    publisher=publisher, 
                    category=category, 
                    details=error.get("message", "Check formatting details.")
                ))
            
        return explanations
