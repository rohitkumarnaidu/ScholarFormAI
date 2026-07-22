<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: "ADR 008: LiteLLM for LLM Routing and Fallback"
description: Decision to use LiteLLM for multi-provider LLM abstraction
sidebar_position: 47
version: "1.0"
status: ✅ Accepted
owner: Engineering Team
review_cadence: never
last_updated: July 2026
---

# ADR 008: LiteLLM for LLM Routing and Fallback

## Context

The AI agent and synthesis features need access to large language models. A single provider introduces availability risk and cost inflexibility.

## Decision

Use LiteLLM as the LLM abstraction layer with a tiered fallback chain:

1. **Primary:** NVIDIA NIM (self-hosted or cloud API)
2. **Fallback 1:** Groq (low-cost, fast inference)
3. **Fallback 2:** DeepSeek via Ollama (local, no external dependency)

## Consequences

- Automatic failover if primary provider is unavailable
- Consistent API interface across all providers
- Prompt/response caching via Redis to reduce costs
- Each provider requires its own API key in environment variables
- `DEFAULT_FAST_MODE=true` skips LLM-dependent stages when no provider is available
