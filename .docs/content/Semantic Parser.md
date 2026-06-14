# Semantic Parser

<cite>
**Referenced Files in This Document**
- [semantic_parser.py](file://backend/app/pipeline/intelligence/semantic_parser.py)
- [classifier.py](file://backend/app/pipeline/classification/classifier.py)
- [orchestrator.py](file://backend/app/pipeline/orchestrator.py)
- [block.py](file://backend/app/models/block.py)
- [settings.py](file://backend/app/config/settings.py)
- [model_store.py](file://backend/app/services/model_store.py)
- [singleton.py](file://backend/app/utils/singleton.py)
- [test_semantic_parser.py](file://backend/tests/test_semantic_parser.py)
- [default_guidelines.json](file://backend/app/pipeline/intelligence/default_guidelines.json)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
The Semantic Parser is a foundational Natural Language Processing (NLP) component responsible for structural analysis and semantic classification of manuscript blocks. It leverages a local SciBERT model to identify document sections such as abstracts, methodologies, conclusions, references, figures, tables, acknowledgments, and equations. The component operates as a safety-guarded interface adapter between the document pipeline and AI-powered classification, providing robust fallback mechanisms for reliability and performance.

## Project Structure
The Semantic Parser resides within the intelligence layer of the document processing pipeline and integrates with multiple pipeline stages:

```mermaid
graph TB
subgraph "Pipeline Intelligence Layer"
SP[SemanticParser]
CE[ContentClassifier]
CA[ContentAnalyzer]
end
subgraph "Pipeline Stages"
EX[Extraction]
SD[StructureDetection]
CL[Classification]
VL[Validation]
FM[Formatting]
end
subgraph "Configuration"
ST[Settings]
MS[ModelStore]
SG[Singleton]
end
EX --> SD
SD --> SP
SP --> CL
CL --> CE
CE --> VL
VL --> FM
SP --> ST
SP --> MS
SP --> SG
CE --> ST
CE --> MS
CE --> SG
```

**Diagram sources**
- [semantic_parser.py:48-328](file://backend/app/pipeline/intelligence/semantic_parser.py#L48-L328)
- [classifier.py:22-830](file://backend/app/pipeline/classification/classifier.py#L22-L830)
- [orchestrator.py:472-492](file://backend/app/pipeline/orchestrator.py#L472-L492)

**Section sources**
- [semantic_parser.py:48-328](file://backend/app/pipeline/intelligence/semantic_parser.py#L48-L328)
- [classifier.py:22-830](file://backend/app/pipeline/classification/classifier.py#L22-L830)
- [orchestrator.py:472-492](file://backend/app/pipeline/orchestrator.py#L472-L492)

## Core Components
The Semantic Parser consists of several key components working together to provide reliable semantic analysis:

### SemanticParser Class
The main class implements:
- Lazy model loading with global ModelStore integration
- Dual-mode operation (transformer-based and heuristic fallback)
- Fragmented heading repair logic
- Batch and single-block classification
- Safety guards against pipeline failures

### Configuration Management
- Environment-driven feature toggles via Settings
- Model preload capability for performance
- Timeout and memory management controls

### Integration Patterns
- Singleton pattern for shared instance management
- Pipeline stage integration with retry and timeout mechanisms
- Cross-stage metadata propagation

**Section sources**
- [semantic_parser.py:48-328](file://backend/app/pipeline/intelligence/semantic_parser.py#L48-L328)
- [settings.py:380-414](file://backend/app/config/settings.py#L380-L414)
- [model_store.py:1-33](file://backend/app/services/model_store.py#L1-L33)

## Architecture Overview
The Semantic Parser operates as a bridge between document structure detection and content classification:

```mermaid
sequenceDiagram
participant OR as Orchestrator
participant SP as SemanticParser
participant MS as ModelStore
participant CL as ContentClassifier
participant BD as Block Data
OR->>SP : analyze_blocks(blocks)
SP->>SP : _load_model()
alt Model Available
SP->>MS : check global model registry
MS-->>SP : model/tokenizer
SP->>SP : _predict_block_types_batch()
SP->>BD : create semantic_blocks[]
else Fallback Mode
SP->>SP : _repair_fragmented_headings()
SP->>SP : _heuristic_classify()
SP->>BD : create semantic_blocks[]
end
SP-->>OR : semantic_blocks
OR->>BD : update metadata
OR->>CL : ContentClassifier.process()
CL->>BD : apply refined classifications
```

**Diagram sources**
- [orchestrator.py:472-492](file://backend/app/pipeline/orchestrator.py#L472-L492)
- [semantic_parser.py:132-185](file://backend/app/pipeline/intelligence/semantic_parser.py#L132-L185)
- [classifier.py:137-236](file://backend/app/pipeline/classification/classifier.py#L137-L236)

## Detailed Component Analysis

### SemanticParser Implementation
The SemanticParser class implements a sophisticated dual-mode classification system:

#### Model Loading Strategy
```mermaid
flowchart TD
Start([Model Load Request]) --> CheckLoaded{"Already Loaded?"}
CheckLoaded --> |Yes| ReturnExisting[Return Existing Instance]
CheckLoaded --> |No| CheckHeuristic{"Heuristic Only?"}
CheckHeuristic --> |Yes| UseHeuristic[Use Heuristic Mode]
CheckHeuristic --> |No| CheckTransformers{"Transformers Available?"}
CheckTransformers --> |No| UseHeuristic[Use Heuristic Mode]
CheckTransformers --> |Yes| CheckGlobalStore{"Global Store Available?"}
CheckGlobalStore --> |Yes| LoadFromStore[Load from ModelStore]
CheckGlobalStore --> |No| LoadLocally[Load Locally]
LoadFromStore --> Success[Model Ready]
LoadLocally --> Success
UseHeuristic --> Success
Success --> End([Ready for Inference])
```

**Diagram sources**
- [semantic_parser.py:60-108](file://backend/app/pipeline/intelligence/semantic_parser.py#L60-L108)
- [model_store.py:19-29](file://backend/app/services/model_store.py#L19-L29)

#### Classification Logic
The parser supports 12 distinct semantic categories:
- HEADING, ABSTRACT, BODY, REFERENCES
- FIGURE_CAPTION, TABLE_CAPTION
- ACKNOWLEDGEMENTS, EQUATION
- METHODOLOGY, CONCLUSION, AUTHOR_INFO, TITLE

#### Safety Mechanisms
- Try-catch wrappers around all public methods
- Graceful degradation to heuristic mode
- Timeout protection via orchestrator integration
- Logging for all failure scenarios

**Section sources**
- [semantic_parser.py:48-328](file://backend/app/pipeline/intelligence/semantic_parser.py#L48-L328)
- [semantic_parser.py:187-251](file://backend/app/pipeline/intelligence/semantic_parser.py#L187-L251)

### Integration with ContentClassifier
The Semantic Parser feeds results to the ContentClassifier for final block type assignment:

```mermaid
classDiagram
class SemanticParser {
+analyze_blocks(blocks) List[Dict]
+predict_blocks_batch(texts) List[Dict]
+classify_block(text, use_transformer) Dict
-_predict_block_types_batch(texts) List[Dict]
-_heuristic_classify(text) Dict
-_repair_fragmented_headings(blocks) List[Block]
}
class ContentClassifier {
+process(document) Document
-_predict_scibert_batch(blocks) List[Dict]
-_apply_scibert_predictions(blocks, predictions) void
-_map_scibert_label(label, block) tuple
}
class Block {
+block_type BlockType
+metadata Dict
+text str
}
SemanticParser --> Block : "produces semantic data"
ContentClassifier --> Block : "assigns final types"
SemanticParser --> ContentClassifier : "provides predictions"
```

**Diagram sources**
- [semantic_parser.py:132-185](file://backend/app/pipeline/intelligence/semantic_parser.py#L132-L185)
- [classifier.py:137-236](file://backend/app/pipeline/classification/classifier.py#L137-L236)
- [block.py:86-181](file://backend/app/models/block.py#L86-L181)

**Section sources**
- [classifier.py:137-236](file://backend/app/pipeline/classification/classifier.py#L137-L236)
- [semantic_parser.py:132-185](file://backend/app/pipeline/intelligence/semantic_parser.py#L132-L185)

### Language Detection and Multilingual Support
The parser includes optional language detection to ensure accurate classification:

```mermaid
flowchart TD
Input[Input Blocks] --> CombineText[Combine Sample Text]
CombineText --> CheckLangDetect{"langdetect Available?"}
CheckLangDetect --> |No| UseEnglish[Assume English]
CheckLangDetect --> |Yes| DetectLang[Detect Language]
DetectLang --> CheckEnglish{"Language == English?"}
CheckEnglish --> |Yes| UseTransformer[Use Transformer]
CheckEnglish --> |No| UseHeuristic[Use Heuristic Only]
UseEnglish --> UseTransformer
UseTransformer --> Output[Classification Results]
UseHeuristic --> Output
```

**Diagram sources**
- [semantic_parser.py:142-157](file://backend/app/pipeline/intelligence/semantic_parser.py#L142-L157)

**Section sources**
- [semantic_parser.py:142-157](file://backend/app/pipeline/intelligence/semantic_parser.py#L142-L157)

## Dependency Analysis
The Semantic Parser has minimal external dependencies and follows a layered architecture:

```mermaid
graph TB
subgraph "External Dependencies"
PT[PyTorch]
HF[Transformers]
LD[langdetect]
end
subgraph "Internal Dependencies"
CFG[Settings]
MS[ModelStore]
BLK[Block Models]
SGL[Singleton Utils]
end
SP[SemanticParser] --> PT
SP --> HF
SP --> LD
SP --> CFG
SP --> MS
SP --> BLK
SP --> SGL
CE[ContentClassifier] --> SP
OR[Orchestrator] --> SP
```

**Diagram sources**
- [semantic_parser.py:1-38](file://backend/app/pipeline/intelligence/semantic_parser.py#L1-L38)
- [settings.py:380-414](file://backend/app/config/settings.py#L380-L414)
- [model_store.py:1-33](file://backend/app/services/model_store.py#L1-L33)

**Section sources**
- [semantic_parser.py:1-38](file://backend/app/pipeline/intelligence/semantic_parser.py#L1-L38)
- [settings.py:380-414](file://backend/app/config/settings.py#L380-L414)

## Performance Considerations
The Semantic Parser implements several optimization strategies:

### Memory Management
- Lazy loading prevents unnecessary model initialization
- Global ModelStore enables shared model instances across requests
- Optional model preloading reduces cold-start latency

### Processing Efficiency
- Batch inference for multiple blocks in a single operation
- Heuristic fallback for non-English or unsupported documents
- Configurable timeouts and retry mechanisms

### Resource Constraints
- Maximum sequence length of 512 tokens for transformer inputs
- Optional language filtering to avoid unnecessary processing
- Graceful degradation maintains pipeline throughput

**Section sources**
- [semantic_parser.py:60-108](file://backend/app/pipeline/intelligence/semantic_parser.py#L60-L108)
- [settings.py:380-414](file://backend/app/config/settings.py#L380-L414)

## Troubleshooting Guide

### Common Issues and Solutions

#### Model Loading Failures
**Symptoms**: Transformer imports fail or model fails to load
**Causes**: Missing PyTorch/Transformers dependencies
**Solutions**: 
- Enable heuristic-only mode via configuration
- Verify Python environment dependencies
- Check model storage availability

#### Performance Degradation
**Symptoms**: Slow classification or timeout errors
**Causes**: Large document batches or insufficient resources
**Solutions**:
- Adjust batch sizes and processing timeouts
- Enable model preloading
- Monitor memory usage during inference

#### Classification Accuracy Issues
**Symptoms**: Incorrect semantic labels or confidence scores
**Causes**: Non-English content or domain mismatch
**Solutions**:
- Verify language detection accuracy
- Consider fine-tuned model variants
- Review heuristic rule adjustments

**Section sources**
- [semantic_parser.py:103-107](file://backend/app/pipeline/intelligence/semantic_parser.py#L103-L107)
- [semantic_parser.py:249-251](file://backend/app/pipeline/intelligence/semantic_parser.py#L249-L251)

## Conclusion
The Semantic Parser provides a robust foundation for academic document processing through intelligent semantic classification. Its dual-mode architecture ensures reliability across diverse document types and environments, while its integration with the broader pipeline enables comprehensive document analysis. The component's safety mechanisms, performance optimizations, and graceful fallback capabilities make it suitable for production deployment in automated academic manuscript formatting systems.