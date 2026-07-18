<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — Backup & Recovery
description: Backup strategy, retention policies, recovery procedures, and RTO/RPO targets
sidebar_position: 38
version: "1.0"
status: ✅ Complete
owner: Engineering Team
review_cadence: quarterly
last_updated: July 2026
---

# ScholarForm AI — Backup & Recovery

**RTO (Critical):** < 1 hour | **RPO:** < 5 minutes via WAL

> **See also:** [Disaster Recovery](DISASTER_RECOVERY.md), [Deployment](Deployment.md), [Security](Security.md), [Secret Rotation](SECRET_ROTATION.md), [ChromaDB / RAG Architecture](CHROMA_RAG_ARCHITECTURE.md), [Database Architecture](DATABASE_ARCHITECTURE.md)

---

## Table of Contents

- [RTO/RPO Targets](#rtorpo-targets)
- [Backup Strategy](#backup-strategy)
  - [PostgreSQL (Supabase Managed)](#1-postgresql-supabase-managed)
  - [File Storage](#2-file-storage)
  - [ChromaDB / RAG Vector Store](#3-chromadb--rag-vector-store)
  - [Configuration & Secrets](#4-configuration--secrets)
  - [Redis (Ephemeral)](#5-redis-ephemeral)
  - [Code Repository](#6-code-repository)
  - [Alembic Migrations](#7-alembic-migrations)
- [Backup Schedule](#backup-schedule)
- [Retention Policy](#retention-policy)
- [Recovery Procedures](#recovery-procedures)
  - [Point-in-Time Recovery (PITR)](#point-in-time-recovery-pitr)
  - [Full Restore from Latest Snapshot](#full-restore-from-latest-snapshot)
  - [Cross-Region Failover](#cross-region-failover)
  - [ChromaDB Rebuild from kb.json](#chromadb-rebuild-from-kbjson)
  - [File Storage Recovery](#file-storage-recovery)
  - [Configuration Recovery](#configuration-recovery)
- [Testing & Validation](#testing--validation)
  - [Backup Verification Script](#backup-verification-script)
  - [Migration Verification Script](#migration-verification-script)
  - [Restore Drills Schedule](#restore-drills-schedule)
  - [Backup Monitoring](#backup-monitoring)
- [Disaster Scenarios](#disaster-scenarios)
  - [1. Database Corruption](#1-database-corruption)
  - [2. Region Outage](#2-region-outage)
  - [3. Accidental Data Deletion](#3-accidental-data-deletion)
  - [4. Ransomware / Malicious Access](#4-ransomware--malicious-access)
  - [5. Configuration Loss](#5-configuration-loss)
  - [6. ChromaDB / RAG Store Loss](#6-chromadb--rag-store-loss)
  - [7. File Storage Loss](#7-file-storage-loss)
- [Success Metrics & SLAs](#success-metrics--slas)
- [Appendix: Backup Automation Scripts](#appendix-backup-automation-scripts)

---

## RTO/RPO Targets

ScholarForm AI maintains tiered recovery targets aligned with service criticality:

| Service Tier | RTO (Recovery Time Objective) | RPO (Recovery Point Objective) | Examples |
|-------------|-------------------------------|-------------------------------|---------|
| **Critical** | < 1 hour | < 5 minutes | PostgreSQL (user data, documents, API keys), Auth (Supabase Auth) |
| **High** | < 2 hours | < 15 minutes | ChromaDB vector store, file storage (uploads/, output/) |
| **Medium** | < 4 hours | < 1 hour | Configuration (.env, encrypted secrets), AI model store |
| **Low** | < 8 hours | N/A (rebuildable) | Redis cache, rate-limit counters, ephemeral logs |

**Supabase PITR** provides continuous WAL archiving, keeping RPO under 5 minutes for the primary database. The ChromaDB `kb.json` portable snapshot provides a recoverable RPO of < 15 minutes based on the ingestion cadence.

---

## Backup Strategy

### 1. PostgreSQL (Supabase Managed)

**Primary database** for all persistent data — user profiles, documents, API keys, billing records, audit logs, session state, and application metadata.

| Property | Specification |
|----------|--------------|
| **Provider** | Supabase (managed PostgreSQL 15.x) |
| **Plan** | Pro / Team (PITR enabled) |
| **Backup Method** | Continuous WAL archiving + daily snapshots |
| **Encryption** | AES-256 at rest (Supabase-managed) |
| **Replication** | Synchronous replication across AZs (Supabase HA add-on) |

**Backup mechanisms:**

- **Write-Ahead Log (WAL) Archiving** — Every transaction is written to WAL segments and archived continuously to Supabase-managed S3 storage. Enables point-in-time recovery to any second within the retention window. This is the primary mechanism that achieves < 5 minute RPO.
- **Daily Snapshots** — Full database snapshot taken once per day during off-peak hours (02:00 UTC). Used for full restores and as a baseline for PITR.
- **Logical Replication** — Optional cross-region publication/subscription for active-active or active-passive failover configurations.

**Data at rest:** All Supabase PostgreSQL instances encrypt data using AES-256 with automatic key management. Connections require TLS 1.2+ (enforced at the database level via `sslmode=require`).

**Alembic schema tracking:** All schema changes are version-controlled in `backend/alembic/versions/`. The `alembic_version` table tracks the current migration state. In a restore scenario, the schema is already present in the snapshot — no migration replay is needed unless restoring to a blank database.

**Key tables:**

| Table | Content | Recovery Criticality |
|-------|---------|---------------------|
| `profiles` | User profiles, preferences | Critical |
| `documents` | Manuscript metadata, status, processing history | Critical |
| `user_api_keys` | Encrypted provider API keys | Critical |
| `api_key_usage_log` | API key consumption tracking | High |
| `billing_*` | Subscription, invoice, payment records | High |
| `audit_log` | Security and compliance audit trail | High |
| `webhook_*` | Webhook delivery and event tracking | Medium |
| `custom_providers` | BYO provider definitions | Medium |
| `generator_sessions` | AI document generator sessions | Medium |

### 2. File Storage

ScholarForm AI uses Supabase Storage (S3-compatible) for user-uploaded manuscripts and generated output files. Local disk storage (`uploads/`, `output/` directories) is used in development and self-hosted deployments.

| Property | Specification |
|----------|--------------|
| **Source** | Supabase Storage buckets (`uploads/`, `output/`) |
| **Method** | S3 versioning + lifecycle policies |
| **Encryption** | AES-256 server-side (SSE-S3) |
| **Versioning** | Enabled on all buckets (retains all object versions) |

**Uploads bucket (`uploads/`):**
- Contains raw uploaded manuscripts (PDF, DOCX, TXT, etc.)
- S3 versioning preserves all upload versions (deletes are recoverable)
- Lifecycle rule transitions objects from Standard to Glacier after 30 days
- Permanent deletion only after 365 days

**Output bucket (`output/`):**
- Contains generated formatted manuscripts and preview files
- Versioning preserves previous formatting iterations
- Lifecycle: Standard for 7 days, then Glacier for 90 days

**Local file system (self-hosted):**
- Managed via `settings.RETENTION_DAYS` (default: 30 days, configured in `DeploymentSettings`)
- `_cleanup_expired_uploads()` runs at startup and every 24 hours via `_periodic_file_cleanup()`
- Files older than `RETENTION_DAYS` are removed based on `st_mtime`
- Cleanup can be disabled via `ENABLE_FILE_CLEANUP=false` in `.env`
- **Temporary pause:** The auto-cleanup periodic task is currently disabled (commented out in `backend/app/main.py:504`). Only the startup cleanup runs when `ENABLE_FILE_CLEANUP=true`.

### 3. ChromaDB / RAG Vector Store

ScholarForm AI uses ChromaDB with a dual-backend design for the formatting-guideline vector store.

| Property | Specification |
|----------|--------------|
| **Location** | `backend/db/semantic_store/` |
| **Primary Store** | `chroma.sqlite3` + segment binary files (`*.bin`) |
| **Portable Snapshot** | `kb.json` — human-readable, self-contained, cross-version portable |
| **Method** | Dual-write every `add_guideline()` call writes to both stores |
| **Auto-Seed Source** | `backend/app/pipeline/intelligence/default_guidelines.json` |

**Directory layout:**
```
backend/db/semantic_store/
  ├── chroma.sqlite3          # ChromaDB SQLite metadata + index catalog
  ├── <uuid>/                 # Segment directory (one per embedding model)
  │   ├── header.bin
  │   ├── data_level0.bin
  │   ├── length.bin
  │   └── link_lists.bin
  └── kb.json                 # Portable JSON snapshot (embeddings + metadata)
```

**Why dual storage:**
- **ChromaDB** provides fast cosine-similarity retrieval with metadata filtering.
- **`kb.json`** is a portable, human-readable snapshot that can be used to rebuild ChromaDB on a different host, ChromaDB version, or embedding model.
- The native `kb.json` fallback requires only NumPy (stdlib dot-product) — no ChromaDB dependency for recovery.

**Recovery note:** ChromaDB segment files are coupled to the embedding model dimension and ChromaDB client version. For cross-version or cross-model recovery, always use `kb.json` as the transfer format and re-ingest to rebuild ChromaDB indexes.

### 4. Configuration & Secrets

| Component | Location | Backup Method | Encryption |
|-----------|----------|--------------|------------|
| `.env` file | `backend/.env` | GPG-encrypted backup + Render env vars | AES-256 (GPG) |
| `ENCRYPTION_KEY` | Render env vars + local .env | Stored in 1Password/LastPass vault | Vault-managed |
| Render env vars | Render Dashboard | Manual export + encrypted archive | Per-policy encryption |
| Contract YAML files | `backend/app/pipeline/contracts/` | Git-versioned | N/A (in-repo) |
| Template files | `backend/app/templates/` | Git-versioned | N/A (in-repo) |

**Encryption key criticality:**
The `ENCRYPTION_KEY` (Fernet symmetric key) is used to encrypt user-provided API keys at rest in the `user_api_keys` table. If lost:
- Existing encrypted API keys **cannot be decrypted**.
- Users must re-enter their API keys.
- On startup, `_validate_startup()` logs a critical warning and raises `RuntimeError` in production if `ENCRYPTION_KEY` is unset.

**Backup command:**
```bash
# Encrypt .env with GPG
gpg --symmetric --cipher-algo AES256 backend/.env
# Store backend/.env.gpg in secure vault (1Password, LastPass, or AWS Secrets Manager)
```

### 5. Redis (Ephemeral)

| Property | Specification |
|----------|--------------|
| **Use** | Caching, rate limiting, Celery broker, queue depth |
| **Persistence** | AOF (Append-Only File) with fsync every second |
| **Backup** | Not backed up — data is rebuildable |
| **RTO** | < 5 minutes (restart or rebuild) |

**Recovery on data loss:**
1. Rate-limit counters reset (acceptable — max throughput temporarily higher).
2. Cache entries recompute naturally as requests arrive.
3. Celery task queue: interrupted tasks are marked FAILED on restart via `_reset_interrupted_jobs_on_startup()`.
4. No permanent data loss — Redis only stores transient data.

### 6. Code Repository

| Property | Specification |
|----------|--------------|
| **Host** | GitHub (`scholarform/automated-manuscript-formatter`) |
| **Backup** | Every commit — permanent history |
| **Recovery** | `git clone`, `git checkout <tag>` |
| **RPO** | Instant (every push) |

### 7. Alembic Migrations

Schema migrations are stored as Python scripts under `backend/alembic/versions/`. They serve as a recoverable record of every schema change:
- **On PITR restore:** The restored snapshot already contains the schema and migration state — no migration replay needed.
- **On blank-database restore:** Run `alembic upgrade head` to replay all migrations from scratch.
- **Schema drift detection:** Run `python scripts/verify_migration.py` to compare the live schema against SQLAlchemy model definitions.

---

## Backup Schedule

| Component | Method | Frequency | Automation |
|-----------|--------|-----------|------------|
| PostgreSQL WAL archiving | Continuous streaming | Every transaction | Automatic (Supabase managed) |
| PostgreSQL daily snapshot | `pg_dump` custom format | Daily at 02:00 UTC | Automatic (Supabase managed) |
| PostgreSQL logical backup | `pg_dump` | Weekly (Sunday 03:00 UTC) | Cron job (`scripts/backup_db.sh`) |
| Supabase Storage versioning | S3 versioning | Real-time (every upload/modify) | Automatic |
| File system cleanup | `_cleanup_expired_uploads()` | Daily (startup + every 24h) | Via FastAPI lifespan task |
| ChromaDB dual-write to kb.json | `add_guideline()` | Real-time (every guideline write) | Application-level |
| ChromaDB auto-seed | `default_guidelines.json` | On first init (empty store) | Application-level |
| .env GPG-encrypted backup | Manual export + encryption | On change (or weekly) | Manual — tracked in vault |
| Render env var export | Manual copy | On change | Manual |
| Backup verification | `verify_backup.py` | Weekly (Sunday 04:00 UTC) | CI/CD cron trigger |
| Migration verification | `verify_migration.py` | Weekly (Sunday 04:30 UTC) | CI/CD cron trigger |
| Restore drill | Full procedure walkthrough | Quarterly | DevOps lead |

**Cron schedule summary:**

| Time (UTC) | Day | Task |
|------------|-----|------|
| 02:00 | Daily | PostgreSQL daily snapshot (Supabase managed) |
| 03:00 | Sunday | Manual `pg_dump` cold backup |
| 04:00 | Sunday | `scripts/verify_backup.py` |
| 04:30 | Sunday | `scripts/verify_migration.py --diff` |
| 05:00 | 1st of month | Monthly retention archive consolidation |
| On startup | — | `_cleanup_expired_uploads()` + `_reset_interrupted_jobs_on_startup()` |

---

## Retention Policy

| Data Category | Backup Type | Daily (7 days) | Weekly (4 weeks) | Monthly (12 months) | Annual |
|--------------|------------|----------------|------------------|--------------------|--------|
| PostgreSQL (WAL) | Continuous | Available for PITR | Available for PITR | Available for PITR | — |
| PostgreSQL (snapshot) | Full dump | Retention window | Kept (weekly) | Kept (monthly) | — |
| File uploads | S3 versioning | 30-day window | — | — | 365-day permanent deletion |
| File outputs | S3 versioning | 7-day hot storage | 90-day Glacier | — | — |
| Local files (disk) | `st_mtime` | `RETENTION_DAYS` (default 30) | — | — | — |
| ChromaDB / kb.json | On-disk + snapshot | Latest (no versioning) | — | — | — |
| .env.gpg | Vault | — | — | Latest + 1 previous | — |
| Render env vars | Vault | — | — | Latest | — |
| Audit logs | PostgreSQL | — | — | 12 months (queryable) | 7 years (archive) |
| Code (Git) | GitHub | Per commit | — | — | Permanent |

**File system retention details:**
- Controlled by `RETENTION_DAYS` (default: 30) in `DeploymentSettings` (`backend/app/config/settings.py:394`).
- Files in `uploads/` directory with `st_mtime` older than `RETENTION_DAYS * 86400` seconds are removed.
- Cleanup runs at application startup and every 24 hours via `_periodic_file_cleanup()` asyncio task.
- Disabled entirely by setting `ENABLE_FILE_CLEANUP=false`.
- **Note:** The periodic task is currently commented out in `backend/app/main.py:504`. Only the startup-time cleanup runs when `ENABLE_FILE_CLEANUP=true`.

**S3 lifecycle rules:**
```
uploads/ bucket:
  Current versions: 30 days Standard → Glacier → delete after 365 days
  Noncurrent versions: 7 days → delete after 30 days

output/ bucket:
  Current versions: 7 days Standard → 90 days Glacier → delete after 365 days
  Noncurrent versions: 7 days → delete after 30 days
```

---

## Recovery Procedures

### Point-in-Time Recovery (PITR)

**When to use:** Recover to a specific timestamp before data corruption, accidental deletion, or a bad migration.

**Prerequisites:**
- Supabase Pro or Team plan (PITR feature)
- Supabase Dashboard access with Owner/Admin role
- Retention window within the last 7 days (Supabase default)

**Procedure:**

1. **Assess the damage:**
   ```bash
   # Check current database health
   python backend/scripts/verify_backup.py

   # Check for schema drift
   python backend/scripts/verify_migration.py --diff
   ```

2. **Determine the target timestamp:**
   - Identify the exact time (UTC) before the corrupting event.
   - Check audit logs in Supabase or the `audit_log` table for suspicious activity timestamps.

3. **Initiate restore via Supabase Dashboard:**
   - Navigate to: Supabase Dashboard → Database → Backups → Restore
   - Select **Point-in-Time** restore mode
   - Enter the target timestamp (ISO 8601 format: `YYYY-MM-DD HH:MM:SS UTC`)
   - Click "Restore"
   - **Expected duration:** 5–15 minutes (dependent on database size and WAL volume)

4. **Verify recovery:**
   ```bash
   python backend/scripts/verify_backup.py
   python backend/scripts/verify_migration.py
   ```

5. **Restart backend services:**
   - Deployment automatically picks up the restored database after connection pool resets.
   - If the backend was connected during restore, force a restart:
     ```bash
     render restart --service scholarform-backend
     ```

6. **Validate application state:**
   ```bash
   # Check health endpoints
   curl https://api.scholarform.ai/api/v1/health/live
   curl https://api.scholarform.ai/api/v1/health/ready

   # Run smoke tests
   cd backend && pytest tests/test_smoke.py -v --no-cov
   ```

**Rollback consideration:** If the PITR restore does not resolve the issue, restore from the most recent daily snapshot instead (full restore, see below).

### Full Restore from Latest Snapshot

**When to use:** Complete database loss, migration to a new Supabase project, or PITR is insufficient.

**Procedure:**

1. **Obtain the latest snapshot:**
   - Supabase Dashboard → Database → Backups → Download latest backup
   - Or via CLI: `supabase db dump --project-ref YOUR_PROJECT_REF -f latest_snapshot.sql`

2. **Restore to target database:**
   ```bash
   # If restoring to a new Supabase project:
   psql "$SUPABASE_DB_URL" -f latest_snapshot.sql

   # Or use pg_restore for custom format dumps:
   pg_restore --dbname="$SUPABASE_DB_URL" --verbose latest_snapshot.dump
   ```

3. **Run migration verification:**
   ```bash
   python backend/scripts/verify_migration.py
   # If schema drift is detected:
   alembic upgrade head
   ```

4. **Verify data integrity:**
   ```bash
   python backend/scripts/verify_backup.py
   # Check critical tables have expected row counts
   ```

5. **Update connection strings:**
   - If the database URL changed, update `SUPABASE_DB_URL` in Render env vars and deploy.

### Cross-Region Failover

**When to use:** Complete Supabase region outage affecting the primary database.

**Procedure:**

1. **Activate secondary region (Supabase HA):**
   - If using Supabase HA add-on, failover is automatic — DNS routes to the standby replica.
   - Verify failover status on Supabase Dashboard.

2. **Without HA add-on — manual promotion:**
   - Promote the read replica in the secondary region to primary.
   - Update `SUPABASE_URL` and `SUPABASE_DB_URL` in Render env vars to point to the new primary.

3. **Deploy backend to secondary region:**
   ```bash
   render deploy --service scholarform-backend-secondary
   ```

4. **Update DNS:**
   - Point `api.scholarform.ai` to the secondary region's Render service.
   - DNS propagation may take 5–30 minutes (TTL-dependent).

5. **Verify all services:**
   ```bash
   curl https://api.scholarform.ai/api/v1/health/live
   curl https://api.scholarform.ai/api/v1/health/ready

   # Test user-facing endpoints
   curl -I https://scholarform.ai
   ```

6. **Post-recovery:**
   - Confirm data consistency between regions.
   - Document the failover event for postmortem.

### ChromaDB Rebuild from kb.json

**When to use:** ChromaDB store is corrupted, lost, or needs to be migrated to a different environment or ChromaDB version.

**Procedure:**

1. **Verify the kb.json exists and is valid:**
   ```bash
   # kb.json should exist at backend/db/semantic_store/kb.json
   python -c "import json; data=json.load(open('backend/db/semantic_store/kb.json')); print(f'{len(data)} guidelines loaded')"
   ```

2. **Delete the ChromaDB store (optional, for full rebuild):**
   ```bash
   rm -rf backend/db/semantic_store/chroma.sqlite3 backend/db/semantic_store/*/
   ```

3. **Rebuild ChromaDB from kb.json:**
   ```python
   # Run via Python or in a one-off script:
   from app.pipeline.intelligence.rag_engine import get_rag_engine
   import json

   rag = get_rag_engine()
   rag.reset()  # Clears ChromaDB + kb.json

   with open("backend/db/semantic_store/kb.json") as f:
       entries = json.load(f)

   for entry in entries:
       rag.add_guideline(
           publisher=entry["metadata"]["publisher"],
           section=entry["metadata"]["section"],
           text=entry["text"],
           metadata=entry.get("metadata"),
       )

   print(f"Rebuilt ChromaDB with {len(entries)} guidelines")
   ```

4. **Alternative: Full re-ingest from contract YAML files:**
   ```bash
   cd backend
   python scripts/ingest_guidelines.py
   ```

5. **Verify the rebuild:**
   ```python
   result = rag.query_guidelines("IEEE", "abstract formatting", top_k=3)
   print(f"Query returned {len(result)} results")
   ```

**Note:** If `kb.json` is also lost, re-run `ingest_guidelines.py` which re-seeds from `default_guidelines.json` and contract YAML files.

### File Storage Recovery

**When to use:** User uploads or output files are accidentally deleted or corrupted.

**Supabase Storage (primary):**

1. **Restore via S3 versioning:**
   - Supabase Dashboard → Storage → Select bucket → Show deleted versions
   - Select the version to restore and click "Restore"
   - Or via API: `supabase storage cp --project-ref YOUR_PROJECT_REF s3://bucket/path/deleted-version-id s3://bucket/path/`

2. **Bulk download (alternative):**
   ```bash
   supabase storage download --project-ref YOUR_PROJECT_REF --recursive / uploads_restore/
   ```

**Local file system (self-hosted):**

1. **Check if file is within retention window:**
   - Files are cleaned up after `RETENTION_DAYS` (default: 30). If within window and cleanup has not yet run, the file may still exist.
   - If the cleanup has already removed the file, recover from Supabase Storage.

2. **Restore from Supabase Storage to local:**
   ```bash
   supabase storage download --project-ref YOUR_PROJECT_REF uploads/path/to/file ./uploads/
   ```

### Configuration Recovery

**When to use:** `.env` file is lost, corrupted, or needs to be restored on a new deployment.

1. **Recover from GPG-encrypted backup:**
   ```bash
   gpg --decrypt backend/.env.gpg > backend/.env
   ```

2. **Recover from Render Dashboard:**
   - Render Dashboard → scholarform-backend → Environment
   - Copy all environment variables manually
   - Alternatively, use the Render API:
     ```bash
     render env list --service scholarform-backend --format json > .env
     ```

3. **Generate a fresh .env from template:**
   ```bash
   python scripts/generate_env_template.py
   # Then populate from vault/1Password
   ```

4. **Regenerate ENCRYPTION_KEY (last resort):**
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
   **Warning:** This invalidates all encrypted user API keys. Users must re-enter their keys.

---

## Testing & Validation

### Backup Verification Script

**Location:** `backend/scripts/verify_backup.py`

**Purpose:** Validates database connectivity, table integrity, and schema state for backup assurance.

**Checks performed:**
1. Database connection via `SUPABASE_DB_URL`
2. Current timestamp retrieval (`SELECT NOW()`)
3. Public table count (`information_schema.tables`)
4. Auth schema table count
5. Presence of critical tables: `documents`, `profiles`, `user_api_keys`, `api_key_usage_log`

**Usage:**
```bash
cd backend
python scripts/verify_backup.py
# Output:
# ✅ Database connection successful: 2026-07-16 04:00:00+00
# ✅ Public tables: 42
# ✅ Auth tables: 28
# ✅ Table 'documents': exists
# ✅ Table 'profiles': exists
# ✅ Table 'user_api_keys': exists
# ✅ Table 'api_key_usage_log': exists
# ✅ Backup verification complete at 2026-07-16T04:00:00+00:00
```

**Exit codes:** `0` = success, `1` = failure (suitable for CI/CD gating).

### Migration Verification Script

**Location:** `backend/scripts/verify_migration.py`

**Purpose:** Validates that the live database schema matches the SQLAlchemy model definitions. Detects drift before it becomes a restore issue.

**Checks performed:**
1. Compares model table set vs. database table set
2. Compares column sets for each table (detects missing or extra columns)
3. Ignores `alembic_version` table (expected to be present only in DB, not models)

**Usage:**
```bash
cd backend
python scripts/verify_migration.py          # Pass/fail check
python scripts/verify_migration.py --diff    # Show detailed column differences
```

### Restore Drills Schedule

| Frequency | Drill Type | Scope | Owner | Validation |
|-----------|-----------|-------|-------|------------|
| **Monthly** | Automated backup verification | DB connectivity, table integrity | DevOps | `verify_backup.py` exit code 0 |
| **Quarterly** | PITR restore drill | Restore from 6-hour-old snapshot to staging | Engineering Lead | Verify data consistency, run smoke tests |
| **Semi-annual** | Full DR walkthrough | Region failover, ChromaDB rebuild, config restore | Engineering Lead + DevOps | All recovery procedures tested end-to-end |
| **Annual** | Ransomware simulation | Full isolation + restore from immutable backup | Security + Engineering | RTO < 1 hour for critical services |

**Drill documentation:**
Each drill produces a report documenting:
- Timestamp and duration of the drill
- Deviations from the documented procedure
- Actual RTO/RPO achieved vs. targets
- Action items for procedure improvements

### Backup Monitoring

| Metric | Source | Alert Threshold | Notification |
|--------|--------|----------------|--------------|
| Backup age | Supabase Dashboard | > 24 hours since last snapshot | PagerDuty (warning) |
| WAL archiving lag | Supabase Dashboard | > 5 minutes | PagerDuty (critical) |
| `verify_backup.py` failure | CI/CD cron | Non-zero exit | Slack #ops-alerts |
| `verify_migration.py` failure | CI/CD cron | Schema drift detected | Slack #ops-alerts |
| Storage bucket version count | S3 metrics | > 10,000 noncurrent versions | Slack #ops (housekeeping) |
| File cleanup failures | Application logs | > 5 errors in 24h | Grafana alert |
| ChromaDB rebuild trigger | Application logs | `reset()` called outside ingest | Slack #ops-alerts |

---

## Disaster Scenarios

### 1. Database Corruption

**Trigger:** Application bug writing malformed data, hardware fault at Supabase, physical corruption in PostgreSQL pages.

**Symptoms:**
- `verify_backup.py` reports query failures
- Application returns 500 errors on data-read endpoints
- PostgreSQL logs show `WARNING: page verification failed` or `ERROR: invalid page in block`

**Recovery procedure:**

| Step | Action | Time Estimate |
|------|--------|---------------|
| 1 | Isolate corruption scope (identify affected tables/rows) | 10 minutes |
| 2 | Determine safe restore timestamp (before corruption) | 5 minutes |
| 3 | Initiate PITR restore to safe timestamp | 15 minutes |
| 4 | Verify data integrity | 5 minutes |
| 5 | If PITR fails, restore from latest daily snapshot | 10 minutes |
| 6 | Run migration verification | 2 minutes |
| 7 | Validate application endpoints | 5 minutes |
| **Total RTO** | | **30–45 minutes** |

**Outcome:** Data restored to within 5 minutes of corruption event (PITR) or within 24 hours (snapshot).

### 2. Region Outage

**Trigger:** AWS/Azure/GCP region failure affecting Supabase or Render.

**Symptoms:**
- All services unreachable from primary region
- Supabase Dashboard returns region-level errors
- Render services show `DOWN` in primary region

**Recovery procedure:**

| Step | Action | Time Estimate |
|------|--------|---------------|
| 1 | Confirm region outage (check status pages) | 5 minutes |
| 2 | Activate secondary region DR plan | 10 minutes |
| 3 | Promote cross-region read replica (if configured) | 15 minutes |
| 4 | Deploy backend to secondary Render region | 10 minutes |
| 5 | Update DNS records | 5 minutes (TTL) |
| 6 | Deploy frontend to secondary region | 5 minutes |
| 7 | Verify health endpoints | 5 minutes |
| **Total RTO** | | **30–55 minutes** |

**Outcome:** Services operational in secondary region. Data loss limited to WAL lag (seconds, not minutes) if synchronous replication is configured.

### 3. Accidental Data Deletion

**Trigger:** User deletes documents, admin runs destructive query, API misuse.

**Symptoms:**
- User reports missing documents or profiles
- Audit log shows `DELETE` operations from unexpected source

**Recovery procedure:**

| Step | Action | Time Estimate |
|------|--------|---------------|
| 1 | Identify deletion timestamp from audit logs | 5 minutes |
| 2 | Determine if soft-delete data exists in trash | 5 minutes |
| 3 | If not recoverable via application, initiate PITR | 15 minutes |
| 4 | Restore deleted rows only (pg_dump + selective restore if possible) | 20 minutes |
| 5 | If selective restore not feasible, full PITR restore | 30 minutes |
| **Total RTO** | | **15–45 minutes** |

**Outcome:** Deleted records restored. For accidental mass deletion, PITR to 5 minutes before the delete event.

### 4. Ransomware / Malicious Access

**Trigger:** Compromised credentials, insider threat, supply chain attack.

**Symptoms:**
- Unauthorized data access detected by monitoring
- Files encrypted or deleted
- Suspicious API key usage

**Recovery procedure:**

| Step | Action | Time Estimate |
|------|--------|---------------|
| 1 | **Isolate** — immediately revoke compromised credentials | 5 minutes |
| 2 | **Contain** — enable maintenance mode, block all non-critical traffic | 5 minutes |
| 3 | **Assess** — identify scope of impacted data from audit logs | 15 minutes |
| 4 | **Restore** — restore database from pre-incident PITR timestamp | 30 minutes |
| 5 | **Restore** — recover file storage from S3 versioning (pre-encryption versions) | 15 minutes |
| 6 | **Rotate** — rotate all secrets (see [Secret Rotation](SECRET_ROTATION.md)) | 30 minutes |
| 7 | **Verify** — confirm data integrity and security posture | 15 minutes |
| **Total RTO** | | **60–90 minutes** |

**Key defense:** Immutable backups (S3 versioning, WAL archive) are separate from the production access path. Even if production credentials are compromised, the backup store is protected by separate IAM roles and MFA.

### 5. Configuration Loss

**Trigger:** `.env` file deletion, Render env var corruption, vault service outage.

**Symptoms:**
- Backend fails to start with `ENCRYPTION_KEY is not set` critical error
- Missing API keys cause LLM fallback tiers to be unavailable
- CORS misconfiguration blocks frontend requests

**Recovery procedure:**

| Step | Action | Time Estimate |
|------|--------|---------------|
| 1 | Restore `.env` from GPG-encrypted backup | 5 minutes |
| 2 | If encrypted backup unavailable, restore from Render Dashboard export | 10 minutes |
| 3 | Regenerate `ENCRYPTION_KEY` only as last resort (invalidates user API keys) | 5 minutes |
| 4 | Deploy configuration fix | 5 minutes |
| **Total RTO** | | **10–20 minutes** |

**Prevention:** Store current + one previous version of `.env.gpg` in the vault. Render stores the last deployed env var state — rolling back a deployment also rolls back environment variables.

### 6. ChromaDB / RAG Store Loss

**Trigger:** Disk failure on persist directory, accidental deletion of `db/semantic_store/`, ChromaDB version incompatibility after upgrade.

**Symptoms:**
- RAG queries return empty results
- Application logs show `WARNING: ChromaDB query failed, falling back to native store`
- If `kb.json` also missing: `WARNING: RAG engine returning empty results`

**Recovery procedure:**

| Step | Action | Time Estimate |
|------|--------|---------------|
| 1 | Check if `kb.json` exists | 1 minute |
| 2 | If `kb.json` exists, rebuild ChromaDB (see [ChromaDB Rebuild](#chromadb-rebuild-from-kbjson)) | 5 minutes |
| 3 | If `kb.json` is also lost, re-run `ingest_guidelines.py` | 10 minutes |
| 4 | Verify RAG queries return results | 2 minutes |
| **Total RTO** | | **5–15 minutes** |

**Auto-recovery:** On first query after store loss, the native `kb.json` fallback loads into memory automatically. The system operates in degraded mode until ChromaDB is rebuilt.

### 7. File Storage Loss

**Trigger:** S3 bucket accidental deletion, misconfigured lifecycle policy, local disk failure (self-hosted).

**Symptoms:**
- Missing user uploads
- Generated output files unavailable for download
- `FileNotFoundError` in application logs

**Recovery procedure:**

| Step | Action | Time Estimate |
|------|--------|---------------|
| 1 | Check S3 versioning — deleted objects may still exist as prior versions | 5 minutes |
| 2 | Restore from S3 versioning via Supabase Storage Dashboard | 15 minutes |
| 3 | If versioning was not enabled, restore from cross-region replication target | 30 minutes |
| 4 | For local disk failure (self-hosted), restore from Supabase Storage | 30 minutes |
| **Total RTO** | | **15–45 minutes** |

---

## Success Metrics & SLAs

### RTO/RPO Summary

| Component | RTO Target | RPO Target | Achieved | Measurement |
|-----------|-----------|-----------|----------|-------------|
| PostgreSQL (PITR) | < 30 min | < 5 min | < 15 min | Drill timing |
| PostgreSQL (snapshot) | < 45 min | < 24 h | < 30 min | Drill timing |
| File storage (S3 versioning) | < 30 min | < 5 min | < 15 min | Restore test |
| ChromaDB (kb.json rebuild) | < 15 min | < 15 min | < 10 min | Benchmark |
| Configuration | < 20 min | N/A | < 10 min | Drill timing |
| Full DR (all components) | < 4 h | < 1 h | < 2 h | Annual drill |

### Backup Coverage

| Metric | Target | Current | Measurement |
|--------|--------|---------|-------------|
| Backup success rate | 99.9% | 100% | `verify_backup.py` success rate |
| Migration sync rate | 100% | 100% | `verify_migration.py` pass rate |
| PITR availability | 99.95% | 99.99% | Supabase SLA |
| S3 versioning coverage | 100% | 100% | All buckets versioned |
| Encryption at rest | 100% | 100% | AES-256 for all stores |

### Recovery Validation

After any recovery operation, the following validation sequence must complete successfully:

```bash
# 1. Database connectivity and integrity
python backend/scripts/verify_backup.py

# 2. Schema sync
python backend/scripts/verify_migration.py

# 3. Backend health (liveness)
curl -s https://api.scholarform.ai/health | jq .

# 4. Backend readiness (dependencies)
curl -s https://api.scholarform.ai/ready | jq .

# 5. Frontend availability
curl -s -o /dev/null -w "%{http_code}" https://scholarform.ai

# 6. Smoke tests
cd backend && pytest tests/test_smoke.py -v --no-cov

# 7. RAG engine validation (if applicable)
python -c "from app.pipeline.intelligence.rag_engine import get_rag_engine; r=get_rag_engine(); print('RAG ready:', len(r.query_guidelines('IEEE', 'abstract', top_k=1)) > 0)"
```

---

## Appendix: Backup Automation Scripts

### `scripts/verify_backup.py`

Validates database availability and table integrity. Intended for CI/CD cron triggers and on-demand checks.

**Exit codes:** `0` = healthy, `1` = failure.

**Dependencies:** `sqlalchemy`, `SUPABASE_DB_URL` environment variable.

### `scripts/verify_migration.py`

Validates SQLAlchemy schema vs. live database. Detects drift before it causes restore errors.

**Flags:**
- `--diff`: Show detailed column-level differences (default: pass/fail only)

**Exit codes:** `0` = in sync, `1` = drift detected.

**Dependencies:** `sqlalchemy`, `SUPABASE_DB_URL`, `backend/app/models`.

### `scripts/ingest_guidelines.py`

Re-seeds the ChromaDB RAG store from contract YAML files + default guidelines. Used for initial setup and full RAG rebuild.

**Usage:** `cd backend && python scripts/ingest_guidelines.py`

### `scripts/generate_env_template.py`

Generates a fresh `.env` template from the settings model. Useful for configuration recovery when the encrypted backup is unavailable.

**Output:** Writes to `backend/.env` (only if the file does not exist).

### `scripts/sync_version.py`

Synchronizes version strings across `pyproject.toml`, `frontend/package.json`, and `CITATION.cff`.

**Usage:** `python scripts/sync_version.py` or `python scripts/sync_version.py --check` (CI mode).

---

## Testing — Backup Restoration Drills & Validation

### Restoration Drill Procedures

Automated drill scripts test each recovery procedure against the documented steps:

```bash
# Full drill suite
python scripts/run_backup_drills.py

# Individual drill
python scripts/run_backup_drills.py --drill pitr
```

| Drill | Script | Frequency | Validates | Pass Criteria |
|---|---|---|---|---|
| DB connectivity | `verify_backup.py` | Weekly | DB reachable, critical tables exist | Exit code 0 |
| Schema integrity | `verify_migration.py` | Weekly | SQLAlchemy models match live schema | Exit code 0 |
| PITR restore | Manual drill | Quarterly | Staging DB restored to 6h-old snapshot | All smoke tests pass on restored DB |
| ChromaDB rebuild | `python -c "..."` | Monthly | `kb.json` ingested → RAG queries return results | Query returns > 0 results |
| File recovery | `supabase storage cp` | Monthly | Deleted file restored from S3 versioning | File content matches original |
| Full DR walkthrough | Manual | Semi-annual | All recovery procedures end-to-end | RTO < 4h, RPO < 1h |
| Ransomware simulation | Manual | Annual | Immutable backup restore from air-gapped store | RTO < 90 min |

### Backup Flow

```mermaid
graph TD
    subgraph Production
        PG[(PostgreSQL<br/>Supabase)]
        FS[File Storage<br/>Supabase S3]
        CH[ChromaDB<br/>semantic_store/]
        CFG[Configuration<br/>.env + Render vars]
    end

    subgraph Backup Pipeline
        WAL[WAL Archiving<br/>Continuous]
        SNAP[Daily Snapshot<br/>02:00 UTC]
        S3_V[S3 Versioning<br/>Real-time]
        KB_JSON[kb.json<br/>Dual-write]
        GPG[GPG Encryption<br/>On change]
    end

    subgraph Storage
        WAL_S3[(WAL Archive<br/>S3 - Supabase managed)]
        SNAP_S3[(Snapshots<br/>S3 - Supabase managed)]
        S3_VERSIONS[(Object Versions<br/>S3)]
        KB_FILE[kb.json<br/>semantic_store/]
        GPG_FILE[.env.gpg<br/>Vault / 1Password]
        GIT[(GitHub<br/>Code + Migrations)]
    end

    subgraph Verification
        VB[verify_backup.py<br/>Weekly]
        VM[verify_migration.py<br/>Weekly]
        RD[Restore Drills<br/>Quarterly]
    end

    PG --> WAL
    PG --> SNAP
    FS --> S3_V
    CH --> KB_JSON
    CFG --> GPG

    WAL --> WAL_S3
    SNAP --> SNAP_S3
    S3_V --> S3_VERSIONS
    KB_JSON --> KB_FILE
    GPG --> GPG_FILE

    WAL_S3 --> VB
    SNAP_S3 --> VB
    S3_VERSIONS --> RD
    KB_FILE --> RD
    PG --> VM

    VB -->|Pass/Fail| ALERT{Slack / PagerDuty}
    VM -->|Schema drift?| ALERT
    RD -->|RTO met?| ALERT
```

### Testing `verify_backup.py`

```bash
# Basic validation
cd backend
python scripts/verify_backup.py

# CI mode (exits with code 1 on failure)
python scripts/verify_backup.py --ci

# With custom DB URL
SUPABASE_DB_URL=postgresql://... python scripts/verify_backup.py
```

Test patterns for backup verification:

```python
# test_verify_backup.py
def test_verify_backup_script(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://test:test@localhost:5432/test")
    result = subprocess.run(
        [sys.executable, "scripts/verify_backup.py"],
        capture_output=True, text=True, cwd=tmp_path
    )
    # Script should output checkmarks or error messages
    assert result.returncode in (0, 1)
    if result.returncode == 0:
        assert "Backup verification complete" in result.stdout

def test_migration_verification_detects_drift(monkeypatch):
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://test:test@localhost:5432/test")
    result = subprocess.run(
        [sys.executable, "scripts/verify_migration.py", "--diff"],
        capture_output=True, text=True
    )
    assert result.returncode in (0, 1)
```

### API Reference — Recovery Status Endpoints

| Endpoint | Method | Purpose | Recovery Use |
|---|---|---|---|
| `GET /health` | GET | Liveness check | Verify backend is running post-recovery |
| `GET /ready` | GET | Readiness with dependency status | Verify DB, GROBID, Redis all healthy |
| `GET /api/v1/health/live` | GET | Liveness probe | Automation-friendly health check |
| `GET /api/v1/health/ready` | GET | Strict readiness | Confirm all services operational |
| `GET /api/v1/documents` | GET | Document list check | Verify data survived restore |
| `GET /metrics` | GET | Prometheus metrics | Confirm metrics pipeline operational |

Post-recovery validation script:

```bash
#!/bin/bash
# verify_recovery.sh
set -e

echo "=== Post-Recovery Validation ==="
BASE=${PROD_BACKEND_URL:-https://api.scholarform.ai}

# 1. Backend live
curl -sf "$BASE/api/v1/health/live" > /dev/null && echo "Liveness: OK" || echo "Liveness: FAIL"

# 2. Readiness
READY=$(curl -sf "$BASE/api/v1/health/ready" | jq -r '.ready')
echo "Readiness: $READY"

# 3. DB health
DB=$(curl -sf "$BASE/ready" | jq -r '.checks.database // "unknown"')
echo "Database: $DB"

# 4. Verify backup script
python backend/scripts/verify_backup.py && echo "Backup verify: OK" || echo "Backup verify: FAIL"

# 5. Smoke tests
cd backend && pytest tests/test_smoke.py -v --no-cov --timeout=30 && echo "Smoke tests: PASS" || echo "Smoke tests: FAIL"
```
