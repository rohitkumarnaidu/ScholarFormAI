<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: ScholarForm AI — Secret Rotation Policy
description: Procedures for rotating API keys, JWT secrets, and database credentials
sidebar_position: 36
version: "1.0"
status: ✅ Complete
owner: DevOps Team
review_cadence: quarterly
last_updated: July 2026
---

# ScholarForm AI — Secret Rotation Policy

**Frequency:** Quarterly (90 days)

> **See also:** [Security](Security.md), [Disaster Recovery](DISASTER_RECOVERY.md), [Deployment](Deployment.md)

---

## Secrets to Rotate

| Secret | Location | Frequency | Owner |
| -------- | ---------- | ----------- | ------- |
| `SECRET_KEY` | Render env vars | 90 days | Engineering Lead |
| `ENCRYPTION_KEY` | Render env vars | 90 days | Engineering Lead |
| `SUPABASE_ANON_KEY` | Supabase + Render | 180 days | DevOps |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase + Render | 180 days | DevOps |
| LLM API Keys | Render env vars | Per provider policy | Engineering |
| Redis password | Render env vars | 90 days | DevOps |

---

## Rotation Procedure

### 1. SECRET_KEY (JWT Signing)

```bash
# Generate new key
python -c "import secrets; print(secrets.token_hex(32))"

# Update in Render dashboard
# Deploy new version (all existing sessions will be invalidated)
# Notify users to re-login
```

### 2. ENCRYPTION_KEY (API Key Encryption)

```bash
# Generate new Fernet key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# IMPORTANT: Before rotating, re-encrypt all stored API keys with new key
# Then update the env var and deploy
```

### 3. LLM API Keys

```bash
# Generate new key from provider dashboard
# Update in Render env vars
# Deploy (no downtime — keys are read at request time)
```

### 4. Supabase Keys

```bash
# Supabase dashboard → Settings → API
# Generate new keys
# Update in Render env vars
# Deploy
```

---

## Automation (Future)

```yaml
# .github/workflows/rotate-secrets.yml
name: Rotate Secrets
on:
  schedule:
    - cron: '0 0 1 */3 *'  # Every 3 months
  workflow_dispatch:

jobs:
  rotate:
    runs-on: ubuntu-latest
    steps:
      - name: Generate new SECRET_KEY
        run: echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" >> $GITHUB_ENV
      - name: Update Render env vars
        run: |
          render env set --service scholarform-backend --key SECRET_KEY --value $SECRET_KEY
      - name: Notify team
        run: |
          curl -X POST $SLACK_WEBHOOK_URL -d '{"text":"SECRET_KEY rotated successfully"}'
```

---

## Emergency Rotation

If a secret is compromised:

1. **Immediately** rotate the compromised secret
2. **Audit** access logs for unauthorized usage
3. **Notify** affected users if their data was at risk
4. **Document** the incident in postmortem
