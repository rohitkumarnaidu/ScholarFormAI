# Parallel Coverage Implementation Plan — 95% Target

**Constraint**: Task/subagent tool is broken ("no such column: replacement_seq") — everything must be done sequentially in this session.
**Pipeline import problem**: `tests/pipeline/*.py` have 2-min import overhead due to module-level `from app.models import *`. Fix: move imports inside test functions.

---

## Phase 0: Fix Pipeline Import Overhead (PREREQUISITE)

**Goal**: Make pipeline test files runnable in <3s each instead of 2+ min.

**Problem**: `tests/pipeline/test_*.py` have `from app.models import *` at module level, which triggers the entire import chain (agents, LLM, etc.)

**Fix for each file**: Move all imports INSIDE test functions or pytest fixtures.

Example — `tests/pipeline/test_orchestrator.py`:

```python
# BAD (current):
from app.pipeline.orchestrator import Orchestrator
# GOOD:
def test_something():
    from app.pipeline.orchestrator import Orchestrator
    ...
```

**Files to fix** (9 files in `tests/pipeline/`):

1. `test_orchestrator.py`
2. `test_classifier.py`
3. `test_formatter.py`
4. `test_rag_engine.py`
5. `test_synthesizer.py`
6. `test_agent.py`
7. `test_document_generator.py`
8. `test_pdf_exporter.py`
9. `test_parser.py`

**Time**: ~5 min per file = 45 min total

---

## Phase 1: Remaining Services (~1,800 stmts, 10 files)

Run command: `pytest tests/test_<file>.py --no-cov -q` (expect <30s each)

| # | File to Create | Module to Cover | Stmts | Pure Functions | Complex Parts | Est. Tests | Est. Time |
|---|---|---|---|---|---|---|---|
| 1 | `test_document_service.py` | `document_service.py` | 459 | `_validate_doc`, `_sanitize` | DB, file I/O | 50 | 45 min |
| 2 | `test_generator_session_service.py` | `generator_session_service.py` | 313 | `_session_key`, `_expiry` | DB CRUD | 35 | 35 min |
| 3 | `test_enhancement_manager.py` | `enhancement_manager.py` | 155 | scoring helpers | pipeline orchestration | 20 | 25 min |
| 4 | `test_quality_score_service.py` | `quality_score_service.py` | 113 | formula functions | DB queries | 15 | 20 min |
| 5 | `test_api_key_rate_limiter.py` | `api_key_rate_limiter.py` | 127 | rate window calc | redis time-window | 15 | 20 min |
| 6 | `test_nvidia_client.py` (extend) | `nvidia_client.py` | 122 | URL building | HTTP calls | 20 | 20 min |
| 7 | `test_crossref_client.py` | `crossref_client.py` | 95 | XML parsing | HTTP fetch | 15 | 20 min |
| 8 | `test_ab_testing.py` | `ab_testing.py` | 96 | bucket calc | variant assignment | 12 | 15 min |
| 9 | `test_citation_assembly.py` | `citation_assembly_service.py` | 87 | template filling | CSL loading | 15 | 15 min |
| 10 | `test_scibert_gate.py` | `scibert_gate.py` | 42 | bool checks | model load | 8 | 10 min |
| 11 | `test_auth_service.py` | `auth_service.py` | 95 | token parsing | JWT verify | 15 | 15 min |
| 12 | `test_encryption_service.py` | `encryption_service.py` | 39 | encrypt/decrypt | key management | 10 | 10 min |
| 13 | `test_vllm_adoption.py` | `vllm_adoption.py` | 26 | config mapping | - | 5 | 5 min |
| 14 | `test_feature_flags.py` | `feature_flags.py` | 75 | flag resolution | DB lookup | 12 | 15 min |

**Subtotal**: ~250 tests, ~4.5 hours

---

## Phase 2: Utils (~600 stmts, 7 files)

