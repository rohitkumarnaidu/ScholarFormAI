<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: ScholarForm AI — Disaster Recovery Plan
description: RTO/RPO targets, backup procedures, and recovery runbooks
sidebar_position: 39
version: "1.0"
status: ✅ Complete
owner: Engineering Team
review_cadence: quarterly
last_updated: July 2026
---

# ScholarForm AI — Disaster Recovery Plan

**RTO:** 4 hours | **RPO:** 1 hour

> **See also:** [Deployment](../deployment/Deployment.md), [Runbooks](runbooks/), [Security](../../SECURITY.md)

---

## Recovery Objectives

| Metric | Target | Current |
| -------- | -------- | --------- |
| **RTO** (Recovery Time Objective) | 4 hours | < 2 hours (Render auto-deploy) |
| **RPO** (Recovery Point Objective) | 1 hour | < 15 minutes (Supabase continuous backup) |
| **MTTR** (Mean Time to Recovery) | 2 hours | < 1 hour |

---

## Table of Contents

- [Recovery Objectives](#recovery-objectives)
- [Disaster Scenarios](#disaster-scenarios)
- [Backup & Restore Procedures](#backup--restore-procedures)
- [Backup Strategy (Summary)](#backup-strategy-summary)
- [Contact List](#contact-list)
- [Post-Recovery Checklist](#post-recovery-checklist)

---

## Disaster Scenarios

### 1. Database Failure

**Trigger:** Supabase outage, data corruption, accidental deletion

**Recovery Steps:**

1. Check Supabase status page: <https://status.supabase.com>
2. If Supabase is down, wait for their recovery (they handle backups)
3. If data corruption, restore from latest point-in-time backup:
   - Supabase dashboard &rarr; Database &rarr; Backups &rarr; Restore
4. Verify data integrity:

   ```bash
   python backend/scripts/verify_backup.py
   python backend/scripts/verify_migration.py
   ```

5. Restart backend to pick up restored data

**Estimated Recovery Time:** 30 minutes - 2 hours

### 2. Backend Service Failure

**Trigger:** Bad deployment, OOM crash, infrastructure failure

**Recovery Steps:**

1. Check Render dashboard for service status
2. If bad deployment, rollback:

   ```bash
   render rollback --service scholarform-backend
   ```

3. If infrastructure failure, redeploy:

   ```bash
   render deploy --service scholarform-backend
   ```

4. Verify health endpoint:

   ```bash
   curl https://api.scholarform.ai/api/v1/health/live
   ```

**Estimated Recovery Time:** 5 - 15 minutes

### 3. Frontend Service Failure

**Trigger:** Build failure, CDN outage, DNS issues

**Recovery Steps:**

1. Check Render/Vercel dashboard
2. Redeploy frontend:

   ```bash
   # If on Render:
   render deploy --service scholarform-frontend
   # If on Vercel:
   vercel --prod
   ```

3. Verify frontend loads:

   ```bash
   curl -s -o /dev/null -w "%{http_code}" https://scholarform.ai
   ```

**Estimated Recovery Time:** 5 - 10 minutes

### 4. Complete Region Outage

**Trigger:** AWS/GCP region failure

**Recovery Steps:**

1. Activate secondary region (if configured)
2. Update DNS to point to secondary region
3. Restore database from cross-region backup
4. Deploy backend and frontend to secondary region
5. Verify all services

**Estimated Recovery Time:** 2 - 4 hours

---

## Backup & Restore Procedures

### Supabase Automated Backups

Supabase provides **continuous point-in-time recovery (PITR)** for Pro and Team plans.

**Verify Backup Status:**

```bash
cd backend
python scripts/verify_backup.py
```

**Restore from Backup:**

1. Go to Supabase Dashboard &rarr; Database &rarr; Backups
2. Select the restore point (PITR allows any timestamp within retention period)
3. Click "Restore"
4. Wait for restoration to complete (typically 5-15 minutes)
5. Verify data integrity:

   ```bash
   python scripts/verify_migration.py
   ```

### Manual Backup (for compliance)

```bash
# Export full database dump
pg_dump $SUPABASE_DB_URL --format=custom --file=backup_$(date +%Y%m%d_%H%M%S).dump

# Export specific tables
pg_dump $SUPABASE_DB_URL --table=documents --table=profiles --format=plain --file=schema_backup.sql
```

### File Storage Backup

Files are stored in Supabase Storage buckets. To backup:

```bash
# List all files in storage
supabase storage ls --project-ref YOUR_PROJECT_REF

# Download all files
supabase storage download --project-ref YOUR_PROJECT_REF --recursive / uploads_backup/
```

### Template Files

Templates are stored in `backend/app/templates/` and version-controlled in Git.

### Environment Variables Backup

1. Go to Render Dashboard &rarr; Environment
2. Export variables (manual copy)
3. Store encrypted backup in 1Password/LastPass

```bash
# Encrypt and backup
gpg --symmetric --cipher-algo AES256 backend/.env
# Store the .env.gpg file securely
```

### Redis Backup

Redis is used for caching and rate limiting. Data is ephemeral and can be rebuilt.

**If Redis data is lost:**

1. Rate limit counters reset (acceptable)
2. Cache warms up naturally as requests come in
3. No data loss &mdash; Redis only stores transient data

### Restore Verification

After any restore, run these checks:

```bash
# 1. Database connectivity
python scripts/verify_backup.py

# 2. Schema sync
python scripts/verify_migration.py

# 3. Backend health
curl -s https://api.scholarform.ai/api/v1/health/live | jq

# 4. Frontend health
curl -s -o /dev/null -w "%{http_code}" https://scholarform.ai

# 5. Run smoke tests
cd backend
pytest tests/test_smoke.py -v --no-cov
```

### Backup Schedule

| Task | Frequency | Automation |
| ------ | ----------- | ------------ |
| Supabase PITR | Continuous | Automatic |
| Manual DB dump | Weekly | Cron job |
| File storage sync | Daily | Supabase Storage API |
| Env var backup | On change | Manual |
| Backup verification | Weekly | CI/CD pipeline |

---

## Backup Strategy (Summary)

| Component | Backup Method | Frequency | Retention |
| ----------- | -------------- | ----------- | ----------- |
| PostgreSQL | Supabase PITR | Continuous | 7 days |
| Redis | AOF persistence | Continuous | N/A |
| Uploaded files | S3 versioning | Real-time | 30 days |
| Environment variables | Render env vars + encrypted backup | Manual | Latest |
| Code | GitHub | Every commit | Permanent |

---

## Contact List

| Role | Name | Contact |
| ------ | ------ | --------- |
| On-Call Engineer | PagerDuty rotation | Via PagerDuty |
| Engineering Lead | [Name] | [Email/Slack] |
| DevOps | [Name] | [Email/Slack] |
| Supabase Support | <support@supabase.com> | Via dashboard |
| Render Support | <support@render.com> | Via dashboard |

---

## Post-Recovery Checklist

- [ ] All services responding to health checks
- [ ] Database integrity verified
- [ ] User authentication working
- [ ] Document processing pipeline functional
- [ ] API key management operational
- [ ] Monitoring dashboards showing normal metrics
- [ ] Error budget impact assessed
- [ ] Postmortem scheduled if outage > 30 minutes
