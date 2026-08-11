# ScholarForm AI — AI Architecture

## 1. Overview

ScholarForm AI is an enterprise-grade automated academic manuscript formatting platform. It transforms raw document uploads (DOCX, PDF, TXT, HTML, Markdown, TeX, LaTeX) into publication-ready, template-compliant outputs through a 16-stage AI-powered processing pipeline.

The system integrates **5 AI/ML subsystems**:

- **Document Understanding Pipeline** — parsing, structure detection, LLM-based classification analysis, content classification, NLP analysis
- **LLM Tier System** — 10 built-in providers with 4-tier automatic fallback (NVIDIA NIM → Groq → OpenRouter → Ollama) + per-provider circuit breakers
- **Intelligence Layer** — RAG engine (ChromaDB + sentence-transformers), reasoning engine for block-level AI classification
- **Agent Subsystem** — LangChain-based document processing agents with 5 tools, memory, streaming, and direct fallback execution
- **Safety Layer** — Circuit breakers, retry with exponential backoff, LLM output validation (Guardrails AI/pybreaker), safe execution decorators

All AI stages are **optional and gracefully degrade**: if LLMClassifier is unavailable, heuristic classification takes over. If all LLM tiers fail, rule-based fallbacks produce deterministic output. If ChromaDB fails, a native JSON-store cosine-similarity fallback maintains retrieval.

---

## 2. System Architecture Diagram

```mermaid
graph TB
    subgraph Input["Input Layer"]
        UPLOAD["File Upload<br/>DOCX/PDF/TXT/MD/TeX/HTML"]
        IC["InputConverter<br/>.doc/.odt/.rtf → DOCX"]
    end

    subgraph Stage1["1. Parsing (ParserFactory)"]
        DP[DocxParser]
        PP["PdfParser<br/>PyMuPDF"]
        NP["LLMPDFParser<br/>OCR Fallback"]
        TP[TxtParser]
        HP["HtmlParser<br/>BeautifulSoup4"]
        MP[MarkdownParser]
        TEP[TexParser]
    end

    subgraph Stage2["2. Metadata & Layout"]
        GRO["GROBID Client<br/>Metadata Extraction"]
        DOC["Docling Client<br/>Layout Analysis"]
        PYMF["PyMuPDF Fallback<br/>Metadata Only"]
    end

    subgraph Stage3["3. AI Intelligence"]
        EQ["Equation Standardizer"]
        SD["StructureDetector<br/>Heading/Section IDs"]
        SP["SemanticParser<br/>LLMClassifier / Heuristics"]
        CC["ContentClassifier<br/>BlockType Assignment"]
        NLP["ContentAnalyzer<br/>NLP & Keywords"]
    end

    subgraph Stage4["4. Content Analysis"]
        CM["CaptionMatcher<br/>Figure Captions"]
        TCM["TableCaptionMatcher<br/>Table Captions"]
        FA["FigureAnalyzer<br/>Quality/DPI"]
        RP["ReferenceParser<br/>Reference Extraction"]
    end

    subgraph Stage5["5. AI Reasoning & Enrichment"]
        RAG["RagEngine<br/>ChromaDB + SBERT"]
        RE["ReasoningEngine<br/>LLM Instruction Sets"]
        CR["CrossRefClient<br/>Citation Validation"]
    end

    subgraph Stage6["6. Validation & Formatting"]
        DV["DocumentValidator<br/>Contract-Driven"]
        AIE["AIExplainer<br/>Validation Explanation"]
        FMT["Formatter<br/>StyleMapper/Numbering/Templates"]
    end

    subgraph Stage7["7. Export"]
        EX["Exporter<br/>DOCX/PDF/LaTeX/JATS/HTML/JSON/MD"]
    end

    subgraph LLM["LLM Provider Tier System"]
        T1["NVIDIA NIM<br/>Llama 3.3 70B"]
        T2["Groq<br/>Llama3/Mixtral"]
        T3["OpenRouter<br/>Multi-Model"]
        T4["Ollama<br/>DeepSeek R1 Local"]
    end

    subgraph Safety["Safety Layer"]
        CB["Circuit Breakers<br/>pybreaker"]
        RG["Retry Guard<br/>Exponential Backoff"]
        LV["LLM Validator<br/>Guardrails AI + Pydantic"]
        SE["SafeExecution<br/>Error Containment"]
    end

    UPLOAD --> IC
    IC --> Stage1
    Stage1 --> Stage2
    Stage2 --> Stage3
    Stage3 --> Stage4
    Stage4 --> Stage5
    Stage5 --> Stage6
    Stage6 --> Stage7

    RE --> LLM
    RAG --> RE
    CR --> RE
    LLM --> Safety
    Safety --> RE
```

### Data Flow Overview

```
Input File → ParserFactory → [GROBID + Docling parallel] → Equation Std → StructureDetect
→ SemanticParser (optional) → ContentClassifier → ContentAnalyzer → CaptionMatch → RefParse
→ CrossRef Enrichment (optional) → AI Reasoning (RAG + LLM, optional) → Validation
→ Formatting (StyleMapper + NumberingEngine + TemplateRenderer) → Export
```

---

## 3. Pipeline Architecture

### 3.1 16-Stage Processing Pipeline

Each stage is orchestrated by `PipelineOrchestrator` (`app/pipeline/orchestrator.py:87`). Stages are sequential except GROBID/Docling which run in parallel. Every stage wraps failures in `safe_execution` to prevent cascading pipeline crashes.

#### Stage 1: Upload & Validation

- **File**: `app/routers/v1/documents_impl.py`
- **Input**: Raw file bytes
- **Output**: Validated file path on disk
- **Checks**: File extension whitelist, magic bytes validation (via `_validate_magic_bytes`), SHA-256 dedup, file size limits (60MB default)
- **Accepted**: `.docx`, `.pdf`, `.txt`, `.html`, `.htm`, `.md`, `.markdown`, `.tex`, `.latex`, `.doc`, `.odt`, `.rtf`

#### Stage 2: Document Parsing — ParserFactory (7 parsers)

- **File**: `app/pipeline/parsing/parser_factory.py:28`
- **Input**: File path with known extension
- **Output**: `PipelineDocument` with `Block[]` (text, position, metadata)
- **Parsers**:
  - `DocxParser` (`parsing/parser.py`) — python-docx extraction, always available
  - `PdfParser` (`parsing/pdf_parser.py`) — PyMuPDF (fitz), primary PDF path
  - `LLMPDFParser` (`parsing/llm_pdf_parser.py`) — Meta AI LLM-based PDF parsing, opt-in via `ENABLE_LLM_PDF_PARSER=true`, fallback for scanned PDFs when primary extraction yields empty blocks
  - `TxtParser` (`parsing/txt_parser.py`) — plain text, always available
  - `HtmlParser` (`parsing/html_parser.py`) — BeautifulSoup4, requires `bs4`
  - `MarkdownParser` (`parsing/md_parser.py`) — markdown-to-text, always available
  - `TexParser` (`parsing/tex_parser.py`) — LaTeX regex extraction, always available
- **Fallback**: Empty extraction triggers LLM-based PDF parsing fallback at `orchestrator.py:729`

#### Stage 3: GROBID Metadata Extraction

- **File**: `app/pipeline/services/grobid_client.py`
- **Input**: PDF file path
- **Output**: `ai_hints['grobid_metadata']` dict with title, authors, abstract, DOI
- **Timeout**: `PIPELINE_GROBID_TIMEOUT_SECONDS` (default 30s)
- **Retry**: `GROBID_MAX_RETRIES` (default 3)
- **Gate**: `GROBID_ENABLED` (default `true`)
- **Default URL**: `http://localhost:8070`

#### Stage 4: Docling Layout Analysis

- **File**: `app/pipeline/services/llm_pdf_parser.py`
- **Input**: PDF file path
- **Output**: `ai_hints['docling_layout']` with detected elements (headings, paragraphs, tables, figures)
- **Timeout**: `PIPELINE_DOCLING_TIMEOUT_SECONDS` (default 30s)
- **Gate**: `USE_DOCLING_FALLBACK` (default `true`)
- **Digital PDF skip**: When `PIPELINE_DOCLING_SKIP_DIGITAL_PDF=true`, Docling is skipped for PDFs with ≥250 chars of extractable text on first 2 pages
- **Parallel execution**: GROBID and Docling run concurrently via `ThreadPoolExecutor(max_workers=2)` — `orchestrator.py:771`

#### Stage 5: PyMuPDF Fallback

- **File**: `orchestrator.py:392` (`_extract_pymupdf_fallback_metadata`)
- **Triggered**: When both GROBID and Docling return empty AND `PYMUPDF_FALLBACK=true`
- **Output**: Lightweight metadata (page count, title, author, sample text) extracted via `fitz`

#### Stage 6: Equation Standardization

- **File**: `app/pipeline/equations/standardizer.py`
- **Process**: Detects and standardizes mathematical equation blocks

#### Stage 7: Structure Detection

- **File**: `app/pipeline/structure_detection/detector.py`
- **Class**: `StructureDetector`
- **Input**: `PipelineDocument` with raw blocks
- **Output**: Document with `detected_headings`, heading metadata, section boundaries
- **Confidence thresholds**: `HEADING_STYLE_THRESHOLD` (0.8), `HEADING_FALLBACK_CONFIDENCE` (0.5)
- **Decorated**: `@retry_with_backoff(max_retries=1, backoff_factor=1.0)` — `orchestrator.py:557`

#### Stage 8: Semantic Parsing — LLMClassifier (Optional)

- **File**: `app/pipeline/intelligence/semantic_parser.py:57`
- **Class**: `SemanticParser`
- **Input**: `Block[]` from document
- **Output**: Per-block `semantic_intent` and `nlp_confidence` in metadata
- **Model**: `allenai/LLMClassifier_scivocab_uncased` (default), 12 classification labels
- **Execution order**:
  1. Remote LLMClassifier endpoint (`LLM_CLASSIFIER_URL`/`LLM_CLASSIFIER_URLS`) — POST JSON to `/predict`
  2. Local LLMClassifier model via HuggingFace `transformers` — `AutoModelForSequenceClassification`
  3. Deterministic heuristics — keyword/pattern matching
- **Labels**: HEADING, ABSTRACT, BODY, REFERENCES, FIGURE_CAPTION, TABLE_CAPTION, ACKNOWLEDGEMENTS, EQUATION, METHODOLOGY, CONCLUSION, AUTHOR_INFO, TITLE
- **Gate**: `USE_LLM_CLASSIFICATION=false` (disabled by default)
- **LLMClassifier Gate**: `app/services/LLMClassifier_gate.should_enable_LLMClassifier()` — benchmarks F1 ≥ 0.85 before auto-enabling
- **Language detection**: Uses `langdetect`; falls to heuristics for non-English documents
- **Head repair**: `_repair_fragmented_headings()` merges split number+text heading patterns

#### Stage 9: Content Classification

- **File**: `app/pipeline/classification/classifier.py:26`
- **Class**: `ContentClassifier(PipelineStage)`
- **Input**: Document with structure metadata
- **Output**: Document with `BlockType` assigned per block
- **Rules**:
  - Abstract keywords → `BlockType.ABSTRACT_BODY`
  - References keywords → `BlockType.REFERENCE_ENTRY`
  - Heading candidates → `BlockType.HEADING_1`–`HEADING_4`
  - Front matter (pre-section) → Title/Author/Affiliation analysis
  - Footnotes → `^(\d+ |\[\d+\]| |‡|※|\*\s)` patterns
  - Appendices → keyword-matched (appendix, annex, supplement)
  - Affiliations → 20+ indicator keywords (university, college, department, ...)
- **LLMClassifier tuning**: Uses `HEURISTIC_CONFIDENCE_MEDIUM` (0.7) as minimum for LLMClassifier override

#### Stage 10: NLP Analysis

- **File**: `app/pipeline/nlp/analyzer.py`
- **Classes**: `ContentAnalyzer`, `extract_keywords()`
- **Input**: Classified document blocks
- **Output**: Enhanced block metadata, extracted keywords, language detection
- **Keyword extraction**: From abstract text, persisted in `doc_obj.metadata.keywords`

#### Stage 11: Caption Matching (Figures & Tables)

- **Files**:
  - `app/pipeline/figures/caption_matcher.py` — `CaptionMatcher(enable_vision=True)`
  - `app/pipeline/tables/caption_matcher.py` — `TableCaptionMatcher()`
- **Input**: Document with classified blocks
- **Output**: Figures/tables associated with their captions, figure export paths

#### Stage 12: Figure Quality Analysis

- **File**: `app/pipeline/figures/analyzer.py` — `figure_analyzer`
- **Input**: Document figures
- **Output**: Per-figure quality analysis (DPI, dimensions, downsampling decisions)
- **Active**: Only when `fast_mode=false`

#### Stage 13: Reference Parsing

- **File**: `app/pipeline/references/parser.py` — `ReferenceParser`
- **Input**: Document blocks identified as references
- **Output**: Structured `Reference[]` objects with parsed authors, title, DOI

#### Stage 14: Reference Formatting (CSL)

- **File**: `app/pipeline/references/formatter_engine.py:21`
- **Class**: `ReferenceFormatterEngine`
- **Input**: `Reference[]` + publisher name
- **Output**: Formatted `Reference.formatted_text` per CSL or contract template
- **Primary**: `CSLEngine` (citeproc-py) — supports standard and custom CSL styles
- **Fallback**: Contract YAML `references.normalization` rules
- **Config**: `contract.yaml` → `references.style` (e.g. "ieee", "apa"), `references.csl_style_path`

#### Stage 15: CrossRef Enrichment (Optional)

- **File**: `app/services/crossref_client.py` (services version) or `app/pipeline/services/crossref_client.py`
- **Input**: Document references
- **Output**: Per-reference `crossref_validation` metadata (DOI, authors, title, url)
- **Gate**: `runtime_flags['crossref_enrichment']` → default disabled in fast mode
- **Workers**: `CROSSREF_MAX_WORKERS` (default 4) via `ThreadPoolExecutor`

#### Stage 16: AI Reasoning — RAG + LLM (Optional)

- **Files**:
  - `app/pipeline/intelligence/rag_engine.py:233` — `RagEngine`
  - `app/pipeline/intelligence/reasoning_engine.py:86` — `ReasoningEngine`
- **Input**: Context blocks (first 12), template name, section name
- **Output**: `semantic_advice` dict with per-block instruction sets
- **Flow**:
  1. `RagEngine.query_guidelines(template, section, top_k=2)` → retrieves formatting rules
  2. `ReasoningEngine.generate_instruction_set(blocks, rules)` → LLM classifies blocks
  3. Instructions with confidence < 0.70 get `review_required=true` flag
- **Gate**: `runtime_flags['ai_reasoning']` → default disabled in fast mode

#### Stage 17: Document Validation

- **File**: `app/pipeline/validation/validator_v3.py:37`
- **Class**: `DocumentValidator(PipelineStage)`
- **Input**: Fully processed document
- **Output**: `ValidationResult` (is_valid, errors[], warnings[], stats)
- **Components**:
  - `SectionOrderValidator` — checks section ordering per contract rules
  - `CrossReferenceEngine` — validates internal cross-references
  - `CrossRefClient` — validates citations against CrossRef API (in pipeline variant)
- **Safety**: Every check wrapped in `@safe_function` — individual check failures degrade gracefully

#### Stage 18: AI Explainer

- **File**: `app/pipeline/validation/ai_explainer.py` — `AIExplainer`
- **Input**: Validation results + template name
- **Output**: Human-readable explanations embedded in `validation_results['ai_explanations']`

#### Stage 19: Formatting

