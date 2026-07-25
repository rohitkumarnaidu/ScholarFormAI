# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
ScholarForm AI — Documentation Update Script
Last Updated: July 2026
Status: ✅ Complete
Owner: Docs Team

Automates replacement of stale technology references across docs.
"""

import os

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(DOCS_DIR, "artifacts")

REPLACEMENTS = {
    "Vite": "Next.js",
    "vite": "Next.js",
    "5173": "3000",
    "Python 3.11+": "Python 3.12+",
    "Python 3.11": "Python 3.12",
    "Python 3.11.9": "Python 3.12",
    "25 page routes": "34 page routes",
    "Spring Boot gateway": "FastAPI backend",
    "Spring Boot": "FastAPI",
}

def update_file(filepath):
    if not os.path.exists(filepath): return
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    for old, new in REPLACEMENTS.items():
        content = content.replace(old, new)
        
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

for filename in ["PRD.md", "Features.md", "TechStack.md", "API.md", "Architecture.md", "Security.md", "Deployment.md", "UIUX.md"]:
    update_file(os.path.join(DOCS_DIR, filename))
    update_file(os.path.join(ARTIFACTS_DIR, filename))

print("Docs updated successfully!")