| # | File | Module | Stmts | Est. Tests | Time |
|---|------|--------|-------|-----------|------|
| 1 | `test_background_tasks.py` | `background_tasks.py` | 58 | 10 | 10 min |
| 2 | `test_dependencies.py` | `dependencies.py` | 74 | 15 | 15 min |
| 3 | `test_cleanup.py` | `cleanup.py` | 40 | 8 | 10 min |
| 4 | `test_serialization.py` | `serialization.py` | 67 | 15 | 15 min |
| 5 | `test_singleton.py` | `singleton.py` | 36 | 8 | 8 min |
| 6 | `test_text_utils.py` | `text_utils.py` | 55 | 12 | 12 min |
| 7 | `test_virus_scanner.py` | `virus_scanner.py` | 93 | 12 | 15 min |
| 8 | `test_id_generator.py` | `id_generator.py` | 14 | 5 | 5 min |

**Subtotal**: ~75 tests, 1.5 hours

---

## Phase 3: Middleware & DB (~700 stmts, 9 files)

| # | File | Module | Stmts | Est. Tests | Time |
|---|------|--------|-------|-----------|------|
| 1 | `test_csrf.py` | `csrf.py` | 71 | 12 | 15 min |
| 2 | `test_security_headers.py` | `security_headers.py` | 35 | 8 | 10 min |
| 3 | `test_request_id.py` (extend) | `request_id.py` | 43 | 8 | 10 min |
| 4 | `test_abuse_detector.py` | `abuse_detector.py` | 44 | 10 | 12 min |
| 5 | `test_tier_rate_limit.py` | `tier_rate_limit.py` | 80 | 15 | 15 min |
| 6 | `test_supabase_client.py` | `supabase_client.py` | 55 | 10 | 15 min |
| 7 | `test_redis_cache.py` (extend) | `redis_cache.py` | 114 | 20 | 25 min |
| 8 | `test_db_session.py` | `session.py` | 43 | 8 | 10 min |
| 9 | `test_monitoring.py` | `monitoring.py` | 24 | 6 | 8 min |

**Subtotal**: ~97 tests, 2 hours

---

## Phase 4: Pipeline Low-Hanging (~1,500 stmts, 7 modules)

**Strategy**: Mock at import boundary. These modules import `app.models` → use lazy imports inside test functions.

| # | Module Dir | Key Files | Stmts | Est. Tests | Time |
|---|-----------|-----------|-------|-----------|------|
| 1 | `pipeline/export/` | exporter, jats, latex, pdf | 579 | 60 | 60 min |
| 2 | `pipeline/validation/` | validator_v3, review_manager | 223 | 30 | 30 min |
| 3 | `pipeline/tables/` | extractor, caption_matcher, renderer | 244 | 35 | 35 min |
| 4 | `pipeline/figures/` | analyzer, caption_matcher | 165 | 25 | 25 min |
| 5 | `pipeline/input_conversion/` | converter | 145 | 20 | 20 min |
| 6 | `pipeline/nlp/` | analyzer | 188 | 25 | 25 min |
| 7 | `pipeline/ocr/` | pdf_ocr | 163 | 20 | 25 min |

**Subtotal**: ~215 tests, 3.5 hours

---

## Phase 5: Pipeline Gen & Classification (~5,000 stmts, 15 files)

| # | Module Dir | Key Files | Stmts | Est. Tests | Time |
|---|-----------|-----------|-------|-----------|------|
| 1 | `pipeline/generation/` | 7 files | 1,045 | 100 | 2 hours |
| 2 | `pipeline/formatting/` | template_renderer, formatter | 994 | 80 | 1.5 hours |
| 3 | `pipeline/classification/` | classifier | 497 | 50 | 45 min |
| 4 | `pipeline/intelligence/` | rag_engine, semantic_parser | 664 | 60 | 60 min |
| 5 | `pipeline/synthesis/` | synthesizer | 322 | 35 | 35 min |

**Subtotal**: ~325 tests, 6 hours

---

## Phase 6: Agents (~2,160 stmts, 25 files)

**Strategy**: Each agent file is mostly LangGraph nodes. Test each node function independently.

