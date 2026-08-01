# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import os
import sys

import yaml

# Add backend to path to import app
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.pipeline.intelligence.rag_engine import get_rag_engine


def ingest_all_guidelines(contracts_dir: str = "backend/app/pipeline/contracts"):
    rag = get_rag_engine()
    rag.reset()
    
    for publisher in os.listdir(contracts_dir):
        pub_path = os.path.join(contracts_dir, publisher)
        if not os.path.isdir(pub_path):
            continue
            
        contract_file = os.path.join(pub_path, "contract.yaml")
        if not os.path.exists(contract_file):
            continue
            
        print(f"Ingesting {publisher} guidelines...")
        try:
            with open(contract_file) as f:
                contract = yaml.safe_load(f)
                
            # 1. Ingest Section Requirements
            sections = contract.get("sections", {})
            required_list = sections.get("required", [])
            for req in required_list:
                rule_text = f"Guidelines for {req} in {publisher}: This section is MANDATORY. Failure to include it will cause validation errors."
                rag.add_guideline(publisher, req, rule_text)
                
            # 2. Ingest Style Rules (Conceptual)
            styles = contract.get("styles", {})
            for style_name, font_info in styles.items():
                rule_text = f"Style requirement for {style_name} in {publisher}: Uses {font_info} formatting."
                rag.add_guideline(publisher, f"style_{style_name}", rule_text)
                
            # 3. Ingest Reference Style
            refs = contract.get("references", {})
            if refs:
                ref_style = refs.get("style", "Standard")
                rule_text = f"Reference formatting for {publisher}: Must follow {ref_style} citation standards."
                rag.add_guideline(publisher, "references", rule_text)
                
        except Exception as e:
            print(f"Error ingesting {publisher}: {e}")

if __name__ == "__main__":
    # Ensure we run from the project root
    ingest_all_guidelines()
    print("Ingestion complete.")
