# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
print("Starting check_docling.py")
start = time.time()

print("Importing app.pipeline.services.docling_client...")
try:
    from app.pipeline.services.docling_client import DoclingClient
    print(f"Imported DoclingClient in {time.time() - start:.2f}s")
except ImportError as e:
    print(f"Failed to import: {e}")
except Exception as e:
    print(f"Error during import: {e}")

print("Initializing DoclingClient...")
try:
    client = DoclingClient()
    print(f"Initialized in {time.time() - start:.2f}s")
    print(f"Available: {client.is_available()}")
except Exception as e:
    print(f"Error during init: {e}")

print("Done.")
