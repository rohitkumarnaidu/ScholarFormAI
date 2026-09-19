# Zero Trust Security Model — ScholarFormAI

## Principle

> **Never trust, always verify.**

Every request to the ScholarFormAI backend is treated as untrusted regardless of network location, IP address, frontend route guards, client-provided headers, or previously established sessions.

## Authentication Flow

1. **Token Extraction**: Bearer token from `Authorization` header (query parameter tokens explicitly rejected)
2. **Algorithm Check**: JWT header inspected — RS256/ES256 via JWKS, HS256 only when JWKS unavailable
3. **Signature Verification**: Cryptographic signature validated
4. **Claims Verification**: `exp`, `aud` ("authenticated"), `iss` (Supabase auth URL)
5. **Identity Extraction**: `sub` claim as user ID
6. **Role Derivation**: From JWT `role` claim + `app_metadata`

## Document Access Control

| Endpoint | Auth Required | Ownership Check | Rationale |
|----------|:---:|:---:|-----------|
| `POST /upload` | Optional | N/A | Try-before-signup flow |
| `GET /documents` | Optional | Scoped to user | Returns only user's own |
| `GET /{id}/status` | Optional | N/A | Anonymous status tracking |
| `GET /{id}/summary` | **Required** | **Yes** | Protected content |
| `POST /{id}/edit` | **Required** | **Yes** | Write operation |
| `GET /{id}/preview` | **Required** | **Yes** | Protected content |
| `GET /{id}/compare` | **Required** | **Yes** | Protected content |
| `GET /{id}/download` | **Required** | **Yes** | Protected content |
| `DELETE /{id}` | **Required** | **Yes** | Destructive operation |

## Security Controls

| Control | Implementation | Status |
|---------|---------------|--------|
| JWT Verification (JWKS) | `security/jwks_verifier.py` | ✅ |
| Algorithm Downgrade Prevention | HS256 blocked when JWKS available | ✅ |
| IDOR Prevention | Ownership + sharing checks | ✅ |
| Mass Assignment Prevention | Typed Pydantic schemas | ✅ |
| CSRF Protection | HMAC-signed timestamped tokens | ✅ |
| Rate Limiting | SlowAPI + custom middleware (multi-layer) | ✅ |
| Security Headers | CSP, HSTS, X-Frame-Options, etc. | ✅ |
| Max Body Size | 60MB streaming check | ✅ |
| Request ID Correlation | UUID per request | ✅ |
| Audit Logging | Write operations middleware | ✅ |
| Error Sanitization | No stack traces in responses | ✅ |
| HTTPS Enforcement | Production redirect + HSTS | ✅ |
