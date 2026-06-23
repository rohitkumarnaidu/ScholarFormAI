# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from app.pipeline.parsing.md_parser import MarkdownParser

parser = MarkdownParser()
print(f"Checking methods on MarkdownParser...")
if hasattr(parser, '_create_paragraph_block'):
    print("SUCCESS: _create_paragraph_block exists.")
else:
    print("ERROR: _create_paragraph_block is MISSING.")

if hasattr(parser, '_create_paragraph_block_internal'):
    print("WARNING: _create_paragraph_block_internal still exists.")
else:
    print("CLEAN: _create_paragraph_block_internal is gone.")

content = "Test paragraph."
try:
    blocks, _ = parser._extract_content(content)
    print(f"Successfully extracted {len(blocks)} blocks.")
    for i, b in enumerate(blocks):
        print(f"Block {i}: {b.text}")
except Exception as e:
    print(f"CRITICAL ERROR during extraction: {e}")
