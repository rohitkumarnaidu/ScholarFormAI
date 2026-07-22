<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — FRS & SRS Documentation
description: Functional requirements specification and software requirements specification
sidebar_position: 56
version: "1.0"
status: ✅ Complete
owner: Product Team
review_cadence: annually
last_updated: July 2026
---

# ScholarForm AI — FRS & SRS Documentation

## Document Control
- Document Title: ScholarForm AI Application Documentation, FRS, and SRS
- Product: Automated Academic Docx Manuscript Formatter
- Version: 1.0 (Audit Baseline)
- Date: February 28, 2026
- Prepared For: Product, Engineering, QA, and Operations teams
- Prepared By: Codex codebase audit synthesis

## Table of Contents
- [1. Executive Summary](#1-executive-summary)
- [2. Scope and Audit Basis](#2-scope-and-audit-basis)
- [3. Product Overview](#3-product-overview)
- [4. System Architecture](#4-system-architecture)
- [5. End-to-End Functional Flow](#5-end-to-end-functional-flow)
- [6. Supported Formats and Options](#6-supported-formats-and-options)
- [7. Template Coverage](#7-template-coverage-and-formatting-capability)
- [8. API Surface Summary](#8-api-surface-summary)
- [9. Data Model Summary](#9-data-model-summary)
- [10. Security and Reliability Controls](#10-security-and-reliability-controls)
- [11. Testing and Quality](#11-testing-and-quality)
- [12. Known Integration Gaps](#12-known-integration-gaps-and-risks-high-priority)
- [13. Future Scope](#13-future-scope-and-product-direction)
- [14. Functional Requirements](#14-functional-requirements-specification-frs)
- [15. System Requirements](#15-system-requirements-specification-srs)
- [16. FRS-SRS Traceability](#16-frs-srs-traceability-matrix-condensed)
- [17. Production-Readiness Backlog](#17-production-readiness-improvement-backlog)

## 1. Executive Summary
ScholarForm AI is a full-stack academic manuscript processing platform with a React frontend and a FastAPI backend. The system accepts multiple manuscript input formats, applies template-driven formatting rules, runs AI-assisted analysis, and exports publication-ready outputs.

Current implementation is strong on pipeline breadth and template infrastructure. Core user flow (upload -> processing -> preview/compare -> download) is implemented. Auth, history, batch upload, metrics, feedback, and custom-template APIs are also present.

Important finding: the product is not realistically "100 percent" for every possible document and every template in all conditions. The platform is close to production capability but still has integration mismatches and UX consistency gaps that should be closed before enterprise release.

## 2. Scope and Audit Basis
This documentation is based on repository source inspection and direct checks completed on February 28, 2026.

### 2.1 Verified inputs used for this pack
- Backend source under `backend/app`
- Frontend source under `frontend/src`
- Existing docs under `docs/` and `backend/docs/`
- Template contracts and DOCX template assets
- Schema and migrations
- Existing audit reports in workspace root

### 2.2 Verified file inventory snapshot
- Total filtered files (excluding heavy caches/vendor): 1345
- Backend filtered files: 1216
- Frontend filtered files: 95
- `backend/app`: 210 files
- `backend/tests`: 83 files
- `frontend/src`: 84 files
- `frontend/src/test`: 19 files

### 2.3 Verified template integrity checks
- Built-in template folders: 15
- `template.docx` present: 15/15
- `contract.yaml` present: 15/15
- `styles.csl` present: 11/15
- Template marker verification script result: all 15 templates valid
- `layout:` block check: all real template contracts contain `layout` (both template contracts and pipeline contracts)

## 3. Product Overview
ScholarForm AI provides automated formatting and validation of academic manuscripts.

### 3.1 Primary value proposition
- Convert manuscript drafts into template-compliant outputs quickly
- Support common publication styles (IEEE, APA, Springer, etc.)
- Preserve a reviewable workflow with status, preview, compare, and edit pass
- Support both guest flow and authenticated account flow

### 3.2 Supported user roles
- Guest user: can use upload flow without account for basic processing
- Authenticated user: history, saved jobs, profile, feedback, custom templates
- Admin user: metrics and health dashboard APIs

## 4. System Architecture

### 4.1 High-level components
- Frontend: React 19, Next.js 16 (App Router), Tailwind CSS
- Backend: FastAPI, Supabase integration, pipeline orchestrator
- Data store: Supabase Postgres tables (`documents`, `document_results`, `processing_status`, etc.)
- AI/ML services: SciBERT, RAG engine, reasoning engine (NVIDIA and local fallback paths)
- External processors: LibreOffice, Pandoc, GROBID, Docling, OCR paths
- Real-time updates: SSE endpoint with Redis Pub/Sub support

### 4.2 Backend module distribution (key)
- `pipeline`: 114 files
- `templates`: 41 files
- `models`: 13 files
- `services`: 10 files
- `routers`: 7 files

### 4.3 Frontend architecture highlights
- Route-based lazy loading in `App.jsx`
- Context providers: Auth, Document, Theme, Toast
- Shared app navbar with role-aware links and responsive states
- Upload workflow split into focused components (`CategoryTabs`, `TemplateSelector`, `FormattingOptions`, `ProcessingStepper`)

## 5. End-to-End Functional Flow

### 5.1 Upload and processing flow
1. User uploads file (single or chunked path for large uploads).
2. Backend validates extension, content signature, and size constraints.
3. Job record created in `documents`.
4. Background task starts orchestrator pipeline.
5. Pipeline runs extraction, structure, NLP analysis, validation, formatting, export, persistence.
6. User polls status and views progress.
7. User reviews preview/compare and downloads output.

### 5.2 Edit flow
1. User submits edited structured payload.
2. Backend reruns validation and formatting.
3. New output is generated and versions can be persisted.

### 5.3 Batch upload flow
- Authenticated users can upload multiple files in a single batch call.
- Batch size and daily quota constraints are enforced.

## 6. Supported Formats and Options

### 6.1 Accepted input formats (validated in router + converter)
- `.docx`, `.doc`, `.pdf`, `.odt`, `.rtf`, `.tex`, `.txt`, `.html`, `.htm`, `.md`, `.markdown`

### 6.2 Conversion strategies
- Native pass-through for `.docx`
- LibreOffice for `.doc`, `.odt`, `.rtf`, and PDF conversion paths
- Pandoc for `.md`, `.html`, `.txt`, `.tex`
- OCR-assisted fallback for PDFs when required

### 6.3 User formatting options exposed in upload UI
- Add page numbers
- Add borders
- Add cover page
- Generate table of contents
- Add line numbers (supported backend option)
- Page size (Letter, A4, Legal)
- Fast mode toggle

### 6.4 Output formats
- Download endpoint supports: `docx`, `pdf`
- Exporter can also produce side artifacts (`json`, `markdown`, `html`, `latex`, `xml` JATS) based on runtime options

## 7. Template Coverage and Formatting Capability

### 7.1 Built-in templates
`acm`, `apa`, `chicago`, `elsevier`, `harvard`, `ieee`, `mla`, `modern_blue`, `modern_gold`, `modern_red`, `nature`, `none`, `numeric`, `springer`, `vancouver`

### 7.2 What is verified as implemented
- Template DOCX files exist for all templates
- Jinja marker validation exists and passes for all templates
- Contract `layout` exists for all templates
- Formatter supports page size, margins, global line spacing, page numbers, borders, line numbers, TOC insertion, and cover page/front matter logic
- Figures and tables have dedicated extraction/matching/rendering modules

### 7.3 Reality check on "100 percent formatting"
A claim of universal 100 percent formatting quality across all possible inputs is not technically defensible without formal corpus-based benchmark evidence. What is true now:
- Core formatting features are implemented and available
- Template infrastructure is present and internally consistent
- Real-world edge-case variance still exists (complex PDFs, malformed docs, missing external dependencies, and integration mismatches)

## 8. API Surface Summary

### 8.1 Auth router (`/api/auth`)
- `GET /me`
- `POST /signup`
- `POST /login`
- `POST /forgot-password`
- `POST /verify-otp`
- `POST /reset-password`

### 8.2 Documents router (`/api/documents`)
- `POST /upload/chunked`
- `GET /`
- `POST /upload`
- `GET /{job_id}/status`
- `GET /{job_id}/summary`
- `POST /{job_id}/edit`
- `GET /{job_id}/preview`
- `GET /{job_id}/compare`
- `GET /{job_id}/download`
- `DELETE /{job_id}`
- `POST /batch-upload`

### 8.3 Templates router (`/api/templates`)
- `GET /`
- `GET /csl/search`
- `GET /csl/fetch`
- `GET /custom`
- `POST /custom`
- `PUT /custom/{template_id}`
- `DELETE /custom/{template_id}`

### 8.4 Other routers
- Metrics: `/api/metrics/*`
- Feedback: `/api/feedback/*`
- Stream SSE: `/api/stream/{job_id}`

## 9. Data Model Summary

### 9.1 Core tables (from schema)
- `profiles`
- `documents`
- `document_versions`
- `document_results`
- `processing_status`
- `model_metrics`

### 9.2 Document lifecycle fields
- `documents.status`, `progress`, `current_stage`, `error_message`, `output_path`, `formatting_options`
- `processing_status` tracks per-phase status
- `document_results` stores structured and validation outputs

### 9.3 Pipeline in-memory model
`PipelineDocument` contains blocks, figures, tables, references, equations, metadata, template info, validation state, review metadata, generated artifact pointer, and processing history.

## 10. Security and Reliability Controls

### 10.1 Implemented controls
- Auth token decode and identity dependency guards
- Optional auth mode for guest-capable endpoints
- CORS controls
- Security headers middleware (CSP, frame deny, etc.)
- Max body size middleware
- Rate limit middleware with optional Redis acceleration
- File extension + magic-byte validation
- Path traversal checks in upload paths
- Background timeout wrapper for pipeline execution
- Graceful startup degraded mode when dependencies are unavailable

### 10.2 Reliability features
- Pipeline semaphore to cap concurrent jobs
- Retry wrappers and safe execution guards
- Partial result persistence on failure
- Output hash persistence attempts (with backward compatibility when schema columns are absent)
- SSE keepalive behavior when Redis not available

## 11. Testing and Quality

### 11.1 Present test footprint
- Backend tests: 80+ files including unit, integration, safety, endpoint, and pipeline tests
- Frontend tests: route/component/auth/upload/download and error boundary tests

### 11.2 Current audit limitation
This documentation pass is source-based verification. Full runtime validation of every requirement needs CI evidence, integration environment checks, and test execution reports for the current branch and environment.

## 12. Known Integration Gaps and Risks (High Priority)

### 12.1 API contract mismatches
- Built-in templates response shape mismatch risk:
  - Backend `GET /api/templates/` returns `{ templates: [...] }`
  - Frontend template loader path currently treats response as array in one code path
- CSL search mismatch risk:
  - Backend returns `{ query, results }`
  - Frontend search handler currently expects array in one code path
- CSL fetch method mismatch risk:
  - Backend defines `GET /api/templates/csl/fetch?slug=...`
  - Frontend helper currently sends `POST /api/templates/csl/fetch`
- JATS download mismatch risk:
  - Frontend calls `/api/jobs/{id}/download?format=jats`
  - No matching backend router endpoint exists

### 12.2 UX consistency concerns
- Logged-in navbar behavior and "More" menu interactions need additional QA on breakpoints and click-away states.
- Upload screen spacing and hierarchy have improved but still need final production polish pass across viewport sizes.

### 12.3 Operational risks
- Repository contains many generated/manual artifacts that should be separated from production source packaging.
- Very large dependency surface in backend requirements increases maintenance and security scanning load.

## 13. Future Scope and Product Direction

### 13.1 User-priority future items (captured from request context)
- Keep `.doc` support as critical path and continuously harden it
- Improve formatting fidelity for all templates and input variants
- Ensure page numbers, line numbers, borders, cover page, tables, and images are consistently correct
- Raise UI/UX to production-level quality on all pages
- Improve logged-in navbar behavior and more-menu interaction quality

### 13.2 Assistant-priority future items
- Add contract tests that enforce frontend-backend API shape parity
- Add end-to-end golden document corpus for template fidelity regression (per template, per format)
- Add formal quality score gate in CI for formatting output checks
- Add explicit JATS API endpoint or remove unsupported UI option
- Add OpenAPI-generated typed client for frontend to reduce contract drift
- Add automated visual regression for navbar and upload flows

## 14. Functional Requirements Specification (FRS)

### 14.1 FRS purpose
Defines what the system must do from business and user perspective.

### 14.2 FRS assumptions
- Supabase credentials are configured in deployment
- External processors (LibreOffice/Pandoc/OCR dependencies) are installed for full format support
- User has modern browser for frontend flow

### 14.3 Functional requirements

- FR-001 User Authentication
  - Description: System shall support signup, login, token-based authenticated access, and logout.
  - Priority: High
  - Acceptance: Auth endpoints return valid session or clear error; protected routes enforce auth.

- FR-002 Password Recovery
  - Description: System shall support forgot password, OTP verify, and reset password.
  - Priority: High
  - Acceptance: User can reset password using OTP flow.

- FR-003 Single File Upload
  - Description: System shall accept supported manuscript formats and create a processing job.
  - Priority: High
  - Acceptance: Upload endpoint returns job_id and processing starts.

- FR-004 Chunked Upload for Large Files
  - Description: System shall support chunk-based upload with reassembly and validation.
  - Priority: High
  - Acceptance: Large file upload completes and yields a valid job.

- FR-005 File Validation
  - Description: System shall enforce extension allowlist, magic-byte checks, size limits, and path safety.
  - Priority: High
  - Acceptance: Invalid files are rejected with 4xx error and clear message.

- FR-006 Template Selection
  - Description: System shall allow selecting built-in templates and default none/general formatting.
  - Priority: High
  - Acceptance: Selected template is persisted in job options and applied in formatting stage.

- FR-007 Formatting Options
  - Description: System shall support page numbers, borders, cover page, TOC, line numbers, line spacing, and page size options.
  - Priority: High
  - Acceptance: Option flags are accepted by API and reflected in output artifact where supported.

- FR-008 Pipeline Processing
  - Description: System shall run extraction, analysis, validation, formatting, and persistence phases.
  - Priority: High
  - Acceptance: Status progresses through expected phases and final status is terminal.

- FR-009 Status Tracking
  - Description: System shall provide status endpoint with progress and phase detail.
  - Priority: High
  - Acceptance: Client can poll and render current progress state.

- FR-010 Preview Retrieval
  - Description: System shall provide structured result and validation data for preview.
  - Priority: Medium
  - Acceptance: Preview endpoint returns data for completed jobs.

- FR-011 Comparison Retrieval
  - Description: System shall provide original vs formatted comparison payload.
  - Priority: Medium
  - Acceptance: Compare endpoint returns payload for UI diff rendering.

- FR-012 Edit and Reformat
  - Description: System shall accept edited structured data and rerun validation/formatting.
  - Priority: Medium
  - Acceptance: Edit endpoint returns processing status and updated output path.

- FR-013 Download Export
  - Description: System shall provide downloadable formatted outputs (DOCX and PDF).
  - Priority: High
  - Acceptance: Download endpoint streams requested supported format.

- FR-014 Document History
  - Description: Authenticated users shall list and manage previous jobs.
  - Priority: Medium
  - Acceptance: List and delete operations work with ownership checks.

- FR-015 Batch Upload
  - Description: Authenticated users shall upload multiple files in one request.
  - Priority: Medium
  - Acceptance: Batch endpoint processes each file and returns job summary.

- FR-016 Feedback Collection
  - Description: Users shall submit correction feedback for model improvement loops.
  - Priority: Medium
  - Acceptance: Feedback endpoint stores data (memory plus DB attempt).

- FR-017 Custom Template Management
  - Description: Authenticated users shall create/read/update/delete custom templates.
  - Priority: Medium
  - Acceptance: CRUD endpoints enforce auth and ownership.

- FR-018 Metrics and Admin Health
  - Description: Admin users shall access system metrics and health dashboards.
  - Priority: Medium
  - Acceptance: Admin endpoints require admin and return observability data.

- FR-019 Frontend Error Logging
  - Description: Frontend shall send client-side error events to backend metrics logger.
  - Priority: Medium
  - Acceptance: `log-error` endpoint receives and records errors.

- FR-020 Access Control and Ownership
  - Description: System shall prevent unauthorized access to other users' jobs.
  - Priority: High
  - Acceptance: Unauthorized reads/edits/downloads return 403.

## 15. System Requirements Specification (SRS)

### 15.1 SRS purpose
Defines technical system requirements needed to satisfy FRS.

### 15.2 External interfaces

#### 15.2.1 User interface requirements
- UI shall provide responsive routes for guest and authenticated workflows.
- UI shall support upload drag-drop and browse controls.
- UI shall display processing progress and phase-based stepper state.
- UI shall provide preview, compare, edit, download, history, templates, profile, and settings pages.

#### 15.2.2 API interface requirements
- Backend shall expose REST endpoints under `/api/*` for auth, documents, templates, feedback, metrics, and stream.
- API shall return structured JSON responses with meaningful status codes.
- Protected endpoints shall require bearer token auth.

#### 15.2.3 Data interface requirements
- Backend shall use Supabase Postgres for persistence of documents and processing metadata.
- Schema shall include unique constraints supporting upsert patterns for document results and processing phase rows.

#### 15.2.4 External service interfaces
- Optional or required integrations include Supabase, LibreOffice, Pandoc, GROBID, Docling, Redis, and model endpoints.

### 15.3 Functional system requirements
- SR-FUNC-001: Request validation and auth dependencies must execute before business logic.
- SR-FUNC-002: File processing must run asynchronously from upload request.
- SR-FUNC-003: Pipeline must publish status updates and persist final state.
- SR-FUNC-004: Formatter must load template contract and apply style/layout mappings.
- SR-FUNC-005: Exporter must persist DOCX and optional side outputs.

### 15.4 Non-functional requirements

- SR-NFR-001 Performance
  - Normal upload request should return quickly with job id; long processing runs in background.
  - Status polling should be lightweight and safe at 2s client interval.

- SR-NFR-002 Scalability
  - Pipeline execution concurrency should be bounded to avoid resource exhaustion.
  - Rate limiting should protect API from burst abuse.

- SR-NFR-003 Reliability
  - Background tasks should have timeout guards.
  - Pipeline failures should mark job status clearly and preserve partial insights when possible.

- SR-NFR-004 Security
  - Enforce JWT-based auth for protected resources.
  - Apply secure headers and body size limits.
  - Validate file signatures and block path traversal vectors.

- SR-NFR-005 Maintainability
  - Code should keep contract mappings explicit (`contract.yaml`) and formatter logic centralized.
  - API contracts should be type-safe and synchronized with frontend.

- SR-NFR-006 Observability
  - Metrics and health endpoints should provide DB/model/service status.
  - Frontend error telemetry should feed backend logs.

- SR-NFR-007 Usability
  - Upload flow must remain clear for both guest and authenticated users.
  - Error messages must be user-friendly and context-specific (for example login credential errors).

### 15.5 Constraints
- Full fidelity of complex document rendering depends on external converters and source-file quality.
- Some advanced exports are generated internally but not yet fully exposed through API download contracts.

### 15.6 Verification strategy
- Unit tests for router/services/pipeline components
- Integration tests for end-to-end processing paths
- Golden-file regression for template outputs
- Frontend component and route tests
- Contract tests to enforce API response shapes

## 16. FRS-SRS Traceability Matrix (Condensed)

- FR-001 -> SR-FUNC-001, SR-NFR-004
- FR-003/FR-004/FR-005 -> SR-FUNC-001, SR-FUNC-002, SR-NFR-001, SR-NFR-004
- FR-006/FR-007/FR-008 -> SR-FUNC-003, SR-FUNC-004
- FR-009/FR-010/FR-011 -> SR-FUNC-003, SR-NFR-006, SR-NFR-007
- FR-012 -> SR-FUNC-003, SR-FUNC-004, SR-NFR-003
- FR-013 -> SR-FUNC-005, SR-NFR-001
- FR-014/FR-020 -> SR-FUNC-001, SR-NFR-004
- FR-015 -> SR-FUNC-002, SR-NFR-001, SR-NFR-002
- FR-016/FR-018/FR-019 -> SR-NFR-006, SR-NFR-005

## 17. Production-Readiness Improvement Backlog

### 17.1 P0 (Immediate)
- Fix API contract mismatches for templates and CSL endpoints.
- Implement or remove JATS UI download path mismatch.
- Add strict frontend-backend contract tests for key routes.
- Complete navbar logged-in behavior QA and fix responsive More-menu edge cases.

### 17.2 P1 (Next Sprint)
- Build golden document benchmark suite for all 15 templates and major input formats.
- Add automated visual regression checks for Upload, Templates, Navbar, and Download pages.
- Reduce stale artifacts from source tree and formalize release packaging rules.

### 17.3 P2 (Roadmap)
- Add richer template authoring workflow and validation UI.
- Add enterprise audit logs, policy controls, and SOC-style operational reporting.
- Add smart retry orchestration with dependency-aware circuit feedback dashboards.

## 18. Delivery Notes
- This document pack intentionally includes both product-level and engineering-level detail.
- It is designed to be used directly in stakeholder reviews, sprint planning, QA planning, and release readiness reviews.
- For board/client-ready format, use this as source and generate a branded version with approved typography and identity.

## Appendix A: Verified Evidence Snippets
- Template marker script result: all 15 templates valid
- Layout checks: all template and pipeline contracts include `layout`
- Upload acceptance includes `.doc` and converter strategy includes LibreOffice path for `.doc`
- Login error mapping now supports specific message for `/api/auth/login` invalid credential 401 while preserving session-expired message for other 401s

## Appendix B: Recommended Next Document Set
- PRD (Product Requirements Document) linked to this FRS/SRS
- UAT test specification derived from FR IDs
- Operations Runbook (incident, rollback, degraded mode)
- Security baseline and threat model
- API contract reference generated from OpenAPI schema