- **File**: `app/pipeline/formatting/formatter.py:44`
- **Class**: `Formatter`
- **Input**: Validated `PipelineDocument`
- **Output**: `Document.generated_doc` (python-docx `Document` object)
- **Sub-components**:
  - `StyleMapper` — maps `BlockType` → Word style names, driven by `contract.yaml`
  - `NumberingEngine` — section/equation/figure/table numbering per contract rules
  - `ReferenceFormatter` — formats reference blocks in Word document
  - `TemplateRenderer` — Jinja2/docxtpl rendering from `.docx` templates
  - `TableRenderer` — table generation from structured data
  - `FigureRenderer` — figure embedding with DPI optimization

#### Stage 20: Export

- **File**: `app/pipeline/export/exporter.py:22`
- **Class**: `Exporter`
- **Input**: Formatted `PipelineDocument` with `generated_doc`
- **Output**: Files on disk
- **Supported formats**: DOCX (primary), PDF (via LibreOffice/`pdf_exporter.py`), LaTeX (`latex_exporter.py`), JATS XML (`jats_generator.py`), JSON, Markdown, HTML

### 3.2 Stage Orchestration

#### PipelineOrchestrator (`app/pipeline/orchestrator.py:87`)

**Concurrency Control**:

- Global semaphore `_pipeline_semaphore` limits concurrent jobs to `_MAX_CONCURRENT_JOBS = 5`
- Semaphore acquire timeout: `PIPELINE_ACQUIRE_TIMEOUT_SECONDS` (default 30s)
- Jobs exceeding the limit receive immediate "Server busy" response

**Timeout Strategy**:

- `_run_with_timeout(func, timeout_sec)` wraps sync stages in `ThreadPoolExecutor(max_workers=1)` with `future.result(timeout=...)`
- Stage-specific timeouts: GROBID (30s), Docling (30s), Reasoning (60s), Semantic (30s), Validation (60s), Formatting (60s)

**Error Propagation**:

- `safe_execution` context managers suppress non-critical stage failures
- Decorated `@retry_with_backoff` stages retry on failure before raising
- Stage failures are logged and pipeline continues to next stage (non-fatal)
- `_persist_partial_result()` saves whatever was processed before a terminal failure
- Cancelled jobs (`asyncio.CancelledError`) trigger graceful shutdown without stack traces

**Status Reporting**:

- Every stage transition updates Supabase `processing_status` table
- SSE events emitted via `emit_event(document_id, "status_update", payload)` for real-time UI
- Idempotent upsert pattern: select → insert/update
- Transient DB errors retried 3× with exponential backoff (0.15s, 0.3s, 0.6s)

**Runtime Flags** (`_resolve_runtime_flags`, line 343):

```python
{
    "fast_mode": False,          # Skips optional AI stages
    "semantic_parser": True,     # Enables LLMClassifier parsing
    "crossref_enrichment": True, # Enables CrossRef lookups
    "ai_reasoning": True,        # Enables RAG + ReasoningEngine
}
```

- `fast_mode` defaults to `DEFAULT_FAST_MODE` (false in production, true in pytest/LOW_MEMORY_MODE)
- All flags are overridable via `formatting_options` dict

**Cancellation**: `_check_cancelled(job_id)` polls Supabase `documents.status == "CANCELLED"` between stages, raising `asyncio.CancelledError` for graceful abort.

**Edit Flow** (`run_edit_flow`, line 1218): Re-runs validation + formatting on user-edited structured data. Creates versioned snapshots in `document_versions` table before overwriting `document_results`.

---

## 4. LLM Tier System

### 4.1 Provider Architecture

**File**: `app/services/provider_registry.py:42`

10 built-in providers defined in `BUILTIN_PROVIDERS` dict:

| Provider | Base URL | Default Model | API Key Env Var |
| ---------- | ---------- | --------------- | ----------------- |
| `openai` | `https://api.openai.com/v1` | `gpt-4o-mini` | `OPENAI_API_KEY` |
| `anthropic` | `https://api.anthropic.com/v1` | `claude-3-5-sonnet-20241022` | `ANTHROPIC_API_KEY` |
| `groq` | `https://api.groq.com/openai/v1` | `llama3-8b-8192` | `GROQ_API_KEY` |
| `deepseek` | `https://api.deepseek.com` | `deepseek-chat` | `DEEPSEEK_API_KEY` |
| `openrouter` | `https://openrouter.ai/api/v1` | `openai/gpt-4o-mini` | `OPENROUTER_API_KEY` |
| `google` | `https://generativelanguage.googleapis.com/v1beta` | `gemini-2.0-flash` | `GOOGLE_API_KEY` |
| `cohere` | `https://api.cohere.com/v1` | `command-r-plus` | `COHERE_API_KEY` |
| `mistral` | `https://api.mistral.ai/v1` | `mistral-small-latest` | `MISTRAL_API_KEY` |
| `ollama` | `OLLAMA_BASE_URL` / `http://localhost:11434` | `deepseek-r1` | None (local) |
| `nvidia` | `https://integrate.api.nvidia.com/v1` | `NVIDIA_MODEL` (configurable) | `NVIDIA_API_KEY` |

**Key properties per provider**:

- `env_key_actual`: Lambda that lazily reads from `settings`
- `supports_custom_base_url`: Only `openrouter` and `ollama`
- `is_local`: Only `ollama`
- Models: Static lists for most providers, dynamically discovered for Ollama

### 4.2 4-Tier Fallback Chain

**File**: `app/services/llm_service.py:552` (`generate_with_fallback`)

```
Start → Tier 1: NVIDIA NIM → Fail → Tier 2: Groq → Fail → Tier 3: OpenRouter → Fail → Tier 4: Ollama/DeepSeek → Fail → Raise LLMUnavailableError
```

Each tier:

1. Resolves API key via `resolve_user_api_key(provider, user_id)` (BYOK) → fallback to env var
2. Calls through provider-specific circuit breaker (`_call_with_provider_circuit`)
3. Uses `generate()` which goes through LiteLLM → direct client fallback
4. Records success/failure metrics via `MetricsManager`
5. On rate limit (429) at Groq, OpenRouter is prioritized as Tier 2.5

**LLMUnavailableError** (`llm_service.py:718`): Raised when all 4 tiers fail. Callers (e.g. `ReasoningEngine`, `MultiDocSynthesizer`) catch this and use rule-based fallbacks.

### 4.3 BYOK (Bring Your Own Key)

**File**: `app/services/llm_service.py:90` (`resolve_user_api_key`)

Priority:

1. User's stored encrypted key in `user_api_keys` table (via `ApiKeyService.get_active_key`)
2. Environment variable default (`OPENAI_API_KEY`, etc.)

**Encryption**: Keys stored encrypted in `user_api_keys` table. Decryption uses `EncryptionService` (Fernet symmetric encryption, `app/services/encryption_service.py`).

**Resolution flow**:

```python
resolve_user_api_key("nvidia", user_id="usr_123")
  → ApiKeyService.get_active_key("usr_123", "nvidia")
    → Service.decrypt_key(encrypted_key)
      → return raw_key
  → fallback: settings.NVIDIA_API_KEY
```

### 4.4 Custom Providers

**File**: `app/services/provider_registry.py:226-251`

Custom (BYO) providers stored in `custom_providers` table, managed via `/api/v1/providers/custom` CRUD.

**Schema**:

- `id`, `user_id`, `name`, `base_url`, `api_key_encrypted`, `models`, `is_active`, `is_local`

**Resolution**: When model string starts with `custom_`, the provider info is loaded from DB, API key decrypted, and call made via `_generate_openai_compat()` (direct OpenAI-compatible HTTP call).

**Model listing**: `list_available_models(db, user_id)` returns built-in providers + user's custom providers + cached discovered models (with 1-hour TTL).

### 4.5 Circuit Breakers

**Per-provider circuit breakers** in `llm_service.py:56-65` (`_provider_breaker`):

- Uses `pybreaker.CircuitBreaker` when available
- Configuration: `EXTERNAL_CIRCUIT_BREAKER_FAILURE_THRESHOLD` (3), `EXTERNAL_CIRCUIT_BREAKER_RESET_SECONDS` (60)
- Gate: `EXTERNAL_CIRCUIT_BREAKER_ENABLED` (default `true`)
- Each provider has its own breaker instance keyed by provider name e.g. `llm_nvidia`

**Method-level circuit breakers** in `reasoning_engine.py:461-465`:

```python
@circuit_breaker(failure_threshold=3, recovery_timeout=60, fallback_function=_instruction_set_circuit_fallback)
def generate_instruction_set(self, ...)
```

- When breaker opens, calls `_instruction_set_circuit_fallback` → `_rule_based_fallback`
- States: CLOSED → OPEN (after N failures) → HALF_OPEN (after recovery_timeout) → CLOSED (on success)
- Listener logs all state transitions

**Fallback chain within ReasoningEngine**:

```
generate_instruction_set()
  → NVIDIA (litellm) → if fail → DeepSeek/Ollama → if fail → Rule-based heuristics
```

---

## 5. AI Agents Subsystem

### 5.1 Agent Architecture

**File**: `app/pipeline/agents/document_agent.py:74`

**Class**: `DocumentAgent`

**Purpose**: Intelligent agent for orchestrating document processing. Can run as a LangChain ReAct agent or execute tools directly.

**Initialization parameters**:

- `llm_provider`: "openai", "anthropic", "ollama"
- `llm_model`: Model name (e.g. "gpt-4")
- `temperature`: Default 0.0 (deterministic)
- `max_retries`: Default 3
- `enable_memory`: Default True
- `enable_streaming`: Default False

**LLM Initialization**:

1. Try legacy `ChatOpenAI` from LangChain (if Python < 3.14)
2. Fall back to `CustomLLMFactory.create_llm()` (LiteLLM shim or LangChain)
3. Test patched constructor support for mock interop

**Fallback modes**:

- **LangChain ReAct agent** (primary, Python < 3.14): Uses `create_react_agent` + `AgentExecutor` with max 10 iterations
- **Direct tool execution** (Python ≥ 3.14 or LangChain unavailable): Runs 5 tools sequentially, collects results, returns analysis

**Async entry point**: `run(document, job_id)` — decorated with `@safe_async_function` + `@retry_guard(max_retries=1)`.

### 5.2 Agent Tools

5 built-in tools in `app/pipeline/agents/tools/`:

| Tool | File | Purpose |
| ------ | ------ | --------- |
| `MetadataExtractionTool` | `tools/metadata_tool.py` | GROBID-based metadata extraction |
| `LayoutAnalysisTool` | `tools/layout_tool.py` | Document layout structure analysis |
| `ValidationTool` | `tools/validation_tool.py` | Validate document structure |
| `ReferenceExtractionTool` | `tools/reference_tool.py` | Extract and parse references |
| `FigureAnalysisTool` | `tools/figure_tool.py` | Detect and analyze figures |

**Custom tool framework** (`app/pipeline/agents/custom_tools.py:24`):

- `ToolRegistry` class for dynamic tool registration
- `register_custom_tool(name, description, input_schema, execute_fn)` → creates Pydantic-validated LangChain tool
- Built-in examples: `create_citation_formatter_tool()`, `create_keyword_extractor_tool()`

### 5.3 Agent Memory

**File**: `app/pipeline/agents/memory.py:14`

**Class**: `AgentMemory`

**Storage**: JSON files on disk in `.agent_memory/` directory:

- `patterns.json` — successful/failed processing strategies
- `errors.json` — error occurrences with solutions
- `metrics.json` — performance metrics (last 100 values kept)
- `corrections.json` — user corrections for learning

**API**:

- `remember_pattern(pattern_type, context, success)` — stores processing patterns with dedup
- `remember_error(error_type, message, solution)` — stores error knowledge
- `get_best_pattern(pattern_type, context)` — retrieves best matching successful pattern
- `get_error_solution(error_type, message)` — finds known solutions for errors
- `remember_correction(document_id, field, original, corrected)` — learns from user edits
- `format_memory_summary()` → human-readable context string injected into agent prompts

### 5.4 LLM Factory

**File**: `app/pipeline/agents/llm_factory.py:78`

**Class**: `CustomLLMFactory`

**Supported providers**: openai, anthropic, ollama, nvidia, custom, litellm

**Two backends**:

1. **`_create_litellm`** (preferred): Creates `_LiteLLMShim` wrapper that exposes `.invoke(prompt)` → text via `llm_service.generate()`. Provider prefix mapping: `ollama → ollama/`, `nvidia → nvidia_nim/`
2. **`_create_langchain`** (fallback): Uses LangChain `ChatOpenAI`, `ChatAnthropic`, or `Ollama` classes directly

**`_LiteLLMShim`** (line 50): LangChain-compatible wrapper that delegates to `llm_service.generate()` — enables agent toolchains to work with LiteLLM-backed providers.

**Provider discovery** (`get_available_providers`): Pings `OLLAMA_BASE_URL/api/tags` to detect local models; checks env vars for API keys.

---

## 6. RAG (Retrieval-Augmented Generation)

### 6.1 ChromaDB Vector Store

**File**: `app/pipeline/intelligence/rag_engine.py:233`

**Class**: `RagEngine`

**Backends**:

1. **ChromaDB** (primary): `PersistentClient(path=persist_directory)`, `get_or_create_collection(name)`
2. **Native JSON** (fallback): `kb.json` file with cosine similarity search

**Collections**:

- `guidelines_bge_m3` — 1024-dim (BGE-M3)
- `publisher_guidelines` — 384-dim (BGE-small-en-v1.5, legacy)

**Persistence**: ChromaDB data in `db/semantic_store/` (relative to backend root). Native store in `kb.json` within the same directory.

**NumPy compatibility**: Auto-patches `np.float_` and `np.int_` for ChromaDB compatibility with NumPy 2.0+.

### 6.2 Knowledge Base

**Embedding Model Loading** (`_load_embedding_model`, line 444):

Priority:

1. **Remote HuggingFace API** (`RAG_EMBEDDING_PROVIDER=huggingface_api`): Uses `_HuggingFaceAPIEmbeddingModel` → free HF Inference API. Requires `HF_TOKEN`. Saves ~1.5GB RAM.
2. **ModelStore reuse**: Check if `embedding_model` already loaded in global `ModelStore`
3. **BAAI/bge-m3** (1024d, 8192 tokens): Primary local model via `sentence-transformers`
4. **BAAI/bge-small-en-v1.5** (384d): Fallback local model
5. **Deterministic hash** (`_DeterministicEmbeddingModel`, 256-dim): Token hashing via `blake2b` → normalized vector. Zero-dependency fallback.

**Guideline Chunking**: `add_guideline(publisher, section, text, metadata)`:

- Stored in ChromaDB with `publisher` and `section` metadata filters
- Also stored in native `knowledge_base` list with computed embedding for fallback query

**Auto-seeding**: On first init (empty store), loads from `default_guidelines.json` (co-located with `rag_engine.py`).

### 6.3 RAG Engine API

**Primary**: `query_guidelines(publisher, intent, top_k=3)` → `List[str]`

1. ChromaDB query with `where={"publisher": publisher.upper()}` filter
2. Fallback: Cosine similarity over native `knowledge_base`

**Adapter**: `query_rules(template_name, section_name, top_k=2)` → `List[Dict]`

- Wraps `query_guidelines` into `[{"text": ..., "metadata": ...}]` format
- Used by `PipelineOrchestrator` at `orchestrator.py:1003`

**Context Preparation** (in orchestrator, line 1002-1015):

```python
for sec in ["abstract", "introduction", "references", "figures"]:
    guidelines = rag.query_guidelines(template_name, sec, top_k=2)
    rules_context += f"\n- {sec.title()}: {' '.join(guidelines)}"
```

**Reset**: `rag.reset()` → deletes ChromaDB collection and clears native store.

---

## 7. Content Generation

### 7.1 Document Generator

**File**: `app/pipeline/generation/document_generator.py:53`

**Class**: `DocumentGenerator`

