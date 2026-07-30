<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: ScholarForm AI — AI Instructions
description: LLM tiers, RAG pipeline, prompt rules, and fallback behavior
sidebar_position: 20
version: "1.0"
status: ✅ Complete
owner: Docs Team
review_cadence: quarterly
last_updated: July 2026
---

# ScholarForm AI — AI Instructions

## LLM Tier Strategy

| Tier | Provider | Model | Use Case | Cost |
| ------ | ---------- | ------- | ---------- | ------ |
| 1 | NVIDIA NIM | llama-3.3-70b-instruct | Primary cloud (high quality) | API credits |
| 2 | Groq | llama-3.3-70b-versatile | Fast secondary (free tier) | Free (rate limited) |
| 3 | Ollama | deepseek-r1 | Local/offline fallback | Free (self-hosted) |
| 4 | vLLM (Future) | Llama-3.1-8B-Instruct | Self-hosted GPU | Hardware cost only |

## LLM Integration via LiteLLM

All LLM calls go through `services/llm_service.py` which uses LiteLLM for provider abstraction. This means the same code works for all tiers — only the model string changes.

## Prompt Engineering Rules

1. **Never call LLM during typing** — only on explicit user action
2. **Section-specific prompts** — `section_prompts.py` has unique prompts for abstract, intro, methods, results, conclusion
3. **JSON mode** — Outline generation uses JSON mode for structured output
4. **Token streaming** — Generator uses SSE token streaming for real-time writing feel
5. **Context window management** — Keep running context across sections, max 50 messages

## RAG Pipeline (ChromaDB)

1. Upload documents → extract text (GROBID for PDF, python-docx for DOCX)
2. Chunk text (512 tokens, 100 overlap)
3. Embed via **multi-qa-MiniLM-L6-v2** (sentence-transformers)
4. Store in ChromaDB collection: `session_{session_id}`
5. Query: embed question → top-5 similarity → build context → LLM answer with sources
6. TTL: auto-delete collection after 24 hours

## LLMClassifier Classifier

- Model: allenai/LLMClassifier_scivocab_uncased
- Purpose: Classify document sections (IMRaD)
- Status: **DISABLED** (`USE_LLM_CLASSIFICATION=false`)
- Needs: Fine-tuning on IMRaD/SciHED dataset for >85% F1

## Quality Scoring

- Pipeline-level: `quality_scorer.py` — checks coherence, tone, novelty
- Service-level: `quality_score_service.py` — per-document scoring
- Composite score: structure + formatting + citations + coherence
- Display: Quality score panel on results page

## Key AI Files

| File | Size | Purpose |
| ------ | ------ | --------- |
| `pipeline/generation/agent.py` | 34KB | Full 11-step AI agent pipeline |
| `pipeline/generation/task_parser.py` | 6.2KB | Extract requirements from user prompt |
| `pipeline/generation/section_prompts.py` | 3.4KB | Per-section system prompts |
| `pipeline/generation/quality_scorer.py` | 4.5KB | AI quality assessment |
| `pipeline/synthesis/synthesizer.py` | 24.2KB | 8-stage multi-doc synthesis |
| `services/llm_service.py` | 14.9KB | Multi-tier LLM abstraction |
| `services/session_vector_store.py` | 7.8KB | ChromaDB RAG |
| `services/nvidia_client.py` | 10.9KB | NVIDIA NIM integration |
