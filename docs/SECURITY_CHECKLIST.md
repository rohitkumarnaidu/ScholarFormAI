<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# Security Checklist — ScholarForm AI

**Version:** 1.0
**Last Updated:** July 2026
**Owner:** Security Team
**Review Cadence:** Quarterly

This checklist documents every active security control in ScholarForm AI. Use it for pre-release verification, audit preparation, and incident-readiness assessment. Each item is a checkbox — mark `[x]` when verified.

---

## Authentication & Authorization

Controls for identity verification, session management, and access enforcement.

- [ ] **JWT verification with algorithm confusion hardening**
  - **Description:** Every authenticated request verifies the JWT via JWKS endpoint. Algorithm confusion attacks are prevented by rejecting HS\* tokens when a shared secret is configured alongside JWKS public keys (`backend/app/security/jwks_verifier.py`).
  - **Verification:** Run `pytest tests/ -k "jwt"` (22 tests). Inspect `jwks_verifier.py` lines 58–72 for HS\* rejection logic.
  - **Severity:** Critical
  - **Reference:** `SECURITY_ARCHITECTURE.md §3.2`

- [ ] **Supabase session management with auto-refresh**
  - **Description:** The frontend calls `supabase.auth.getSession()` on every API request, allowing automatic token refresh by Supabase. Expired or missing sessions redirect to `/login?reason=session_expired` with the return URL preserved (`frontend/src/services/api.core.js`).
  - **Verification:** Trigger a session expiry in E2E tests — confirm redirect to `/login?reason=session_expired&next={path}`.
  - **Severity:** Critical
  - **Reference:** `SECURITY_ARCHITECTURE.md §3.3`

- [ ] **RBAC middleware for role-based access**
  - **Description:** Role hierarchy `free (1) → pro (2) → admin (3)` enforced via `require_role()` dependency in route handlers. Supabase roles aliased to ScholarForm roles. Insufficient role returns HTTP 403 (`backend/app/middleware/rbac.py`).
  - **Verification:** Run `pytest tests/ -k "rbac"` (19 tests). Confirm each endpoint's required level returns 403 for under-privileged users.
  - **Severity:** High
  - **Reference:** `SECURITY_ARCHITECTURE.md §4.2`

- [ ] **Admin route protection in Next.js middleware**
  - **Description:** The frontend middleware (`frontend/middleware.js`) verifies JWTs via Supabase Admin `getUser()` on 28 protected paths. Admin routes return HTTP 403 JSON when the user lacks the `admin` app_metadata role.
  - **Verification:** Attempt to access `/admin/*` without admin role — confirm HTTP 403 JSON, not redirect.
  - **Severity:** Critical
  - **Reference:** `SECURITY_ARCHITECTURE.md §3.2`

- [ ] **API key authentication (user API keys)**
  - **Description:** User-supplied API keys for LLM providers are encrypted with Fernet at rest in the `user_api_keys` table. Keys are resolved at request time via `resolve_user_api_key()` in `llm_service.py`, scoped to the authenticated user.
  - **Verification:** Confirm keys in `user_api_keys` table are ciphertext, not plaintext. Run `pytest tests/ -k "api_key"`.
  - **Severity:** High
  - **Reference:** `SECURITY_ARCHITECTURE.md §6.1`

- [ ] **OAuth 2.0 (Google) integration**
  - **Description:** Supabase Auth handles Google OAuth sign-in. The flow uses PKCE, state parameter anti-forgery, and token exchange server-side. No client secret is exposed to the browser.
  - **Verification:** Complete Google sign-in E2E. Inspect network tab for client secret leakage — none should appear.
  - **Severity:** High
  - **Reference:** `SECURITY_ARCHITECTURE.md §3.1`

---

## Network Security

Controls for transport-layer security, content policy, and origin validation.