**Purpose**: End-to-end document generation from scratch (not formatting existing docs).

**Flow** (`run_pipeline`, line 249):

1. Build prompt via `PromptBuilder.build(doc_type, metadata, options)`
2. Call LLM via `_llm_generate(prompt)` — NVIDIA → DeepSeek → rule-based skeleton
3. Parse LLM output via `ContentParser.parse(response, doc_type)`
4. Extract outline from heading blocks
5. Save structured data to Supabase
6. Format + export via `_format_and_export()` → Formatter + Exporter
7. Compute SHA-256 hash, mark document complete

**LLM fallback chain** (`_llm_generate`, line 446):

```
LLM_NVIDIA.complete(prompt) → fail → LLM_DEEPSEEK.complete(prompt) → fail → _rule_based_skeleton()
```

**Rule-based skeleton** (`_rule_based_skeleton`, line 484):

- Generates placeholder JSON with title, abstract, introduction/body/conclusion
- Supports `academic_paper` and `resume` doc types with different templates

**Session management**: `start_job()` creates Supabase `generator_sessions` record + `DocumentService.create_document()`. Status updates via SSE. Volatile fallback for DB-unavailable scenarios.

### 7.2 Prompt Builder

**File**: `app/pipeline/generation/prompt_builder.py:14`

**Class**: `PromptBuilder`

**Supported doc_types**:

- `academic_paper` — Title, Author, Affiliation, Abstract, Keywords, sections, References
- `resume` — Name, Contact, Summary, Skills, Experience, Education
- `portfolio` — Bio, Projects, Publications, research-focused
- `report` — Executive Summary, sections, Recommendations
- `thesis` — Chapter-structured with candidate/university/degree metadata

**Output format**: Strict JSON array instruction:

```json
[{"type": "TITLE|ABSTRACT|HEADING_1|BODY|...", "content": "...", "level": 0}]
```

### 7.3 Token Streaming

**SSE-based streaming** in `MultiDocSynthesizer` (`_stream_chunks`, line 638):

- Content chunked at 400 characters
- Events published via Redis Pub/Sub to `session:{session_id}` channel
- Event types: `stage_update`, `writing_chunk`, `outline_chunk`

**Agent streaming** (`StreamingAgentCallback` in `app/pipeline/agents/streaming.py`):

- Callback passed to LangChain `AgentExecutor`
- Captures intermediate steps for real-time UI updates

### 7.4 Quality Scoring

**File**: `app/pipeline/generation/quality_scorer.py:18`

**Class**: `QualityScorer`

**Metrics**:

- `template_compliance` (30%) — percentage of required sections present
- `content_completeness` (30%) — sections with ≥100 words
- `citation_score` (20%) — citations per section (regex patterns for `[1]`, `(Author, 2020)`)
- `section_balance` (20%) — coefficient of variation of section lengths

**Pipeline quality score** (orchestrator `_build_quality_summary`, line 444):

```
quality = (avg_confidence × 0.60) + (structure_score × 0.25) + (asset_score × 0.15) - penalty
```

Where `structure_score = 1.0` (if headings exist) else 0.45, `asset_score = 1.0` (if figures/tables exist) else 0.65.

---

## 8. Multi-Doc Synthesis

**File**: `app/pipeline/synthesis/synthesizer.py:42`

**Class**: `MultiDocSynthesizer`

**Purpose**: Synthesize 2–6 documents into a single coherent output.

**8-stage pipeline** (`run()`, line 59):

1. **Upload Validation**: Magic bytes, SHA-256 dedup, file type check, 2–6 file range
2. **Per-Doc Extraction**: Parallel `_run_extraction_stage()` via `asyncio.to_thread` + `asyncio.as_completed`
3. **Embedding**: `SessionVectorStore.create_collection(session_id)`, chunk at 1000 chars with 200-char overlap
4. **Cross-Doc Analysis**: LLM identifies overlaps, gaps, and unique points between documents
5. **Outline Generation**: LLM generates structured outline with title + sections + key points
6. **Content Generation**: Per-section generation with RAG context from vector store query (top_k=4)
7. **Citation Insertion**: `[REF:query]` → CrossRef lookup → CSL formatting → `[1]`, `[2]`, ...
8. **Template Render**: Formatter + Exporter → final DOCX

**Dependencies**: `GeneratorSessionService`, `SessionVectorStore`, `PipelineOrchestrator`, `RedisPubSub`, `CrossRefClient`, `CSLEngine`

---

## 9. Safety & Validation

### 9.1 LLM Output Validation

**File**: `app/pipeline/safety/llm_validator.py:49`

**Function**: `guard_llm_output(schema, error_return_value)`

**Two modes**:

1. **Guardrails AI** (preferred, Python < 3.14): Uses `guard = Guard.for_pydantic(output_class=schema)` → `guard.parse(raw_result_str)` for Pydantic schema compliance
2. **Native fallback**: `validator_guard.validate_output()` with basic Pydantic validation

**Prompt injection detection** in `llm_service.py:185-244`:

- 25+ regex patterns covering:
  - Ignore/forget/disregard previous instructions
  - System prompt extraction
  - API key/secret stealing
  - Dangerous tool calls (`delete_all_documents`, `drop table`)
  - Token smuggling (`base64 decode`, `hex decode`)
  - Multi-language injection (Chinese, Arabic, Russian)
  - XML/System tag injection (`<|im_start|>`, `<<SYS>>`)
  - Emotional manipulation (`begging you`, `developer mode`)
- Max input length: 8000 chars via `sanitize_for_llm()` (line 248)

### 9.2 Circuit Breaker Pattern

**File**: `app/pipeline/safety/circuit_breaker.py:32`

**Decorator**: `@circuit_breaker(failure_threshold, recovery_timeout, fallback_function)`

**States**: CLOSED → OPEN → HALF_OPEN → CLOSED

**Two implementations**:

1. **pybreaker-backed** (preferred): Thread-safe, listener-based, `pybreaker.CircuitBreaker`
2. **Legacy fallback** (no pybreaker): Manual counter with `time.time()` based reset

**Behavior**:

- OPEN: Calls blocked, fallback invoked if provided, else raises `CircuitBreakerOpenException`
- HALF_OPEN: Single probe call allowed; success → CLOSED, failure → OPEN
- Fallback chaining: If fallback also fails, returns `{}` (silent degradation)

### 9.3 Retry with Backoff

**File**: `app/pipeline/safety/retry_guard.py:13`

**Function**: `retry_with_backoff(max_retries=2, backoff_factor=1.0)` / `retry_guard`

**Pattern**: Exponential backoff: `sleep = backoff_factor * (2 ^ (retries - 1))`

**Usage**: `@retry_with_backoff(max_retries=2, backoff_factor=1.0)` — decorator for sync and async functions

**Helper**: `execute_with_retry(func, *args, max_retries=2, backoff_factor=1.0)` for inline retry wrapping.

### 9.4 Document Validation

**File**: `app/pipeline/validation/validator_v3.py:37`

**Class**: `DocumentValidator`

**YAML Contract System**: Validation rules driven by `contract.yaml` per publisher:

- `SectionOrderValidator` — enforces section ordering rules
- `CrossReferenceEngine` — validates internal refs (figure/table/equation numbers)
- `CrossRefClient` — validates citations against CrossRef API

**Safe wrapping**: All checks wrapped in `@safe_function(fallback_value=ValidationResult(is_valid=False, errors=["crash"]))`.

**AIExplainer** (`app/pipeline/validation/ai_explainer.py`): Generates human-readable explanations from validation results for the UI review panel.

---

## 10. Model Management

### 10.1 Model Store

**File**: `app/services/model_store.py`

**Singleton**: `model_store` — global in-memory registry for loaded models.

**Stored models**:

- `embedding_model` → SentenceTransformer for RAG
- `LLMClassifier_tokenizer` → LLMClassifier tokenizer
- `LLMClassifier_model` → LLMClassifier model
- Future: Other models

**Pre-loading**: `PRELOAD_AI_MODELS=true` (default) loads models at startup. `LOW_MEMORY_MODE=true` skips pre-loading and forces deterministic embedding fallback.

**LLMClassifier Gate** (`app/services/classification_gate.py`):

- `should_enable_LLMClassifier()` → checks `USE_LLM_CLASSIFICATION` env var
- If `LLM_CLASSIFIER_AUTO_ENABLE_FROM_BENCHMARK=true`: Only enables if benchmark F1 ≥ `LLM_CLASSIFIER_MIN_BENCHMARK_F1` (0.85)
- Benchmark state persisted in `.metrics/classification_benchmark_state.json`

### 10.2 Model Metrics

**File**: `app/services/model_metrics.py`

**Interface**: `get_model_metrics()` → `ModelMetrics` singleton

**Recorded**:

- `record_call(provider, success, latency)` — per-call success/failure
- `record_fallback(from_provider, to_provider, reason)` — fallback chain tracking
- `record_metrics(name, value, metadata)` — generic metric storage

**Prometheus integration**: `MetricsManager` records:

- `llm_request{provider, model, success}` — counter
- `llm_duration{provider, model}` — histogram
- `llm_ttft{provider, model}` — time to first token
- `llm_cache_hit/miss{provider, model}` — cache efficiency
- `pipeline_stage_duration{stage}` — stage timing

---

## 11. Monitoring & Observability

**Prometheus Metrics** (`app/middleware/prometheus_metrics.py`):

- `MetricsManager.record_pipeline_stage_duration(stage, duration)` → per-stage timing
- `MetricsManager.record_llm_request(provider, model, success)` → LLM call counts
- `MetricsManager.record_llm_duration(provider, model, duration)` → LLM latency
- `MetricsManager.record_llm_cache_hit/miss(provider, model)` → cache efficiency
- `MetricsManager.record_llm_failure(provider)` → failure tracking

**Error Tracking**: Error tracking is handled via Prometheus metrics and structured logging. (Sentry was removed.)

**Structured Logging**: `ENABLE_STRUCTURED_LOGGING` flag enables JSON log output. `log_extra()` utility adds context to log records.

**Health Checks**: `llm_service.check_health()` returns status of NVIDIA, OpenRouter, and Ollama/DeepSeek providers.

**Cancellation Monitoring**: `_check_cancelled(job_id)` polls Supabase for CANCELLED status between pipeline stages.

---

## 12. Configuration Reference

### LLM Provider Settings (`LLMSettings`, `settings.py:225`)

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `NVIDIA_API_KEY` | `None` | NVIDIA NIM API key |
| `NVIDIA_MODEL` | `""` | NVIDIA model name (e.g. `meta/llama-3.3-70b-instruct`) |
| `GROQ_API_KEY` | `None` | Groq API key |
| `GROQ_MODEL` | `""` | Groq model name |
| `GROQ_API_BASE` | `""` | Groq custom base URL |
| `OPENAI_API_KEY` | `None` | OpenAI API key |
| `ANTHROPIC_API_KEY` | `None` | Anthropic API key |
| `DEEPSEEK_API_KEY` | `None` | DeepSeek API key |
| `OPENROUTER_API_KEY` | `None` | OpenRouter API key |
| `OPENROUTER_MODEL` | `openai/gpt-4o-mini` | OpenRouter default model |
| `OPENROUTER_API_BASE` | `https://openrouter.ai/api/v1` | OpenRouter base URL |
| `GOOGLE_API_KEY` | `None` | Google AI API key |
| `COHERE_API_KEY` | `None` | Cohere API key |
| `MISTRAL_API_KEY` | `None` | Mistral API key |
| `OLLAMA_URL` | `""` | Ollama server URL |
| `OLLAMA_BASE_URL` | `""` | Ollama base URL (used if `OLLAMA_URL` empty) |
| `LLM_PROVIDER_TIMEOUT_SECONDS` | `15` | Per-LLM-call timeout |

### Pipeline AI Settings (`PipelineSettings`, `settings.py:252`)

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `GROBID_ENABLED` | `true` | Enable GROBID metadata extraction |
| `GROBID_URL` | `http://localhost:8070` | GROBID service URL |
| `GROBID_TIMEOUT` | `10s` | GROBID request timeout |
| `GROBID_MAX_RETRIES` | `3` | GROBID retry count |
| `USE_DOCLING_FALLBACK` | `true` | Enable Docling layout analysis |
| `PYMUPDF_FALLBACK` | `true` | Enable PyMuPDF metadata fallback |
| `PIPELINE_GROBID_TIMEOUT_SECONDS` | `30` | GROBID stage timeout |
| `PIPELINE_DOCLING_TIMEOUT_SECONDS` | `30` | Docling stage timeout |
| `PIPELINE_REASONING_TIMEOUT_SECONDS` | `60` | AI reasoning stage timeout |
| `PIPELINE_SEMANTIC_TIMEOUT_SECONDS` | `30` | LLMClassifier stage timeout |
| `PIPELINE_ACQUIRE_TIMEOUT_SECONDS` | `30.0` | Semaphore acquire timeout |
| `PIPELINE_DOCLING_SKIP_DIGITAL_PDF` | `false` | Skip Docling for digital-native PDFs |
| `PIPELINE_DOCLING_FORCE` | `false` | Force Docling even for digital PDFs |
| `ENABLE_LLM_PDF_PARSER` | `false` | Enable LLM-based PDF parsing parser |
| `ENABLE_NVIDIA_REASONER` | `false` | Enable NVIDIA NIM reasoning |
| `USE_LLM_CLASSIFICATION` | `false` | Enable LLM-based classification parsing |
| `LLM_CLASSIFIER_AUTO_ENABLE_FROM_BENCHMARK` | `true` | Auto-enable LLMClassifier based on F1 |
| `LLM_CLASSIFIER_MIN_BENCHMARK_F1` | `0.85` | Minimum F1 for auto-enable |
| `PRELOAD_AI_MODELS` | `true` | Pre-load AI models at startup |
| `LOW_MEMORY_MODE` | `false` | Low-memory mode (force deterministic embeddings) |
| `RAG_USE_TRANSFORMERS` | `true` | Use sentence-transformers for RAG |
| `DEFAULT_FAST_MODE` | `false` | Skip optional AI stages by default |

### RAG Settings (Environment Variables)

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `RAG_EMBEDDING_PROVIDER` | `""` | Embedding provider (e.g. `huggingface_api`) |
| `RAG_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | HF model for remote API |
| `RAG_EMBEDDING_API_URL` | `""` | Custom embedding API URL |
| `HF_TOKEN` | `""` | HuggingFace API token |
| `RAG_HF_TIMEOUT_SECONDS` | `30` | HF API request timeout |
| `RAG_HF_MAX_RETRIES` | `3` | HF API retry count |
| `RAG_HF_RETRY_BACKOFF_SECONDS` | `1.0` | HF API backoff |

### Cache & Redis Settings (`CacheSettings`, `settings.py:355`)

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `REDIS_ENABLED` | `false` | Enable Redis caching |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `LLM_CACHE_TTL_SECONDS` | `3600` | LLM response cache TTL |
| `CSL_SEARCH_CACHE_TTL_SECONDS` | `300` | CSL search cache TTL |
| `CSL_FETCH_CACHE_TTL_SECONDS` | `1800` | CSL fetch cache TTL |

### Circuit Breaker Settings (`DeploymentSettings`, `settings.py:386`)

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `EXTERNAL_CIRCUIT_BREAKER_ENABLED` | `true` | Enable per-provider circuit breakers |
| `EXTERNAL_CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `3` | Failures before circuit opens |
| `EXTERNAL_CIRCUIT_BREAKER_RESET_SECONDS` | `60` | Recovery timeout |

### Confidence Thresholds

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `HEADING_STYLE_THRESHOLD` | `0.8` | Minimum confidence for heading detection |
| `HEADING_FALLBACK_CONFIDENCE` | `0.5` | Fallback heading confidence |
| `HEURISTIC_CONFIDENCE_HIGH` | `0.9` | High heuristic confidence |
| `HEURISTIC_CONFIDENCE_MEDIUM` | `0.7` | Medium heuristic confidence |
| `HEURISTIC_CONFIDENCE_LOW` | `0.4` | Low heuristic confidence |

