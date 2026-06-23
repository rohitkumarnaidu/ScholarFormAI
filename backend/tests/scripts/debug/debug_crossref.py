# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


"""
Debug script to verify CrossRef DOI validation with real API calls.
"""
import logging
import sys
from app.pipeline.services.crossref_client import CrossRefClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_crossref")

def test_crossref():
    client = CrossRefClient(email="test@example.com")
    
    # 1. Valid DOI
    doi_valid = "10.1126/science.169.3946.635"  # Codd's Relational Model paper
    print(f"\nChecking valid DOI: {doi_valid}")
    print(f"URL: {client.BASE_URL}{doi_valid}")
    try:
        # validate_doi swallows errors, so let's try get_metadata to see what's wrong if it fails
        try:
            metadata = client.get_metadata(doi_valid)
            print(f"[OK] Exists: True")
            print(f"   Title: {metadata.get('title', [''])[0]}")
            print(f"   Publisher: {metadata.get('publisher')}")
            
            # Confidence check
            ref_data = {
                "title": "A Relational Model of Data for Large Shared Data Banks",
                "year": 1970,
                "authors": ["Codd"] 
            }
            conf = client.calculate_confidence(ref_data, metadata)
            print(f"   Confidence Score: {conf:.2f}")
        except Exception as e:
             print(f"[FAIL] Exists: False (Error: {e})")
            
    except Exception as e:
        print(f"[ERR] Error: {e}")

    # 2. Invalid DOI
    doi_invalid = "10.1000/nonexistent_doi_12345"
    print(f"\nChecking invalid DOI: {doi_invalid}")
    try:
        is_valid = client.validate_doi(doi_invalid)
        print(f"[OK] Exists: {is_valid}") # Should be False
    except Exception as e:
        print(f"[ERR] Error: {e}")

if __name__ == "__main__":
    test_crossref()