- [ ] **HTTPS enforced with HSTS (production only, 1-year max-age)**
  - **Description:** `HTTPSRedirectMiddleware` redirects HTTP → HTTPS with HTTP 307 (method-preserving). `HSTSMiddleware` sets `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`. Both activate only when `FORCE_HTTPS=true` and `DEBUG=false` (`backend/app/middleware/https_redirect.py`).
  - **Verification:** Deploy to staging with `FORCE_HTTPS=true` — confirm all plaintext requests receive 307, and response includes HSTS header.
  - **Severity:** Critical
  - **Reference:** `SECURITY_ARCHITECTURE.md §2.3`

- [ ] **CSP with nonce-based script/style restrictions**
  - **Description:** A 16-byte cryptographically random nonce is generated per-request via `secrets.token_urlsafe(16)`. Strict CSP is applied server-side: `script-src 'self' 'nonce-{nonce}'`, `style-src 'self' 'nonce-{nonce}'`. Docs routes get relaxed CSP for Swagger UI (`backend/app/middleware/security_headers.py`).
  - **Verification:** Inject an inline `<script>alert(1)</script>` — confirm browser blocks it (check console). Verify nonce changes on every request.
  - **Severity:** High
  - **Reference:** `SECURITY_ARCHITECTURE.md §2.5`

- [ ] **CORS configured with specific origins (no wildcard in production)**
  - **Description:** `CORS_ORIGINS` env var supplies the allowed origin list. In production, must be an explicit comma-separated list. Development mode auto-appends loopback origins on ports 3000–3010, 4173, 5173. `allow_credentials=True` prevents wildcard usage (`backend/app/main.py:684–701`).
  - **Verification:** Set `CORS_ORIGINS=https://app.scholarform.com` — confirm requests from `https://evil.com` receive no `Access-Control-Allow-Origin` header.
  - **Severity:** High
  - **Reference:** `SECURITY_ARCHITECTURE.md §2.1`

- [ ] **X-Frame-Options: DENY**
  - **Description:** All responses include `X-Frame-Options: DENY` to prevent clickjacking. Set by `HSTSMiddleware` and `SecurityHeadersMiddleware` redundantly.
  - **Verification:** `curl -I https://api.scholarform.com/health | grep X-Frame-Options` — confirm `DENY`.
  - **Severity:** Medium
  - **Reference:** `SECURITY_ARCHITECTURE.md §2.5`

- [ ] **X-Content-Type-Options: nosniff**
  - **Description:** All responses include `X-Content-Type-Options: nosniff` to prevent MIME-type sniffing attacks.
  - **Verification:** `curl -I https://api.scholarform.com/health | grep X-Content-Type-Options` — confirm `nosniff`.
  - **Severity:** Medium
  - **Reference:** `SECURITY_ARCHITECTURE.md §2.5`

- [ ] **Permissions-Policy with restricted features**
  - **Description:** `Permissions-Policy` header set to `camera=(), microphone=(), geolocation=()` to disable unnecessary browser features.
  - **Verification:** `curl -I https://api.scholarform.com/health | grep Permissions-Policy` — confirm camera, microphone, geolocation all disabled.
  - **Severity:** Low
  - **Reference:** `SECURITY_ARCHITECTURE.md §2.5`

---

## Data Protection

Controls for encryption at rest, upload security, and input sanitization.

- [ ] **Fernet encryption for user API keys at rest**
  - **Description:** User API keys are encrypted with `cryptography.fernet` (AES-128-CBC with HMAC-SHA256 authentication) before storage in the `user_api_keys` table. Decryption occurs only in memory when the key is used (`backend/app/services/encryption_service.py`).
  - **Verification:** Query `user_api_keys` table — confirm `encrypted_key` is base64 ciphertext, not plaintext. Run `pytest tests/ -k "encryption"`.
  - **Severity:** Critical
  - **Reference:** `SECURITY_ARCHITECTURE.md §6.1`