---

## 13. Performance Characteristics

### Stage Latency Estimates

| Stage | Typical | Timeout | Notes |
| ------- | --------- | --------- | ------- |
| ParserFactory | 0.5–3s | — | DOCX fastest, PDF PyMuPDF ~1s |
| GROBID | 5–15s | 30s | REST call to local service |
| Docling | 5–15s | 30s | REST call to local service |
| Structure Detection | 0.5–2s | — | Retry once on failure |
| Semantic Parser (LLMClassifier) | 10–30s | 30s | Local model: 0.5–2s/doc; Remote: +network |
| Content Classification | 0.5–2s | — | Regex + keyword matching |
| NLP Analysis | 0.5–3s | — | Keyword extraction |
| Caption Matching | 1–5s | — | Includes vision analysis |
| Reference Parsing | 1–5s | — | Regex-based |
| Reference Formatting | 1–3s | — | CSL engine |
| CrossRef Enrichment | 5–30s | — | Per-reference API calls (up to 4 workers) |
| AI Reasoning (RAG + LLM) | 15–60s | 60s | RAG query + LLM inference |
| Document Validation | 1–5s | 60s | Contract checks |
| Formatting | 5–20s | 60s | python-docx operations |
| Export | 2–10s | — | DOCX save → PDF/LaTeX/JATS |

**Total (fast mode, no AI)**: ~20–60s for a typical 10-page PDF
**Total (full AI)**: ~60–180s depending on document complexity and provider latency

### Throughput

- **Concurrent jobs**: 5 (hard limit via semaphore)
- **Per-job acquisition timeout**: 30s
- **Max upload**: 60MB per file, 10 files per batch
- **Rate limit**: 120 requests/minute global, 10 uploads/minute

### Memory Usage

| Component | RAM | Notes |
| ----------- | ----- | ------- |
| LLMClassifier local model | ~1.5GB | Only loaded when `USE_LLM_CLASSIFICATION=true` |
| BGE-M3 embedding | ~2.2GB | Only loaded when `RAG_USE_TRANSFORMERS=true` and not `LOW_MEMORY_MODE` |
| BGE-small-en-v1.5 | ~0.5GB | Lighter embedding fallback |
| GROBID | ~1.5GB (external Docker) | Separate process |
| Base application | ~200MB | Without AI models |
| Total (all models loaded) | ~4–5GB | Application + models |

**Memory optimization**: `LOW_MEMORY_MODE=true` skips all local model loading and uses deterministic hash embeddings + remote HuggingFace API.

---

## 14. Deployment Considerations

### GPU Requirements

| Component | GPU | Notes |
| ----------- | ----- | ------- |
| LLMClassifier | Optional (CPU: ~2s/doc) | Inference, no training |
| BGE-M3 embedding | Optional (CPU: ~1s/doc) | sentence-transformers on CPU is adequate |
| NVIDIA NIM | External API | No local GPU needed |
| Ollama | Optional (GPU: ~10× faster) | Local 8B model runs on CPU at ~5 tok/s |
| GROBID | CPU only | Java service |
| Docling | CPU only | Layout analysis |

### Memory Requirements

| Tier | RAM | AI Features Available |
| ------ | ----- | ---------------------- |
| Minimal | 512MB + 2GB swap | No local models; deterministic embeddings; remote APIs only |
| Standard | 4GB | Deterministic embeddings; LLMClassifier if enabled; remote LLMs |
| AI-Enhanced | 8GB | BGE-M3 + LLMClassifier local; optional Ollama |
| Full | 16GB+ | All local models + Ollama with 8B+ models |

### Service Dependencies

| Service | Type | RAM | Deployment |
| --------- | ------ | ----- | ------------ |
| GROBID | Docker (Java) | ~1.5GB | HF Spaces / Render / self-hosted |
| Docling | Docker (Python) | ~2GB | HF Spaces / Render / self-hosted |
| ChromaDB | Embedded | — | Runs in-process |
| Redis | External | ~100MB | Render Redis / Upstash |
| Supabase | External | — | Managed SaaS |
| HF Spaces | Serverless | — | For LLMClassifier/GROBID endpoints |

### Deployment Types

**Render (primary)**: Web service + Celery worker + Redis. GROBID/Docling as external services.

**HF Spaces**: GROBID, Docling, LLMClassifier as free-tier HF Spaces with auto-sleep.

**Local dev**: All services via Docker Compose (GROBID, Docling, Redis). Models loaded on demand.

**Production recommendation**: `LOW_MEMORY_MODE=true`, `PRELOAD_AI_MODELS=false`, `DEFAULT_FAST_MODE=true`, LLMClassifier via remote HF Space endpoint, GROBID via HF Space, LLMs via NVIDIA NIM/Groq API keys.

---

## 15. Testing & Validation

The AI pipeline uses a 4-tier test pyramid spanning unit → integration → golden file → end-to-end tests. All test files reside under `backend/tests/`.

```mermaid
graph TD
    subgraph Tier4["Tier 4: E2E (5%)"]
        E2E["Playwright e2e tests<br/>Full pipeline smoke tests<br/>frontend/e2e/*.spec.ts"]
    end

    subgraph Tier3["Tier 3: Golden File (15%)"]
        GF["Golden file regression<br/>test_formatting_enterprise.py<br/>test_orchestrator.py"]
    end

    subgraph Tier2["Tier 2: Integration (30%)"]
        INT["GROBID/Docling mock fixtures<br/>pipeline stage wiring tests<br/>test_enterprise_batch*.py"]
    end

    subgraph Tier1["Tier 1: Unit (50%)"]
        UNIT["Mocked LLM/MagicMock chains<br/>Circuit breaker state tests<br/>RAG engine mock tests<br/>test_pipeline/*_test*.py"]
    end

    E2E --> GF --> INT --> UNIT
```

### 15.1 Unit Testing Patterns

Each pipeline stage is tested in isolation with all external dependencies mocked at the import boundary.

**Pattern — mock external service, test stage logic**:

```python
from unittest.mock import patch, MagicMock

@patch("app.pipeline.intelligence.semantic_parser.AutoTokenizer")
@patch("app.pipeline.intelligence.semantic_parser.AutoModelForSequenceClassification")
def test_semantic_parser_returns_labels(mock_model, mock_tokenizer):
    mock_tokenizer.return_value = MagicMock()
    mock_model.return_value = MagicMock()
    parser = SemanticParser()
    blocks = [Block(text="Introduction", block_type=BlockType.HEADING_1)]
    result = parser.parse(blocks)
    assert len(result) > 0
```

**Key files**: `tests/pipeline/test_enterprise_batch1.py` (85 tests), `tests/pipeline/test_enterprise_batch2.py` (135 tests), `tests/pipeline/test_enterprise_batch3.py` (56 tests).

### 15.2 Integration Testing with Mock Fixtures

GROBID and Docling are Docker services. Tests use mock fixtures that return canned XML/JSON responses without launching containers.

**Pattern — GROBID mock fixture**:

```python
@pytest.fixture
def mock_grobid_client():
    with patch("app.pipeline.services.grobid_client.GrobidClient.process_document") as mock:
        mock.return_value = {
            "title": "Sample Paper",
            "authors": [{"given": "John", "family": "Doe"}],
            "abstract": "This is a sample abstract.",
            "doi": "10.1234/example",
        }
        yield mock
```

**Key considerations**:

- Patch the **source module**, not the consumer — `app.pipeline.services.grobid_client.GrobidClient`, not `app.pipeline.orchestrator.GrobidClient`
- Async methods require `from unittest.mock import AsyncMock` and `mock.return_value = AsyncMock()` or `mock.side_effect = AsyncMock()`
- Lazy imports inside function bodies (e.g. `from app.pipeline.orchestrator import PipelineOrchestrator`) require patching the source module path

**Test files**: `tests/pipeline/test_orchestrator.py` (15 tests), `tests/pipeline/test_orchestrator_deep.py` (34 tests).

### 15.3 Golden File Regression Testing

Formatting output is validated against golden (reference) DOCX files stored in `tests/fixtures/golden/`. A golden file test:

1. Runs the format pipeline on a known input
2. Compares output checksum or content structure against the golden reference
3. Fails if the output diverges — preventing silent regressions

**Pattern**:

```python
def test_formatting_matches_golden(golden_file_regression):
    input_doc = load_fixture("simple_ieee_paper.json")
    result = formatter.format(input_doc)
    golden_file_regression.check(result.generated_doc.element.xml)
```

**Test files**: `tests/pipeline/test_formatting_enterprise.py` (87 tests), `tests/test_formatting_enterprise.py` (87 tests).

### 15.4 LLM Mocking with MagicMock Chain Patterns

LLM service calls (`generate_with_fallback`, `generate_with_model`) are replaced with `MagicMock` chains to avoid real API calls.

**Pattern — mock LLM return value**:

```python
@patch("app.services.llm_service.generate_with_fallback")
def test_reasoning_engine_uses_llm_advice(mock_generate):
    mock_generate.return_value = {"text": '{"blocks": [{"type": "BODY", "advice": "rewrite"}]}'}
    engine = ReasoningEngine(...)
    advice = engine.generate_instruction_set(blocks, rules)
    assert advice[0].get("advice") == "rewrite"
```

**Key MagicMock chain behaviors**:

- Each attribute access creates a **new** `MagicMock` — chain segments must be separate for conditional `.eq()` filters
- `model_copy` on `MagicMock` returns a `MagicMock` — set `.text` on the copy explicitly
- Two different `MagicMock` instances are `!=` (identity check) — share mocks when tests compare objects
- `patch.object(Cls, "method")` replaces the class attribute — `instance.method(args)` passes `self` to side_effect (3 params). Use `patch.object(instance, "method")` to get 2 params

**MagicMock model_copy pattern**:

```python
mock_resp = MagicMock()
mock_resp.text = "original"
mock_copy = MagicMock(text="fallback")
mock_resp.model_copy = lambda **kw: mock_copy
```

### 15.5 Circuit Breaker Test Patterns

Circuit breakers (`app/pipeline/safety/circuit_breaker.py`) are tested by forcing failure thresholds and verifying state transitions.

**Pattern — state machine verification**:

```python
def test_circuit_breaker_transitions_to_open():
    call_count = 0
    @circuit_breaker(failure_threshold=2, recovery_timeout=60)
    def failing_func():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("API down")

    with pytest.raises(ConnectionError):
        failing_func()

    with pytest.raises(CircuitBreakerOpenException):
        failing_func()

    assert call_count == 2
```

**Key behaviors**:

- OPEN state: calls blocked, fallback invoked if provided
- HALF_OPEN: single probe call allowed; success → CLOSED, failure → OPEN
- `pybreaker.CircuitBreaker` (preferred) vs legacy manual counter fallback
- Module-level `sys.modules` contamination: files that inject `pybreaker` mocks must save originals and restore (via `atexit.register`)

**Test files**: `tests/pipeline/test_circuit_breaker*.py`, `tests/pipeline/test_enterprise_batch1.py`.

### 15.6 RAG Engine Test Patterns

`RagEngine` (`app/pipeline/intelligence/rag_engine.py`) requires mocking ChromaDB and embedding model loading.

**Pattern — mock ChromaDB + embedding fallback**:

```python
@patch("app.pipeline.intelligence.rag_engine.RagEngine._load_embedding_model")
@patch("chromadb.PersistentClient")
def test_rag_query_falls_back_to_native_store(mock_chroma, mock_embed):
    mock_embed.return_value = MagicMock()
    mock_chroma.return_value.get_or_create_collection.return_value.query.side_effect = Exception("ChromaDB down")
    engine = RagEngine(...)
    engine.knowledge_base = [{"text": "rule 1", "embedding": [0.1, 0.2, 0.3]}]
    engine._compute_embedding = MagicMock(return_value=[0.1, 0.2, 0.3])
    results = engine.query_guidelines("IEEE", "abstract", top_k=1)
    assert len(results) == 1
    assert "rule 1" in results[0]
```

**Key behaviors**:

- `RagEngine.__init__` calls `_load_embedding_model` which connects to HuggingFace — **must** patch this in tests
- Data stored in `self.knowledge_base` (not `self.guidelines`)
- `_is_reusable_embedding_model` returns `tuple[bool, Optional[int]]`, not just `bool`
- ChromaDB `PersistentClient` raises `numpy` compatibility errors with NumPy 2.0+ — mock avoids this

**Test files**: `tests/pipeline/test_rag_engine*.py`, `tests/pipeline/test_enterprise_batch2.py`.

---

## 16. API Endpoint Reference

All AI-related API endpoints are served under the `api/v1` prefix. Each endpoint is documented in its respective router file.

| Endpoint | Method | Description | Router File |
| ---------- | -------- | ------------- | ------------- |
| `/api/v1/generator/sessions` | `POST` | Create generation session (agent or multi-doc) | `routers/v1/generator.py:260` |
| `/api/v1/generator/sessions` | `GET` | List user's generation sessions | `routers/v1/generator.py:426` |
| `/api/v1/generator/sessions/{sessionId}` | `GET` | Get session status and metadata | `routers/v1/generator.py:444` |
| `/api/v1/generator/sessions/{sessionId}/messages` | `GET` | Retrieve session message history | `routers/v1/generator.py:476` |
| `/api/v1/generator/sessions/{sessionId}/messages` | `POST` | Send message to agent (supports rewrite detection) | `routers/v1/generator.py:616` |
| `/api/v1/generator/sessions/{sessionId}/outline/approve` | `POST` | Approve outline and resume generation | `routers/v1/generator.py:759` |
| `/api/v1/generator/sessions/{sessionId}/stop` | `POST` | Cancel an active session | `routers/v1/generator.py:809` |
| `/api/v1/generator/sessions/{sessionId}/document` | `GET` | Fetch latest generated document content | `routers/v1/generator.py:510` |
| `/api/v1/generator/sessions/{sessionId}/download` | `GET` | Download generated DOCX/PDF artifact | `routers/v1/generator.py:540` |
| `/api/v1/generator/sessions/{sessionId}/events` | `GET` | SSE stream for session events | `routers/v1/generator.py:568` |
| `/api/v1/synthesis/sessions` | `POST` | Create multi-doc synthesis session (2-6 files) | `routers/v1/synthesis.py:89` |
| `/api/v1/synthesis/sessions/{sessionId}` | `GET` | Get synthesis session status | `routers/v1/synthesis.py:179` |
| `/api/v1/synthesis/sessions/{sessionId}/events` | `GET` | SSE stream for synthesis events | `routers/v1/synthesis.py:211` |
| `/api/v1/synthesis/sessions/{sessionId}/messages` | `POST` | Send Q&A message on synthesized documents | `routers/v1/synthesis.py:259` |
| `/api/v1/stream/{jobId}` | `GET` | SSE stream for pipeline/job progress events | `routers/v1/stream.py:57` |
| `/api/v1/providers` | `GET` | List all available providers with models | `routers/v1/providers.py:169` |
| `/api/v1/providers/health` | `GET` | Check provider configuration status | `routers/v1/providers.py:154` |
| `/api/v1/providers/{providerId}/models` | `GET` | Discover models from a provider's live API | `routers/v1/providers.py:187` |
| `/api/v1/providers/{providerId}/models/sync` | `POST` | Cache discovered models for model selector | `routers/v1/providers.py:244` |
| `/api/v1/providers/custom` | `POST` | Register a custom (BYO) provider | `routers/v1/providers.py:259` |
| `/api/v1/providers/custom` | `GET` | List user's custom providers | `routers/v1/providers.py:295` |
| `/api/v1/providers/custom/{id}` | `GET` | Get custom provider details | `routers/v1/providers.py:307` |
| `/api/v1/providers/custom/{id}` | `PUT` | Update custom provider configuration | `routers/v1/providers.py:324` |
| `/api/v1/providers/custom/{id}` | `DELETE` | Remove a custom provider | `routers/v1/providers.py:363` |
| `/api/v1/providers/test` | `POST` | Test provider connection (rate-limited) | `routers/v1/providers.py:384` |
| `/api/v1/metrics/health` | `GET` | AI service health (LLM, DB, models) | `routers/v1/metrics.py:114` |
| `/api/v1/metrics/dashboard` | `GET` | Admin dashboard with model metrics and A/B test results | `routers/v1/metrics.py:161` |
| `/api/v1/metrics/enhancements` | `GET` | Enhancement manager profile and queue status | `routers/v1/metrics.py:208` |
| `/api/v1/metrics/usage` | `GET` | User usage analytics (7d/30d/90d/all) | `routers/v1/metrics.py:235` |
| `/api/v1/health` | `GET` | Basic liveness check | `routers/v1/health.py:22` |
| `/api/v1/health/live` | `GET` | Kubernetes-style liveness probe | `routers/v1/health.py:28` |
| `/api/v1/health/ready` | `GET` | Readiness check (DB + LLM providers) | `routers/v1/health.py:33` |

