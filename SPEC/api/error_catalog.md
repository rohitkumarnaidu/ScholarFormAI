<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# ScholarForm AI — Machine Error Catalog & HTTP Status Specification (`SPEC`)

> **AUTHORITATIVE ERROR CODE SPECIFICATION**  
> This catalog specifies the normative machine error codes, HTTP status mappings, and domain exception catalogs.  
> Ground truth derived directly from `backend/app/common/constants.py` and `backend/app/core/errors.py`.

---

## 1. Top-Level HTTP Status to Machine Error Mapping

Every HTTP status code produced by the ScholarForm AI API maps to a default machine code in the response envelope:

| HTTP Status | Default Error Code (`constants.py`) | Description |
| :---: | :--- | :--- |
| **400** | `BAD_REQUEST` | Malformed request syntax or unparseable input. |
| **401** | `UNAUTHORIZED` | Missing, expired, or invalid bearer token / API key. |
| **403** | `FORBIDDEN` | Valid authentication but insufficient permissions for resource. |
| **404** | `NOT_FOUND` | Document, job, template, or entity ID does not exist. |
| **409** | `CONFLICT` | Resource state conflict (e.g. duplicate upload, concurrent job). |
| **413** | `PAYLOAD_TOO_LARGE` | Uploaded manuscript exceeds the maximum allowed file size. |
| **422** | `VALIDATION_ERROR` | Schema validation failed against Pydantic request models. |
| **429** | `RATE_LIMITED` | Request exceeds user tier rate limit or global threshold. |
| **500** | `INTERNAL_SERVER_ERROR` | Unhandled server exception during pipeline processing. |
| **501** | `NOT_IMPLEMENTED` | Endpoint or capability requested is not implemented. |
| **502** | `BAD_GATEWAY` | External upstream service (GROBID, LibreOffice converter) failed. |
| **503** | `SERVICE_UNAVAILABLE` | Database or critical AI model provider unreachable. |

---

## 2. Core Domain Error Catalog (`core/errors.py`)

Fine-grained exceptions raised in pipeline processing or business logic carry specific string codes:

### Manuscript & Ingestion Errors
- `UNSUPPORTED_FORMAT`: Input file is not a supported format (DOCX, PDF, Markdown, LaTeX).
- `MANUSCRIPT_TOO_LARGE`: Manuscript exceeds token or byte quota.
- `UNSUPPORTED_CONTENT_TYPE`: MIME type not accepted by upload handler.
- `MISSING_TITLE`: Mandatory title block not found during structural parsing.
- `MISSING_AUTHORS`: Author block missing in manuscript.
- `MISSING_ABSTRACT`: Abstract section missing for templates that mandate it.
- `TITLE_TOO_LONG`: Title length exceeds template constraint.
- `TOO_MANY_AUTHORS`: Author list exceeds template limit.
- `TOO_MANY_SECTIONS`: Section count exceeds allowable threshold.
- `SECTION_DEPTH_EXCEEDED`: Heading hierarchy deeper than supported template styles (e.g., > H4).

### Template & Formatting Errors
- `STYLE_NOT_FOUND`: Referenced template or CSL style definition does not exist.
- `FORMATTING_ERROR`: python-docx or pandoc AST formatting failed.
- `INVALID_PATH`: File path resolution failed inside template archive.

### Rate Limiting & Tier Errors
- `RATE_LIMIT_EXCEEDED`: User tier limit exceeded.
- `UPGRADE_REQUIRED`: Feature is restricted to Pro or Enterprise tiers.

---

## 3. Client Handling Invariants

1. **Machine Parsing:** Clients MUST inspect `error.code` for programmatic branching (e.g. redirecting to login on `UNAUTHORIZED`, displaying upgrade modal on `UPGRADE_REQUIRED`).
2. **Display Messages:** Clients MAY present `error.message` directly in toasts or banners.
3. **Traceability:** When reporting bugs or errors to support, clients MUST supply `request_id`.
