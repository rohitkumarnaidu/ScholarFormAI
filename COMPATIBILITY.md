<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


# Platform Compatibility

## Python Compatibility

| Python Version | Status | Notes |
|---------------|--------|-------|
| 3.12.x | ✅ Full support | Tested in CI; recommended for production |
| 3.11.x | ❌ Incompatible | Pytest import collision with FastAPI test client |
| 3.13.x | 🔄 Experimental | Not yet tested in CI; may work but unsupported |
| 3.10.x | ❌ End of life | Dependencies require 3.11+ |

## Node.js Compatibility

| Node Version | Frontend | Backend Dev (lint) | Notes |
|-------------|----------|-------------------|-------|
| 22.x | ✅ Full | ✅ Full | Recommended |
| 20.x (LTS) | ✅ Full | ✅ Full | Minimum recommended |
| 18.x |  ️ Partial |  ️ Partial | Next.js 16 requires 18.17+; may work |
| < 18 | ❌ | ❌ | Next.js 16 requires 18.17+ |

## Browser Compatibility

| Browser | Frontend | Live Preview | Notes |
|---------|----------|-------------|-------|
| Chrome 120+ | ✅ Full | ✅ Full | Primary test target |
| Firefox 120+ | ✅ Full | ✅ Full | |
| Safari 17+ | ✅ Full | ✅ Full | |
| Edge 120+ | ✅ Full | ✅ Full | Chromium-based |
| Chrome < 120 |  ️ Partial |  ️ Partial | Last 2 major versions supported |
| IE 11 | ❌ | ❌ | Not supported |

## Database Compatibility

| Database | Version | Status | Notes |
|----------|---------|--------|-------|
| PostgreSQL | 15+ | ✅ Full | Supabase uses 15.x |
| PostgreSQL | 14 | ✅ Full | |
| PostgreSQL | < 14 |  ️ Partial | Some features may not work |
| SQLite | All | ❌ | Not supported; use PostgreSQL |

## Redis Compatibility

| Redis Version | Status | Notes |
|--------------|--------|-------|
| 7.x | ✅ Full | Recommended |
| 6.x | ✅ Full | |
| < 6 | ❌ | Not supported |

## Operating System

| OS | Backend | Frontend Dev | Production |
|----|---------|-------------|------------|
| Linux (Ubuntu 22.04+) | ✅ Full | ✅ Full | ✅ Recommended |
| macOS 14+ | ✅ Full | ✅ Full | ✅ Full |
| Windows 11 / Windows Server | ✅ Full | ✅ Full |  ️ Production not recommended |
| Windows 10 | ✅ Full | ✅ Full |  ️ Production not recommended |

## Docker

| Platform | Status | Notes |
|----------|--------|-------|
| Docker Engine 24+ | ✅ Full | |
| Docker Compose v2 | ✅ Full | |
| Podman |  ️ Untested | Should work; not in CI |
| Kubernetes |  ️ Experimental | Render deployment only; no K8s native config |

## LLM Provider Compatibility

| Provider | Model | Status | Fallback Tier |
|----------|-------|--------|---------------|
| NVIDIA NIM | Llama 3.3 70B | ✅ Full | Primary |
| Groq | llama-3.3-70b-versatile | ✅ Full | Fallback 1 |
| Ollama | DeepSeek, Llama | ✅ Full | Fallback 2 |
| OpenAI | GPT-4, GPT-3.5 | 🔄 Untested | API-compatible; not in CI |
| Anthropic | Claude | 🔄 Untested | API-compatible; not in CI |

---

*Last updated: July 2026*