- [ ] **ENCRYPTION_KEY configured in production**
  - **Description:** The `ENCRYPTION_KEY` environment variable must be set in production. Startup validation raises `RuntimeError` if absent when `DEBUG=false`. The key is 32-byte base64-encoded, generated via `EncryptionService.generate_key()`.
  - **Verification:** Start the app with `DEBUG=false` and no `ENCRYPTION_KEY` — confirm `RuntimeError`. Deploy with a valid key — confirm startup succeeds.
  - **Severity:** Critical
  - **Reference:** `SECURITY_ARCHITECTURE.md §12`

- [ ] **File upload virus scanning (ClamAV)**
  - **Description:** All uploaded files are scanned via ClamAV `INSTREAM` protocol in 64KB chunks before any processing begins. If ClamAV is unreachable, the file is marked `{"clean": true, "engine": "unavailable"}` and processing proceeds (`backend/app/utils/virus_scanner.py`).
  - **Verification:** Upload the EICAR test file — confirm detection. Disconnect ClamAV — confirm graceful degradation with `"clean": true, "engine": "unavailable"`.
  - **Severity:** High
  - **Reference:** `SECURITY_ARCHITECTURE.md §6.2`

- [ ] **Path traversal protection for uploads/downloads**
  - **Description:** `validate_path_safety()` resolves absolute paths and checks they begin with an allowed directory prefix: `uploads/`, `data/uploads/`, `output/`, `outputs/`. Explicit `..` traversal detection (`backend/app/tasks/celery_tasks.py`).
  - **Verification:** Submit a path containing `../../etc/passwd` — confirm rejection. Run `pytest tests/ -k "path_traversal"`.
  - **Severity:** Critical
  - **Reference:** `SECURITY_ARCHITECTURE.md §6.2`

- [ ] **Max body size enforcement (60MB)**
  - **Description:** Two-tier ASGI enforcement: pre-read `Content-Length` header check returns HTTP 413 immediately if exceeded; streaming body chunk accumulation drains excess bytes without processing to prevent slow-loris attacks. Default: 60MB (`backend/app/middleware/security_headers.py`).
  - **Verification:** Send a request with `Content-Length: 70000000` — confirm HTTP 413. Run `pytest tests/ -k "max_body_size"`.
  - **Severity:** Medium
  - **Reference:** `SECURITY_ARCHITECTURE.md §2.6`

- [ ] **Input sanitization (control chars, HTML entities)**
  - **Description:** `sanitizeText()` strips control characters, decodes HTML entities, and removes `<>` brackets from all API response data. `sanitizePayload()` recursively sanitizes all string values. Sensitive fields (password, OTP, token) are trimmed but not HTML-sanitized (`frontend/src/services/api.core.js`).
  - **Verification:** Submit a payload with `<script>alert(1)</script>` — confirm it becomes `[FILTERED]`. Run `pytest tests/ -k "sanitize"`.
  - **Severity:** High
  - **Reference:** `SECURITY_ARCHITECTURE.md §5.2`

---

## API Security

Controls for request throttling, idempotency, input validation, and tracing.

- [ ] **Rate limiting (3 layers: SlowAPI global, sliding-window, tier-based)**
  - **Description:** Three independent rate limiters stack for defense in depth: **SlowAPI** (120 req/min per IP, token bucket), **RateLimitMiddleware** (sliding window, 60s, per-IP + per-token fingerprint for uploads, 10 uploads/min), **TierRateLimitMiddleware** (guest 5 POST/day, free 60/min, pro 300/min). Health checks are never rate-limited.
  - **Verification:** Exceed 120 requests/min from a single IP — confirm HTTP 429. Run `pytest tests/ -k "rate_limit"` (50 tests).
  - **Severity:** High
  - **Reference:** `SECURITY_ARCHITECTURE.md §2.4, §5.3`

- [ ] **Idempotency keys for POST requests**
  - **Description:** `Idempotency-Key` header is detected on POST requests to idempotent endpoints (`/upload`, `/generator/sessions`, `/synthesis/sessions`). Key-value pairs are logged for downstream deduplication via `RequestIDMiddleware` (`backend/app/middleware/request_id.py`).
  - **Verification:** Submit two identical POST requests with the same `Idempotency-Key` — confirm only one mutation occurs. Run `pytest tests/ -k "idempotency"`.
  - **Severity:** Medium
  - **Reference:** `SECURITY_ARCHITECTURE.md §2.2`

