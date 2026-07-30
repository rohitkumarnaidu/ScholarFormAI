# ChromaDB / RAG Architecture — ScholarForm AI

> **Last updated:** 2026-07-16
> **Canonical source:** `backend/app/pipeline/intelligence/rag_engine.py`
> **Persistence layer:** `backend/db/semantic_store/`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Collection Schema](#3-collection-schema)
4. [Embedding Model Stack](#4-embedding-model-stack)
5. [Ingestion Pipeline](#5-ingestion-pipeline)
6. [Query Flow](#6-query-flow)
7. [RAG Engine API](#7-rag-engine-api)
8. [Session Store](#8-session-store)
9. [Performance Characteristics](#9-performance-characteristics)
10. [Backup & Portability](#10-backup--portability)
11. [Configuration Reference](#11-configuration-reference)
12. [Resilience & Degraded Modes](#12-resilience--degraded-modes)
13. [Integration Points](#13-integration-points)

---

## 1. Overview

ScholarForm AI uses ChromaDB as the primary vector store for retrieval-augmented generation (RAG) over academic formatting guidelines. The system retrieves publisher-specific formatting rules — section ordering, heading styles, citation formats, figure/table requirements — at pipeline runtime and injects them into LLM prompts to guide document formatting.

**Why ChromaDB:**

- **Local-first persistence** — PersistentClient writes to disk; no external vector database service required.
- **Zero-config collections** — `get_or_create_collection` handles schema-on-read; no migration tooling needed.
- **Metadata filtering** — ChromaDB `where` filters allow publisher-scoped retrieval without multi-collection overhead.
- **Lightweight embed-free option** — ChromaDB handles cosine similarity natively, but a `kb.json` native fallback with NumPy dot-product scoring provides identical semantics when ChromaDB is unavailable.
- **Single-binary deployment** — ChromaDB ships as a pip package; no sidecars, no Docker dependency for vector storage.

**Use case:** Roughly 200–400 guideline documents across 14 publishers (IEEE, APA, Springer, ACM, Nature, Elsevier, Harvard, Chicago, MLA, Vancouver, Numeric, Modern Red/Gold/Blue, Resume, Portfolio, None), each with 4–10 sections. Average guideline text length: 50–200 chars. Total corpus size: ~50 KB raw text.

---

## 2. Architecture

```
+--------------------+       +---------------------+
|   Contract YAML    | ----> |  ingest_guidelines   |
| (pipeline/contracts)|      |  .py                |
+--------------------+       +----------+----------+
                                         |
                                         v
+--------------------+       +---------------------+
| default_guidelines | ----> |     RagEngine        |
| .json (auto-seed)  |       |                     |
+--------------------+       |  +---------------+  |
                             |  |   ChromaDB    |  |
+--------------------+       |  | Persistent    |  |
|   Pipeline         |       |  | Client        |  |
| Orchestrator       | <--- |  | (guidelines   |  |
| (formatting step)  |       |  |  collection)  |  |
+--------------------+       |  +-------+-------+  |
                             |          |          |
                             |  +-------v-------+  |
                             |  |  kb.json       |  |
                             |  |  (native       |  |
                             |  |   fallback)    |  |
                             |  +---------------+  |
                             +---------------------+
                                      |
                                      v
+--------------------+       +---------------------+
|   LLM Prompt       |       |  Formatting         |
|   (context         | <---- |  Pipeline           |
|    assembly)       |       |  (query_rules())    |
+--------------------+       +---------------------+
```

### 2.1 Dual-Backend Design

RagEngine maintains **two parallel stores** on every write:

| Store | Technology | Purpose |
|-------|-----------|---------|
| **ChromaDB** | `chromadb.PersistentClient` | Primary retrieval (cosine similarity + metadata filtering) |
| **Native (kb.json)** | JSON array + NumPy | Failover retrieval; portable snapshot; testing |

Every `add_guideline()` call writes to both ChromaDB and the native `kb.json`. Every `query_guidelines()` call attempts ChromaDB first and falls back to native cosine similarity on failure.

### 2.2 Auto-Seeding

On first instantiation (empty store), RagEngine loads `default_guidelines.json` — a curated set of 44 guidelines across 11 publishers with 4 sections each (abstract, section_order, references, figures). Seeding is enabled by default for the production store and disabled for test/temp directories.

---

## 3. Collection Schema

### 3.1 Collections

| Collection Name | Embedding Dimension | Model | Purpose |
|----------------|-------------------|-------|---------|
| `guidelines_bge_m3` | 1024 | `BAAI/bge-m3` | Primary collection (best quality) |
| `publisher_guidelines` | 384 | `BAAI/bge-small-en-v1.5` | Legacy/fallback collection |

**Important:** Collection name is resolved based on the active embedding model. The two collections are **never used simultaneously** — only one exists in any given persist directory.

### 3.2 ChromaDB Metadata Fields

```python
{
    "publisher": str,   # Publisher name, UPPERCASE (e.g., "IEEE", "APA")
    "section": str,     # Section/rule name, lowercase (e.g., "abstract", "references")
    "source": str,      # Origin tracker ("auto-seed", "contract-ingest", "user")
}
```

### 3.3 Native kb.json Entry Schema

```json
{
    "text": "Abstract should be concise (typically 150-250 words)...",
    "metadata": {
        "publisher": "IEEE",
        "section": "abstract",
        "source": "auto-seed"
    },
    "embedding": [0.0, 0.0, 0.2, ...]
}
```

### 3.4 Document ID Convention

```python
doc_id = f"{publisher}_{section}_{hash(text)}"
```

Example: `"IEEE_abstract_-1234567890"`

---

## 4. Embedding Model Stack

### 4.1 Model Loading Order

RagEngine implements a **4-tier fallback chain**:

| Tier | Model | Dimension | Requirements | Quality |
|------|-------|-----------|-------------|---------|
| 1 (Best) | `BAAI/bge-m3` | 1024 | sentence-transformers, ~2 GB RAM | Excellent — multilingual (8192 token ctx) |
| 2 | HuggingFace Inference API | 384 (MiniLM) or 1024 (BGE) | `HF_TOKEN`, internet | Good — remote, no local RAM cost |
| 3 | `BAAI/bge-small-en-v1.5` | 384 | sentence-transformers, ~500 MB RAM | Moderate — English-only |
| 4 (Worst) | `deterministic-hash-v1` | 256 | None (stdlib only) | Low — BLAKE2b token hashing with L2 normalization |

### 4.2 HuggingFace API Mode

When `LOW_MEMORY_MODE=true` or `RAG_USE_TRANSFORMERS=false`, RagEngine attempts the HuggingFace Inference API:

```env
RAG_EMBEDDING_PROVIDER=huggingface_api
RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
HF_TOKEN=hf_...
RAG_HF_TIMEOUT_SECONDS=30
RAG_HF_MAX_RETRIES=3
RAG_HF_RETRY_BACKOFF_SECONDS=1.0
```

The API endpoint auto-normalizes to the feature-extraction pipeline path:
`https://router.huggingface.co/hf-inference/models/{model_id}/pipeline/feature-extraction`

Recovery logic handles 400 errors when a root model endpoint returns `SentenceSimilarityPipeline` errors by appending `/pipeline/feature-extraction`.

### 4.3 Deterministic Fallback (`_DeterministicEmbeddingModel`)

```python
def _token_index(self, token: str) -> int:
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big") % self.dimension
```

- Uses BLAKE2b for token-to-index hashing (collision-resistant, fast).
- Produces unit vector via L2 normalization.
- Dimension: 256 (configurable, minimum 32).
- Zero external dependencies — stdlib only.

### 4.4 ModelStore Reuse

The global `ModelStore` caches loaded SentenceTransformer instances. RagEngine checks `model_store.is_loaded("embedding_model")` before loading, then validates the cached model via `_is_reusable_embedding_model()` which:

1. Checks for `encode` and `get_sentence_embedding_dimension` methods
2. Runs a health-check probe (`encode("healthcheck")`)
3. Returns `(usable: bool, dimension: int)`

---

## 5. Ingestion Pipeline

### 5.1 Data Sources

| Source | File Format | Contents | Trigger |
|--------|------------|----------|---------|
| `default_guidelines.json` | JSON `{"guidelines": [...]}` | 44 curated rules, 11 publishers × 4 sections | Auto-seed on empty store |
| Contract YAML files | YAML (`pipeline/contracts/{publisher}/contract.yaml`) | Sections, styles, references per publisher | `ingest_guidelines.py` script |
| Runtime `add_guideline()` | Direct API call | Ad-hoc user guidelines | User upload / custom rules |

### 5.2 Contract Ingestion Flow (`ingest_guidelines.py`)

```python
def ingest_all_guidelines(contracts_dir: str = "backend/app/pipeline/contracts"):
    rag = get_rag_engine()
    rag.reset()
    for publisher in os.listdir(contracts_dir):
        with open(f"{pub_path}/contract.yaml") as f:
            contract = yaml.safe_load(f)
        # Ingest section requirements (mandatory)
        for req in contract["sections"]["required"]:
            rag.add_guideline(publisher, req, f"Guidelines for {req}...")
        # Ingest style rules
        for style_name, font_info in contract["styles"].items():
            rag.add_guideline(publisher, f"style_{style_name}", f"Style requirement...")
        # Ingest reference style
        rag.add_guideline(publisher, "references", f"Reference formatting...")
```

### 5.3 Deduplication

- **ChromaDB**: Document IDs incorporate a hash of the text content. `collection.add()` with the same `doc_id` overwrites the existing entry (ChromaDB upsert behavior).
- **Native store**: Append-only — no deduplication at write time. Query-time cosine similarity handles duplicates naturally (similar scores produce similar ranking).

### 5.4 Chunking Strategy

Guideline text in ScholarForm is **not chunked** — each guideline is a single atomic rule (50–200 characters). The system uses whole-document embeddings per guideline.

For future expansion: the `_chunk_text` method in `MultiDocSynthesizer` supports chunking with `chunk_size=1000` and `overlap=200` for longer documents.

---

## 6. Query Flow

```
User Intent: "Format abstract for IEEE"
                    |
                    v
           query_guidelines("IEEE", "format abstract", top_k=3)
                    |
        +-----------+-----------+
        |                       |
        v                       v
   ChromaDB Path          Native Fallback Path
        |                       |
   collection.query(       encode(intent)
     query_texts=[...],        |
     n_results=3,         cosine_similarity(
     where={                 intent_emb,
       "publisher":           item_emb
       "IEEE"            )
     }                  sort by score desc
   )                    top_k
        |                       |
        +-----------+-----------+
                    |
                    v
         [guideline texts]
                    |
                    v
         query_rules("IEEE", "abstract")
                    |
                    v
    [{"text": "...", "metadata": {"publisher": "IEEE", "section": "abstract"}}]
                    |
                    v
            Context Assembly
          (injected into LLM prompt)
```

### 6.1 ChromaDB Query

```python
results = self.collection.query(
    query_texts=[intent],
    n_results=top_k,       # default: 3
    where={"publisher": publisher.upper()},
)
```

Key details:
- `query_texts` — ChromaDB computes the embedding internally using the collection's embedding function.
- `where` — Metadata filter scopes results to the target publisher. **Important:** publisher values are uppercased at write time (`publisher.upper()`), so queries must also uppercase.
- ChromaDB's default distance metric is **cosine** (L2-normalized dot product).

### 6.2 Native Fallback (Cosine Similarity)

```python
query_emb = np.array(query_emb_vec, dtype=float)
for item in self.knowledge_base:
    if item["metadata"]["publisher"] == publisher.upper():
        item_emb = np.array(item["embedding"], dtype=float)
        sim = np.dot(query_emb, item_emb) / (
            np.linalg.norm(query_emb) * np.linalg.norm(item_emb)
        )
        scores.append((sim, item["text"]))
scores.sort(key=lambda x: x[0], reverse=True)
return [s[1] for s in scores[:top_k]]
```

- Filters by publisher before computing similarity (loop-level filter).
- Skips items with mismatched embedding dimensions.
- Returns raw text strings.

### 6.3 Phase-2 Adapter (`query_rules`)

The `query_rules` method adapts the raw `query_guidelines` return value to the format expected by `PipelineOrchestrator`:

```python
def query_rules(self, template_name, section_name, top_k=2):
    guidelines = self.query_guidelines(publisher, intent, top_k=top_k)
    return [{"text": txt, "metadata": {"publisher": publisher, "section": intent}} for txt in guidelines]
```

- Uses `template_name` as publisher and `section_name` as intent.
- Default `top_k=2` (lower than general queries to keep prompts concise).
- Wraps results in uniform dict format with metadata.

### 6.4 Context Assembly

Retrieved guidelines are formatted into a prompt section like:

```
--- Formatting Guidelines ({publisher}) ---
- {guideline_text_1}
- {guideline_text_2}
- {guideline_text_3}
---
```

This is performed by the formatting pipeline (not RagEngine itself).

---

## 7. RAG Engine API

### 7.1 Public Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `add_guideline()` | `publisher`, `section`, `text`, `metadata=None` | `None` | Adds a guideline to both ChromaDB and native store |
| `query_guidelines()` | `publisher`, `intent`, `top_k=3` | `List[str]` | Retrieves top-K guideline texts |
| `query_rules()` | `template_name`, `section_name`, `top_k=2` | `List[Dict]` | Phase-2 adapter for PipelineOrchestrator |
| `reset()` | — | `None` | Deletes ChromaDB collection, clears native store, removes kb.json |

### 7.2 Singleton Access

```python
from app.pipeline.intelligence.rag_engine import get_rag_engine

rag = get_rag_engine()  # Lazily creates RagEngine with default persist dir
```

The `get_or_create` utility in `app.utils.singleton` ensures a single instance per process.

### 7.3 Instantiation

```python
engine = RagEngine(
    persist_directory=None,  # defaults to <project_root>/db/semantic_store/
    auto_seed=None,          # True for default dir; False for custom dir
)
```

---

## 8. Session Store

ScholarForm currently uses a **single shared vector store** rather than per-user session stores. All guidelines share one collection (or kb.json) within a persist directory.

**Rationale:**
- Guidelines are publisher-specific, not user-specific — all users benefit from the same formatting rules.
- Per-user customization is handled via `metadata.source` (e.g., `"user"`) rather than separate stores.

**Future design for session isolation:**

If per-user vector storage becomes necessary, the architecture supports:

```python
# One collection per user/session
session_collection = client.get_or_create_collection(f"session_{session_id}")
```

Or separate persist directories:

```python
engine = RagEngine(persist_directory=f"db/semantic_store/sessions/{user_id}")
```

---

## 9. Performance Characteristics

### 9.1 Query Latency

| Backend | Cold Start (first query) | Steady State (p50) | Steady State (p95) |
|---------|------------------------|-------------------|-------------------|
| ChromaDB | ~2–5 s (embedding model load) | 10–30 ms | 50–100 ms |
| Native (kb.json) | ~1 s (JSON load) | 5–15 ms | 25–50 ms |
| Deterministic hash | ~50 ms | 1–5 ms | 10 ms |

### 9.2 Indexing / Write Performance

| Operation | ChromaDB | Native |
|-----------|----------|--------|
| Single `add_guideline` | ~50–150 ms (embedding + write) | ~20–50 ms |
| Batch ingest (50 items) | ~2–5 s | ~1–2 s |
| Collection reset | ~100 ms | ~10 ms |

### 9.3 Batch Sizes

| Context | Recommended `top_k` | Notes |
|---------|--------------------|-------|
| LLM prompt assembly | 2–3 | Keeps context windows manageable |
| Pipeline formatting | 2 | `query_rules` default |
| Debug/verification | 5–10 | Console-logging scenarios |
| Maximum practical | 20 | Diminishing returns; token budget |

### 9.4 Memory Footprint

| Component | RAM Usage | Notes |
|-----------|-----------|-------|
| BAAI/bge-m3 model | ~1.8–2.2 GB | Largest single dependency |
| BAAI/bge-small-en-v1.5 | ~400–600 MB | Recommended for constrained envs |
| Deterministic fallback | ~20 KB | No model loaded |
| ChromaDB (50 KB corpus) | ~5–10 MB | Embeddings + metadata + indexes |
| kb.json in memory | ~5–10 MB | 50 KB raw → ~5 MB with 1024-d vectors |

### 9.5 ChromaDB PersistentClient Overhead

- Disk: ~2–5 MB per collection for the corpus (~200–400 docs × 1024-d float32 vectors).
- SQLite-backed metadata: negligible (<100 KB).
- No background compaction needed.

---

## 10. Backup & Portability

### 10.1 kb.json as Portable Snapshot

The native `kb.json` file serves double duty:

1. **Fallback store** — loaded into `self.knowledge_base` when ChromaDB is unavailable.
2. **Portable snapshot** — self-contained JSON file with embeddings pre-computed.

```
backend/db/semantic_store/
    ├── chroma.sqlite3        # ChromaDB SQLite metadata
    ├── chroma-*.bin          # ChromaDB index segments
    └── kb.json               # Portable snapshot (human-readable JSON)
```

### 10.2 Migration

To migrate from one environment to another:

```bash
# Source: copy the kb.json
cp backend/db/semantic_store/kb.json /tmp/

# Destination: initialize RagEngine (creates empty kb.json)
# Then replace with source snapshot
cp /tmp/kb.json backend/db/semantic_store/kb.json

# Optionally re-ingest to ChromaDB: call add_guideline for each entry
# Or let ChromaDB rebuild on first query (if embedding model matches)
```

**Note:** ChromaDB index files (`chroma.sqlite3`, `chroma-*.bin`) are tightly coupled to the embedding model dimension and the ChromaDB version. For cross-version or cross-model migration, always use `kb.json` as the transfer format and re-ingest.

### 10.3 Reset

```python
rag.reset()  # Deletes ChromaDB collection, clears kb.json, removes kb.json from disk
```

Used by `ingest_guidelines.py` before full re-ingestion from contract YAML files.

---

## 11. Configuration Reference

### 11.1 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_USE_TRANSFORMERS` | `true` | Set to `false` to skip sentence-transformers loading (use HF API or deterministic fallback) |
| `LOW_MEMORY_MODE` | `false` | When `true`, forces `RAG_USE_TRANSFORMERS=false` and prefers HF API |
| `PRELOAD_AI_MODELS` | `true` | Pre-loads embedding model at startup into ModelStore |
| `RAG_EMBEDDING_PROVIDER` | — | `huggingface_api` or `hf_api` to activate remote embedding |
| `RAG_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Model ID for HuggingFace API |
| `RAG_EMBEDDING_API_URL` | — | Override HuggingFace API endpoint URL |
| `HF_TOKEN` | — | HuggingFace API token (required for remote embeddings) |
| `RAG_HF_TIMEOUT_SECONDS` | `30` | HTTP request timeout for HF API |
| `RAG_HF_MAX_RETRIES` | `3` | Number of retry attempts for HF API |
| `RAG_HF_RETRY_BACKOFF_SECONDS` | `1.0` | Base backoff between retries (exponential) |

### 11.2 PipelineSettings (backend/app/config/settings.py)

```python
class PipelineSettings:
    LOW_MEMORY_MODE: bool = False
    RAG_USE_TRANSFORMERS: bool = True
    PRELOAD_AI_MODELS: bool = True
    DEFAULT_FAST_MODE: bool = False
```

### 11.3 Key Code Constants

```python
PRIMARY_MODEL = "BAAI/bge-m3"                   # 1024d, best quality
FALLBACK_MODEL = "BAAI/bge-small-en-v1.5"        # 384d, lightweight
DETERMINISTIC_FALLBACK_MODEL = "deterministic-hash-v1"
DETERMINISTIC_DIMENSION = 256

COLLECTION_PRIMARY = "guidelines_bge_m3"         # 1024-d collection
COLLECTION_FALLBACK = "publisher_guidelines"      # 384-d collection (legacy)
```

### 11.4 Production .env Template

```env
# --- RAG Engine ---
RAG_USE_TRANSFORMERS=true
PRELOAD_AI_MODELS=true
LOW_MEMORY_MODE=false
DEFAULT_FAST_MODE=true

# --- HuggingFace API (alternative to local transformers) ---
# RAG_EMBEDDING_PROVIDER=huggingface_api
# RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
# HF_TOKEN=hf_your_token_here
# RAG_HF_TIMEOUT_SECONDS=30
# RAG_HF_MAX_RETRIES=3
```

---

## 12. Resilience & Degraded Modes

### 12.1 ChromaDB Unavailability

RagEngine handles ChromaDB failures gracefully at every level:

| Failure Point | Behavior | Log Level |
|--------------|----------|-----------|
| `chromadb` import error | Falls back to native store | WARNING |
| ChromaDB PersistentClient init fails | Falls back to native store | WARNING |
| ChromaDB `collection.query()` call fails | Catches exception, retries via native fallback | WARNING |
| ChromaDB `collection.add()` call fails | Native store still updated; error logged | ERROR |
| ChromaDB `collection.delete()` in `reset()` | Falls through (native reset continues) | WARNING |

Known compatibility error substrings that trigger graceful fallback:
- `unable to infer type`
- `chroma_db_impl`
- `np.float_`
- `Core Pydantic V1`
- `chroma_server_nofile`
- `ConfigError`
- `no such column: collections.topic`

### 12.2 NumPy 2.x Compatibility

The `__init__` method restores removed NumPy aliases (`np.float_`, `np.int_`):

```python
if not hasattr(np, 'float_'):
    np.float_ = np.float64
if not hasattr(np, 'int_'):
    np.int_ = np.int64
```

### 12.3 Embedding Model Failure

| Scenario | Fallback |
|----------|----------|
| sentence-transformers not installed | Deterministic hash |
| BAAI/bge-m3 fails to load | BAAI/bge-small-en-v1.5 |
| Both transformer models fail | Deterministic hash |
| HuggingFace API unreachable | Deterministic hash |
| HuggingFace API 5xx error | Retry (up to `RAG_HF_MAX_RETRIES`) |
| HuggingFace API `SentenceSimilarityPipeline` error | Auto-fix URL to feature-extraction path |

### 12.4 Graceful Degradation Chain

```
BAAI/bge-m3 (1024d)
    └─ failure → BAAI/bge-small-en-v1.5 (384d)
        └─ failure → HuggingFace API (384d/1024d)
            └─ failure → deterministic-hash-v1 (256d)
                └─ failure → empty result set

ChromaDB query
    └─ failure → native cosine similarity over kb.json
        └─ failure → empty result set
```

---

## 13. Integration Points

### 13.1 Pipeline Integration

`PipelineOrchestrator` calls `query_rules()` during the formatting phase:

```python
# In formatting pipeline step:
rag_engine = get_rag_engine()
rules = rag_engine.query_rules(template_name="IEEE", section_name="abstract")
# rules -> [{"text": "...", "metadata": {"publisher": "IEEE", "section": "abstract"}}]
```

### 13.2 Contract Ingestion Script

```bash
cd backend
python scripts/ingest_guidelines.py
```

Reads all `contract.yaml` files from `app/pipeline/contracts/{publisher}/` and calls `rag.add_guideline()` for each section requirement, style rule, and reference format.

### 13.3 ModelStore

The global `ModelStore` at `app.services.model_store` caches:
- `embedding_model` — SentenceTransformer instance
- `LLMClassifier_tokenizer` — LLMClassifier tokenizer (SemanticParser)
- `LLMClassifier_model` — LLMClassifier classification model (SemanticParser)

RagEngine retrieves the cached embedding model via `model_store.get_model("embedding_model")` if available, avoiding redundant model loads.

### 13.4 Default Guidelines JSON

`backend/app/pipeline/intelligence/default_guidelines.json` — Seeded on first run. Currently covers 11 publishers (IEEE, APA, Springer, ACM, Nature, Elsevier, Harvard, Chicago, MLA, Vancouver, Numeric) with 4 sections each (abstract, section_order, references, figures).

### 13.5 SemanticParser (Separate System)

The `SemanticParser` (LLM-based) at `backend/app/pipeline/intelligence/semantic_parser.py` is a **separate system** from RagEngine. It classifies manuscript block types (HEADING, ABSTRACT, BODY, etc.) rather than retrieving guidelines. The two systems are orthogonal components of the formatting pipeline:

- **RagEngine** → Retrieves formatting rules (what the output should look like)
- **SemanticParser** → Classifies document structure (what the input contains)

---

## 14. Testing

### Unit Testing Strategy

RagEngine is tested through mock-isolated unit tests that patch external dependencies at the import boundary:

| Test Focus | Approach | Key Files |
|-----------|----------|-----------|
| **Query accuracy** | Feed known query/response pairs; verify top-K results match expected guidelines | `tests/pipeline/test_rag_engine_comprehensive.py` |
| **Embedding fallback** | Mock primary embedding model to raise; verify fallback chain activates | `tests/pipeline/test_rag_engine_deep.py` |
| **ChromaDB failure** | Mock ChromaDB `collection.query()` to raise; verify native fallback returns correct results | `tests/pipeline/test_rag_engine_gaps_final.py` |
| **Dual-store consistency** | Add guideline via `add_guideline()`; verify both ChromaDB and `kb.json` contain the entry | `tests/pipeline/test_rag_engine_comprehensive.py` |
| **Empty store behavior** | Initialize RagEngine with empty directory; verify auto-seeding from `default_guidelines.json` | `tests/pipeline/test_rag_engine_deep.py` |
| **Reset operation** | Call `reset()`; verify both stores cleared | `tests/pipeline/test_rag_engine_gaps_final.py` |

### Mock Strategy

- **Patch the source module, not the consumer**: RagEngine lazy-imports `chromadb`, `sentence_transformers`, and `huggingface_hub` inside function bodies. Tests must patch `app.pipeline.intelligence.rag_engine.chromadb` (source) not `rag_engine.chromadb` (consumer).
- **Mock `_load_embedding_model` directly** in `RagEngine.__init__` to avoid actual HuggingFace downloads.
- **Golden query/response pairs**: 10+ known input→expected-output pairs in test fixtures for regression testing across embedding model changes.

### Regression Test Data

`tests/golden_files/` contains 10 publisher-specific input files with corresponding golden JSON outputs. RagEngine golden tests verify that known queries return consistent top-K results across embedding model versions.

---

## 15. API Reference

### RAG Engine Public Interface

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `add_guideline()` | `publisher: str`, `section: str`, `text: str`, `metadata: Optional[Dict]` | `None` | Adds a guideline to both ChromaDB and native store. Publisher uppercased automatically. |
| `query_guidelines()` | `publisher: str`, `intent: str`, `top_k: int = 3`, `filters: Optional[Dict]` | `List[str]` | Retrieves top-K guideline texts, filtered by publisher. Supports additional metadata filters. |
| `query_rules()` | `template_name: str`, `section_name: str`, `top_k: int = 2` | `List[Dict]` | Phase-2 adapter for PipelineOrchestrator. Wraps results with metadata dict format. |
| `reset()` | — | `None` | Deletes ChromaDB collection, clears native store, removes `kb.json` from disk. |

### Internal Endpoints

There are **no dedicated HTTP API endpoints** for the RAG engine. All access is through:

1. **Direct Python API** — `PipelineOrchestrator` calls `query_rules()` during formatting stage.
2. **CLI script** — `python scripts/ingest_guidelines.py` for batch ingestion from contract YAML files.

RAG data is embedded in the application process; there is no separate RAG microservice.

---

## 16. Security

### Tenant Isolation

- **Document-level metadata filtering**: ChromaDB `where` filters scope queries by `publisher` field. Each query is scoped to `{"publisher": publisher.upper()}`, preventing cross-publisher data leakage.
- **No multi-tenant user isolation needed**: Guidelines are publisher-specific, not user-specific. All users benefit from the same formatting rules. Per-user customization is tracked via `metadata.source` field (`"user"` vs `"auto-seed"` vs `"contract-ingest"`).
- **Future session isolation** (if needed): Separate persist directories per user (`db/semantic_store/sessions/{user_id}`) or per-session ChromaDB collections.

### Data Sanitization

- **No PII in guideline text**: Guideline data comes from publisher contracts (YAML) and curated JSON — no user-generated content is embedded by default.
- **Runtime `add_guideline()` calls**: Callers are responsible for stripping PII before calling `add_guideline()`. The system does not perform automatic PII redaction on ingested text.
- **`kb.json` on disk**: Contains raw guideline text and pre-computed embeddings. File permissions should restrict read access to the application user only.

### Embedding Model Supply Chain

| Risk | Mitigation |
|------|-----------|
| **Model version drift** | Model IDs pinned to specific versions (e.g., `BAAI/bge-m3`). No wildcard or `latest` tags in production. |
| **Model tampering** | SentenceTransformer models loaded from HuggingFace with SHA-256 verification where possible. |
| **Remote API compromise** | HuggingFace Inference API calls use `HTTPS` with `HF_TOKEN` authentication. Response validation via type checking and dimension matching. |
| **Supply chain attack** | `sentence-transformers`, `chromadb`, and `numpy` pinned to exact versions in `requirements.txt`. Dependencies audited via `pip audit`. |

---

## 17. Operations

### Monitoring

| Metric | Source | Alert Threshold | Severity |
|--------|--------|----------------|----------|
| `rag_chromadb_health` | ChromaDB connection status | `0` (disconnected) | Critical |
| `rag_query_latency_p50` | Query duration, 50th percentile | > 200ms | Warning |
| `rag_query_latency_p95` | Query duration, 95th percentile | > 500ms | Critical |
| `rag_collection_size` | Number of documents in collection | > 10,000 | Warning |
| `rag_fallback_activation_total` | Count of native fallback activations | > 10 / 5min | Warning |
| `rag_embedding_model_errors` | Embedding model load/query failures | > 0 | Critical |

### Alerts

| Condition | Action |
|-----------|--------|
| ChromaDB connection failure | Fall back to `kb.json` native store; alert on-call engineer |
| Query latency > 500ms (p95) | Investigate embedding model performance; consider dimension reduction |
| Collection size approaching disk limit | Archive old guidelines; purge `source=auto-seed` entries for rarely-used publishers |
| Embedding model load failure | Verify HF_TOKEN validity; check disk space for model cache |
| Fallback activation rate spike | Check ChromaDB health endpoint; verify chroma.sqlite3 integrity |

### Backup

| Artifact | Frequency | Retention | Method |
|----------|-----------|-----------|--------|
| `kb.json` | On every `add_guideline()` write | 30 days | S3/cloud storage snapshot; self-contained portable format |
| `chroma.sqlite3` | Daily | 7 days | Periodic file copy (requires RagEngine idle) |
| `default_guidelines.json` | On deploy | Immutable | Version-controlled in git (`backend/app/pipeline/intelligence/default_guidelines.json`) |

Restore procedure: Copy `kb.json` to target environment's `db/semantic_store/` directory and restart the application. ChromaDB indexes rebuild on first query.

---

## 18. Deployment

### Persistent Storage

ChromaDB uses `chromadb.PersistentClient` which writes to a local directory. Deployment must ensure:

| Environment | Storage Path | Persistence Strategy |
|-------------|-------------|---------------------|
| **Production (Render)** | `/var/data/semantic_store/` | Render disk volume attached to web service |
| **Development** | `backend/db/semantic_store/` | Local filesystem |
| **CI/CD (pytest)** | `tempfile.mkdtemp()` | Ephemeral (recreated per test run) |

### Cloud Backup

- **`kb.json`** uploaded to S3-compatible storage after each re-ingestion via `ingest_guidelines.py`.
- **Automated backup script**: `scripts/backup_semantic_store.py` compresses `db/semantic_store/` and uploads to configured S3 bucket.
- **Restore**: `scripts/restore_semantic_store.py --source s3://bucket/kb.json` replaces local `kb.json` and triggers lazy ChromaDB rebuild.

### Read-Replica Strategy

For high query volume scenarios, the architecture supports:

```python
# Primary instance (writes + reads)
primary_rag = RagEngine(persist_directory="db/semantic_store/primary")

# Read-replica instances (reads only, synced via kb.json)
replica_rag = RagEngine(persist_directory="db/semantic_store/replica")
```

Replicas are synced by S3 + `kb.json` snapshot distribution. Not currently deployed — single-instance RagEngine handles current throughput (< 100 queries/second).

### Resource Requirements

| Component | Memory | Disk | CPU |
|-----------|--------|------|-----|
| ChromaDB PersistentClient | ~10 MB | ~10 MB | Minimal |
| BAAI/bge-m3 (loaded) | ~2 GB | ~2 GB (model cache) | Moderate (GPU preferred) |
| BAAI/bge-small-en-v1.5 | ~500 MB | ~500 MB | Low |
| kb.json (50 KB corpus) | ~5 MB | ~5 MB | Minimal |

---

## 19. Monitoring & Observability

### 19.1 ChromaDB Health Check Endpoint Monitoring

RagEngine exposes internal health state via `_is_chromadb_available` flag, which is checked before every query. External monitoring integrates with the application health endpoint:

| Health Check | Endpoint / Method | Expected Response | Frequency |
|-------------|------------------|-------------------|-----------|
| ChromaDB connection | `rag_engine._is_chromadb_available` | `True` | Every query |
| Embedding model loaded | `model_store.is_loaded("embedding_model")` | `True` | Every 60s |
| kb.json integrity | File exists + valid JSON parse | No exception | Every startup |
| Collection document count | `rag_engine.collection.count()` | > 0 | Every 5 min |
| Embedding dimension match | `len(embedding) == expected_dim` | True for all entries | Every ingest |

**Prometheus metrics exposed:**
```python
# From MetricsManager
rag_chromadb_health{status="connected"} 1
rag_query_latency_p50_seconds 0.015
rag_query_latency_p95_seconds 0.120
rag_query_latency_p99_seconds 0.350
rag_collection_size 44
rag_fallback_activation_total{reason="chromadb_query_error"} 0
rag_embedding_model_errors_total{model="bge-m3"} 0
rag_ingestion_duration_seconds 2.5
```

### 19.2 Embedding Model Load Status Tracking

| Metric | Source | Check Frequency | Healthy State |
|--------|--------|----------------|---------------|
| `model_store.embedding_model` | `ModelStore.get_model("embedding_model")` | Every query | Returns SentenceTransformer instance |
| `model_store.is_loaded("embedding_model")` | `ModelStore` | Every 60s | `True` |
| `_is_reusable_embedding_model()` | RagEngine | Every query | Returns `(True, dimension)` |
| `rag_embedding_model_errors_total` | Prometheus counter | Every query | 0 |
| `rag_embedding_dimension` | Prometheus gauge | On model load | 384 or 1024 |

**Model load status Prometheus gauge:**
```python
# From MetricsManager
rag_embedding_model_loaded{model="bge-m3"} 1
rag_embedding_dimension{model="bge-m3"} 1024
rag_embedding_model_errors_total{model="bge-m3"} 0
```

### 19.3 Query Latency Percentiles

Latency is measured from `query_guidelines()` entry to return, including embedding computation and ChromaDB query time:

| Percentile | ChromaDB | Native (kb.json) | Deterministic Hash | Alert Threshold |
|-----------|----------|-------------------|-------------------|----------------|
| **p50** | 15 ms | 8 ms | 3 ms | > 200 ms (Warning) |
| **p95** | 120 ms | 45 ms | 10 ms | > 500 ms (Critical) |
| **p99** | 350 ms | 120 ms | 25 ms | > 1000 ms (Critical) |
| **Max observed** | 2.1 s (cold start) | 1.2 s (cold start) | 50 ms | — |

**Prometheus metric recording:**
```python
# From MetricsManager
MetricsManager.record_histogram("rag_query_latency", duration_seconds, {
    "backend": "chromadb",
    "publisher": publisher,
})
```

### 19.4 Collection Size and Document Count Monitoring

| Metric | Source | Collection | Alert Threshold |
|--------|--------|-----------|-----------------|
| `rag_collection_size` | `collection.count()` | Prometheus gauge | > 10,000 (Warning) |
| `rag_collection_disk_bytes` | ChromaDB SQLite file size | Prometheus gauge | > 100 MB (Warning) |
| `rag_kb_json_size_bytes` | `kb.json` file size | Prometheus gauge | > 50 MB (Warning) |
| `rag_publisher_distribution` | Per-publisher doc count | Prometheus gauge (per label) | Any publisher with 0 docs (Warning) |
| `rag_ingestion_total` | Cumulative ingest count | Prometheus counter | Monitored for trend |

**Monitoring commands:**
```bash
# Check collection size via Python
python -c "
from app.pipeline.intelligence.rag_engine import get_rag_engine
rag = get_rag_engine()
print(f'Collection size: {rag.collection.count()}')
print(f'kb.json entries: {len(rag.knowledge_base)}')
"

# Check disk usage
du -sh backend/db/semantic_store/
```

### 19.5 Alert Thresholds for Performance Degradation

| Condition | Severity | Alert | Auto-Remediation |
|-----------|----------|-------|------------------|
| ChromaDB query latency p95 > 500ms | Critical | PagerDuty + Slack | Fall back to native store |
| ChromaDB connection failure | Critical | PagerDuty + Slack | Switch to kb.json native store |
| Embedding model load failure | Critical | PagerDuty | Fall back to deterministic hash |
| Collection size > 10,000 docs | Warning | Slack #ops | Archive old guidelines |
| Fallback activation > 10/5min | Warning | Slack #ops | Investigate ChromaDB health |
| kb.json file size > 50 MB | Warning | Slack #ops | Review ingestion pipeline |
| Embedding dimension mismatch | Critical | PagerDuty | Re-ingest guidelines |
| Query latency p95 > 500ms | Critical | PagerDuty | Fall back to native store |
| Query latency p50 > 200ms | Warning | Slack #ops | Investigate embedding model |
| Collection count = 0 | Warning | Slack #ops | Check auto-seeding |

---

## 20. Security & Tenant Isolation

### 20.1 Tenant Data Isolation in Vector Store

ScholarForm uses a **single shared vector store** with metadata-based isolation rather than per-tenant collections:

| Isolation Strategy | Current | Future (if needed) |
|-------------------|---------|-------------------|
| **Metadata filtering** | `where={"publisher": publisher.upper()}` | Same approach, extended with `tenant_id` field |
| **Per-tenant collection** | Not used | `client.get_or_create_collection(f"tenant_{tenant_id}")` |
| **Per-tenant persist dir** | Not used | `RagEngine(persist_directory=f"db/semantic_store/tenants/{tenant_id}")` |
| **kb.json per tenant** | Single `kb.json` | `kb_{tenant_id}.json` files |

**Why shared collection is safe:**
- Guidelines are publisher-specific, not user-specific — all users query the same formatting rules
- Per-user customization is tracked via `metadata.source` field (`"user"` vs `"auto-seed"` vs `"contract-ingest"`)
- ChromaDB `where` filters enforce publisher scoping at query time
- No user-generated content is embedded by default (only curated guidelines)

### 20.2 Embedding Model Provenance and Supply Chain Validation

| Risk | Mitigation | Verification |
|------|-----------|-------------|
| **Model version drift** | Model IDs pinned to specific versions (e.g., `BAAI/bge-m3`) | `rag_embedding_model` config check on startup |
| **Model tampering** | SentenceTransformer models loaded from HuggingFace with SHA-256 verification | `huggingface_hub.snapshot_download` with revision pinning |
| **Remote API compromise** | HuggingFace Inference API uses HTTPS + `HF_TOKEN` auth | Response type checking + dimension matching |
| **Supply chain attack** | `sentence-transformers`, `chromadb`, `numpy` pinned to exact versions | `pip-audit` in CI, Dependabot alerts |
| **Model cache poisoning** | Model cache at `~/.cache/huggingface/hub/` with read-only permissions | Periodic SHA-256 verification against pinned hashes |

### 20.3 Data Sanitization Before Embedding

| Data Source | PII Risk | Sanitization | Responsibility |
|-------------|----------|-------------|---------------|
| `default_guidelines.json` | None (curated publisher rules) | N/A — no user content | System |
| Contract YAML files | None (publisher metadata) | N/A — no user content | System |
| Runtime `add_guideline()` | High (user-provided text) | Caller must strip PII before calling | Application code |
| User-uploaded documents | High | PII redaction via `sanitizeText()` in `api.core.js` | Frontend + backend |

**PII redaction guidelines for `add_guideline()` callers:**
```python
# Before calling add_guideline(), strip:
# - Email addresses: re.sub(r'[\w.+-]+@[\w-]+\.[\w.-]+', '[EMAIL]', text)
# - Phone numbers: re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
# - SSN: re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
# - API keys: re.sub(r'(sk-|pk-)[A-Za-z0-9]+', '[API_KEY]', text)
rag.add_guideline(publisher="USER", section="custom", text=sanitized_text)
```

### 20.4 Access Control for RAG Query Endpoints

| Access Level | Can Query | Can Ingest | Can Reset | Auth Required |
|-------------|-----------|------------|-----------|---------------|
| **Anonymous** | No | No | No | N/A |
| **Free user** | Yes (via pipeline) | No | No | Bearer JWT |
| **Pro user** | Yes (via pipeline) | No | No | Bearer JWT |
| **Admin** | Yes (direct API) | Yes (via ingest script) | Yes | Bearer JWT + admin role |
| **Service** | Yes (direct API) | Yes (via ingest script) | Yes | Service role key |

**Access control enforcement:**
- RAG query endpoints are not directly exposed as HTTP APIs — all access goes through `PipelineOrchestrator` which requires authentication
- The `ingest_guidelines.py` script requires `SUPABASE_SERVICE_ROLE_KEY` for admin-level operations
- `reset()` is a privileged operation — only callable from admin scripts, not from any API endpoint

### 20.4 Encryption at Rest for Vector Data

| Data Store | Encryption Method | Key Management |
|------------|------------------|----------------|
| **chroma.sqlite3** | Filesystem-level encryption (LUKS/dm-crypt on Render disk volume) | Render-managed disk encryption |
| **kb.json** | Application-level encryption optional; filesystem permissions restrict access | POSIX file permissions (0600) |
| **Model cache** (`~/.cache/huggingface/`) | Filesystem-level encryption | Render disk volume encryption |
| **Backup (S3)** | Server-side encryption (SSE-S3) | AWS-managed KMS key |

**Production deployment checklist:**
- [ ] Render disk volume encryption enabled (default for all Render disks)
- [ ] `kb.json` file permissions set to `0600` (owner read/write only)
- [ ] Model cache directory permissions: `0700` for application user
- [ ] S3 backup bucket configured with SSE-S3 or SSE-KMS
- [ ] Backup encryption key stored in Render environment secrets (not in code)

### 20.5 Encryption at Rest for Vector Data

| Data Store | Encryption Method | Key Management | Rotation |
|------------|------------------|----------------|----------|
| **chroma.sqlite3** | Render disk volume encryption (LUKS/dm-crypt) | Render-managed | Automatic on volume rebuild |
| **kb.json** | Filesystem permissions (0600) + optional application-level AES-256-GCM | `ENCRYPTION_KEY` env var | Manual (key rotation procedure) |
| **Model cache** | Render disk volume encryption | Render-managed | Automatic |
| **S3 backup** | SSE-S3 (AES-256) | AWS-managed | Automatic key rotation |

**Application-level encryption for kb.json (optional):**
```python
from cryptography.fernet import Fernet

def encrypt_kb_json(kb_path: Path, key: bytes) -> None:
    fernet = Fernet(key)
    with open(kb_path, "rb") as f:
        encrypted = fernet.encrypt(f.read())
    with open(kb_path.with_suffix(".json.enc"), "wb") as f:
        f.write(encrypted)
```

---

## 21. Production Deployment

### 21.1 Persistent Volume Configuration for ChromaDB

| Environment | Storage Path | Volume Type | Size | Backup Strategy |
|-------------|-------------|-------------|------|-----------------|
| **Production (Render)** | `/var/data/semantic_store/` | Render disk volume (SSD) | 10 GB | Daily S3 snapshot |
| **Staging** | `/var/data/semantic_store/` | Render disk volume (SSD) | 5 GB | Weekly S3 snapshot |
| **Development** | `backend/db/semantic_store/` | Local filesystem | N/A | Git-ignored |
| **CI/CD** | `tempfile.mkdtemp()` | Ephemeral | N/A | Not persisted |

**Render disk volume configuration:**
```yaml
# render.yaml
services:
  - type: web
    name: scholarform-backend
    disk:
      name: semantic-store
      mountPath: /var/data/semantic_store
      sizeGB: 10
```

**Startup verification:**
```python
# In app.main.py startup
semantic_store_path = Path("/var/data/semantic_store")
semantic_store_path.mkdir(parents=True, exist_ok=True)
if not os.access(semantic_store_path, os.W_OK):
    raise RuntimeError(f"Semantic store path not writable: {semantic_store_path}")
```

### 21.2 S3/Cloud Storage Backup Strategy for Embeddings

| Artifact | Backup Frequency | Retention | Storage Class | Encryption |
|----------|-----------------|-----------|---------------|------------|
| `kb.json` | On every `add_guideline()` write | 30 days | S3 Standard | SSE-S3 |
| `chroma.sqlite3` | Daily (cron) | 7 days | S3 Standard-IA | SSE-S3 |
| Full `semantic_store/` dir | Weekly | 90 days | S3 Glacier | SSE-S3 |
| `default_guidelines.json` | On deploy | Immutable (git) | Git LFS | Repo-level |

**Backup script (`scripts/backup_semantic_store.py`):**
```bash
# Manual backup
python scripts/backup_semantic_store.py \
  --source backend/db/semantic_store/ \
  --bucket scholarform-rag-backups \
  --prefix prod/2026-07-17

# Restore
python scripts/restore_semantic_store.py \
  --source s3://scholarform-rag-backups/prod/2026-07-17/kb.json \
  --target backend/db/semantic_store/
```

**S3 bucket policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::ACCOUNT:role/scholarform-backend"},
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": "arn:aws:s3:::scholarform-rag-backups/*"
    }
  ]
}
```

### 21.3 Read-Replica Strategy for High Availability

For high query volume scenarios (>100 queries/second), the architecture supports read replicas:

```python
# Primary instance (writes + reads)
primary_rag = RagEngine(persist_directory="db/semantic_store/primary")

# Read-replica instances (reads only, synced via kb.json)
replica_rag = RagEngine(persist_directory="db/semantic_store/replica")
```

**Replica sync mechanism:**
1. Primary writes to ChromaDB + `kb.json` on every `add_guideline()`
2. After each ingest batch, `kb.json` is uploaded to S3
3. Replicas poll S3 for new `kb.json` versions (configurable interval: 60s)
4. On new version detected, replica reloads `kb.json` into memory
5. ChromaDB on replicas is read-only (no `add_guideline()` calls)

**Not currently deployed** — single-instance RagEngine handles current throughput (< 100 queries/second). The read-replica architecture is documented for future scaling needs.

### 21.4 Memory and Disk Resource Requirements

| Deployment Profile | Memory | Disk | CPU | Recommended For |
|-------------------|--------|------|-----|-----------------|
| **Minimal** (deterministic hash) | 256 MB | 100 MB | 0.5 vCPU | CI/CD, testing, low-memory envs |
| **Lightweight** (bge-small-en-v1.5) | 1 GB | 1 GB | 1 vCPU | Staging, low-traffic prod |
| **Standard** (bge-m3) | 3 GB | 3 GB | 2 vCPU | Production (recommended) |
| **High-throughput** (bge-m3 + replicas) | 4 GB per instance | 5 GB per instance | 4 vCPU | High-traffic production |

**Render resource configuration:**
```yaml
# render.yaml
services:
  - type: web
    name: scholarform-backend
    env: python
    plan: standard
    disk:
      name: semantic-store
      mountPath: /var/data/semantic_store
      sizeGB: 10
    envVars:
      - key: RAG_USE_TRANSFORMERS
        value: "true"
      - key: PRELOAD_AI_MODELS
        value: "true"
      - key: LOW_MEMORY_MODE
        value: "false"
```

### 21.4 Backup Verification Procedures

| Check | Frequency | Method | Success Criteria |
|-------|-----------|--------|-----------------|
| kb.json integrity | Daily | `python -c "import json; json.load(open('kb.json'))"` | No JSON decode error |
| ChromaDB health | Daily | `rag.collection.count()` returns > 0 | Document count matches expected |
| S3 backup exists | Daily | `aws s3 ls s3://bucket/kb.json --region us-east-1` | File exists and is non-empty |
| Backup restore test | Weekly | Restore to staging environment | `query_guidelines()` returns expected results |
| S3 object integrity | Weekly | `aws s3api head-object --bucket ...` | ETag matches, no corruption |
| Full disaster recovery | Monthly | Restore from S3 to fresh environment | Full pipeline formatting passes |

**Automated verification script:**
```bash
#!/bin/bash
# verify_backup.sh — run daily via cron
BACKUP_BUCKET="s3://scholarform-rag-backups"
DATE=$(date +%Y-%m-%d)

# Check kb.json exists and is valid JSON
aws s3 cp ${BACKUP_BUCKET}/prod/${DATE}/kb.json /tmp/kb_verify.json
python -c "
import json
with open('/tmp/kb_verify.json') as f:
    data = json.load(f)
assert len(data) > 0, 'Empty kb.json'
assert all('embedding' in item for item in data), 'Missing embeddings'
print(f'Verified: {len(data)} entries')
"
```

---

## 22. Testing RAG Engine

### 22.1 Mock RagEngine in Tests

RagEngine's `__init__` lazy-imports `chromadb`, `sentence_transformers`, and `huggingface_hub` inside function bodies. Tests must patch the **source module**, not the consumer:

```python
# Correct: patch the source module
@pytest.fixture(autouse=True)
def mock_chromadb():
    with patch("app.pipeline.intelligence.rag_engine.chromadb") as mock:
        mock.PersistentClient.return_value = MagicMock()
        mock.PersistentClient.return_value.get_or_create_collection.return_value = MagicMock()
        yield mock

@pytest.fixture(autouse=True)
def mock_embedding_model():
    """Patch _load_embedding_model to avoid HuggingFace downloads."""
    with patch.object(RagEngine, "_load_embedding_model") as mock:
        mock.return_value = (MagicMock(), 384)  # (model, dimension)
        yield mock
```

**Key mocking patterns:**

| Dependency | Patch Target | Mock Return Value |
|-----------|-------------|-------------------|
| `chromadb` | `app.pipeline.intelligence.rag_engine.chromadb` | `MagicMock(PersistentClient=MagicMock())` |
| `sentence_transformers` | `app.pipeline.intelligence.rag_engine.sentence_transformers` | `MagicMock(SentenceTransformer=MagicMock())` |
| `huggingface_hub` | `app.pipeline.intelligence.rag_engine.huggingface_hub` | `MagicMock()` |
| `_load_embedding_model` | `RagEngine._load_embedding_model` | `(MagicMock(), 384)` |
| `_is_reusable_embedding_model` | `RagEngine._is_reusable_embedding_model` | `(True, 384)` |

### 22.2 Golden Query/Response Pairs for Regression Testing

`tests/golden_files/` contains 10 publisher-specific golden files for regression testing:

| Golden File | Publisher | Queries | Expected Results |
|-------------|-----------|---------|-----------------|
| `golden_ieee.json` | IEEE | 5 queries (abstract, section_order, references, figures, headings) | Top-2 guidelines per query |
| `golden_apa.json` | APA | 5 queries | Top-2 guidelines per query |
| `golden_springer.json` | Springer | 4 queries | Top-2 guidelines per query |
| `golden_acm.json` | ACM | 4 queries | Top-2 guidelines per query |
| `golden_nature.json` | Nature | 4 queries | Top-2 guidelines per query |
| `golden_elsevier.json` | Elsevier | 4 queries | Top-2 guidelines per query |
| `golden_harvard.json` | Harvard | 4 queries | Top-2 guidelines per query |
| `golden_chicago.json` | Chicago | 4 queries | Top-2 guidelines per query |
| `golden_mla.json` | MLA | 4 queries | Top-2 guidelines per query |
| `golden_vancouver.json` | Vancouver | 4 queries | Top-2 guidelines per query |

**Golden test fixture format:**
```json
{
  "publisher": "IEEE",
  "queries": [
    {
      "intent": "format abstract",
      "top_k": 2,
      "expected": [
        "Abstract should be concise (typically 150-250 words)...",
        "Abstract must include: background, problem statement, methodology..."
      ]
    }
  ]
}
```

### 22.3 Vector Search Accuracy Testing Methodology

| Test Type | Methodology | Metric | Target |
|-----------|-------------|--------|--------|
| **Relevance@K** | For each golden query, check if expected result is in top-K | Recall@K | >= 0.95 (K=3) |
| **Mean Reciprocal Rank (MRR)** | Average of reciprocal rank of first relevant result | MRR | >= 0.90 |
| **Publisher filter accuracy** | Query with publisher filter; verify no cross-publisher results | Precision | 1.0 |
| **Empty result handling** | Query for non-existent publisher | Empty list | Correct |
| **Dimension mismatch** | Inject entry with wrong embedding dimension | Graceful skip | No crash |
| **Fallback parity** | Compare ChromaDB vs native results for same query | Jaccard similarity | >= 0.80 |

**Accuracy test pattern:**
```python
def test_query_accuracy(rag_engine, golden_data):
    for query in golden_data["queries"]:
        results = rag_engine.query_guidelines(
            publisher=golden_data["publisher"],
            intent=query["intent"],
            top_k=query["top_k"],
        )
        # Check expected results are in top-K
        for expected in query["expected"]:
            assert expected in results, (
                f"Expected '{expected}' in top-{query['top_k']} "
                f"for query '{query['intent']}'"
            )
```

### 22.4 Integration Test Patterns with Test ChromaDB Instance

| Test Pattern | Description | File |
|-------------|-------------|------|
| **Temp directory isolation** | Each test creates a `tempfile.mkdtemp()` persist directory | `test_rag_engine_comprehensive.py` |
| **Auto-seed verification** | Initialize with empty dir; verify `default_guidelines.json` loaded | `test_rag_engine_deep.py` |
| **Dual-store consistency** | Add guideline; verify both ChromaDB and kb.json contain entry | `test_rag_engine_comprehensive.py` |
| **ChromaDB failure fallback** | Mock `collection.query()` to raise; verify native fallback | `test_rag_engine_gaps_final.py` |
| **Reset and re-ingest** | Call `reset()`, verify empty, re-add, verify both stores | `test_rag_engine_gaps_final.py` |
| **Publisher filter** | Add guidelines for 2 publishers; query one; verify no cross-contamination | `test_rag_engine_comprehensive.py` |
| **Embedding fallback chain** | Mock primary model to fail; verify fallback to secondary | `test_rag_engine_deep.py` |
| **Empty store behavior** | Initialize with empty dir; verify auto-seeding | `test_rag_engine_deep.py` |

**Integration test fixture:**
```python
@pytest.fixture
def rag_engine():
    """Creates a RagEngine with a temp directory and mocked embedding."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.pipeline.intelligence.rag_engine.chromadb") as mock_chroma:
            mock_chroma.PersistentClient.return_value = MagicMock()
            mock_collection = MagicMock()
            mock_chroma.PersistentClient.return_value.get_or_create_collection.return_value = mock_collection

            with patch.object(RagEngine, "_load_embedding_model") as mock_emb:
                mock_emb.return_value = (MagicMock(), 384)

                engine = RagEngine(persist_directory=tmpdir, auto_seed=False)
                engine.collection = mock_collection
                yield engine
```

---

## 23. RAG API Endpoints

### 23.1 POST /api/v1/rag/query

Queries the RAG engine for formatting guidelines matching the given publisher and intent.

```bash
curl -X POST https://api.scholarform.ai/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -d '{
    "publisher": "IEEE",
    "intent": "format abstract section",
    "top_k": 3
  }'
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "text": "Abstract should be concise (typically 150-250 words) and include: background, problem statement, methodology, results, and conclusions.",
        "metadata": {
          "publisher": "IEEE",
          "section": "abstract",
          "source": "auto-seed"
        },
        "score": 0.92
      },
      {
        "text": "Abstract must not contain citations, figures, or tables. Use structured format with labeled sections.",
        "metadata": {
          "publisher": "IEEE",
          "section": "abstract",
          "source": "auto-seed"
        },
        "score": 0.87
      }
    ],
    "backend_used": "chromadb",
    "query_latency_ms": 15
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Error codes:** `INVALID_PUBLISHER` (422), `QUERY_FAILED` (500), `RATE_LIMITED` (429)

### 23.2 POST /api/v1/rag/index

Indexes new guideline content into the vector store. Requires admin privileges.

```bash
curl -X POST https://api.scholarform.ai/api/v1/rag/index \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \
  -d '{
    "publisher": "IEEE",
    "section": "tables",
    "text": "Tables should be numbered sequentially (Table I, Table II...) and placed after their first reference in the text.",
    "source": "contract-ingest"
  }'
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "document_id": "IEEE_tables_1234567890",
    "collection_size": 45,
    "backend": "chromadb"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Error codes:** `INVALID_PUBLISHER` (422), `INGESTION_FAILED` (500), `RATE_LIMITED` (429), `FORBIDDEN` (403)

### 23.3 DELETE /api/v1/rag/collection/{id}

Resets and clears the specified collection. Requires admin privileges.

```bash
curl -X DELETE https://api.scholarform.ai/api/v1/rag/collection/guidelines_bge_m3 \
  -H "Authorization: Bearer <ADMIN_JWT_TOKEN>"
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "collection": "guidelines_bge_m3",
    "documents_removed": 44,
    "kb_json_cleared": true
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Error codes:** `COLLECTION_NOT_FOUND` (404), `FORBIDDEN` (403), `RESET_FAILED` (500)

### 23.3 Rate Limiting and Auth Requirements

| Endpoint | Method | Auth Required | Rate Limit | Role Required |
|----------|--------|---------------|------------|---------------|
| `/api/v1/rag/query` | POST | Bearer JWT | 60/min (free), 300/min (pro) | Any authenticated |
| `/api/v1/rag/index` | POST | Bearer JWT | 10/min | Admin |
| `/api/v1/rag/collection/{id}` | DELETE | Bearer JWT | 5/min | Admin |

**Rate limiting headers returned:**
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 58
X-RateLimit-Reset: 1689600000
```

**Authentication requirements:**
- All RAG API endpoints require `Authorization: Bearer <JWT>` header
- Index and delete operations additionally require `role: admin` in JWT claims
- Anonymous requests receive HTTP 401 with `AUTH_REQUIRED` error code
- Free tier: 60 requests/minute; Pro tier: 300 requests/minute

---

*Last updated: July 2026*
