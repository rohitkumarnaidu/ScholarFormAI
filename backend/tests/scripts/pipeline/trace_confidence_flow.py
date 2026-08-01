# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
RUNTIME TRACE ANALYSIS - Confidence Engine Verification
Traces NLP confidence flow through classifier to verify integration.
"""

from app.pipeline.classification.classifier import ContentClassifier
from app.pipeline.intelligence.semantic_parser import get_semantic_parser
from app.pipeline.normalization.normalizer import Normalizer
from app.pipeline.parsing.parser import DocxParser
from app.pipeline.structure_detection.detector import StructureDetector


def trace_confidence_flow(docx_path: str):
    """
    Detailed runtime trace of confidence flow through classifier.
    """
    print("="*80)
    print("RUNTIME TRACE ANALYSIS - CONFIDENCE ENGINE VERIFICATION")
    print("="*80)
    print()
    
    # Parse and normalize
    print("[1/5] Parsing document...")
    doc = DocxParser().parse(docx_path, 'trace_test')
    
    print("[2/5] Normalizing...")
    doc = Normalizer().process(doc)
    
    print("[3/5] Structure detection...")
    doc = StructureDetector(contracts_dir='app/pipeline/contracts').process(doc)
    
    print()
    print("="*80)
    print("BEFORE SEMANTIC PARSER")
    print("="*80)
    print()
    
    # Check metadata BEFORE SemanticParser
    print("Checking metadata BEFORE SemanticParser runs:")
    for i, block in enumerate(doc.blocks[:3]):  # First 3 blocks
        nlp_conf = block.metadata.get('nlp_confidence', 'NOT_PRESENT')
        print(f"  Block {i} [{block.block_id}]: nlp_confidence = {nlp_conf}")
    print()
    
    print("[4/5] Running SemanticParser (NLP layer)...")
    semantic_parser = get_semantic_parser()
    semantic_blocks = semantic_parser.analyze_blocks(doc.blocks)
    
    # Update block metadata with NLP predictions
    for i, b in enumerate(doc.blocks):
        if i < len(semantic_blocks):
            b.metadata["semantic_intent"] = semantic_blocks[i]["predicted_section_type"]
            b.metadata["nlp_confidence"] = semantic_blocks[i]["confidence_score"]
    
    print()
    print("="*80)
    print("AFTER SEMANTIC PARSER, BEFORE CLASSIFIER")
    print("="*80)
    print()
    
    # Check metadata AFTER SemanticParser, BEFORE Classifier
    print("Checking metadata AFTER SemanticParser, BEFORE Classifier:")
    for i, block in enumerate(doc.blocks[:3]):  # First 3 blocks
        nlp_conf = block.metadata.get('nlp_confidence', 'NOT_PRESENT')
        semantic_intent = block.metadata.get('semantic_intent', 'NOT_PRESENT')
        block_type = block.block_type.value if hasattr(block.block_type, 'value') else str(block.block_type)
        print(f"  Block {i} [{block.block_id}]:")
        print(f"    block_type: {block_type}")
        print(f"    nlp_confidence: {nlp_conf}")
        print(f"    semantic_intent: {semantic_intent}")
    print()
    
    print("[5/5] Running Classifier...")
    doc = ContentClassifier().process(doc)
    
    print()
    print("="*80)
    print("AFTER CLASSIFIER - DETAILED BLOCK ANALYSIS")
    print("="*80)
    print()
    
    # Detailed analysis of each block
    for i, block in enumerate(doc.blocks):
        block_type = block.block_type.value if hasattr(block.block_type, 'value') else str(block.block_type)
        nlp_conf = block.metadata.get('nlp_confidence', 'NOT_PRESENT')
        classification_conf = block.classification_confidence
        method = block.metadata.get('classification_method', 'NOT_PRESENT')
        text_preview = block.text[:40] + "..." if len(block.text) > 40 else block.text
        
        print(f"Block {i:2d} [{block.block_id:15s}]")
        print(f"  Text: {text_preview}")
        print(f"  block_type: {block_type}")
        print(f"  nlp_confidence: {nlp_conf}")
        print(f"  classification_confidence: {classification_conf}")
        print(f"  classification_method: {method}")
        print()
    
    print("="*80)
    print("DIAGNOSTIC ANALYSIS")
    print("="*80)
    print()
    
    # Diagnostic checks
    blocks_with_nlp = sum(1 for b in doc.blocks if b.metadata.get('nlp_confidence', 0) > 0)
    blocks_using_nlp_fallback = sum(1 for b in doc.blocks if b.metadata.get('classification_method') == 'fallback_with_nlp')
    blocks_using_last_resort = sum(1 for b in doc.blocks if b.metadata.get('classification_method') == 'fallback_last_resort')
    deterministic_blocks = sum(1 for b in doc.blocks if 'deterministic' in b.metadata.get('classification_method', '') or 'structure' in b.metadata.get('classification_method', ''))
    
    print(f"Total Blocks: {len(doc.blocks)}")
    print(f"Blocks with NLP confidence: {blocks_with_nlp}/{len(doc.blocks)}")
    print(f"Blocks using NLP fallback: {blocks_using_nlp_fallback}/{len(doc.blocks)}")
    print(f"Blocks using last resort (0.5): {blocks_using_last_resort}/{len(doc.blocks)}")
    print(f"Blocks using deterministic rules: {deterministic_blocks}/{len(doc.blocks)}")
    print()
    
    # Focus on TITLE block (blk_000)
    print("="*80)
    print("TITLE BLOCK (blk_000) DETAILED TRACE")
    print("="*80)
    print()
    
    title_block = doc.blocks[0]
    print(f"block_id: {title_block.block_id}")
    print(f"text: {title_block.text}")
    print(f"block_type: {title_block.block_type.value if hasattr(title_block.block_type, 'value') else str(title_block.block_type)}")
    print(f"nlp_confidence: {title_block.metadata.get('nlp_confidence', 'NOT_PRESENT')}")
    print(f"classification_confidence: {title_block.classification_confidence}")
    print(f"classification_method: {title_block.metadata.get('classification_method', 'NOT_PRESENT')}")
    print()
    
    # Root cause determination
    print("="*80)
    print("ROOT CAUSE DETERMINATION")
    print("="*80)
    print()
    
    # A) NLP confidence missing?
    if blocks_with_nlp == 0:
        print("❌ A) NLP CONFIDENCE MISSING")
        print("   SemanticParser is NOT populating metadata['nlp_confidence']")
        print("   This means the integration is NOT working.")
    else:
        print(f"✅ A) NLP confidence present on {blocks_with_nlp}/{len(doc.blocks)} blocks")
    print()
    
    # B) Deterministic logic not executing?
    if deterministic_blocks == 0:
        print("❌ B) DETERMINISTIC LOGIC NOT EXECUTING")
        print("   No blocks are using deterministic classification methods.")
        print("   This is a critical failure.")
    else:
        print(f"✅ B) Deterministic logic executing on {deterministic_blocks}/{len(doc.blocks)} blocks")
    print()
    
    # C) Fallback running prematurely?
    if blocks_using_last_resort > 0:
        print(" ️  C) FALLBACK RUNNING PREMATURELY")
        print(f"   {blocks_using_last_resort} blocks are using last resort fallback (0.5)")
        print("   This suggests NLP integration is NOT being used.")
    else:
        print("✅ C) No premature fallback (0 blocks using last resort)")
    print()
    
    # D) Old classifier file loaded?
    title_method = title_block.metadata.get('classification_method', 'NOT_PRESENT')
    if title_method == 'NOT_PRESENT' or 'structure' not in title_method:
        print("❌ D) OLD CLASSIFIER FILE LOADED")
        print("   TITLE block is not using 'structure_title_preserved' method.")
        print("   This suggests the old classifier code is still running.")
    else:
        print(f"✅ D) New classifier loaded (TITLE method: {title_method})")
    print()
    
    # Final verdict
    print("="*80)
    print("FINAL VERDICT")
    print("="*80)
    print()
    
    if blocks_with_nlp > 0 and blocks_using_nlp_fallback > 0:
        print("✅ NLP CONFIDENCE INTEGRATION IS WORKING")
        print(f"   - {blocks_with_nlp} blocks have NLP predictions")
        print(f"   - {blocks_using_nlp_fallback} blocks are using NLP fallback")
        print(f"   - {deterministic_blocks} blocks use deterministic rules")
    elif blocks_with_nlp > 0 and blocks_using_nlp_fallback == 0:
        print(" ️  NLP PREDICTIONS PRESENT BUT NOT USED")
        print(f"   - {blocks_with_nlp} blocks have NLP predictions")
        print("   - 0 blocks are using NLP fallback")
        print("   - This suggests deterministic rules are matching all blocks")
        print("   - This is EXPECTED if most blocks match deterministic patterns")
    else:
        print("❌ NLP CONFIDENCE INTEGRATION IS NOT WORKING")
        print(f"   - {blocks_with_nlp} blocks have NLP predictions (expected: {len(doc.blocks)})")
        print(f"   - {blocks_using_nlp_fallback} blocks are using NLP fallback")
        print("   - Integration code may not be running")

if __name__ == "__main__":
    trace_confidence_flow("uploads/132dbdae-b6e3-4936-bdb5-bc398ed0ac19.docx")
