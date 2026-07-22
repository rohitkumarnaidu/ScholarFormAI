<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — Features List
description: Complete feature inventory with implementation status
sidebar_position: 52
version: "1.0"
status: 🔄 In Progress
owner: Docs Team
review_cadence: monthly
last_updated: July 2026
---

# ScholarForm AI — Features List

> **Codex Status Key:** ✅ Confirmed working | ⚠️ Files exist, needs runtime verification | ❌ Stub / not implemented  
> **Source:** Codex 5.4 Audit. Items marked TODO in earlier plans but **confirmed done** are now marked ✅.

> **See also:** [PRD](PRD.md), [Roadmap](Roadmap.md), [Testing](Testing.md)

---

## Table of Contents
- [Formatter Mode A (Upload & Format)](#formatter-mode-a-upload--format)
- [Formatter Mode B (Live Preview Editor)](#formatter-mode-b-live-preview-editor)
- [Generator Mode A (Multi-Doc Synthesis)](#generator-mode-a-multi-doc-synthesis)
- [Generator Mode B (AI Agent)](#generator-mode-b-ai-agent)
- [LLM & AI](#llm--ai)
- [Security & Auth](#security--auth)
- [UX & Design](#ux--design)
- [Billing](#billing)
- [CI/CD & DevOps](#cicd--devops)
- [Frontend Route Count](#frontend-route-count)

## Formatter Mode A (Upload & Format)

| Feature | Status | Notes |
|---------|--------|-------|
| 9-format file upload (DOCX, PDF, ODT, TeX, HTML, MD, TXT, RTF, DOC) | ✅ | MIME + magic byte + extension tri-validation |
| 12-stage processing pipeline | ✅ | Parse → Structure Detect → Block Classify → NLP → Validate → Format → Export |
| 17 journal templates | ✅ | Whitelist complete and validated in `document.py` (Codex-confirmed) |
| DOCX export | ✅ | Via python-docx + docxtpl |
| PDF export | ✅ | Via LibreOffice |
| LaTeX export | ❌ | `latex_exporter.py` is 743B stub — needs Pandoc subprocess |
| Processing stepper animation | ✅ | `Stepper.jsx` (10.4KB) |
| Quality score calculation | ✅ | `quality_score_service.py` (4.4KB) |
| Quality score display on results page | ⚠️ | Exists; needs browser-level verification |
| TipTap rich text editor on `/edit` | ✅ | **Codex-confirmed done** (was marked "needs verification" in earlier plans) |
| Batch upload (`BatchUploadPanel.jsx`) | ✅ | 9.7KB — wired and complete |
| Template editor save | ⚠️ | API connection needs runtime testing |

---

## Formatter Mode B (Live Preview Editor)

| Feature | Status | Notes |
|---------|--------|-------|
| WebSocket handler | ✅ | `preview.py` (7.4KB) |
| Preview renderer with cache | ✅ | `preview_renderer.py` (15.6KB) |
| Redis pub/sub realtime | ✅ | `pubsub.py`, `events.py` |
| `SplitEditor.jsx` | ✅ | 9.8KB |
| `PreviewPane.jsx` | ✅ | 3.5KB |
| `useLivePreviewSocket` hook | ✅ | 5.5KB |
| `/formatter/live` page | ✅ | Route live |
| AI sidebar | ⚠️ | Scaffolded; needs runtime testing |
| Violet accent drift in live preview | ⚠️🎨 | Codex finding: some components use `violet-*` tokens outside the blue design system — needs a design system style guide |

---

## Generator Mode A (Multi-Doc Synthesis)

| Feature | Status | Notes |
|---------|--------|-------|
| Session service | ✅ | `generator_session_service.py` (6.8KB) |
| Session vector store / ChromaDB RAG | ✅ | `session_vector_store.py` (7.8KB) |
| Synthesizer pipeline | ✅ | `synthesizer.py` (24.2KB) |
| SSE event streaming | ✅ | `v1/synthesis.py` (8.8KB) |
| `MultiUploadPanel.jsx` | ✅ | 11.4KB |
| `SynthesisStageTimeline.jsx` | ✅ | 6KB |
| `api.synthesis.js` (frontend API bridge) | ⚠️ | Was 36B stub — now wired via synthesis hooks |

---

## Generator Mode B (AI Agent)

| Feature | Status | Notes |
|---------|--------|-------|
| Task parser | ✅ | `task_parser.py` (6.2KB) |
| Agent pipeline | ✅ | `agent.py` (34KB) — most substantial backend file |
| Section prompts | ✅ | `section_prompts.py` (3.4KB) |
| Quality scorer | ✅ | `quality_scorer.py` (4.5KB) |
| Citation assembly | ✅ | `citation_assembly_service.py` (4.9KB) |
| `OutlineApproval.jsx` | ✅ | 10.7KB |
| `AgentChatPane.jsx` | ✅ | 11KB |
| `TokenStream.jsx` | ✅ | 11.3KB — rich token-streaming animations |
| `DocumentBuildPane.jsx` | ✅ | 6.6KB |
| `SessionHistory.jsx` | ✅ | 8KB |
| `/agent` page | ✅ | Route live |

---

## LLM & AI

| Feature | Status | Notes |
|---------|--------|-------|
| NVIDIA NIM (Tier 1) | ✅ | `llm_service.py` (15KB) |
| Groq fallback (Tier 2) | ✅ | **Codex-confirmed done** (was marked TODO in some plans) |
| Ollama / DeepSeek (Tier 3) | ✅ | Local offline fallback |
| LiteLLM abstraction | ✅ | Same client code across all providers |
| SciBERT classification | ⚠️ | Disabled by default (`USE_SCIBERT_CLASSIFICATION=false`) |
| ChromaDB RAG | ✅ | Properly implemented |

---

## Security & Auth

| Feature | Status | Notes |
|---------|--------|-------|
| Supabase Auth (JWT, OTP, OAuth Google/GitHub) | ✅ | |
| JWKS JWT verifier | ✅ | `jwks_verifier.py` (5.4KB) |
| Rate limiting (base) | ✅ | `rate_limit.py` (6.9KB) |
| Tier-aware rate limiting | ✅ | `tier_rate_limit.py` (4.1KB) |
| Security headers (CSP, HSTS) | ✅ | `security_headers.py` (4.6KB) |
| Abuse detection | ✅ | `abuse_detector.py` (2.7KB) |
| Virus scanning | ✅ | `virus_scanner.py` (4.4KB) — ClamAV |
| Request ID correlation | ✅ | `request_id.py` (2.2KB) |
| RBAC middleware | ⚠️ | `rbac.py` (708B) — stub, needs expansion |
| Audit logging | ⚠️ | `audit_log_service.py` (1.1KB) — minimal |

---

## UX & Design

| Feature | Status | Notes |
|---------|--------|-------|
| Dark/light mode | ✅ | `ThemeContext.jsx` (2.2KB) + `ThemeToggle` unified — **Codex-confirmed done** |
| Onboarding tour | ✅ | `OnboardingTour.jsx` (6.8KB) |
| Error boundary | ✅ | `ErrorBoundary.jsx` (3.6KB) |
| Icon system consistency | ⚠️ | Codex finding: inconsistent icon sets (lucide-react vs heroicons vs radix icons) — needs audit and consolidation |
| Design token documentation | ❌ | Tailwind config exists; semantic token guide is missing |
| `FeedbackForm.jsx` | ✅ | 8KB |
| Notification bell | ✅ | |

---

## Billing

| Feature | Status | Notes |
|---------|--------|-------|
| Stripe webhook router | ✅ | `v1/billing.py` (3.8KB) |
| Plan tier utility | ✅ | `planTier.js` (2.5KB) |
| Upgrade modal | ✅ | `UpgradeModal.jsx` (3.7KB) |
| Settings billing tab | ⚠️ | Exists; needs Stripe CLI verification |

---

## CI/CD & DevOps

| Feature | Status | Notes |
|---------|--------|-------|
| `backend-ci.yml` | ✅ | Ruff + mypy + pytest |
| `frontend-ci.yml` | ✅ | ESLint + build |
| `security.yml` | ✅ | Trivy + Bandit + OWASP |
| `deploy-production.yml` | ✅ | Production deployment |
| `e2e-production.yml` | ✅ | E2E tests |
| `deploy-staging.yml` | ❌ | **Missing** — needed before first deploy |
| Grafana dashboards | ❌ | Not set up |

---

## Frontend Route Count

| Old Plan Claim | Codex-Verified Reality |
|---------------|----------------------|
| 25 routes | **34 routes** confirmed in `frontend/src/app/` |
