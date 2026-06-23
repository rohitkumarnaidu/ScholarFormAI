# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(os.getcwd())

try:
    print("Attempting to import app.models...")
    from app.models import Reference, PipelineDocument, DocumentMetadata
    print("✅ app.models imported successfully")
except ImportError as e:
    print(f"❌ Failed to import app.models: {e}")
    sys.exit(1)

try:
    print("Attempting to import CSLEngine...")
    from app.pipeline.services.csl_engine import CSLEngine
    engine = CSLEngine()
    print("✅ CSLEngine instantiated successfully")
except Exception as e:
    print(f"❌ Failed to instantiate CSLEngine: {e}")

try:
    print("Attempting to import TemplateRenderer...")
    from app.pipeline.formatting.template_renderer import TemplateRenderer
    renderer = TemplateRenderer()
    print("✅ TemplateRenderer instantiated successfully")
except Exception as e:
    print(f"❌ Failed to instantiate TemplateRenderer: {e}")
