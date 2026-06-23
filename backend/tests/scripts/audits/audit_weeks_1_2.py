# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


import os
import sys
import pytest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

def check_file(path, description):
    if os.path.exists(path):
        print(f"✅ FOUND: {description} ({path})")
        return True
    else:
        print(f"❌ MISSING: {description} ({path})")
        return False

def run_audit():
    print("🚀 Starting Week 1 & 2 Comprehensive Audit...")
    
    base_dir = str(Path(__file__).parent.parent.parent.parent)
    os.chdir(base_dir)
    
    # Week 1: Agent A (GROBID)
    print("\n--- Week 1: Agent A (GROBID) ---")
    check_file("app/pipeline/services/grobid_client.py", "GROBID Client")
    check_file("tests/test_grobid_client.py", "GROBID Tests")
    
    # Week 1: Agent B (CSL)
    print("\n--- Week 1: Agent B (CSL) ---")
    check_file("app/pipeline/services/csl_engine.py", "CSL Engine")
    check_file("app/templates/ieee/styles.csl", "IEEE CSL Style")
    check_file("app/templates/apa/styles.csl", "APA CSL Style")
    check_file("tests/test_csl_engine.py", "CSL Tests")
    
    # Week 2: Agent A (Docling)
    print("\n--- Week 2: Agent A (Docling) ---")
    check_file("app/pipeline/services/docling_client.py", "Docling Client")
    check_file("tests/test_docling_client.py", "Docling Tests")
    check_file("app/pipeline/structure_detection/detector.py", "Structure Detector (Enhanced)")
    check_file("tests/test_structure_detector_docling.py", "Structure Detector Tests")
    
    # Week 2: Agent B (docxtpl)
    print("\n--- Week 2: Agent B (docxtpl) ---")
    check_file("app/pipeline/formatting/template_renderer.py", "Template Renderer")
    check_file("tests/test_template_renderer.py", "Template Renderer Tests")
    
    # Run Tests
    print("\n--- Running All Relevant Tests ---")
    ret_code = pytest.main([
        "-v", 
        "--tb=short",
        "-m", "not integration",
        "tests/test_grobid_client.py",
        "tests/test_csl_engine.py",
        "tests/test_docling_client.py",
        "tests/test_structure_detector_docling.py",
        "tests/test_template_renderer.py"
    ])
    
    if ret_code == 0:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print(f"\n⚠️ TESTS FAILED with exit code {ret_code}")

if __name__ == "__main__":
    run_audit()
