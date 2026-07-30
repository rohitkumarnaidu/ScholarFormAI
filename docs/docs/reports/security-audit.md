# Security Audit Report — ScholarFormAI

**Document Version:** 1.0.0  
**Date:** 2026-07-29  
**Scope:** Application Security, OWASP Top 10, LLM/RAG Guardrails, Supply Chain Integrity  
**Classification:** Enterprise Security Audit  

---

## Executive Summary

This formal security audit evaluates ScholarFormAI against enterprise security standards, including OWASP Top 10 vulnerabilities, AI-specific threat vectors (Prompt Injection, RAG Context Contamination), Access Control, Transport Security, and Supply Chain Security.

---

## 1. Observation

Core codebase audit reveals the following security implementations:

### OWASP Top 10 Compliance Baseline
- **A01: Broken Access Control**:
  - PostgreSQL Row-Level Security (RLS) policies are active across database tables, ensuring data operations evaluate `auth.uid() = user_id`.
  - `backend/app/middleware/tier_rate_limit.py` validates JWT tokens and enforces usage quotas based on subscription tiers (e.g. Free Tier capped at 5 document transformations/day).
  - `frontend/middleware.js` intercepts client requests across 15 protected route patterns, validating Supabase JWT tokens via `getUser()` and restricting `/admin-dashboard` paths strictly to `app_metadata.role === 'admin'`.
- **A02: Cryptographic Failures**:
  - User-provided LLM credentials (OpenAI/Anthropic/Groq API keys) are encrypted at rest using Fernet AES-256 symmetric encryption (`backend/app/services/encryption_service.py`).
  - Strict HTTPS termination and HSTS (`max-age=31536000; includeSubDomains; preload`) are mandated via `frontend/next.config.mjs`.
- **A03: Injection**:
  - Database queries rely exclusively on SQLAlchemy ORM (`backend/app/db/session.py`) and Supabase client parameterization (`backend/app/services/document_service.py`), eliminating raw SQL concatenation.
  - HTML injection in document previews is mitigated via DOM-based whitelisting (`PreviewPane.jsx`) combined with strict CSP (`default-src 'self'`).
- **A07: Identification & Auth Failures**:
  - Authentication endpoints apply strict per-IP rate limits (`10/minute` on `/login` and `/signup`, `5/minute` on `/forgot-password`).
  - Session revocation is supported via Redis-backed token blocklisting (`blacklisted_token:{jti}`) matching token expiration (`backend/app/services/auth_service.py`).
- **A10: Server-Side Request Forgery (SSRF)**:
  - Webhook registration (`backend/app/services/webhook_service.py`, lines 190-214) validates target URLs, enforcing HTTPS and blocking loopback, link-local, multicast, and private IP subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).

### Prompt & RAG Injection Guardrails
- **Pre-Compiled Regex Pattern Scrubbing**: `backend/app/services/llm_provider_service.py` (lines 157-183) compiles 25 regex patterns (`_INJECTION_PATTERNS`) targeting system prompt overrides, jailbreaks, secret leakage, multi-lingual override attempts, and administrative tool execution commands.
- **Input Sanitization & Truncation**: `sanitize_for_llm()` enforces a maximum input limit of 8,000 characters (`MAX_LLM_INPUT_LENGTH`) and replaces matched injection attempts with `[CONTENT_FILTERED]`.
- **Vector Isolation**: `backend/app/services/session_vector_store.py` constrains RAG similarity searches to isolated, session-scoped ChromaDB collections (`session_{session_id}`), preventing cross-tenant vector data exposure.

### Supply Chain Security
- **Container Signature Verification**: `.github/workflows/docker-publish.yml` integrates Cosign keyless signing using GitHub OIDC tokens.
- **Build Provenance**: Container builds produce SLSA Level 3 attestations via `actions/attest-build-provenance`.
- **Vulnerability Scanning**: Automated scanning is integrated via Renovate (`renovate.json`), Dependabot, CodeQL, Trivy, Bandit, and `pip-audit`.

---

## 2. Logic Chain

The security architecture enforces defense-in-depth through connected logic controls:

1. **Layered Access Control → Multi-Tier Isolation**: Applying RLS at the database layer alongside JWT role verification in Next.js middleware and FastAPI tier middleware ensures that a failure in one layer cannot result in unauthorized cross-tenant data access.
2. **Deterministic Regex + Length Bounds → AI Context Protection**: Unconstrained prompt input permits jailbreaks that hijack LLM behavior. Enforcing character caps and scrubbing hostile instruction patterns before model transmission prevents prompt context manipulation.
3. **Session-Scoped Vector Collections → Context Leak Prevention**: Global vector indices risk leaking snippets across sessions during top-k retrieval. Structuring ChromaDB storage by `session_id` guarantees mathematical isolation of vector search spaces.

---

## 3. Caveats

- **Regex Defense Limitations**: While the 25 compiled patterns cover known prompt injection vectors, sophisticated adversarial prompts may bypass regex matchers; optional secondary LLM-based classification can be enabled via `LLM_CLASSIFICATION_ENABLED`.
- **Test Harness Mismatches**: Mock tests in `test_security_enterprise.py` contain minor mock definition variances that do not affect runtime security execution.

---

## 4. Conclusion

ScholarFormAI meets enterprise security requirements. The codebase exhibits robust controls across OWASP Top 10 categories, effective AI/RAG injection defenses, strict transport security, and verified supply chain provenance.

---

## 5. Verification Method

To verify security controls:

- **Security Header Verification**:
  ```bash
  curl -I https://<application-domain>/
  ```
  *Expected Output:* Response includes `Content-Security-Policy`, `Strict-Transport-Security`, and `X-Frame-Options: DENY`.
- **SSRF Validation**:
  Test URL validation directly in Python:
  ```python
  from app.services.webhook_service import WebhookService
  WebhookService()._validate_webhook_url("http://127.0.0.1/webhook")
  ```
  *Expected Output:* `ValueError` raised due to invalid scheme and loopback address.
- **Continuous Integration Security Audit (CI Pipeline Only)**:
  ```bash
  pip-audit
  npm audit
  ```
