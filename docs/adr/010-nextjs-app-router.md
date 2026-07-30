<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: "ADR 010: Next.js App Router (Not Vite)"
description: Decision to use Next.js App Router over Vite for frontend
sidebar_position: 49
version: "1.0"
status: ✅ Accepted
owner: Engineering Team
review_cadence: never
last_updated: July 2026
---

# ADR 010: Next.js App Router (Not Vite)

## Context

Early scaffolding may have referenced Vite as the frontend build tool. The project uses Next.js 16 with the App Router and React 19.

## Decision

Next.js 16 (App Router) is the sole frontend framework. Vite is not used. Key implications:

- File-based routing with `layout.jsx` and `page.jsx`
- Server Components by default, Client Components via `"use client"`
- Per-route metadata via `generateMetadata` or layout exports
- Turbopack as the dev server (`next dev --turbopack`)

## Consequences

- Frontend env vars must use `NEXT_PUBLIC_*` prefix (not `VITE_*`)
- `npm run dev` uses `next dev --turbopack`
- Client pages cannot export metadata — use parent layout.jsx for page titles
- No Vite-related config files should exist in the frontend directory