- [ ] **API envelope pattern (consistent error responses)**
  - **Description:** All v1/v2 API responses use a consistent envelope: `{"success": true, "data": ..., "request_id": "..."}` or `{"success": false, "code": "ERROR_CODE", "message": "...", "request_id": "..."}`. Global exception handlers wrap HTTP exceptions and validation errors, stripping stack traces (`backend/app/main.py:642–679`).
  - **Verification:** Send a request with invalid data — confirm envelope shape. Send a request to a non-existent route — confirm no stack trace leakage. Run `pytest tests/ -k "envelope"`.
  - **Severity:** Medium
  - **Reference:** `SECURITY_ARCHITECTURE.md §5.1`

- [ ] **Input validation via Pydantic schemas**
  - **Description:** All API inputs are validated by Pydantic v2 models with type constraints, field validators, and `mode="before"` coercions for boolean fields. Invalid inputs return 422 with structured error details (no stack traces).
  - **Verification:** Submit an integer where a string is expected — confirm HTTP 422 with descriptive error. Run `pytest tests/ -k "validation"`.
  - **Severity:** High
  - **Reference:** `SECURITY_ARCHITECTURE.md §5.2`

- [ ] **CSRF protection with token validation**
  - **Description:** HMAC-SHA256 token with timestamp and 32-byte random value, stored in httpOnly SameSite=Lax cookie. POST/PUT/PATCH/DELETE require `X-CSRF-Token` header matching the cookie. Bearer-authenticated requests are exempt (`backend/app/middleware/csrf.py`).
  - **Verification:** Send a POST without `X-CSRF-Token` — confirm HTTP 403. Run `pytest tests/ -k "csrf"` (26 tests).
  - **Severity:** Medium
  - **Reference:** `SECURITY_ARCHITECTURE.md §2.7`

- [ ] **Request ID tracing**
  - **Description:** Every request receives a UUID4 `X-Request-Id` (or preserves an existing one). The ID is bound to structured logging context and injected into response headers for client-side tracing (`backend/app/middleware/request_id.py`).
  - **Verification:** Send a request — confirm `X-Request-Id` in response. Repeat — confirm unique IDs. Check logs for `request_id` field.
  - **Severity:** Low
  - **Reference:** `SECURITY_ARCHITECTURE.md §2.2`

---

## LLM Security

Controls for prompt injection prevention, output safety, and provider isolation.

- [ ] **Prompt injection guard (25+ regex patterns)**
  - **Description:** 25+ regex patterns organized into 12 categories (instruction override, system tag injection, API key redaction, prompt extraction, dangerous tool calls, privilege escalation, token smuggling, multi-language injection, encoded system tags, emotional manipulation, authority override, unicode/boundary escape). Matches are replaced with `[CONTENT_FILTERED]`. Input truncated to 8000 characters (`backend/app/services/llm_service.py:182–259`).
  - **Verification:** Submit each injection category sample — confirm `[CONTENT_FILTERED]` replacement. Run `pytest tests/ -k "prompt_injection"` (26 tests, 50+ patterns).
  - **Severity:** Critical
  - **Reference:** `SECURITY_ARCHITECTURE.md §8.1`

- [ ] **Output validation and sanitization**
  - **Description:** `guard_llm_output()` from `app.pipeline.safety.llm_validator` validates LLM output for harmful content and format compliance before passing to downstream processors. Structured output (JSON, citations) is validated against expected schemas.
  - **Verification:** Send a prompt that causes an LLM to return harmful content — confirm the output is rejected. Run `pytest tests/ -k "llm_output"`.
  - **Severity:** High
  - **Reference:** `SECURITY_ARCHITECTURE.md §8.2`

