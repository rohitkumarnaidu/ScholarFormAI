# Retrieval-Augmented Generation (RAG) Guide

## Overview

AMF's RAG capabilities enable intelligent manuscript enhancement by retrieving relevant information from academic knowledge bases.

## Current Status

RAG features are in **planning stage** for v2.0.

## Architecture (Planned)

```
User Manuscript
      │
      ▼
┌─────────────┐     ┌─────────────┐
│  Query      │────▶│  Embedding  │
│  Processor  │     │  Model      │
└─────────────┘     └──────┬──────┘
                           │
                           ▼
                   ┌─────────────┐     ┌─────────────┐
                   │  Vector DB  │◀────│  Knowledge  │
                   │  (Chroma)   │     │  Base       │
                   └──────┬──────┘     └─────────────┘
                           │
                           ▼
                   ┌─────────────┐
                   │  LLM        │
                   │  (Optional) │
                   └──────┬──────┘
                           │
                           ▼
                   ┌─────────────┐
                   │  Enhanced   │
                   │  Manuscript │
                   └─────────────┘
```

## Use Cases

### Citation Enhancement

- Retrieve missing DOI information
- Suggest additional relevant references
- Validate citation format

### Section Recommendations

- Suggest appropriate section structure
- Recommend content based on similar papers
- Identify missing required sections

### Style Compliance

- Retrieve style-specific formatting rules
- Compare against style guidelines
- Suggest corrections

## Implementation Plan

1. Embedding-based search for style guidelines
2. Citation database integration (DOI, CrossRef, Semantic Scholar)
3. Knowledge base of academic writing best practices
4. Optional LLM integration for natural language suggestions

## Configuration

```python
# Future configuration
RAG_ENABLED=true
RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2
RAG_VECTOR_DB=chroma
RAG_COLLECTION_NAME=amf-knowledge
```