---

## 17. Operations & Monitoring

### 17.1 Prometheus Metrics

The following counters and histograms are registered in `app/middleware/prometheus_metrics.py` and should be scraped for production monitoring:

| Metric | Type | Labels | Source |
| -------- | ------ | -------- | -------- |
| `llm_requests_total` | Counter | `provider`, `model`, `success` | `llm_service.generate()` |
| `llm_duration_seconds` | Histogram | `provider`, `model` | Per-LLM-call timing |
| `llm_time_to_first_token` | Histogram | `provider`, `model` | Streaming TTFT |
| `llm_cache_hit_total` | Counter | `provider`, `model` | LLM response cache |
| `llm_cache_miss_total` | Counter | `provider`, `model` | LLM response cache |
| `llm_failures_total` | Counter | `provider` | `llm_service.generate()` failures |
| `circuit_breaker_state` | Gauge | `breaker_name`, `state` | `pybreaker.CircuitBreaker` listener |
| `circuit_breaker_transitions_total` | Counter | `breaker_name`, `from_state`, `to_state` | State transition listener |
| `pipeline_stage_duration_seconds` | Histogram | `stage` | Per-stage timing in `PipelineOrchestrator` |
| `pipeline_stage_failures_total` | Counter | `stage` | Failed stage executions |
| `rag_query_duration_seconds` | Histogram | `backend` (chromadb/native) | `RagEngine.query_guidelines()` |
| `rag_query_results_count` | Histogram | `backend` | Number of results per query |
| `rag_embedding_fallback_total` | Counter | `from_provider`, `to_provider` | Embedding model fallback chain |
| `agent_tool_usage_total` | Counter | `tool_name`, `status` | Agent tool calls |
| `sse_connections_current` | Gauge | — | Active SSE connections |
| `provider_operations_total` | Counter | `action`, `status` | Provider CRUD + test operations |

### 17.2 Alert Recommendations

Configure alerts on the following thresholds in production:

| Alert Rule | Condition | Severity | Rationale |
| ------------ | ----------- | ---------- | ----------- |
| LLM Error Rate >5% | `rate(llm_requests_total{success="false"}[5m]) / rate(llm_requests_total[5m]) > 0.05` | Critical | All 4 tiers failing — users cannot generate content |
| Circuit Breaker Open >5min | `avg_over_time(circuit_breaker_state{state="open"}[5m]) > 0` | Warning | Provider degradation — fallback chain active |
| Pipeline Stage Timeout >1% | `rate(pipeline_stage_failures_total[15m]) / rate(pipeline_stage_duration_seconds_count[15m]) > 0.01` | Warning | Stage timeout indicates resource pressure |
| RAG Query Latency >5s p95 | `histogram_quantile(0.95, rate(rag_query_duration_seconds[5m])) > 5` | Warning | ChromaDB or embedding degradation |
| All 4 LLM Tiers Down | `llm_failures_total{provider="nvidia"} - ... offset 5m > 0` (4 consecutive) | Critical | Complete LLM outage — rule-based fallback only |
| Pipeline Concurrency at Limit | `sum(pipeline_stage_duration_seconds_count[1m]) / (5 * 60) > 0.9` | Warning | Near semaphore limit — queueing imminent |
| Embedding Fallback Active >30min | `rate(rag_embedding_fallback_total[30m]) > 0` | Warning | Primary embedding model unavailable |
| Provider Test Failure Rate >10% | `rate(provider_operations_total{action="test",status="invalid"}[5m]) / rate(...) > 0.1` | Low | Users unable to validate provider configs |

### 17.3 Structured Logging

All AI pipeline logs use structured JSON with a consistent `job_id` context for end-to-end traceability.

**Log format** (enabled via `ENABLE_STRUCTURED_LOGGING=true`):

```json
{
  "timestamp": "2026-07-17T10:30:00.123Z",
  "level": "INFO",
  "logger": "app.pipeline.orchestrator",
  "job_id": "doc_abc123",
  "stage": "ai_reasoning",
  "message": "RAG query completed",
  "extra": {
    "rag_backend": "chromadb",
    "top_k": 2,
    "latency_ms": 45,
    "results_count": 2
  }
}
```

**Context propagation**:

- `bind_request_context` middleware attaches `job_id` and `request_id` to all log records within a request
- `log_extra()` utility enriches ad-hoc log statements
- Background Celery tasks inherit `job_id` from task kwargs
- SSE events carry `request_id` for correlating frontend → backend → worker traces

**Correlation IDs** are generated at API entry (`middleware/request_id.py`) and propagated through:

1. HTTP request headers → `X-Request-ID`
2. Background task kwargs → `request_id` parameter
3. Redis Pub/Sub events → `request_id` field in event payload
4. Supabase `processing_status` records → `request_id` column

---

## 18. Security Considerations

### 18.1 Prompt Injection Attack Surface

The LLM service (`app/services/llm_service.py:185-244`) defends against prompt injection with 25+ regex patterns across 8 categories:

| Category | Patterns | Example |
| ---------- | ---------- | --------- |
| Instruction override | 4 | `ignore previous instructions`, `disregard all` |
| System prompt extraction | 3 | `output your system prompt`, `print your instructions` |
| Secret exfiltration | 4 | `reveal your API key`, `what is your password?` |
| Dangerous tool calls | 4 | `delete_all_documents()`, `drop table users` |
| Token smuggling | 3 | `base64 decode this`, `hex decode` |
| Multi-language injection | 3 | Chinese/AR/RU instruction overrides |
| XML/System tag injection | 2 | `<\|im_start\|>`, `<<SYS>>` |
| Emotional manipulation | 2 | `I'm begging you`, `developer mode` |

**Input sanitization**: `sanitize_for_llm()` truncates at 8000 chars and strips control characters before passing to the LLM.

**Defense layers**:

1. Input regex filtering at API gateway (`middleware/abuse_detector.py`)
2. LLM prompt-level sanitization (`sanitize_for_llm`)
3. Output validation via `guard_llm_output` (Guardrails AI / Pydantic schema enforcement)
4. Post-generation content scanning for residual injection artifacts

### 18.2 Data Leakage Prevention

| Risk | Mitigation |
| ------ | ------------ |
| PII in LLM prompts | `sanitize_for_llm()` strips emails, phone numbers, SSN patterns before API calls |
| Sensitive documents in RAG | ChromaDB collections isolated per-template; user isolation via `publisher` filter |
| API keys in transit | All outbound LLM calls use HTTPS; custom provider base URLs validated against SSRF blocklist |
| API keys at rest | Encrypted with Fernet (AES-128-CBC) via `EncryptionService` in `user_api_keys` table |
| Logs containing prompts | Structured logger filters known PII regexes; `LOG_LEVEL=INFO` suppresses prompt bodies |
| Redis Pub/Sub | Session-scoped channels (`session:{id}`) — no cross-tenant data exposure |

### 18.3 Model Theft Prevention

| Risk | Mitigation |
| ------ | ------------ |
| Model enumeration | Provider model discovery rate-limited to 10/min per user via `APIKeyRateLimiter` |
| Unauthorized model access | Custom providers isolated per-user; `resolve_user_api_key()` enforces user ownership |
| Model output scraping | `abuse_detector.record_llm_call()` tracks per-user LLM call volume; `MAX_FILE_SIZE` limits document throughput |
| Embedding model extraction | `RagEngine` does not expose raw embeddings via API; only text results returned |
| Local model bypass | `LOW_MEMORY_MODE` forces deterministic embeddings — no trainable weights exposed |

### 18.4 Dependency Supply Chain

| Risk | Mitigation |
| ------ | ------------ |
| HuggingFace model provenance | Models pinned to specific revisions (`allenai/LLMClassifier_scivocab_uncased`, `BAAI/bge-m3`); no wildcard model loading |
| LLMPDFParser parser availability | Gated behind `ENABLE_LLM_PDF_PARSER=true` (opt-in); installed from `transformers` registry, not arbitrary sources |
| GROBID/Docling container validation | Docker images pinned to tags (`grobid/grobid:0.8.0`, `ds4sd/docling:latest`) — tag immutability verified in CI |
| Python dependency verification | `requirements.txt` with exact versions; `pip install --require-hashes` in CI/CD |
| LLM provider API key rotation | Keys stored in `user_api_keys` with `created_at`/`updated_at` timestamps; `EncryptionService` supports key rotation |

---

## 19. Deployment Tiers

### 19.1 Tier Recommendations

| Tier | CPU | RAM | GPU | AI Features | Estimated Cost/Month |
| ------ | ----- | ----- | ----- | ------------- | --------------------- |
| **Free / Dev** | 2 vCPU | 4GB | None | Deterministic embeddings; remote LLMs only; LLMClassifier via HF Spaces; GROBID via HF Spaces | $0–$25 (Render free tier) |
| **Starter** | 2 vCPU | 8GB | None | BGE-small-en-v1.5 embeddings; remote LLMs; LLMClassifier via HF Spaces; GROBID via HF Spaces | $25–$75 (Render starter) |
| **Production (Standard)** | 4 vCPU | 8GB | Optional T4 | BGE-M3 embeddings; NVIDIA NIM + Groq LLMs; LLMClassifier remote; GROBID self-hosted Docker | $150–$400 (Render pro + HF Spaces + API keys) |
| **Production (AI-Enhanced)** | 8 vCPU | 16GB | T4 (16GB) | All local models: BGE-M3, LLMClassifier, LLM-based PDF parsing; Ollama 8B local fallback; GROBID + Docling self-hosted | $400–$1,200 (Render pro + GPU instance) |
| **Enterprise** | 16 vCPU | 32GB | A10G (24GB) | Full local stack + Ollama 70B local; redundant LLM tiers; GROBID + Docling clustered; Redis cluster; ChromaDB HA | $1,200–$4,000 (multi-instance + HA) |

### 19.2 Service Topology Per Tier

**Production (Standard) — recommended starting point**:

```
┌─ Render Web Service ─────────────────────┐
│ FastAPI (4 vCPU, 8GB)                    │
│  ├─ LOW_MEMORY_MODE=true                  │
│  ├─ PRELOAD_AI_MODELS=false               │
│  ├─ DEFAULT_FAST_MODE=true                │
│  ├─ RAG_EMBEDDING_PROVIDER=huggingface_api│
│  └─ SSE streaming via Redis               │
├─ Render Celery Worker ────────────────────┤
│ Background pipeline tasks (2 vCPU, 4GB)   │
├─ Render Redis ────────────────────────────┤
│ Pub/sub + LLM cache + rate limiting       │
├─ HF Spaces ───────────────────────────────┤
│ GROBID (1.5GB) + Docling (2GB) + LLMClassifier  │
│ Auto-sleep on idle                        │
├─ NVIDIA NIM API ──────────────────────────┤
│ Primary LLM tier                          │
├─ Groq API ────────────────────────────────┤
│ Fallback LLM tier                         │
├─ Supabase ────────────────────────────────┤
│ Primary DB + file storage                 │
└───────────────────────────────────────────┘
```

**Enterprise — maximum throughput and resilience**:

```
┌─ Load Balancer ──────────────────────────────┐
├─ Web Service Cluster (×3) ───────────────────┤
│ FastAPI (16 vCPU, 32GB each)                 │
│  LOW_MEMORY_MODE=false                       │
│  PRELOAD_AI_MODELS=true                      │
│  All local models: BGE-M3 + LLMClassifier          │
├─ Celery Worker Pool (×2) ────────────────────┤
│ Background pipeline (8 vCPU, 16GB each)      │
├─ GPU Worker ─────────────────────────────────┤
│ A10G: LLM-based PDF parsing + Ollama 70B (local LLM)   │
├─ Redis Cluster ──────────────────────────────┤
│ 3 nodes: caching + pub/sub + rate limiting   │
├─ GROBID Cluster (×2) ────────────────────────┤
│ Java services behind internal LB (3GB each)  │
├─ Docling Cluster (×2) ───────────────────────┤
│ Python services behind internal LB (4GB each)│
├─ NVIDIA NIM API ─────────────────────────────┤
├─ Groq API ───────────────────────────────────┤
├─ OpenRouter API ─────────────────────────────┤
├─ Ollama (local, 70B) ────────────────────────┤
│ 4th-tier LLM fallback on GPU                 │
├─ ChromaDB (persistent) ──────────────────────┤
├─ Supabase ───────────────────────────────────┤
└──────────────────────────────────────────────┘
```

### 19.3 Horizontal Scaling Strategy

| Constraint | Scaling Approach |
| ------------ | ------------------ |
| Semaphore limit (5 concurrent jobs) | Increase `_MAX_CONCURRENT_JOBS` with CPU/memory headroom; monitor `pipeline_stage_duration_seconds` for latency regression |
| GROBID throughput (~1 req/s per instance) | Deploy multiple GROBID instances behind internal load balancer; configure `GROBID_URLS` for round-robin |
| Docling memory (~2GB/instance) | Scale workers horizontally; each worker handles 1 Docling call at a time |
| ChromaDB write contention | Use persistent single-instance ChromaDB; writes are sequential (guideline seeding) — reads scale with embedding parallelism |
| Redis pub/sub fan-out | Redis Cluster for high-throughput SSE; monitor `sse_connections_current` gauge |
| LLM API rate limits | Configure `CROSSREF_MAX_WORKERS` and pipeline concurrency to stay within tier limits; BYOK distributes rate limit across user keys |

### 19.4 Cold Start Mitigation

| Component | Cold Start Issue | Mitigation |
| ----------- | ----------------- | ------------ |
| HF Spaces (GROBID/Docling) | 20–40s start on idle wake | `KEEP_WARM_PING_INTERVAL_SECONDS` (default 300) sends periodic health checks |
| LLMClassifier local model | 5–10s model load time | `PRELOAD_AI_MODELS=true` loads at startup; `LOW_MEMORY_MODE` skips entirely |
| BGE-M3 embedding model | 8–15s load time | Pre-loaded via `ModelStore` singleton; lazy init on first `RagEngine` query if not pre-loaded |
| ChromaDB collection creation | 1–2s first query | Collections created at startup via `RagEngine.__init__` `get_or_create_collection()` |
| Docker container pull | 30–60s | Pull images during deployment; use `imagePullPolicy: IfNotPresent` in K8s |

---

## 20. Operations & Monitoring — Enhancement Reference

### 20.1 Grafana Dashboard Recommendations

Configure the following Grafana dashboard panels using the Prometheus metrics from Section 17.1:

