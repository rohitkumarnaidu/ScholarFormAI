<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# Self-Update & Release System — Developer Guide

## Architecture Overview

The update system provides automated version detection, cryptographic artifact verification, and zero-downtime updates across CLI, SDK, and Web UI environments.

```mermaid
flowchart TD
    subgraph Clients["Client Update Handlers"]
        CLI["CLI Tool\n(amf update)"]
        SDK["Python SDK\n(Version Audit)"]
        Web["Web UI\n(Version Banner)"]
    end

    subgraph Backend["Update Gateway"]
        Routes["/api/v1/updates/*\n(Version Check & Catalog)"]
        Service["UpdateService\n(Release Management & SHA256 Verification)"]
    end

    subgraph Upstream["Artifact Sources"]
        GH["GitHub Releases\n(Binaries & Changelogs)"]
        PyPI["PyPI Index\n(amf-cli / amf-sdk)"]
    end

    CLI --> Routes
    SDK --> Routes
    Web --> Routes

    Routes --> Service
    Service --> GH
    Service --> PyPI

    style Clients fill:#1a3a5c,color:#fff
    style Backend fill:#1a4a3c,color:#fff
    style Upstream fill:#4a2a5c,color:#fff
```

> [!IMPORTANT]
> All binary downloads are verified against SHA-256 checksum manifests before installation to prevent tampering and incomplete artifact downloads.

---

## Key Components

| Component | File | Purpose |
| ----------- | ------ | --------- |
| `UpdateService` | `backend/app/services/update_service.py` | Version discovery, release caching, and cryptographic verification |
| `update_routes.py` | `backend/app/api/update_routes.py` | REST endpoints for version checking and artifact metadata |
| `update.py` (CLI) | `cli/amf/commands/update.py` | `amf update` command implementation with automatic rollback |
| `UpdateBanner.tsx` | `frontend/src/components/UpdateBanner.tsx` | Real-time notification banner when a newer release is published |

---

## Update Verification Sequence

```mermaid
sequenceDiagram
    autonumber
    actor CLI as "amf update"
    participant Svc as "UpdateService"
    participant GH as "GitHub Releases"

    CLI->>Svc: check_latest_version(current_version)
    activate Svc
    Svc->>GH: Fetch Latest Release Manifest & SHA256 Checksums
    GH-->>Svc: Release Metadata + Signatures
    Svc-->>CLI: Version Comparison Report
    deactivate Svc

    alt Newer Version Available
        CLI->>GH: Download Updated Binary
        CLI->>CLI: Compute Local SHA256 Hash
        alt Signature Match
            CLI->>CLI: Replace Executable & Restart
            CLI-->>CLI: Update Successful ✅
        else Checksum Mismatch
            CLI-->>CLI: Abort Update & Maintain Current Binary ❌
        end
    end
```

---

## CLI Commands

```bash
# Check if a new version is available
amf update check

# Perform self-update to the latest version
amf update --yes

# Rollback to the previous version
amf update rollback
```
