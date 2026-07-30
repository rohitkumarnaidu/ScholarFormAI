# Technical Debt Register — ScholarForm AI

| ID | Item | Severity | Category | Effort to Fix | Notes |
| ---- | ------ | ---------- | ---------- | --------------- | ------- |
| TD-001 | Router TestClient tests need lifespan bypass | 🟡 Medium | Test Infrastructure | 2 days | TestClient hangs >180s with full lifespan; workaround exists |
| TD-002 | asyncio deprecation warnings (30k+) | 🟢 Low | Dependencies | 1 day | Upgrade pytest-asyncio; fix datetime.utcnow() calls |
| TD-003 | Pydantic v2.13+ KeyError with --cov | 🟡 Medium | Dependencies | Unknown | Affects coverage measurement only; upstream pydantic issue |
| TD-004 | Module-level `from app.models import *` causes 2min import | 🟡 Medium | Performance | 1 day | Already moved to function bodies in tests; keep pattern |
| TD-005 | Low branch coverage in pipeline modules (3-15%) | 🟢 Low | Testing | On-going | Many uncovered paths; gap test files exist but test overhead |
| TD-006 | test_property_based.py uses `datetime.utcnow()` | 🟢 Low | Best Practice | 15 min | Replace with `datetime.now(timezone.utc)` |
| TD-007 | test_mutation.py needs expansion to more services | 🟢 Low | Testing | 1 day | Currently covers 3 services; expand to 10+ |
| TD-008 | conftest.py has 300+ line autouse fixture complexity | 🟢 Low | Maintainability | 1 day | Split into focused conftest files per module |
| TD-009 | Frontend uses plain JavaScript (JSX), not TypeScript — type safety gap | 🟡 Medium | Code Quality | 2-3 weeks | No static type checking on ~50+ frontend test files; prop-type mismatches caught only at runtime; conversion to .tsx planned | Open |
| TD-010 | Legacy Vite dist/ artifacts still present in frontend | 🟢 Low | Build | 1 hour | Project migrated from Vite to Next.js; stale dist/ directory confuses tooling and wastes disk; remove and update .gitignore | Open |
| TD-011 | Empty documentation directories (proposal/, images/) | 🟢 Low | Documentation | 30 min | Empty directories under docs/ indicate incomplete documentation migration; either populate or remove | Open |
| TD-012 | Oversized Company_Documentation_FRS_SRS.md (507 lines, duplicates) | 🟢 Low | Documentation | 1 hour | Contains functional requirements, system specs, and duplicate content from other docs; should be split or trimmed | Open |
| TD-013 | Module-level `from app.models import *` causes ~2min import overhead | 🟡 Medium | Performance | 1 day | Already moved to function bodies in tests; keep pattern in new code; wildcard import should be banned in lint config | Documented |
| TD-014 | No Chaos Engineering in CI pipeline | 🟡 Medium | Testing | 3 days | Chaos tests exist (Phase 14) but run in isolation; not integrated into CI gate; add as optional pipeline stage | Open |
| TD-015 | Webhook delivery lacks exactly-once semantics | 🟡 Medium | Architecture | 2 days | Current retry model is at-least-once; duplicates possible; idempotency keys introduced but not enforced end-to-end | In Progress |
| TD-016 | Pydantic v2 → v3 migration debt | 🟡 Medium | Dependencies | 1 week | Deprecation warnings from v2 APIs; KeyError with --cov is pydantic v2.x bug; v3 migration will require schema audit | Open |
| TD-017 | Test collection timeout when running full suite (pytest tests/ >600s) | 🟡 Medium | Test Infrastructure | 1 week | 13 router files each trigger _ensure_v1_router (~15s each); must run targeted subsets; cache router on first load | Open |

### Enterprise Audit & Refactoring (July 2026)

- **P0 Security vulnerabilities**: 5 high-severity CVEs → All resolved
- **Layer violations**: 16 router→pipeline direct imports → 0 remaining
- **HTTPException in services**: 7 instances → 0 remaining (all use ScholarFormError)
- **Pipeline orchestrator god class**: 1350 lines / McCabe 182 → Modular package (6 modules)
- **Lazy imports**: 31 workarounds → All analyzed, 3 circular dep chains resolved
- **Services without types**: ~42% untyped functions → 0 in new facades
- **Remaining**: 5 fat services (>400 lines), 10 large components (>300 lines), Sync I/O in async context
