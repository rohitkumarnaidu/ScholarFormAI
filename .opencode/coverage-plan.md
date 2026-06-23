# ScholarForm AI — Coverage Plan: 35% → 95%

**Current:** 19,991 stmts, ~7,349 covered (35.15%)  
**Target:** ~18,991 covered (95%) — need **11,642 more stmts covered**

---

## Phase 0: Pipeline Low-Hanging Fruit (~2,200 stmts)

| Module | Files | Stmts | Current | Target |
|---|---|---|---|---|
| `pipeline/export/` | `exporter.py`, `jats_generator.py`, `latex_exporter.py`, `pdf_exporter.py` | 404 | ~13% | 85% |
| `pipeline/validation/` | `validator_v3.py`, `review_manager.py`, `ai_explainer.py` | 243 | ~45% | 85% |
| `pipeline/input_conversion/` | `converter.py` | 145 | 10% | 85% |
| `pipeline/nlp/` | `analyzer.py` | 188 | 10% | 80% |
| `pipeline/ocr/` | `pdf_ocr.py` | 163 | 36% | 85% |
| `pipeline/tables/` | `extractor.py`, `caption_matcher.py`, `renderer.py` | 244 | ~30% | 85% |
| `pipeline/figures/` | `analyzer.py`, `caption_matcher.py` | 165 | ~38% | 85% |

## Phase 1: Pipeline Generation & Classification (~1,300 stmts)

| Module | Files | Stmts | Current | Target |
|---|---|---|---|---|
| `pipeline/generation/` | `agent.py`, `document_generator.py`, `prompt_builder.py`, `content_parser.py`, `quality_scorer.py`, `section_prompts.py`, `task_parser.py` | 1,045 | 0% | 80% |
| `pipeline/formatting/` | `template_renderer.py` | 210 | 54% | 85% |
| `pipeline/classification/` | `classifier.py` | 497 | 30% | 75% |
| `pipeline/intelligence/` | `semantic_parser.py` | 295 | 17% | 75% |
| `pipeline/synthesis/` | `synthesizer.py` | 322 | 0% | 75% |
| `pipeline/safety/` | `llm_validator.py` | 75 | 24% | 85% |
| `pipeline/structure_detection/` | `detector.py` | 247 | 52% | 80% |

## Phase 2: Agents Module (~2,160 stmts)

20 files in `app/pipeline/agents/` + 5 in `agents/tools/` — all 0%.

| Group | Stmts | Target |
|---|---|---|
| `document_agent.py`, `llm_factory.py`, `memory.py` | ~440 | 75% |
| `adaptive.py`, `autoscaling.py`, `realtime_adaptation.py` | ~312 | 70% |
| `distributed.py`, `federated_learning.py`, `multi_doc_learning.py` | ~492 | 65% |
| `dashboard.py`, `advanced_dashboard.py`, `nextgen_dashboard.py` | ~149 | 70% |
| `metrics.py`, `custom_tools.py`, `tool_marketplace.py` | ~285 | 70% |
| `deep_learning.py`, `ml_patterns.py`, `streaming.py` | ~267 | 65% |
| `tools/*.py` (5 files) | ~388 | 75% |

## Phase 3: Services Module (~2,500 stmts)

`enhancement_manager`, `document_service`, `llm_service`, `preview_renderer`, `health_checks`, `generator_session_service`, `quality_score_service`, `ab_testing`, `model_metrics`, `session_vector_store`, `api_key_rate_limiter`, `auth_service`, `user_service`, `citation_assembly_service`, `feature_flags`, `encryption_service`, `nvidia_client`, `crossref_client`, `scibert_gate`, `vllm_adoption`, `model_store` — target 75-85%.

## Phase 4: Models, Config, Utils, Schemas (~900 stmts)

`pipeline_document.py`, `table.py`, `figure.py`, `reference.py`, `settings.py`, `logging_config.py`, `id_generator.py`, `serialization.py`, `singleton.py`, `logging_context.py`, `dependencies.py`, `background_tasks.py`, `cleanup.py`, `virus_scanner.py`, `schemas/*`, `exceptions.py` — target 85-98%.

## Phase 5: Middleware, DB, Cache (~900 stmts)

`prometheus_metrics`, `rate_limit`, `tier_rate_limit`, `request_id`, `abuse_detector`, `csrf`, `security_headers`, `feature_flags`, `session.py`, `supabase_client.py`, `redis_cache.py` — target 80-85%.

## Phase 6: Routers & App Entry (~3,200 stmts)

All `routers/v1/*.py`, `routers/preview.py`, `routers/deprecation.py`, `main.py` — target 60-80% using TestClient.

## Phase 7: Security, Realtime, Tasks (~500 stmts)

`jwks_verifier`, `events.py`, `pubsub.py`, `celery_tasks.py`, `cleanup.py` — target 60-80%.

## Running Total

```
Phase 0: Pipeline low-hanging     +2,000 →  9,349 (46.8%)
Phase 1: Pipeline gen/etc         +1,100 → 10,449 (52.3%)
Phase 2: Agents                   +1,500 → 11,949 (59.8%)
Phase 3: Services                 +1,900 → 13,849 (69.3%)
Phase 4: Models/Config/Utils      +  750 → 14,599 (73.0%)
Phase 5: Middleware/DB/Cache      +  700 → 15,299 (76.5%)
Phase 6: Routers/main.py         +1,800 → 17,099 (85.5%)
Phase 7: Security/Realtime/Tasks +  400 → 17,499 (87.5%)
Wrap-up: Gap-closing pass         +1,500 → 18,999 (95.0%)
```

## Patterns & Strategies

- **Use pytest markers:** `unit`, `slow`, `integration`, `pipeline`
- **Mock at boundaries:** HTTP calls → `httpx`/`aiohttp` mock; DB → `SupabaseClient` mock; ML → `MagicMock` at import guard
- **Pydantic v2:** Always provide `block_id`, `index`, `text` for `Block`; `reference_id` for `Reference`; `figure_id` for `Figure`
- **FastAPI routes:** Use `TestClient` with `app`, patch service dependencies via `app.dependency_overrides`
- **Big modules (agents, services):** Split tests into focused test files, one per business concern
