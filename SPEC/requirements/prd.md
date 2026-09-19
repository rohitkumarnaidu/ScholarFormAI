<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: ScholarForm AI — Product Requirements Document (PRD)
description: Product vision, user stories, acceptance criteria, and out-of-scope items
sidebar_position: 55
version: "1.0"
status: ✅ Complete
owner: Product Team
review_cadence: quarterly
last_updated: July 2026
---

# ScholarForm AI — Product Requirements Document (PRD)

> **Codex Verdict:** "Feature-rich but operationally unstable" — strong file coverage, runtime validation required across all 34 routes.

> **See also:** [Features](Features.md), [Roadmap](../reports/ROADMAP.md), [Architecture](architecture.md)

---

## Product Vision

ScholarForm AI is a web-based academic manuscript formatting and AI document generation platform. It empowers academic researchers, students, and professionals to produce journal-compliant documents without LaTeX knowledge.

---

## Two Products, Four Modes

### Product 1 — Document Formatter

| Mode | Description | Status (Codex-verified) |
| ------ | ------------- | ------------------------ |
| **Mode A: Upload & Format** | Upload any document → select journal template → download formatted DOCX/PDF | ~60% Done (core pipeline works; quality score display & template save need live testing) |
| **Mode B: Live Preview Editor** | Split-screen TipTap editor with real-time HTML preview, template switching, AI sidebar | ~85% Files ✅ TipTap confirmed on `/edit`; WebSocket needs runtime QA |

### Product 2 — AI Document Generator

| Mode | Description | Status (Codex-verified) |
| ------ | ------------- | ------------------------ |
| **Mode A: Multi-Doc Synthesis** | Upload 2-6 papers → AI reads all → removes duplicates → generates synthesis | ~80% Files; `api.synthesis.js` was 36B stub (now wired) |
| **Mode B: AI Agent** | Chat-based: user describes paper → AI plans → generates outline → writes sections → refines | ~90% Files; end-to-end flow needs live LLM testing |

---

## Target Users

| Persona | Need | Key Flow |
| --------- | ------ | --------- |
| **PhD Student** | Format thesis for IEEE/ACM submission | Upload → Select IEEE → Download formatted |
| **Research Professor** | Generate literature review from multiple papers | Multi-upload → Synthesis → Review → Export |
| **Undergraduate** | Write a first research paper guided by AI | Chat with Agent → Outline → Generate → Edit |
| **Journal Editor** | Check formatting compliance | Upload → Quality score → Fix suggestions |
| **Guest User** | Quick format without account (5/day limit) | Upload → Process → Download (no login) |

---

## KPIs

| Metric | Target |
| -------- | -------- |
| Guest → Signup conversion | >15% |
| Upload → Download completion rate | >80% |
| Average generation quality score | >70% |
| P99 upload ACK latency | <400ms |
| P99 live preview RTT | <200ms |
| Monthly active users (6 months) | 1,000+ |

---

## Supported Templates (17)

IEEE, ACM, APA, MLA, Chicago, Harvard, Vancouver, Springer, Nature, Elsevier, Numeric, Modern Blue, Modern Gold, Modern Red, None, Resume, Portfolio

> **Codex finding:** Template whitelist is complete and validated in `backend/app/schemas/document.py`.

## Supported Input Formats (9)

DOCX, PDF (via GROBID/Docling fallback), ODT, TeX, HTML, Markdown, TXT, RTF, DOC

> **PDF parsing:** 3-tier fallback — GROBID (if running) → Docling → PyMuPDF. GROBID Docker requires 1.5GB RAM; Render free tier has 512MB. Docling is the production default.

## Supported Export Formats

DOCX, PDF (via LibreOffice), LaTeX (via Pandoc — stub, needs implementation)

---

## Route Inventory (34 Frontend Routes)

The master plan projected 25 frontend routes. As of the Codex audit there are **34 confirmed routes** in `frontend/src/app/`.

> **Stale plan drift note:** Original plan documents citing 25 routes are outdated. Use this file as truth.

---

## Quality Ratings (Codex 5.4 Audit, March 2026)

| Dimension | Score | Notes |
| ----------- | ------- | ------- |
| QA / Testing | **3/10** | 93 E2E files but most are stubs (<700 bytes each) |
| DevEx | **4/10** | Good architecture, but build issues logged × 13 |
| Documentation | **3/10** → **7/10** (target) | This reset addresses the gap |
| Production Readiness | **3/10** | Needs staging deploy + live validation |
| Backend File Coverage | **90%** | Files exist; runtime verification pending |
| Frontend File Coverage | **88%** | Files exist; runtime verification pending |
