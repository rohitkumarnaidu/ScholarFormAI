# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
POST-INTEGRATION PRODUCTION MONITORING SCRIPT
Analyzes runtime behavior after NLP confidence integration.
"""

import json
import numpy as np
from app.pipeline.parsing.parser import DocxParser
from app.pipeline.normalization.normalizer import Normalizer
from app.pipeline.structure_detection.detector import StructureDetector
from app.pipeline.classification.classifier import ContentClassifier
from app.pipeline.intelligence.semantic_parser import get_semantic_parser

def analyze_production_behavior(docx_path: str):
    """
    Comprehensive production monitoring analysis.
    """
    print("="*70)
    print("POST-INTEGRATION PRODUCTION MONITORING AUDIT")
    print("="*70)
    print()
    
    # Run pipeline with SemanticParser
    print("[1/5] Parsing document...")
    doc = DocxParser().parse(docx_path, 'monitoring_test')
    
    print("[2/5] Normalizing...")
    doc = Normalizer().process(doc)
    
    print("[3/5] Structure detection...")
    doc = StructureDetector(contracts_dir='app/pipeline/contracts').process(doc)
    
    print("[4/5] Running SemanticParser (NLP layer)...")
    semantic_parser = get_semantic_parser()
    semantic_blocks = semantic_parser.analyze_blocks(doc.blocks)
    
    # Update block metadata with NLP predictions
    for i, b in enumerate(doc.blocks):
        if i < len(semantic_blocks):
            b.metadata["semantic_intent"] = semantic_blocks[i]["predicted_section_type"]
            b.metadata["nlp_confidence"] = semantic_blocks[i]["confidence_score"]
    
    print("[5/5] Classification with NLP integration...")
    doc = ContentClassifier().process(doc)
    
    print()
    print("="*70)
    print("ANALYSIS RESULTS")
    print("="*70)
    print()
    
    # 1️⃣ Confidence Distribution Analysis
    confidences = [b.classification_confidence for b in doc.blocks]
    methods = [b.metadata.get('classification_method', 'unknown') for b in doc.blocks]
    types = [b.block_type.value if hasattr(b.block_type, 'value') else str(b.block_type) for b in doc.blocks]
    nlp_confidences = [b.metadata.get('nlp_confidence', 0.0) for b in doc.blocks]
    
    print("1️⃣  CONFIDENCE DISTRIBUTION ANALYSIS")
    print("-" * 70)
    print(f"Total Blocks: {len(doc.blocks)}")
    print(f"Min Confidence: {min(confidences):.3f}")
    print(f"Max Confidence: {max(confidences):.3f}")
    print(f"Mean Confidence: {np.mean(confidences):.3f}")
    print(f"Std Deviation: {np.std(confidences):.3f}")
    print()
    
    # Histogram
    print("Confidence Distribution:")
    bins = [(0.0, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0), (1.0, 1.01)]
    for low, high in bins:
        count = sum(1 for c in confidences if low <= c < high)
        if count > 0:
            bar = "█" * count
            print(f"  [{low:.1f}-{high:.1f}): {count:2d} blocks {bar}")
    print()
    
    # 2️⃣ CRITICAL Threshold Verification
    print("2️⃣  CRITICAL THRESHOLD VERIFICATION")
    print("-" * 70)
    critical_threshold = 0.65  # Typical threshold
    critical_violations = sum(1 for c in confidences if c < critical_threshold)
    print(f"CRITICAL Threshold: {critical_threshold}")
    print(f"Total Violations: {critical_violations}/{len(doc.blocks)}")
    print(f"Violation Rate: {(critical_violations/len(doc.blocks)*100):.1f}%")
    print(f"Lowest Confidence: {min(confidences):.3f}")
    print()
    
    # 3️⃣ Deterministic Rule Dominance
    print("3️⃣  DETERMINISTIC RULE DOMINANCE")
    print("-" * 70)
    deterministic_methods = [
        "structure_title_preserved",
        "deterministic_figure_caption_rule",
        "deterministic_table_caption_rule",
        "deterministic_affiliation_rule",
        "deterministic_author_rule",
        "structure_ref_heading",
        "structure_ref_entry"
    ]
    
    deterministic_count = sum(1 for m in methods if any(dm in m for dm in deterministic_methods))
    nlp_fallback_count = sum(1 for m in methods if m == "fallback_with_nlp")
    last_resort_count = sum(1 for m in methods if m == "fallback_last_resort")
    
    print(f"Deterministic Classifications: {deterministic_count}/{len(doc.blocks)}")
    print(f"NLP-Enhanced Fallback: {nlp_fallback_count}/{len(doc.blocks)}")
    print(f"Last Resort Fallback (0.5): {last_resort_count}/{len(doc.blocks)}")
    print()
    
    print("Deterministic Rule Integrity:")
    for block in doc.blocks:
        block_type = block.block_type.value if hasattr(block.block_type, 'value') else str(block.block_type)
        method = block.metadata.get('classification_method', 'unknown')
        
        if block_type == "title":
            status = "✅" if "structure_title" in method else "❌"
            print(f"  {status} TITLE: {method}")
        elif block_type == "figure_caption":
            status = "✅" if "deterministic_figure" in method else "❌"
            print(f"  {status} FIGURE_CAPTION: {method}")
        elif block_type == "table_caption":
            status = "✅" if "deterministic_table" in method else "❌"
            print(f"  {status} TABLE_CAPTION: {method}")
        elif block_type == "affiliation":
            status = "✅" if "deterministic_affiliation" in method else "❌"
            print(f"  {status} AFFILIATION: {method}")
    print()
    
    # 4️⃣ Structural Invariant Check
    print("4️⃣  STRUCTURAL INVARIANT REGRESSION CHECK")
    print("-" * 70)
    indices = [b.index for b in doc.blocks]
    block_ids = [b.block_id for b in doc.blocks]
    
    # Check for duplicates
    duplicate_indices = len(indices) != len(set(indices))
    duplicate_ids = len(block_ids) != len(set(block_ids))
    
    # Check ordering
    is_ordered = all(indices[i] <= indices[i+1] for i in range(len(indices)-1))
    
    print(f"✅ No duplicate indices: {not duplicate_indices}")
    print(f"✅ No duplicate block_ids: {not duplicate_ids}")
    print(f"✅ Blocks ordered by index: {is_ordered}")
    print(f"✅ Index domain preserved: {all(i >= 0 for i in indices)}")
    print()
    
    # 5️⃣ NLP Confidence Utilization
    print("5️⃣  NLP CONFIDENCE UTILIZATION CHECK")
    print("-" * 70)
    nlp_present = sum(1 for nlp_conf in nlp_confidences if nlp_conf > 0)
    nlp_used = sum(1 for m in methods if m == "fallback_with_nlp")
    
    print(f"Blocks with NLP predictions: {nlp_present}/{len(doc.blocks)}")
    print(f"Blocks using NLP confidence: {nlp_used}/{len(doc.blocks)}")
    print()
    
    print("NLP Integration Status:")
    for i, block in enumerate(doc.blocks):
        nlp_conf = block.metadata.get('nlp_confidence', 0.0)
        method = block.metadata.get('classification_method', 'unknown')
        conf = block.classification_confidence
        
        if method == "fallback_with_nlp":
            status = "✅" if conf > 0.5 else "⚠️"
            print(f"  {status} Block {i}: NLP={nlp_conf:.3f}, Final={conf:.3f}, Method={method}")
    
    if nlp_used == 0:
        print("  ⚠️  WARNING: No blocks using NLP confidence!")
        print("  This suggests SemanticParser predictions are not being integrated.")
    print()
    
    # Final Verdict
    print("="*70)
    print("FINAL MONITORING VERDICT")
    print("="*70)
    print()
    
    # Stability checks
    uniform_pattern = np.std(confidences) < 0.1
    critical_reduced = critical_violations < 3  # Expect <20% violations
    no_invariant_regression = not duplicate_indices and not duplicate_ids and is_ordered
    deterministic_preserved = deterministic_count >= 10  # Most blocks should be deterministic
    nlp_integrated = nlp_used > 0
    
    print(f"✅ No uniform fallback pattern: {not uniform_pattern}")
    print(f"✅ CRITICAL violations reduced: {critical_reduced} ({critical_violations} violations)")
    print(f"✅ No invariant regressions: {no_invariant_regression}")
    print(f"✅ Deterministic rules preserved: {deterministic_preserved} ({deterministic_count} blocks)")
    print(f"{'✅' if nlp_integrated else '❌'} NLP confidence integrated: {nlp_integrated} ({nlp_used} blocks)")
    print()
    
    if all([not uniform_pattern, critical_reduced, no_invariant_regression, deterministic_preserved]):
        if nlp_integrated:
            print("🎯 VERDICT: STABLE ✅")
            print("System is functioning correctly with NLP integration.")
        else:
            print("⚠️  VERDICT: STABLE (NLP NOT INTEGRATED)")
            print("System is stable but NLP predictions are not being used.")
    else:
        print("❌ VERDICT: UNSTABLE")
        print("System has regressions or integration issues.")
    print()
    
    # Detailed block analysis
    print("="*70)
    print("DETAILED BLOCK ANALYSIS")
    print("="*70)
    print()
    for i, block in enumerate(doc.blocks):
        block_type = block.block_type.value if hasattr(block.block_type, 'value') else str(block.block_type)
        method = block.metadata.get('classification_method', 'unknown')
        conf = block.classification_confidence
        nlp_conf = block.metadata.get('nlp_confidence', 0.0)
        text_preview = block.text[:50] + "..." if len(block.text) > 50 else block.text
        
        print(f"Block {i:2d} [{block_type:20s}] Conf={conf:.3f} NLP={nlp_conf:.3f} Method={method}")
        print(f"         Text: {text_preview}")
        print()

if __name__ == "__main__":
    analyze_production_behavior("uploads/132dbdae-b6e3-4936-bdb5-bc398ed0ac19.docx")
