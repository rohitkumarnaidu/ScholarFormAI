# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Contract Loading Verification Script
Tests all 4 templates to ensure they load without errors.
"""

from app.pipeline.contracts.loader import ContractLoader

def verify_all_contracts():
    """Verify all publisher contracts load correctly."""
    
    contracts_dir = "app/pipeline/contracts"
    loader = ContractLoader(contracts_dir=contracts_dir)
    
    templates = ["none", "ieee", "apa", "springer"]
    results = {}
    
    print("="*80)
    print("CONTRACT LOADING VERIFICATION")
    print("="*80)
    print()
    
    for template in templates:
        print(f"Testing: {template.upper()}")
        print("-" * 40)
        
        if template == "none":
            print("  Status: BYPASS (no contract file)")
            results[template] = {
                "loads": True,
                "bypass": True,
                "error": None
            }
            print()
            continue
        
        try:
            contract = loader.load(template)
            
            # Verify key sections exist
            has_sections = "sections" in contract
            has_numbering = "numbering" in contract
            has_styles = "styles" in contract
            has_references = "references" in contract
            has_layout = "layout" in contract
            has_equations = "equations" in contract
            
            print(f"  ✅ Contract loaded successfully")
            print(f"  Publisher: {contract.get('publisher', 'N/A')}")
            print(f"  Description: {contract.get('description', 'N/A')}")
            print(f"  Has sections: {has_sections}")
            print(f"  Has numbering: {has_numbering}")
            print(f"  Has styles: {has_styles}")
            print(f"  Has references: {has_references}")
            print(f"  Has layout: {has_layout}")
            print(f"  Has equations: {has_equations}")
            
            complete = all([has_sections, has_numbering, has_styles, has_references, has_layout, has_equations])
            print(f"  Complete: {'✅ YES' if complete else '❌ NO'}")
            
            results[template] = {
                "loads": True,
                "bypass": False,
                "complete": complete,
                "sections": has_sections,
                "numbering": has_numbering,
                "styles": has_styles,
                "references": has_references,
                "layout": has_layout,
                "equations": has_equations,
                "error": None
            }
            
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            results[template] = {
                "loads": False,
                "bypass": False,
                "error": str(e)
            }
        
        print()
    
    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print()
    
    all_load = all(r["loads"] for r in results.values())
    complete_count = sum(1 for r in results.values() if r.get("complete", False))
    
    print(f"Templates tested: {len(templates)}")
    print(f"All load successfully: {'✅ YES' if all_load else '❌ NO'}")
    print(f"Complete contracts: {complete_count}/3 (excluding 'none')")
    print()
    
    for template, result in results.items():
        if result["bypass"]:
            status = "✅ BYPASS"
        elif result["loads"] and result.get("complete", False):
            status = "✅ COMPLETE"
        elif result["loads"]:
            status = " ️  PARTIAL"
        else:
            status = "❌ FAILED"
        
        print(f"  {template.upper():12s} {status}")
    
    print()
    print("="*80)
    
    if all_load and complete_count == 3:
        print("✅ ALL TEMPLATES PRODUCTION READY")
    else:
        print(" ️  CONTRACT INCOMPLETE")
    
    print("="*80)
    
    return results

if __name__ == "__main__":
    verify_all_contracts()