- [ ] **Circuit breaker for provider failures**
  - **Description:** `pybreaker` circuit breaker decorator wraps all LLM provider calls. After configurable failure threshold, the circuit opens and requests fail fast rather than hanging. Automatic half-open probe after recovery timeout. Prevents cascading failures and resource exhaustion.
  - **Verification:** Point a provider to a dead endpoint — confirm circuit opens after threshold. Wait for recovery timeout — confirm half-open probe fires. Run `pytest tests/ -k "circuit_breaker"`.
  - **Severity:** Medium
  - **Reference:** `SECURITY_ARCHITECTURE.md §10.3, HARDENING.md`

- [ ] **User API key isolation (BYOK)**
  - **Description:** Users can bring their own LLM provider API keys. Keys are Fernet-encrypted at rest, decrypted in memory only at request time, and scoped per user via `user_api_keys` table. The `generate_with_model()` function bypasses the shared fallback chain when a user key is available.
  - **Verification:** Authenticate as user A, set a custom OpenAI key — confirm user B cannot see or use it. Run `pytest tests/ -k "byok"`.
  - **Severity:** High
  - **Reference:** `SECURITY_ARCHITECTURE.md §8`

---

## Frontend Security

Controls for client-side protection, session management, and secure rendering.

- [ ] **Next.js security headers configuration**
  - **Description:** `next.config.mjs` applies global headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`. Static assets (`/_next/static/`, `/static/`) are cached with `public, max-age=31536000, immutable`.
  - **Verification:** `curl -I https://app.scholarform.com | grep -E "(X-Content-Type-Options|X-Frame-Options|Referrer-Policy)"` — confirm all three headers present.
  - **Severity:** Medium
  - **Reference:** `SECURITY_ARCHITECTURE.md §9.1`

- [ ] **Session token stored in httpOnly cookies**
  - **Description:** Supabase auth session tokens are stored in httpOnly, Secure, SameSite=Lax cookies (`sb-{ref}-auth-token`). Chunked cookies support large sessions split across `.0`, `.1`, etc. Tokens are never accessible via `document.cookie` in JavaScript.
  - **Verification:** Open browser DevTools → Application → Cookies — confirm `sb-*` cookies have httpOnly ✔ and Secure ✔ flags.
  - **Severity:** Critical
  - **Reference:** `SECURITY_ARCHITECTURE.md §3.2`

- [ ] **XSS prevention (React built-in + CSP)**
  - **Description:** Three layers: (1) React DOM auto-escapes all rendered content; (2) `sanitizePayload()` strips control characters, HTML entities, and `<>` from API responses before component state; (3) CSP nonce blocks any inline script without a valid nonce, even if React escaping is bypassed via `dangerouslySetInnerHTML`.
  - **Verification:** Inject `<img src=x onerror=alert(1)>` via an input field — confirm no execution. Run `pytest tests/ -k "xss"` (12 tests).
  - **Severity:** Critical
  - **Reference:** `SECURITY_ARCHITECTURE.md §9.3`

- [ ] **Secure form validation (Zod schemas)**
  - **Description:** Frontend uses Zod schemas for runtime response validation via `parseApiResponse()`. Catches contract drift between frontend and backend. Invalid data is rejected before rendering, preventing type-confusion-based attacks.
  - **Verification:** Modify an API response to return unexpected types — confirm `parseApiResponse()` throws and UI shows error state.
  - **Severity:** Medium
  - **Reference:** `SECURITY_ARCHITECTURE.md §5.2`

- [ ] **Session expiry handling with redirect**
  - **Description:** `handleUnauthorizedSession()` debounces concurrent 401 responses, calls `supabase.auth.signOut({ scope: 'local' })`, wipes Supabase cookies from localStorage/sessionStorage, dispatches `scholarform:session-expired` custom event, and redirects to `/login?next={currentPath}`.
  - **Verification:** Expire the session token — confirm redirect to `/login?next=/dashboard`. Confirm return URL is preserved after re-login.
  - **Severity:** High
  - **Reference:** `SECURITY_ARCHITECTURE.md §3.3`

---

## Infrastructure Security