| Dashboard Panel | Metrics Used | Visualization | Refresh |
| ---------------- | ------------- | --------------- | --------- |
| **LLM Request Rate** | `rate(llm_requests_total[5m])` | Stacked bar chart by `provider` | 15s |
| **LLM Error Rate** | `rate(llm_requests_total{success="false"}[5m]) / rate(llm_requests_total[5m])` | Time series with threshold line at 5% | 15s |
| **P50/P95/P99 LLM Latency** | `histogram_quantile(0.50/0.95/0.99, rate(llm_duration_seconds[5m]))` | Three time series per provider | 30s |
| **Circuit Breaker States** | `circuit_breaker_state{state="open"}` over time | State heatmap (green/yellow/red per breaker) | 15s |
| **Pipeline Stage Duration** | `histogram_quantile(0.95, rate(pipeline_stage_duration_seconds[5m]))` | Horizontal bar chart by `stage` | 30s |
| **Pipeline Stage Failure Rate** | `rate(pipeline_stage_failures_total[15m])` | Time series per `stage` | 30s |
| **RAG Query Performance** | `histogram_quantile(0.95, rate(rag_query_duration_seconds[5m]))` | Split by `backend` (chromadb vs native) | 60s |
| **Agent Tool Usage** | `rate(agent_tool_usage_total[5m])` | Pie chart by `tool_name` | 60s |
| **Active SSE Connections** | `sse_connections_current` | Single stat gauge | 5s |
| **Provider Health Status** | `rate(provider_operations_total{status="invalid"}[5m])` | Single stat + threshold | 30s |
| **Pipeline Concurrency** | `sum(pipeline_stage_duration_seconds_count[1m]) / (5 * 60)` | Gauge with warning at 0.8 | 15s |
| **Embedding Model Usage** | `rag_embedding_fallback_total` | Stacked area by `to_provider` | 60s |
| **Cache Hit Ratio** | `llm_cache_hit_total / (llm_cache_hit_total + llm_cache_miss_total)` | Time series per `provider` | 30s |
| **TTFT Distribution** | `histogram_quantile(0.50/0.95, rate(llm_time_to_first_token[5m]))` | Two time series | 30s |

### 20.2 Alert Rule Definitions

Extend the Section 17.2 alert table with Prometheus-compatible alerting rules:

```yaml
# prometheus-rules.yml — AI Pipeline Alerting Rules
groups:
  - name: ai_pipeline_alerts
    interval: 30s
    rules:
      - alert: HighLLMErrorRate
        expr: rate(llm_requests_total{success="false"}[5m]) / rate(llm_requests_total[5m]) > 0.05
        for: 2m
        labels: { severity: critical }
        annotations:
          summary: "LLM error rate above 5% (current: {{ $value | humanizePercentage }})"
          runbook_url: "docs/runbooks/llm-error-rate.md"

      - alert: CircuitBreakerStuckOpen
        expr: avg_over_time(circuit_breaker_state{state="open"}[5m]) > 0
        for: 5m
        labels: { severity: warning }
        annotations:
          summary: "Circuit breaker {{ $labels.breaker_name }} stuck OPEN for >5min"
          description: "Provider {{ $labels.breaker_name }} has been degraded for >5 minutes."

      - alert: PipelineStageTimeoutRate
        expr: rate(pipeline_stage_failures_total[15m]) / rate(pipeline_stage_duration_seconds_count[15m]) > 0.01
        for: 5m
        labels: { severity: warning }
        annotations:
          summary: "Pipeline stage {{ $labels.stage }} timeout rate >1%"

      - alert: AllLLMTiersDown
        expr: llm_failures_total{provider="nvidia"} - llm_failivals_total{provider="nvidia"} offset 5m > 0
        for: 1m
        labels: { severity: critical }
        annotations:
          summary: "All 4 LLM tiers unreachable — system operating on rule-based fallback only"

      - alert: RAGQueryLatencySpike
        expr: histogram_quantile(0.95, rate(rag_query_duration_seconds[5m])) > 5
        for: 2m
        labels: { severity: warning }
        annotations:
          summary: "RAG query p95 latency >5s (backend: {{ $labels.backend }})"

      - alert: LLMCacheHitRateDrop
        expr: llm_cache_hit_total / (llm_cache_hit_total + llm_cache_miss_total) < 0.1
        for: 10m
        labels: { severity: low }
        annotations:
          summary: "LLM cache hit rate below 10% — cache configuration may need review"

      - alert: EmbeddingFallbackActive
        expr: rate(rag_embedding_fallback_total[30m]) > 0
        for: 30m
        labels: { severity: warning }
        annotations:
          summary: "Primary embedding model unavailable for >30min — fallback active"
```

### 20.3 Logging Best Practices

All AI pipeline components MUST emit structured JSON logs with the following consistent schema:

**Required fields** (every log record):

```json
{
  "timestamp": "2026-07-17T10:30:00.123Z",
  "level": "INFO|WARN|ERROR|DEBUG",
  "logger": "app.pipeline.<module>",
  "request_id": "req_abc123",
  "job_id": "doc_abc123",
  "message": "human-readable description",
  "extra": {}
}
```

**Stage-specific extra fields**:

| Stage | Extra Fields | Example |
| ------- | ------------- | --------- |
| ParserFactory | `parser`, `file_size`, `extension`, `block_count` | `{parser: "DocxParser", block_count: 142}` |
| GROBID/Docling | `service`, `latency_ms`, `success`, `retry_count` | `{service: "GROBID", latency_ms: 1234}` |
| LLM Call | `provider`, `model`, `latency_ms`, `tokens_in`, `tokens_out`, `cache_hit` | `{provider: "nvidia", tokens_out: 512}` |
| Circuit Breaker | `breaker_name`, `state`, `from_state`, `to_state` | `{breaker_name: "llm_nvidia", state: "open"}` |
| RAG Query | `backend`, `top_k`, `results`, `latency_ms` | `{backend: "chromadb", results: 2}` |
| Pipeline Stage | `stage`, `duration_ms`, `status` | `{stage: "structure_detection", duration_ms: 450}` |
| Agent | `tool_name`, `status`, `duration_ms`, `tier` | `{tool_name: "ValidationTool", status: "success"}` |

**Performance-sensitive areas to log with `DEBUG` level** (enable via `LOG_LEVEL=DEBUG`):

- Per-token streaming chunks (aggregated by event batch, not individual tokens)
- ChromaDB query plans and collection stats
- Thread pool queue wait times
- Stage semaphore acquisition blocking

### 20.4 Health Check Endpoint Details

```python
# app/services/llm_service.py:821
async def check_health() -> Dict[str, str]:
    """
    Returns per-provider status: "ok", "degraded" (circuit half-open), "down" (circuit open).
    Aggregated status = "healthy" if at least one LLM tier is reachable.
    """
```

**Consumed by**:

- `/api/v1/health/ready` — Kubernetes readiness probe (line 33)
- `/api/v1/metrics/health` — admin AI health dashboard (line 114)
- `/api/v1/providers/health` — per-provider configuration status (line 154)

**Behavior**:

- Pings NVIDIA NIM, Groq, and Ollama endpoints with lightweight requests
- Returns circuit breaker state for each provider (open → "down", half-open → "degraded")
- Reports embedding model availability from `ModelStore`
- Timeout per provider: `LLM_PROVIDER_TIMEOUT_SECONDS` (default 15s)
- Aggregate status requires ≥1 LLM tier reachable + embedding service available

---

## 21. Testing — Enhanced Patterns & Reference

### 21.1 LLM Mock Strategies

Every LLM-dependent test must patch at the import boundary where the LLM call originates, not where it is consumed.

**Mocking `generate_with_fallback`** (most common pattern):

```python
from unittest.mock import patch, MagicMock

@patch("app.services.llm_service.generate_with_fallback")
def test_reasoning_engine_uses_fallback(mock_gen):
    mock_gen.side_effect = [{"text": '{"blocks":[{"type":"BODY","advice":"rewrite"}]}'}]
    advice = engine.generate_instruction_set(blocks, rules)
    assert advice[0]["advice"] == "rewrite"
```

**Mocking `generate_with_model`** (specific provider, no fallback):

```python
@patch("app.services.llm_service.generate_with_model")
def test_generator_uses_nvidia(mock_gen):
    mock_gen.return_value = {"text": json.dumps(VALID_OUTLINE)}
    result = doc_generator._llm_generate("write a paper")
    assert result["title"] == "Expected Title"
    mock_gen.assert_called_once_with(model="nvidia_nim/meta-llama-3.3-70b", ...)
```

**Mocking circuit breaker to test failure path**:

```python
@patch("app.pipeline.safety.circuit_breaker.circuit_breaker", lambda **kw: lambda f: f)
def test_pipeline_runs_without_breaker():
    """Disable circuit breaker entirely for integration tests."""
    result = pipeline.run(document)
    assert result is not None
```

**Mocking provider registry for custom provider tests**:

```python
@patch("app.services.provider_registry.BUILTIN_PROVIDERS", {"test_provider": {...}})
@patch("app.services.llm_service.resolve_user_api_key", return_value="sk-test")
def test_custom_provider_call(mock_key):
    result = generate_with_fallback(provider="test_provider", prompt="hello")
    assert result is not None
```

**Key rules** (from `AGENTS.md`):

- Lazy imports inside function bodies require patching the **source module**, not the consumer — e.g. `app.pipeline.orchestrator.PipelineOrchestrator` (source) vs `app.routers.v1.documents_impl.PipelineOrchestrator` (consumer)
- `patch.object(Cls, "method")` replaces the CLASS attribute — `instance.method(args)` passes `self` to side_effect (3 params). Use `patch.object(instance, "method")` for 2 params
- Async methods require `from unittest.mock import AsyncMock` and `mock.return_value = AsyncMock()` or `mock.side_effect = AsyncMock()`

### 21.2 Golden File Testing Pattern

Golden files are stored under `backend/tests/fixtures/golden/` and contain expected DOCX output structures.

**Pattern** (full pipeline regression):

```python
def test_full_pipeline_matches_golden(golden_file_regression):
    """Run the full 16-stage pipeline on a fixture input and compare output."""
    input_doc = load_fixture("golden_inputs/ieee_paper.json")
    result = orchestrator.run_pipeline(input_doc)
    golden_file_regression.check(
        result.generated_doc.element.xml,
        basename="ieee_paper_output"
    )
```

**Golden file update workflow**:

1. Run `pytest tests/pipeline/test_golden_files.py --update-golden` to regenerate all golden files
2. Commit updated golden files alongside intentional output changes
3. CI job `frontend-ci.yml` runs golden file tests **before** deploy — a golden mismatch blocks deployment
4. Review golden diffs in PR — any divergence from expected output must be explained in the PR description

**Current golden files** (10 files from Phase 10 AI Quality Expansion):

| File | Coverage |
| ------ | ---------- |
| `ieee_paper_output.docx` | IEEE template formatting |
| `apa_paper_output.docx` | APA 7th edition formatting |
| `springer_paper_output.docx` | Springer LNCS template |
| `elsarticle_paper_output.docx` | Elsevier formatting |
| `resume_simple.docx` | Resume template |
| `multi_doc_synthesis.docx` | 2-document synthesis output |
| `LLMClassifier_classified.docx` | LLMClassifier classified document |
| `rag_enriched.docx` | RAG-advised output |
| `agent_generated.docx` | Agent-generated academic paper |
| `crossref_validated.docx` | CrossRef-enriched references |

### 21.3 Pipeline Test Patterns

**Stage isolation pattern** — each stage tested with `safe_execution` wrapper mocked:

```python
@patch("app.pipeline.safety.safe_execution.safe_execution")
def test_stage_failure_does_not_crash_pipeline(mock_safe):
    """Verify that a single failing stage does not cascade to subsequent stages."""
    mock_safe.return_value = MagicMock(__enter__=MagicMock(), __exit__=MagicMock(return_value=True))
    result = orchestrator.run_pipeline(document)
    assert result.stage_completed("parsing") is False
    assert result.stage_completed("structure_detection") is True  # next stage still runs
```

**Semaphore acquisition pattern**:

```python
@patch("app.pipeline.orchestrator._pipeline_semaphore")
def test_pipeline_semaphore_timeout(mock_sem):
    mock_sem.acquire.side_effect = TimeoutError("Server busy")
    with pytest.raises(TimeoutError):
        orchestrator.run_pipeline(document)
```

**Cancellation pattern**:

```python
@patch("app.pipeline.orchestrator.PipelineOrchestrator._check_cancelled")
def test_pipeline_cancellation_during_stage(mock_cancel):
    mock_cancel.side_effect = [None, None, asyncio.CancelledError()]
    with pytest.raises(asyncio.CancelledError):
        orchestrator.run_pipeline(document)
    assert result.cancelled_stage == "structure_detection"
```

**Concurrent job limit pattern**:

```python
@patch("app.pipeline.orchestrator._MAX_CONCURRENT_JOBS", 5)
def test_concurrent_job_limit_enforced():
    """Start 6 jobs, verify the 6th raises 'Server busy'."""
    async def run_many():
        tasks = [orchestrator.run_pipeline(doc) for doc in docs[:6]]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        assert isinstance(results[5], TimeoutError)
```

**Reference test files** (all under `backend/tests/pipeline/`):

| File | Tests | Coverage |
| ------ | ------- | ---------- |
| `test_enterprise_batch1.py` | 85 | StyleMapper, SectionOrderValidator, NumberingEngine, CrossReferenceEngine, ContractLoader, RetryGuard, SafeExecution, ValidateOutput, ReferenceNormalizer, SectionPrompts, EquationStandardizer, ContentParser, QualityScorer, TaskParser |
| `test_enterprise_batch2.py` | 135 | AgentPipeline, DocumentGenerator, PromptBuilder, ReferenceFormatter, TemplateRenderer, Formatter, CircuitBreaker, LLMValidator, ReferenceFormatterEngine, ReferenceParser, ContentClassifier, HeadingRules, PositionRules, StructureDetector, RagEngine, MultiDocSynthesizer |
| `test_enterprise_batch3.py` | 56 | BaseParser, TxtParser, MarkdownParser, TexParser, HtmlParser, ParserFactory, DocxParser, PdfParser, Normalizer |
| `test_enterprise_batch4.py` | 914 | agents/, orchestrator, intelligence/, services/ (historical — consolidated into dedicated files) |
| `test_circuit_breaker.py` | — | Circuit breaker state machine transitions |
| `test_rag_engine_comprehensive.py` | — | RAG query, fallback, reset |
| `test_rag_engine_deep.py` | — | RAG embedding edge cases |
| `test_coverage_gap_*.py` | 8 files | Fallbacks, classifier, external services, parsing, orchestration, RAG |
| `test_formatting_enterprise.py` | 87 | StyleMapper, SectionOrderValidator, NumberingEngine, ReferenceFormatter, TemplateRenderer, Formatter edge cases |
| `test_formatting_enterprise.py` (root `tests/`) | 87 | Second copy for root-level pipeline tests |

### 21.4 Unit vs Integration vs E2E Decision Matrix

| Component | Unit Test | Integration Test | E2E Test |
| ----------- | ----------- | ----------------- | ---------- |
| PipelineOrchestrator | Isolated stage logic | Stage wiring + mock services | Full pipeline smoke (Playwright) |
| RagEngine | ChromaDB patched + native store fallback | ChromaDB in-memory client | RAG query against real ChromaDB |
| LLM Service | MagicMock return values | Circuit breaker state transitions | Real API call (opt-in, `@pytest.mark.llm`) |
| DocumentGenerator | Mock LLM output parsing | Prompt → LLM → parse cycle | Generate + download (Playwright) |
| Formatter | Golden file comparison | StyleMapper + NumberingEngine contracts | Export DOCX/PDF (Playwright) |
| Agent | Tool result assembly | LangChain agent execution | Agent chat session (Playwright) |
| Circuit Breaker | State machine (open/closed/half-open) | pybreaker vs legacy fallback | — |
| Provider Registry | Provider list filtering | Custom provider CRUD | Provider test endpoint (Playwright) |