| # | Group | Files | Stmts | Est. Tests | Time |
|---|-------|-------|-------|-----------|------|
| 1 | Core agents | document_agent, llm_factory, memory | 440 | 50 | 1 hour |
| 2 | Infra agents | adaptive, autoscaling, realtime_adaptation | 312 | 35 | 45 min |
| 3 | Distributed | distributed, federated_learning, multi_doc_learning | 492 | 50 | 60 min |
| 4 | Dashboard | dashboard, advanced_dashboard, nextgen_dashboard | 149 | 20 | 30 min |
| 5 | Tools | metrics, custom_tools, tool_marketplace | 285 | 30 | 40 min |
| 6 | ML agents | deep_learning, ml_patterns, streaming | 267 | 30 | 40 min |
| 7 | Tool files | 5 tool files | 388 | 40 | 50 min |

**Subtotal**: ~255 tests, 5.5 hours

---

## Phase 7: Routers (~3,200 stmts, 15+ files)

**Strategy**: Use FastAPI `TestClient` + `app.dependency_overrides` to mock services.

| # | File | Stmts | Est. Tests | Time |
|---|------|-------|-----------|------|
| 1 | `routers/v1/documents.py` + `_impl` | 658 | 60 | 60 min |
| 2 | `routers/v1/generator.py` | 379 | 40 | 40 min |
| 3 | `routers/v1/templates.py` | 180 | 25 | 25 min |
| 4 | `routers/v1/synthesis.py` | 145 | 20 | 20 min |
| 5 | `routers/v1/metrics.py` | 106 | 15 | 15 min |
| 6 | `routers/v1/stream.py` | 52 | 10 | 10 min |
| 7 | `routers/v1/feedback.py` | 50 | 10 | 10 min |
| 8 | `routers/v1/billing.py` | 78 | 15 | 15 min |
| 9 | `routers/v1/_helpers.py` | 65 | 15 | 15 min |
| 10 | `routers/v1/api_keys.py` | 134 | 20 | 20 min |
| 11 | `routers/v1/auth.py` | 41 | 10 | 10 min |
| 12 | `routers/preview.py` | 129 | 20 | 20 min |
| 13 | `routers/deprecation.py` | 31 | 8 | 8 min |
| 14 | `main.py` | 416 | 40 | 45 min |

**Subtotal**: ~308 tests, 5.5 hours

---

## TOTAL ESTIMATE

| Phase | Tests | Time |
|-------|-------|------|
| Phase 0: Fix pipeline imports | - | 45 min |
| Phase 1: Services | 250 | 4.5 hr |
| Phase 2: Utils | 75 | 1.5 hr |
| Phase 3: Middleware/DB | 97 | 2 hr |
| Phase 4: Pipeline low-hanging | 215 | 3.5 hr |
| Phase 5: Pipeline gen+classify | 325 | 6 hr |
| Phase 6: Agents | 255 | 5.5 hr |
| Phase 7: Routers | 308 | 5.5 hr |
| **Total** | **~1,525 tests** | **~29 hours** |

---

## Execution Strategy

### Sequential order (since parallel task tool is broken)

1. **Phase 0 first** — unblocks everything
2. **Phases 1-3** (services + utils + middleware) — fast, independent, no pipeline import issues
3. **Phase 4** (pipeline low-hanging) — uses lazy imports, should run fine
4. **Phase 5** (pipeline gen) — largest phase, biggest gain
5. **Phase 6** (agents) — last pipeline work
6. **Phase 7** (routers) — uses TestClient, no pipeline imports

### Key Mocking Patterns

- **LLM calls**: `patch("app.services.llm_service.generate")`
- **DB calls**: `patch("app.db.session.get_db")`
- **HTTP calls**: `patch("httpx.AsyncClient")` with `__aenter__.return_value.get`
- **File I/O**: `patch("builtins.open", mock_open(read_data=...))`
- **Agents**: Each LangGraph node is a pure function — test independently
- **Redis**: `patch.object(redis_cache, "client", mock_redis)`