Controls for container security, dependency management, and CI/CD hardening.

- [ ] **Docker: non-root user, minimal base images**
  - **Description:** Backend images use `python:3.12-slim` for minimal attack surface. Containers run as a non-privileged user (no `USER root`). No secrets embedded in images — all secrets injected at runtime via environment variables.
  - **Verification:** `docker inspect ghcr.io/scholarform/backend:latest | jq '.[0].Config.User'` — confirm non-root. Review Dockerfile for `USER` directive and base image choice.
  - **Severity:** High
  - **Reference:** `SECURITY_ARCHITECTURE.md §10.1`

- [ ] **Dependency scanning: Dependabot, Renovate, pip-audit, npm audit**
  - **Description:** Dependabot runs continuously with auto-PR for vulnerable dependencies. Renovate updates weekly. CI runs `pip-audit` and `npm audit` on every push to detect new CVEs. All dependency versions pinned in `requirements.txt` and `package-lock.json` with integrity hashes.
  - **Verification:** Inspect GitHub → Security → Dependabot for active alerts. Check CI logs for `pip-audit` and `npm audit` steps. Confirm zero open CVEs.
  - **Severity:** High
  - **Reference:** `SECURITY_ARCHITECTURE.md §10.2`

- [ ] **SBOM generation and tracking**
  - **Description:** SPDX 2.3 bill of materials is generated every release via GitHub Actions. SBOM lists all dependencies with versions, licenses, and checksums. Published alongside release artifacts.
  - **Verification:** Check the latest release on GitHub for an SBOM attachment. Validate with `cyclonedx-cli validate`.
  - **Severity:** Medium
  - **Reference:** `SECURITY_ARCHITECTURE.md §10.2`

- [ ] **SLSA Level 3 attestation for releases**
  - **Description:** Hermetic builds in ephemeral CI environments with signed provenance attestations available on every GitHub Release. Verification via `gh attestation verify ghcr.io/scholarform/backend:1.0.0 --repo rohitkumarnaidu/ScholarFormAI`.
  - **Verification:** Run the `gh attestation verify` command against the latest release — confirm provenance passes.
  - **Severity:** High
  - **Reference:** `SECURITY.md §SLSA`, `SECURITY_ARCHITECTURE.md §11`

- [ ] **CodeQL analysis for Python + JavaScript**
  - **Description:** CodeQL runs on every push to `main` and every PR, analyzing both Python (`.github/workflows/codeql.yml`) and JavaScript/TypeScript code paths. Results surface in GitHub Security → Code Scanning.
  - **Verification:** Check GitHub → Security → Code Scanning — confirm zero open alerts on `main`.
  - **Severity:** High
  - **Reference:** `SECURITY_ARCHITECTURE.md §10.3`

- [ ] **Trivy filesystem scanning**
  - **Description:** Trivy scans all Docker images for CRITICAL and HIGH CVEs on every build. Failures block the CI pipeline. Scans cover OS packages (Debian) and language-specific dependencies (pip, npm).
  - **Verification:** Review CI logs for Trivy scan output. Confirm blocking on CRITICAL/HIGH findings.
  - **Severity:** High
  - **Reference:** `SECURITY_ARCHITECTURE.md §10.2`

- [ ] **Cosign container image signing**
  - **Description:** All `ghcr.io` container images are signed with Cosign keyless OIDC signing. Signatures provide verifiable artifact integrity. Verification: `cosign verify ghcr.io/scholarform/backend:1.0.0`.
  - **Verification:** Run `cosign verify` against the latest published image — confirm valid signature.
  - **Severity:** Medium
  - **Reference:** `SECURITY_ARCHITECTURE.md §10.1`

---

## Webhook Security

Controls for outbound webhook authenticity, replay prevention, and delivery reliability.