**Test markers** (`pytest.ini`):

- `@pytest.mark.unit` — No external deps, runs <100ms each
- `@pytest.mark.integration` — Requires mocked services, runs <2s each
- `@pytest.mark.pipeline` — Pipeline stage logic, runs <5s each
- `@pytest.mark.llm` — Real LLM API calls (opt-in, skipped in CI)
- `@pytest.mark.slow` — Duration >10s, skipped unless `--run-slow`
- `@pytest.mark.database` — Requires DB connection (auto-deselected in CI)
- `@pytest.mark.e2e` — Full browser test (Playwright, requires running backend)

**Run commands**:

```bash
# Unit + integration (CI pipeline)
pytest tests/pipeline/ -m "not llm and not slow and not e2e" -x -q

# Fast pipeline subset (use during development)
pytest tests/pipeline/test_enterprise_batch1.py tests/pipeline/test_enterprise_batch2.py -x -q

# Full pipeline sweep (pre-merge)
pytest tests/pipeline/ -m "not llm and not e2e" --timeout=300 -x

# LLM integration (manual, requires API keys)
pytest tests/pipeline/ -m "llm" --run-llm
```

---

## 22. API Reference — Enhanced Table with Auth & Curl Examples

### 22.1 Auth & Rate Limit Matrix

All endpoints require Supabase JWT authentication via `get_current_user` dependency (`app/utils/dependencies.py:17`). The `get_optional_user` variant allows unauthenticated access for public endpoints.

| Endpoint | Method | Auth | Rate Limit | Tier | Idempotent |
| ---------- | -------- | ------ | ------------ | ------ | ------------ |
| `/api/v1/generator/sessions` | `POST` | Required | 10/min | Session | Yes (`idempotency_key`) |
| `/api/v1/generator/sessions` | `GET` | Required | 120/min | Read | Yes |
| `/api/v1/generator/sessions/{sessionId}` | `GET` | Required | 120/min | Read | Yes |
| `/api/v1/generator/sessions/{sessionId}/messages` | `GET` | Required | 60/min | Read | Yes |
| `/api/v1/generator/sessions/{sessionId}/messages` | `POST` | Required | 30/min | Session | Yes (`idempotency_key`) |
| `/api/v1/generator/sessions/{sessionId}/outline/approve` | `POST` | Required | 10/min | Session | Yes |
| `/api/v1/generator/sessions/{sessionId}/stop` | `POST` | Required | 10/min | Action | Yes |
| `/api/v1/generator/sessions/{sessionId}/document` | `GET` | Required | 60/min | Read | Yes |
| `/api/v1/generator/sessions/{sessionId}/download` | `GET` | Required | 30/min | Read | Yes |
| `/api/v1/generator/sessions/{sessionId}/events` | `GET` | Required | — | SSE | No (streaming) |
| `/api/v1/synthesis/sessions` | `POST` | Required | 5/min | Session | Yes (`idempotency_key`) |
| `/api/v1/synthesis/sessions/{sessionId}` | `GET` | Required | 60/min | Read | Yes |
| `/api/v1/synthesis/sessions/{sessionId}/events` | `GET` | Required | — | SSE | No (streaming) |
| `/api/v1/synthesis/sessions/{sessionId}/messages` | `POST` | Required | 20/min | Session | Yes |
| `/api/v1/stream/{jobId}` | `GET` | Required | — | SSE | No (streaming) |
| `/api/v1/providers` | `GET` | Required | 30/min | Read | Yes |
| `/api/v1/providers/health` | `GET` | Required | 30/min | Read | Yes |
| `/api/v1/providers/{providerId}/models` | `GET` | Required | 20/min | Read | Yes |
| `/api/v1/providers/{providerId}/models/sync` | `POST` | Required | 5/min | Action | Yes |
| `/api/v1/providers/custom` | `POST` | Required | 10/min | Write | No |
| `/api/v1/providers/custom` | `GET` | Required | 30/min | Read | Yes |
| `/api/v1/providers/custom/{id}` | `GET` | Required | 30/min | Read | Yes |
| `/api/v1/providers/custom/{id}` | `PUT` | Required | 10/min | Write | Yes |
| `/api/v1/providers/custom/{id}` | `DELETE` | Required | 10/min | Write | Yes |
| `/api/v1/providers/test` | `POST` | Required | 3/min | Action | No |
| `/api/v1/metrics/health` | `GET` | Required | 30/min | Read | Yes |
| `/api/v1/metrics/dashboard` | `GET` | Admin | 10/min | Read | Yes |
| `/api/v1/metrics/enhancements` | `GET` | Required | 30/min | Read | Yes |
| `/api/v1/metrics/usage` | `GET` | Required | 30/min | Read | Yes |
| `/api/v1/health` | `GET` | Optional | 120/min | Read | Yes |
| `/api/v1/health/live` | `GET` | Optional | 120/min | Read | Yes |
| `/api/v1/health/ready` | `GET` | Optional | 60/min | Read | Yes |

**Rate limit tiers** (`api_key_service.py`):

- Default: `GLOBAL_RATE_LIMIT_PER_MINUTE` = 120 (configurable in `.env`)
- Per-API-key: `ApiKey.rate_limit_per_minute` (default 60, configurable 1–1000)
- Admin endpoints: Tier 2 rate limiting (10/min for metrics dashboard)
- SSE streams: No rate limit applied (connection-level throttling instead)

**Auth implementation**:

- All auth-protected endpoints use `user=Depends(get_current_user)` from `app/utils/dependencies.py:17`
- `get_current_user` extracts the JWT from the `Authorization: Bearer <token>` header
- Supabase JWT validation: decodes and verifies the token, fetches user from Supabase
- `get_optional_user` returns `None` for unauthenticated requests (used by health endpoints)
- Admin-only endpoints use `require_admin_user(user: User = Depends(get_current_user))` — `app/utils/dependencies.py:133`

### 22.2 Curl Examples for Key AI Endpoints

```bash
# ── Authentication ─────────────────────────────────────────────
# Obtain a JWT token (replace with your Supabase credentials)
JWT="<your-supabase-jwt-token>"

# ── List all available LLM providers ──────────────────────────
curl -s -H "Authorization: Bearer $JWT" \
  http://localhost:8000/api/v1/providers | jq .

# ── Check provider health (status of each LLM tier) ───────────
curl -s -H "Authorization: Bearer $JWT" \
  http://localhost:8000/api/v1/providers/health | jq .

# ── List models for a specific provider ───────────────────────
curl -s -H "Authorization: Bearer $JWT" \
  http://localhost:8000/api/v1/providers/nvidia/models | jq .

# ── Create a generation session (agent-based) ─────────────────
curl -s -X POST -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"doc_type": "academic_paper", "title": "Deep Learning Survey", "options": {"fast_mode": true}}' \
  http://localhost:8000/api/v1/generator/sessions | jq .

# ── Send a message to an agent session ────────────────────────
SESSION_ID="<session_id_from_above>"
curl -s -X POST -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"content": "Write the introduction section focusing on transformer architectures.", "role": "user"}' \
  http://localhost:8000/api/v1/generator/sessions/$SESSION_ID/messages | jq .

# ── Get session message history ──────────────────────────────
curl -s -H "Authorization: Bearer $JWT" \
  http://localhost:8000/api/v1/generator/sessions/$SESSION_ID/messages | jq .

# ── Approve outline and resume generation ─────────────────────
curl -s -X POST -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"sections": ["Introduction", "Background", "Methodology", "Results", "Conclusion"]}' \
  http://localhost:8000/api/v1/generator/sessions/$SESSION_ID/outline/approve | jq .

# ── Download generated document ───────────────────────────────
curl -s -H "Authorization: Bearer $JWT" \
  http://localhost:8000/api/v1/generator/sessions/$SESSION_ID/download \
  -o generated_paper.docx

# ── Fetch generated document content as JSON ─────────────────
curl -s -H "Authorization: Bearer $JWT" \
  http://localhost:8000/api/v1/generator/sessions/$SESSION_ID/document | jq .

# ── Subscribe to SSE stream (session events) ─────────────────
curl -s -N -H "Authorization: Bearer $JWT" \
  http://localhost:8000/api/v1/generator/sessions/$SESSION_ID/events

# ── Stop a running session ───────────────────────────────────
curl -s -X POST -H "Authorization: Bearer $JWT" \
  http://localhost:8000/api/v1/generator/sessions/$SESSION_ID/stop | jq .

# ── Create a multi-doc synthesis session ─────────────────────
curl -s -X POST -H "Authorization: Bearer $JWT" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@paper1.docx" -F "files=@paper2.docx" \
  -F "options={\"synthesis_type\": \"survey\", \"template\": \"ieee\"}" \
  http://localhost:8000/api/v1/synthesis/sessions | jq .

# ── Query synthesized documents (Q&A) ────────────────────────
SYNTH_ID="<synthesis_session_id>"
curl -s -X POST -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the key differences between the two papers?", "role": "user"}' \
  http://localhost:8000/api/v1/synthesis/sessions/$SYNTH_ID/messages | jq .

# ── Create a custom (BYO) provider ───────────────────────────
curl -s -X POST -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-ollama", "base_url": "http://192.168.1.50:11434", "models": ["llama3"], "is_local": true}' \
  http://localhost:8000/api/v1/providers/custom | jq .

# ── Test provider connection ─────────────────────────────────
curl -s -X POST -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"provider": "nvidia", "model": "meta/llama-3.3-70b-instruct", "prompt": "Say hello"}' \
  http://localhost:8000/api/v1/providers/test | jq .

# ── Get admin metrics dashboard ──────────────────────────────
curl -s -H "Authorization: Bearer $JWT" \
  http://localhost:8000/api/v1/metrics/dashboard | jq .

# ── Get AI pipeline health ───────────────────────────────────
curl -s http://localhost:8000/api/v1/health/ready | jq .
```

---

## 23. Security — Threat Model & Data Flow

### 23.1 AI Pipeline Threat Model (STRIDE per Component)

| Threat | Component Affected | Impact | Likelihood | Risk Score |
| -------- | ------------------- | -------- | ------------ | ------------ |
| **Prompt injection** (Tampering) | LLM Service, ReasoningEngine, Generator | Attacker bypasses instructions, exfiltrates system prompts | High | **Critical** |
| **PII data leakage** (Information Disclosure) | Pipeline document content → LLM API calls | Sensitive manuscript data sent to 3rd-party LLM APIs | Medium | **High** |
| **Model denial of service** (DoS) | Circuit breakers, LLM tier system | Thousands of cheap requests exhaust API quota or budget | High | **High** |
| **API key extraction** (Information Disclosure) | Provider registry, BYOK storage | Attacker steals LLM API keys from DB or logs | Low | **Critical** |
| **Model theft via enumeration** (Information Disclosure) | Provider discovery endpoints | Attacker enumerates available models and capabilities | Medium | **Medium** |
| **SSRF via custom provider** (Elevation of Privilege) | Custom provider base URL | Attacker points LLM calls to internal services | Medium | **High** |
| **ChromaDB data contamination** (Tampering) | RAG Engine, knowledge base | Attacker injects malicious guidelines into vector store | Low | **Medium** |
| **Rate limit bypass** (DoS) | AbuseDetector, RateLimiter | Attacker floods pipeline jobs to exhaust resources | Medium | **Medium** |
| **Cache poisoning** (Tampering) | LLM response cache, Redis | Attacker caches malicious LLM responses served to other users | Low | **High** |
| **Session hijacking** (Spoofing) | Generation sessions, SSE streams | Attacker accesses another user's active session | Medium | **High** |
| **JWT token replay** (Spoofing) | Auth middleware | Reused JWT tokens to escalate privileges | Low | **Medium** |
| **Supply chain compromise** (Tampering) | HuggingFace models, PyPI dependencies | Compromised ML model weights or Python packages | Low | **Critical** |

### 23.2 Mitigation Matrix

| Threat ID | Mitigation | Implementation | Verification |
| ----------- | ----------- | --------------- | ------------- |
| Prompt injection | Multi-layer input sanitization | `sanitize_for_llm()` (25+ regex patterns, 8000-char limit, Section 18.1) | `test_prompt_injection*.py` |
| Prompt injection | Output schema enforcement | `guard_llm_output()` with Guardrails AI / Pydantic | `test_llm_validator*.py` |
| Prompt injection | Abuse detector at API gateway | `AbuseDetector.record_generation_request()` in `middleware/abuse_detector.py` | `test_abuse_detector*.py` |
| PII leakage | Pre-LLM PII stripping | `sanitize_for_llm()` strips emails, SSNs, phone numbers | `test_sanitize_llm*.py` |
| PII leakage | Structured log filtering | PII regex filters in logger; `LOG_LEVEL=INFO` suppresses prompt bodies | `test_logging_security*.py` |
| PII leakage | Session-scoped Redis channels | `session:{id}` prefix — no cross-tenant data exposure | `test_sse_isolation*.py` |
| Model DoS | Per-provider circuit breakers | `pybreaker.CircuitBreaker`, threshold=3, reset=60s | `test_circuit_breaker*.py` |
| Model DoS | Per-user rate limiting | `GLOBAL_RATE_LIMIT_PER_MINUTE=120`, per-key `rate_limit_per_minute` | `test_rate_limiting*.py` |
| Model DoS | Pipeline semaphore | `_MAX_CONCURRENT_JOBS=5`, acquire timeout=30s | `test_concurrent_processing*.py` |
| API key theft | Fernet encryption at rest | `EncryptionService` in `app/services/encryption_service.py` (AES-128-CBC) | `test_encryption_service*.py` |
| API key theft | Key rotation support | `created_at`/`updated_at` timestamps on `user_api_keys` | `test_api_key_rotation*.py` |
| API key theft | No key in logs | Structured logger suppresses env vars and API key patterns | `test_log_scrubbing*.py` |
| SSRF | Private IP blocklist | Base URL validation against RFC 1918 ranges, loopback, link-local | `test_ssrf_protection*.py` |
| SSRF | Custom provider URL validation | `CustomProviderValidator` in provider registry | `test_custom_provider_security*.py` |
| ChromaDB contamination | Isolated collections per template | `where={"publisher": publisher.upper()}` filter in all queries | `test_rag_isolation*.py` |
| Cache poisoning | Cache key includes user context | LLM cache key = `provider:model:prompt_hash` + `user_id` prefix | `test_cache_isolation*.py` |
| Session hijacking | JWT validation per request | `get_current_user()` on every endpoint; token expiry check | `test_auth_middleware*.py` |
| Supply chain | Pinned model revisions | `allenai/LLMClassifier_scivocab_uncased`, `BAAI/bge-m3` with specific revisions | `test_model_pinning*.py` |
| Supply chain | Dependency hash verification | `pip install --require-hashes` in CI/CD | `test_dependency_scan*.py` |
| Cross-tenant leakage | Isolation per user/API key | `resolve_user_api_key()` enforces user ownership of API keys | `test_user_isolation*.py` |

### 23.3 Data Flow Description for Sensitive Data Through AI Pipeline

```
User Upload ──→ API Gateway ──→ PipelineOrchestrator ──→ LLM/External Services ──→ Output
    │               │                    │                        │                    │
    │         [Auth check]          [Dedup check]            [PII stripped]       [Validated]
    │         get_current_user()    SHA-256 hash            sanitize_for_llm()   guard_llm_output()
    │               │                    │                        │                    │
    v               v                    v                        v                    v
Sensitive data:  ┌──────────┐     ┌──────────────┐        ┌───────────────┐    ┌──────────┐
Manuscript text, │ JWT token│     │ File metadata │         │ Cleaned text │     │ Final    │
PII, API keys    └──────────┘     └──────────────┘        └───────────────┘    │ document │
                                                                               └──────────┘
```

