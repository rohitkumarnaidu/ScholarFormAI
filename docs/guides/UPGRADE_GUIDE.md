# Upgrade Guide

This guide outlines best practices for upgrading self-hosted ScholarFormAI enterprise deployments.

## Pre-requisites

Before upgrading your enterprise deployment:
1. **Backup Database**: Perform a full backup of your PostgreSQL database containing user and job metadata.
2. **Backup Volumes**: Ensure any persistent volumes storing `.docx` objects are backed up.
3. **Review Changelog**: Carefully read the `CHANGELOG.md` for any infrastructure requirement changes (e.g., Redis version bumps).

## Standard Upgrade Path (Docker)

If you are running ScholarFormAI via Docker Compose:

1. **Pull the latest images:**
   ```bash
   docker-compose pull
   ```

2. **Run database migrations:**
   Our containers automatically apply Alembic database migrations on startup.

3. **Restart the stack:**
   ```bash
   docker-compose up -d
   ```

## Kubernetes Upgrades (Helm)

If you are managing the deployment via our official Helm chart:

1. **Update repositories:**
   ```bash
   helm repo update
   ```

2. **Upgrade the release:**
   ```bash
   helm upgrade scholarform-release scholarform/scholarform-ai -f custom-values.yaml
   ```

## Post-Upgrade Validation
- Access the health check endpoint: `GET /health` to ensure all services report `UP`.
- Run a test document through the formatting pipeline to verify worker nodes are properly attached.

If you encounter issues, refer to the [Troubleshooting Guide](../support/TROUBLESHOOTING.md) or revert to the previous snapshot.
