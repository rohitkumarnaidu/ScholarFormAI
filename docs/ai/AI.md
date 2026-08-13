# AI Subsystem Overview

ScholarFormAI integrates advanced Large Language Models (LLMs) to perform complex reasoning, extraction, and formatting tasks on academic manuscripts.

## AI Capabilities

1. **Text Extraction & Parsing**
   - We utilize a 3-Tier extraction system.
   - **Tier 1:** PyMuPDF + LLM Enrichment (for tables and complex layouts).
   - **Tier 2:** Vision API Fallback (for scanned or non-selectable PDFs).
   - **Tier 3:** Raw PyMuPDF (fastest, for simple text).

2. **Automated AI Generator**
   - Generates novel academic content from user prompts and outlines.
   - Streams responses back to the client in real-time.

3. **Multi-Doc RAG Synthesis**
   - Synthesizes content across multiple reference documents.

## Model Strategy

We employ a multi-model strategy depending on the task's complexity:
- **Fast/Cheap Models (e.g., Llama 3 on Groq):** Used for simple parsing, grammar checks, and basic formatting.
- **Reasoning Models (e.g., NVIDIA hosted models, GPT-4o):** Used for complex synthesis, forensic auditing, and mathematical equation parsing.

## Related Documents
- [AI Agents](AGENTS.md)
- [RAG System](RAG.md)
- [Memory Management](MEMORY.md)