**Detailed data flow for sensitive manuscript content**:

1. **Upload phase** (data at rest in memory):
   - Raw file bytes received by `documents_impl.py`
   - JWT-authenticated via `get_current_user()` — user identity resolved
   - SHA-256 hash computed for dedup (hash is NOT considered sensitive)
   - File written to temp staging directory (cleaned up post-processing)

2. **Parsing phase** (data in use):
   - File read from disk → parsed into `PipelineDocument` with `Block[]`
   - Blocks contain raw manuscript text — includes potential PII (author names, emails, affiliations, supplemental data)
   - Stored in memory only; no persistence of raw text

3. **Pre-LLM sanitization** (data transformation):
   - Before ANY external API call, `sanitize_for_llm()` runs:
     - Strips email addresses: `re.sub(EMAIL_PATTERN, "[EMAIL REDACTED]", text)`
     - Strips phone numbers: `re.sub(PHONE_PATTERN, "[PHONE REDACTED]", text)`
     - Strips SSN patterns: `re.sub(SSN_PATTERN, "[SSN REDACTED]", text)`
     - Truncates at 8000 characters
     - Strips control characters and zero-width Unicode
   - **Output**: Sanitized text — PII irreversibly removed before leaving the backend process

4. **LLM API call** (data in transit):
   - Sanitized text sent to NVIDIA NIM / Groq / OpenRouter / Ollama over HTTPS (TLS 1.3)
   - No user-identifying metadata sent with the prompt (no user_id, no email, no IP)
   - `x-request-id` header sent for traceability (opaque, non-sensitive UUID)
   - Response received and validated by `guard_llm_output()` before use

5. **RAG Enrichment** (data at rest in ChromaDB):
   - If RAG is enabled, document text is embedded via sentence-transformers
   - Embeddings are stored in ChromaDB (local, in-process) — NOT sent to any external service
   - ChromaDB collections isolated by `publisher` filter — no cross-template contamination
   - **No raw text stored in ChromaDB** — only policy/guideline embeddings from `default_guidelines.json`

6. **Result assembly** (data at rest in Supabase):
   - Final formatted document stored in Supabase `document_results` table
   - Document content accessible only to the owning user (via `user_id` filter in queries)
   - `document_versions` table stores versioned snapshots on edit flow
   - Supabase RLS policies enforce row-level security by `user_id`

7. **Download** (data in transit):
   - Output file served over HTTPS with `Content-Disposition: attachment`
   - No caching headers for sensitive content (`Cache-Control: no-store`)
   - Download URL includes a single-use signed token (not the raw session ID)

### 23.4 Encryption Key Hierarchy

```
┌─────────────────────────────────────────────────────┐
│  Environment Variable / Vault                        │
│  FERNET_MASTER_KEY (base64, 32 bytes)                │
│  → Used to encrypt all user API keys                 │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  EncryptionService.decrypt_key(encrypted_key)        │
│  → Fernet(fmaster_key).decrypt(encrypted_key)       │
│  → Returns raw API key string (in memory only)      │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  resolve_user_api_key(provider, user_id)             │
│  1. Lookup user_api_keys WHERE user_id + provider    │
│  2. If found: EncryptionService.decrypt_key()        │
│  3. If not found: return env var fallback            │
│  4. Key used for a single LLM call, then GC'd        │
└─────────────────────────────────────────────────────┘
```

---

## 24. Deployment — Environment Variable Matrix

### 24.1 Complete AI Pipeline Environment Variable Matrix

Organized by functional domain. All variables are defined in `backend/app/config/settings.py`.

**LLM Provider Configuration** (Section 12 reference):

| Variable | Required | Default | Sensitive | Runtime Change | Typical Production Value |
| ---------- | ---------- | --------- | ----------- | ---------------- | -------------------------- |
| `NVIDIA_API_KEY` | Yes* | `""` | Yes | No | `nvapi-...` |
| `NVIDIA_MODEL` | No | `""` | No | No | `meta/llama-3.3-70b-instruct` |
| `GROQ_API_KEY` | Yes* | `""` | Yes | No | `gsk_...` |
| `GROQ_MODEL` | No | `""` | No | No | `llama3-8b-8192` |
| `OPENAI_API_KEY` | No | `""` | Yes | No | `sk-...` |
| `ANTHROPIC_API_KEY` | No | `""` | Yes | No | `sk-ant-...` |
| `DEEPSEEK_API_KEY` | No | `""` | Yes | No | `sk-...` |
| `OPENROUTER_API_KEY` | No | `""` | Yes | No | `sk-or-...` |
| `GOOGLE_API_KEY` | No | `""` | Yes | No | `AIza...` |
| `COHERE_API_KEY` | No | `""` | Yes | No | `...` |
| `MISTRAL_API_KEY` | No | `""` | Yes | No | `...` |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | No | Yes | `http://ollama.internal:11434` |
| `LLM_PROVIDER_TIMEOUT_SECONDS` | No | `15` | No | Yes | `30` |

\* At least one API key required for LLM functionality.

**Pipeline Settings** (Section 12 reference):

| Variable | Required | Default | Description | Production Value |
| ---------- | ---------- | --------- | ------------- | ----------------- |
| `DEFAULT_FAST_MODE` | No | `false` | Skip optional AI stages | `true` |
| `GROBID_ENABLED` | No | `true` | Enable GROBID metadata extraction | `true` |
| `GROBID_URL` | No | `http://localhost:8070` | GROBID service endpoint | `http://localhost:8070` |
| `GROBID_MAX_RETRIES` | No | `3` | GROBID retry count | `3` |
| `PIPELINE_GROBID_TIMEOUT_SECONDS` | No | `30` | GROBID stage timeout | `30` |
| `USE_DOCLING_FALLBACK` | No | `true` | Enable Docling layout analysis | `true` |
| `PIPELINE_DOCLING_TIMEOUT_SECONDS` | No | `30` | Docling stage timeout | `30` |
| `PIPELINE_DOCLING_SKIP_DIGITAL_PDF` | No | `false` | Skip Docling for digital-native PDFs | `true` |
| `PYMUPDF_FALLBACK` | No | `true` | Enable lightweight metadata fallback | `true` |
| `ENABLE_LLM_PDF_PARSER` | No | `false` | Enable LLM-based PDF parsing (scanned PDFs) | `false` |
| `PIPELINE_REASONING_TIMEOUT_SECONDS` | No | `60` | AI reasoning stage timeout | `60` |
| `PIPELINE_ACQUIRE_TIMEOUT_SECONDS` | No | `30.0` | Semaphore acquire timeout | `30.0` |

**AI Model & Embedding Configuration**:

| Variable | Required | Default | Description | Production Value |
| ---------- | ---------- | --------- | ------------- | ----------------- |
| `PRELOAD_AI_MODELS` | No | `true` | Pre-load models at startup | `false` |
| `LOW_MEMORY_MODE` | No | `false` | Skip local model loading, use deterministic embeddings | `true` |
| `USE_LLM_CLASSIFICATION` | No | `false` | Enable LLM-based classification parsing | `false` |
| `LLM_CLASSIFIER_URL` | No | `""` | Remote LLMClassifier endpoint | `http://localhost:8001` |
| `LLM_CLASSIFIER_URLS` | No | `""` | Comma-separated LLMClassifier URL fallbacks | `""` |
| `LLM_CLASSIFIER_AUTO_ENABLE_FROM_BENCHMARK` | No | `true` | Auto-enable based on F1 score | `false` |
| `LLM_CLASSIFIER_MIN_BENCHMARK_F1` | No | `0.85` | Minimum F1 for auto-enable | `0.85` |
| `RAG_EMBEDDING_PROVIDER` | No | `""` | Embedding provider (`huggingface_api` or empty for local) | `huggingface_api` |
| `RAG_EMBEDDING_MODEL` | No | `sentence-transformers/all-MiniLM-L6-v2` | HF model for remote API | `sentence-transformers/all-MiniLM-L6-v2` |
| `RAG_HF_TIMEOUT_SECONDS` | No | `30` | HF API request timeout | `30` |
| `RAG_HF_MAX_RETRIES` | No | `3` | HF API retry count | `3` |
| `RAG_HF_RETRY_BACKOFF_SECONDS` | No | `1.0` | HF API backoff | `1.0` |
| `ENABLE_NVIDIA_REASONER` | No | `false` | Enable NVIDIA NIM reasoning | `false` |

**Circuit Breaker & Safety**:

| Variable | Required | Default | Description | Production Value |
| ---------- | ---------- | --------- | ------------- | ----------------- |
| `EXTERNAL_CIRCUIT_BREAKER_ENABLED` | No | `true` | Enable per-provider circuit breakers | `true` |
| `EXTERNAL_CIRCUIT_BREAKER_FAILURE_THRESHOLD` | No | `3` | Failures before circuit opens | `3` |
| `EXTERNAL_CIRCUIT_BREAKER_RESET_SECONDS` | No | `60` | Recovery timeout | `60` |

**Redis & Caching**:

| Variable | Required | Default | Description | Production Value |
| ---------- | ---------- | --------- | ------------- | ----------------- |
| `REDIS_ENABLED` | No | `false` | Enable Redis caching | `true` |
| `REDIS_URL` | No | `redis://localhost:6379` | Redis connection URL | `rediss://default:...@...upstash.io` |
| `LLM_CACHE_TTL_SECONDS` | No | `3600` | LLM response cache TTL | `3600` |
| `CSL_SEARCH_CACHE_TTL_SECONDS` | No | `300` | CSL search cache TTL | `300` |

**Rate Limiting & Abuse Prevention**:

| Variable | Required | Default | Description | Production Value |
|----------|----------|---------|-------------|-----------------|
| `GLOBAL_RATE_LIMIT_PER_MINUTE` | No | `120` | Global API rate limit | `120` |
| `KEEP_WARM_PING_INTERVAL_SECONDS` | No | `300` | HF Spaces keep-alive interval | `300` |

**Observability**:

| Variable | Required | Default | Description | Production Value |
| ---------- | ---------- | --------- | ------------- | ----------------- |
| `ENABLE_STRUCTURED_LOGGING` | No | `false` | JSON log output | `true` |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG/INFO/WARN/ERROR) | `INFO` |

### 24.2 Service Dependency Diagram

```mermaid
graph TB
    subgraph External["External ("3rd Party SaaS")"]
        NVIDIA["NVIDIA NIM API"]
        GROQ["Groq API"]
        OR["OpenRouter API"]
        HF["HuggingFace Inference API"]
        SUPABASE["Supabase DB + Storage"]
    end

    subgraph SelfHosted["Self-Hosted / HF Spaces"]
        GROBID["GROBID<br/>Java, 1.5GB RAM"]
        DOCLING["Docling<br/>Python, 2GB RAM"]
        LLMClassifier["LLMClassifier<br/>HF Space"]
        OLLAMA["Ollama<br/>Optional, GPU"]
    end

    subgraph App["ScholarForm Backend"]
        API["FastAPI Web Service"]
        CELERY["Celery Worker"]
        CHROMA["ChromaDB<br/>Embedded"]
        REDIS["Redis<br/>Cache + Pub/Sub"]
    end

    subgraph Frontend["Frontend"]
        NEXT["Next.js 16<br/>App Router"]
    end

    NEXT --> API
    API --> CELERY
    API --> CHROMA
    API --> REDIS
    CELERY --> NVIDIA
    CELERY --> GROQ
    CELERY --> OR
    CELERY --> OLLAMA
    CELERY --> HF
    CELERY --> GROBID
    CELERY --> DOCLING
    CELERY --> LLMClassifier
    API --> SUPABASE
    CELERY --> SUPABASE
    CHROMA -.->|Fallback| HF

    classDef external fill:#e1f5fe,stroke:#0288d1
    classDef selfhosted fill:#fff3e0,stroke:#f57c00
    classDef app fill:#e8f5e9,stroke:#388e3c
    classDef frontend fill:#f3e5f5,stroke:#7b1fa2

    class NVIDIA,GROQ,OR,HF,SUPABASE external
    class GROBID,DOCLING,LLMClassifier,OLLAMA selfhosted
    class API,CELERY,CHROMA,REDIS app
    class NEXT frontend
```

### 24.3 Service Dependency Startup Order

For production deployments, follow this startup sequence to minimize errors during rolling updates:

1. **Supabase** (always available — managed SaaS)
2. **Redis** (start → wait for `PONG` on `PING`)
3. **ChromaDB** (embedded — starts with backend but creates collections lazily)
4. **GROBID** (start → wait for `http://localhost:8070/api/health` → 200 OK)
5. **Docling** (start → wait for `/health` endpoint)
6. **LLMClassifier HF Space** (starts on first request — use `KEEP_WARM_PING_INTERVAL_SECONDS=300` to prevent cold start)
7. **Ollama** (start → pull models → `ollama list` returns expected models)
8. **Celery Worker** (start after all services — connects to Redis, waits for tasks)
9. **FastAPI Web Service** (start last — health endpoint checks all dependencies before `ready` returns 200)

**Dependency failure handling**:

- GROBID/Docling unavailable → pipeline proceeds without metadata extraction
- All LLM providers down → pipeline returns rule-based formatted output (quality score reduced)
- ChromaDB corruption → auto-rebuilds from `default_guidelines.json`
- Redis unavailable → LLM cache disabled, fallback to in-memory rate limiting
- Supabase unavailable → read-only mode (cached templates only, no new processing)

---

## 25. Cross-Reference Index

| External Document | Location | Relevance to AI Architecture |
| ------------------- | ---------- | ------------------------------ |
| `AGENTS.md` | Root | Test patterns, mock strategies, pipeline import rules, provider system |
| `ENTERPRISE_CERTIFICATION.md` | Root | Test counts, security posture for AI pipeline |
| `COVERAGE_GAP_REPORT.md` | Root | Gap closure tracking across 38 AI-related categories |
| `PRODUCTION_READINESS_CHECKLIST.md` | Root | 45+ item checklist including AI-specific readiness items |
| `OPENSSF_README.md` | Root | OpenSSF Best Practices for AI supply chain |
| `SECURITY_CHECKLIST.md` | `docs/` | Full security compliance for AI pipeline |
| `DEPLOYMENT_GUIDE.md` | `docs/` | Production deployment workflow |
| `MONITORING_OBSERVABILITY.md` | `docs/` | Prometheus/Grafana setup for AI metrics |
| `pipeline-architecture.md` | `docs/explanation/` | Detailed 16-stage pipeline walkthrough |
| `creating-a-custom-template.md` | `docs/guides/` | Template system that AI reasoning retrieves |
\n

## AI Pipeline Diagram

```mermaid
graph LR
    Input["Docx Upload"] --> Parse[Parser/Grobid/OCR]
    Parse --> Chunks["Text Chunking"]
    Chunks --> Embed["Embedding Model"]
    Embed --> VectorDB["("Vector Store")"]
    Query["User Query"] --> EmbedQuery["Embed Query"]
    EmbedQuery --> Retrieve["Retrieve Chunks"]
    Retrieve --> Context["Context Builder"]
    Context --> LLM["LLM Generator"]
    LLM --> Formatter["Output Formatter"]
    classDef default fill:#1f2937,stroke:#ec4899,stroke-width:2px,color:#f9fafb;
```

## Related Documentation

- [AI Architecture](AI_ARCHITECTURE.md)
- [Frontend Architecture](FRONTEND_ARCHITECTURE.md)
- [Realtime Architecture](REALTIME_ARCHITECTURE.md)
- [Chroma RAG Architecture](CHROMA_RAG_ARCHITECTURE.md)
- [Database Architecture](DATABASE_ARCHITECTURE.md)
- [API Reference](API.md)
