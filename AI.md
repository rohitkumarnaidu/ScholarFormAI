# AI Features

## Overview

AMF's AI-powered features assist researchers in creating, formatting, and improving their academic manuscripts.

## Current Features

### Smart Suggestions

When validating manuscripts, AMF provides intelligent suggestions for:

- Section structure improvements
- Citation format corrections
- Missing recommended sections

### Intelligent Parsing

The parser can intelligently detect manuscript structure even in loosely formatted text, identifying:

- Title and authorship
- Section headings and hierarchy
- Abstract and keywords
- Reference entries

## Planned AI Features

### Citation Quality Check (Q4 2026)

- Detect missing citation information (DOI, volume, pages)
- Suggest complete citation entries from partial information
- Validate citation format compliance

### Structure Recommendations (Q1 2027)

- Suggest optimal section order for selected style
- Identify missing required sections
- Recommend paragraph restructuring

### Abstract Enhancement (Q2 2027)

- Summarize manuscript for abstract generation
- Extract keywords from content
- Suggest improvements for abstract clarity

### Reference Management (Q2 2027)

- Auto-detect reference format
- Suggest DOI lookups for incomplete references
- Detect duplicate references

## Usage

AI features are currently limited to rule-based suggestions. Machine-learning-powered features are in development.

```bash
# Get AI-powered validation suggestions
amf validate -i manuscript.md -s apa
```

## Privacy

AMF processes all manuscript content locally by default. When using the hosted API:

- Manuscript content is processed in memory
- No content is permanently stored
- Content is not used for model training

## Future Architecture

The planned AI pipeline:

```
Manuscript → Parser → Validator → AI Suggestions → User Review → Formatter
                                      │
                                      ▼
                              ML Models (optional)
                              - Citation classifier
                              - Section predictor
                              - Abstract summarizer
```