- [ ] **HMAC-SHA256 signature verification**
  - **Description:** Outgoing webhooks are signed with HMAC-SHA256 using the subscription's secret. Signature sent in `X-Webhook-Signature` header. Stripe webhooks verified via `stripe.Webhook.construct_event()`. Invalid signatures logged to audit trail (`backend/app/services/webhook_service.py:181–186`).
  - **Verification:** Intercept a webhook delivery — modify the payload and replay — confirm HMAC verification fails. Run `pytest tests/ -k "webhook_signature"`.
  - **Severity:** Critical
  - **Reference:** `SECURITY_ARCHITECTURE.md §7.1`

- [ ] **Replay attack prevention (timestamp window)**
  - **Description:** Webhook delivery uses exponential backoff (`min(2^attempt * 60, 3600)` seconds, 3 max attempts). `next_retry_at` field enables monitoring of delivery health. Timestamp window prevents replay of old events.
  - **Verification:** Replay an expired webhook event — confirm rejection. Run `pytest tests/ -k "webhook_replay"`.
  - **Severity:** High
  - **Reference:** `SECURITY_ARCHITECTURE.md §7.2`

- [ ] **Origin validation**
  - **Description:** Webhook delivery uses `User-Agent: ScholarForm-Webhook/1.0` header. Subscription verification restricts dispatch to user-owned subscriptions only (`user_id` scoping prevents cross-user webhook manipulation).
  - **Verification:** Attempt to register a webhook for another user's subscription — confirm HTTP 403.
  - **Severity:** High
  - **Reference:** `SECURITY_ARCHITECTURE.md §7.3`

- [ ] **Retry with exponential backoff**
  - **Description:** Failed deliveries retry with exponential backoff capped at 3600 seconds. Maximum 3 delivery attempts. Delivery logs persist status, response code, and timestamp for audit. Failed deliveries are queryable for external monitoring.
  - **Verification:** Configure a dead webhook endpoint — confirm 3 retries with increasing delays. Run `pytest tests/ -k "webhook_retry"`.
  - **Severity:** Medium
  - **Reference:** `SECURITY_ARCHITECTURE.md §7.2`

---

## Incident Response

Controls for vulnerability reporting, disclosure process, and audit trail.

- [ ] **Security vulnerability reporting process (SECURITY.md)**
  - **Description:** Public `SECURITY.md` documents the reporting process: email `security@scholarform.ai` (PGP-encrypted), response SLA, disclosure timeline, and out-of-scope items. `security.txt` at `/.well-known/security.txt` follows RFC 9116.
  - **Verification:** Confirm `https://scholarform.com/.well-known/security.txt` resolves. Confirm `SECURITY.md` exists at repository root.
  - **Severity:** High
  - **Reference:** `SECURITY.md §Reporting a Vulnerability`

- [ ] **24h acknowledgement SLA for critical reports**
  - **Description:** Engineering team acknowledges security reports within 24 hours. Initial triage within 48 hours. Critical fixes deployed within 7 days from report. Scope: web app, API endpoints, auth mechanisms, file upload pipeline, template engine, third-party integrations.
  - **Verification:** Submit a test report to `security@scholarform.ai` — confirm automated acknowledgement within 24h. Review `SECURITY.md §Response SLA`.
  - **Severity:** High
  - **Reference:** `SECURITY.md §Response SLA`

- [ ] **CVE disclosure process**
  - **Description:** Confirmed vulnerabilities follow: GitHub Security Advisory (draft) → CVE ID via GitHub CNA → fix deployment → public disclosure. Critical/high CVEs disclosed after 60 days; medium after 90; low after 120. Published CVEs listed in `SECURITY.md`.
  - **Verification:** Review the CVE advisory workflow in `.github/workflows/`. Confirm GHSA creation steps documented.
  - **Severity:** Medium
  - **Reference:** `SECURITY.md §CVE Process`

- [ ] **Audit logging for write operations**
  - **Description:** Every HTTP write (POST, PUT, DELETE, PATCH) is asynchronously logged via `AuditLogService` with request method, path, status code, and authenticated user. Errors in audit logging are caught and do not affect the response (`backend/app/main.py:750–761`).
  - **Verification:** Perform a write operation — confirm an audit log entry with `request_id`, `user_id`, method, path, and timestamp. Run `pytest tests/ -k "audit"`.
  - **Severity:** Medium
  - **Reference:** `SECURITY_ARCHITECTURE.md §2.11`

