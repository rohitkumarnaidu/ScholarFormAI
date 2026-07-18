# Risk Register — ScholarForm AI

| ID | Risk | Severity | Likelihood | Impact | Mitigation | Status |
|----|------|----------|------------|--------|------------|--------|
| R-001 | Coverage measurement broken (pydantic KeyError) | 🟡 Medium | High | Medium | Tests pass without --cov; CI measures independently | Documented |
| R-002 | conftest mock_redis breaks isinstance checks | 🟡 Medium | High | Low | Patched via isinstance; alternative fixtures exist | Documented |
| R-003 | ChromaDB falls back to SQLite (no persistence) | 🟡 Medium | Medium | Medium | Acceptable for staging; prod uses persistent volume | Mitigated |
| R-004 | Router collection time ~15s (lazy v1 init) | 🟢 Low | Always | Low | Runtime not affected; only test collection | Documented |
| R-005 | Coverage threshold 90% not reached without --cov | 🟢 Low | Always | Low | CI achieves target; dev env has broken measurement | Documented |
| R-006 | AI provider outage (NVIDIA → Groq → Ollama) | 🟡 Medium | Low | High | 4-tier fallback tested in chaos suite | ✅ Mitigated |
| R-007 | Prompt injection via indirect RAG documents | 🟡 Medium | Low | High | 28 injection tests pass; sanitize_for_llm active | ✅ Mitigated |
| R-008 | Vector database poisoning | 🟢 Low | Low | Medium | Vector DB security tests validate resistance | ✅ Mitigated |
| R-009 | Pipeline gap file corruption recurrence | 🟢 Low | Low | Medium | Root cause identified (squished during write) | Documented |
| R-010 | Secrets leak via CI logs | 🟢 Low | Low | Critical | detect-secrets active; baseline maintained | ✅ Mitigated |
| R-011 | ChromaDB single-writer limitation (SQLite concurrency) | 🟡 Medium | Medium | Medium | Acceptable for single-user/session; Celery serializes writes to semantic store; evaluate pgvector for multi-user | Analyzed |
| R-012 | LLM API provider dependency (vendor lock-in, rate limits, cost) | 🟡 Medium | Medium | High | 4-tier fallback (NVIDIA → Groq → OpenRouter → Ollama); user can BYO keys; cost monitoring dashboard | Mitigated |
| R-013 | Supabase vendor lock-in (managed PostgreSQL, auth, storage) | 🟡 Medium | Low | Medium | PostgreSQL is standard; auth/storage wrappers abstracted in app/db/; migration path to raw PostgreSQL documented | Documented |
| R-014 | HF Spaces cold start latency | 🟢 Low | High | Low | Not in critical path; optional inference; pre-warm script available for production | Documented |
| R-015 | Celery queue backpressure under load | 🟡 Medium | Medium | High | RabbitMQ/Redis broker monitoring; worker auto-scaling in staging; task prioritization (interactive > batch) | Analyzed |
| R-016 | Pydantic coverage measurement breakage (KeyError: root_model) | 🟡 Medium | High | Medium | Tests pass without --cov; CI uses continue-on-error coverage job; upstream pydantic issue tracked | Documented |
| R-017 | Frontend test state contamination (17+ files fail only in full suite) | 🟢 Low | High | Low | Root cause identified (module-level mock leaks); mitigation documented; switch to --pool=fork when critical | Documented |
| R-018 | Large AI model memory pressure on Render (512MB limit) | 🔴 High | Medium | High | DEFAULT_FAST_MODE=true by default; PRELOAD_AI_MODELS=false; memory profiling in CI; swap to larger plan if needed | Mitigated |
| R-019 | WebSocket connection limits on Render free tier | 🟡 Medium | Medium | Medium | Connection pooling; exponential backoff on reconnect; upgrade path to paid tier documented | Analyzed |
| R-020 | Redis single point of failure | 🔴 High | Low | Critical | Redis Sentinel in staging/prod; local file cache fallback in app/services/cache.py; RDB/AOF persistence enabled | Mitigated |
| R-021 | OpenAPI schema disabled in production (no /docs) | 🟢 Low | Always | Low | Debug mode disabled for security; internal staging instance has docs enabled; API spec available as openapi.json | Accepted |
| R-022 | Webhook delivery reliability (no exactly-once guarantee) | 🟡 Medium | Medium | High | Idempotency keys on /api/v2/webhooks; retry with exponential backoff (3 attempts); webhook log in Supabase for audit | Analyzed |
