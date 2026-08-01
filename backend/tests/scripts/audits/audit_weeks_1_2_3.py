# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Comprehensive Week 1-3 Audit Script
Verifies all components from parallel implementation plan are complete.
"""

from pathlib import Path

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def check_file(path, description):
    """Check if a file exists and return status."""
    if Path(path).exists():
        print(f"{GREEN}✅ FOUND{RESET}: {description} ({path})")
        return True
    else:
        print(f"{RED}❌ MISSING{RESET}: {description} ({path})")
        return False

def main():
    print("=" * 80)
    print("🔍 COMPREHENSIVE WEEK 1-3 AUDIT")
    print("=" * 80)
    
    results = {
        "week1_agent_a": [],
        "week1_agent_b": [],
        "week2_agent_a": [],
        "week2_agent_b": [],
        "week3_agent_a": [],
        "week3_agent_b": []
    }
    
    # ========== WEEK 1: PARALLEL SETUP ==========
    print("\n" + "=" * 80)
    print("📅 WEEK 1: PARALLEL SETUP")
    print("=" * 80)
    
    print("\n--- Agent A: GROBID Integration ---")
    results["week1_agent_a"].append(check_file(
        "app/pipeline/services/grobid_client.py",
        "GROBID Client"
    ))
    results["week1_agent_a"].append(check_file(
        "tests/test_grobid_client.py",
        "GROBID Tests"
    ))
    
    print("\n--- Agent B: CSL Citation Engine ---")
    results["week1_agent_b"].append(check_file(
        "app/pipeline/services/csl_engine.py",
        "CSL Engine"
    ))
    results["week1_agent_b"].append(check_file(
        "app/templates/ieee/styles.csl",
        "IEEE CSL Style"
    ))
    results["week1_agent_b"].append(check_file(
        "app/templates/apa/styles.csl",
        "APA CSL Style"
    ))
    results["week1_agent_b"].append(check_file(
        "tests/test_csl_engine.py",
        "CSL Tests"
    ))
    
    # ========== WEEK 2: CORE COMPONENTS ==========
    print("\n" + "=" * 80)
    print("📅 WEEK 2: CORE COMPONENTS")
    print("=" * 80)
    
    print("\n--- Agent A: Docling Layout Analysis ---")
    results["week2_agent_a"].append(check_file(
        "app/pipeline/services/docling_client.py",
        "Docling Client"
    ))
    results["week2_agent_a"].append(check_file(
        "tests/test_docling_client.py",
        "Docling Tests"
    ))
    results["week2_agent_a"].append(check_file(
        "app/pipeline/structure_detection/detector.py",
        "Structure Detector (Enhanced)"
    ))
    results["week2_agent_a"].append(check_file(
        "tests/test_structure_detector_docling.py",
        "Structure Detector Tests"
    ))
    
    print("\n--- Agent B: docxtpl Template Rendering ---")
    results["week2_agent_b"].append(check_file(
        "app/pipeline/formatting/template_renderer.py",
        "Template Renderer"
    ))
    results["week2_agent_b"].append(check_file(
        "tests/test_template_renderer.py",
        "Template Renderer Tests"
    ))
    
    # ========== WEEK 3: REFINEMENT ==========
    print("\n" + "=" * 80)
    print("📅 WEEK 3: REFINEMENT")
    print("=" * 80)
    
    print("\n--- Agent A: Remove Hard Guards ---")
    # Check for soft guards in heading_rules.py
    heading_rules_path = Path("app/pipeline/structure_detection/heading_rules.py")
    if heading_rules_path.exists():
        content = heading_rules_path.read_text()
        has_hard_guard = "if len(text) > 120:\n        return None" in content or "if len(text) > 120:\n        return False" in content
        if not has_hard_guard:
            print(f"{GREEN}✅ VERIFIED{RESET}: Hard guards removed from heading_rules.py")
            results["week3_agent_a"].append(True)
        else:
            print(f"{RED}❌ INCOMPLETE{RESET}: Hard guards still present in heading_rules.py")
            results["week3_agent_a"].append(False)
    else:
        print(f"{RED}❌ MISSING{RESET}: heading_rules.py not found")
        results["week3_agent_a"].append(False)
    
    # Check classifier.py for comma requirement removal
    classifier_path = Path("app/pipeline/classification/classifier.py")
    if classifier_path.exists():
        content = classifier_path.read_text()
        has_comma_requirement = "if ',' in text and 2 <= len(cap_words)" in content
        if not has_comma_requirement:
            print(f"{GREEN}✅ VERIFIED{RESET}: Comma requirement removed from classifier.py")
            results["week3_agent_a"].append(True)
        else:
            print(f"{YELLOW} ️  WARNING{RESET}: Comma requirement may still be present in classifier.py")
            results["week3_agent_a"].append(False)
    else:
        print(f"{RED}❌ MISSING{RESET}: classifier.py not found")
        results["week3_agent_a"].append(False)
    
    print("\n--- Agent B: Template Conversion ---")
    # Check for .docx templates
    ieee_template = check_file("app/templates/ieee/template.docx", "IEEE Template (docx)")
    apa_template = check_file("app/templates/apa/template.docx", "APA Template (docx)")
    results["week3_agent_b"].append(ieee_template)
    results["week3_agent_b"].append(apa_template)
    
    # ========== SUMMARY ==========
    print("\n" + "=" * 80)
    print("📊 AUDIT SUMMARY")
    print("=" * 80)
    
    def calculate_completion(results_list):
        if not results_list:
            return 0
        return (sum(results_list) / len(results_list)) * 100
    
    week1_a_pct = calculate_completion(results["week1_agent_a"])
    week1_b_pct = calculate_completion(results["week1_agent_b"])
    week2_a_pct = calculate_completion(results["week2_agent_a"])
    week2_b_pct = calculate_completion(results["week2_agent_b"])
    week3_a_pct = calculate_completion(results["week3_agent_a"])
    week3_b_pct = calculate_completion(results["week3_agent_b"])
    
    print(f"\nWeek 1 - Agent A (GROBID):           {week1_a_pct:.0f}% ({sum(results['week1_agent_a'])}/{len(results['week1_agent_a'])})")
    print(f"Week 1 - Agent B (CSL):              {week1_b_pct:.0f}% ({sum(results['week1_agent_b'])}/{len(results['week1_agent_b'])})")
    print(f"Week 2 - Agent A (Docling):          {week2_a_pct:.0f}% ({sum(results['week2_agent_a'])}/{len(results['week2_agent_a'])})")
    print(f"Week 2 - Agent B (docxtpl):          {week2_b_pct:.0f}% ({sum(results['week2_agent_b'])}/{len(results['week2_agent_b'])})")
    print(f"Week 3 - Agent A (Hard Guards):      {week3_a_pct:.0f}% ({sum(results['week3_agent_a'])}/{len(results['week3_agent_a'])})")
    print(f"Week 3 - Agent B (Templates):        {week3_b_pct:.0f}% ({sum(results['week3_agent_b'])}/{len(results['week3_agent_b'])})")
    
    overall_pct = calculate_completion([
        item for sublist in results.values() for item in sublist
    ])
    
    print(f"\n{'='*80}")
    print(f"OVERALL COMPLETION: {overall_pct:.1f}%")
    print(f"{'='*80}")
    
    if overall_pct == 100:
        print(f"\n{GREEN}🎉 ALL WEEKS COMPLETE! Ready to proceed to next phase.{RESET}")
        return 0
    elif overall_pct >= 80:
        print(f"\n{YELLOW} ️  MOSTLY COMPLETE. Review missing items before proceeding.{RESET}")
        return 1
    else:
        print(f"\n{RED}❌ INCOMPLETE. Significant work remaining.{RESET}")
        return 2

if __name__ == "__main__":
    exit(main())