---

## Compliance

Controls for supply-chain security, license management, and legal attribution.

- [ ] **OpenSSF Scorecard passing (10/10 on 14 of 16 checks)**
  - **Description:** The repository is evaluated weekly by OpenSSF Scorecard. 14 of 16 checks score 10/10. Known gaps: Contributors (5/10 — single contributor), Fuzzing (0/10 — not implemented). Binary Artifacts, Branch Protection, CI Tests, Code Review, Dependency Update Tool, License, Maintained, Packaging, Pinned Dependencies, SAST, Security Policy, Signed Releases, Token Permissions, Vulnerabilities all at 10/10.
  - **Verification:** Check the Scorecard badge in `SECURITY.md` or run `npx openssf-scorecard --repo=github.com/rohitkumarnaidu/ScholarFormAI`.
  - **Severity:** Medium
  - **Reference:** `SECURITY.md §OpenSSF Scorecard`

- [ ] **SLSA Level 3**
  - **Description:** All releases meet SLSA Level 3 requirements: hermetic builds in ephemeral CI environments, signed provenance attestations, no user-defined build steps. Verified via `gh attestation verify`.
  - **Verification:** `gh attestation verify ghcr.io/scholarform/backend:<tag> --repo rohitkumarnaidu/ScholarFormAI` — confirm Level 3 attestation.
  - **Severity:** High
  - **Reference:** `SECURITY.md §SLSA`

- [ ] **FOSSA license compliance**
  - **Description:** Weekly FOSSA scans check all dependencies for license compliance. Results published in the repository. Prohibited licenses (AGPL, non-commercial) trigger blocking alerts.
  - **Verification:** Check FOSSA dashboard for active license issues. Confirm zero prohibited licenses.
  - **Severity:** Medium
  - **Reference:** `SECURITY_ARCHITECTURE.md §10.2`

- [ ] **SPDX license headers on all source files**
  - **Description:** Every source file begins with `<!-- SPDX-License-Identifier: MIT -->` and `<!-- Copyright (c) 2026 ScholarForm AI -->`. Enforced via pre-commit hook and linting.
  - **Verification:** Run `grep -rL "SPDX-License-Identifier" backend/ frontend/` — confirm no files missing the header.
  - **Severity:** Low
  - **Reference:** `CODING_STANDARDS.md`

---

## Scoring Methodology

| Category | Items | Checked | Score |
|----------|-------|---------|-------|
| Authentication & Authorization | 6 | __ / 6 | __ % |
| Network Security | 6 | __ / 6 | __ % |
| Data Protection | 6 | __ / 6 | __ % |
| API Security | 6 | __ / 6 | __ % |
| LLM Security | 4 | __ / 4 | __ % |
| Frontend Security | 5 | __ / 5 | __ % |
| Infrastructure Security | 7 | __ / 7 | __ % |
| Webhook Security | 4 | __ / 4 | __ % |
| Incident Response | 4 | __ / 4 | __ % |
| Compliance | 4 | __ / 4 | __ % |
| **Total** | **52** | **__ / 52** | **__ %** |

**Scoring tiers:**

| Score | Rating | Action |
|-------|--------|--------|
| 100% | ✅ **Pass** | All controls verified. Ready for audit. |
| 90–99% | ⚠️ **At Risk** | One or more controls unverified. Schedule verification. |
| 75–89% | 🔴 **Degraded** | Multiple controls missing. Block production deployment. |
| < 75% | ❌ **Failing** | Significant security gaps. Immediate remediation required. |

**To use:** Open this file, replace each `[ ]` with `[x]` for verified items, count the checks per category, and fill in the scoring table.

---

*Review cadence: Quarterly. Next review: October 2026.*
*Maintained by the ScholarForm AI Security Team.*
