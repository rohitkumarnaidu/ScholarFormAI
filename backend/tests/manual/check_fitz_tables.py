# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


try:
    import fitz
    print(f"PyMuPDF Version: {fitz.__version__}")
    
    # Check if find_tables exists
    doc = fitz.open()
    page = doc.new_page()
    if hasattr(page, "find_tables"):
        print("SUCCESS: find_tables is available")
    else:
        print("FAILURE: find_tables is NOT available")
        
except ImportError:
    print("PyMuPDF not installed")
except Exception as e:
    print(f"Error: {e}")
