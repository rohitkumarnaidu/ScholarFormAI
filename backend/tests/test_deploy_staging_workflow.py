from __future__ import annotations

from pathlib import Path


def test_deploy_staging_workflow_exists_and_has_required_contract():
    repo_root = Path(__file__).resolve().parents[2]
    workflow_path = repo_root / ".github" / "workflows" / "deploy-staging.yml"

    assert workflow_path.exists(), "deploy-staging.yml must exist"
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert "name: deploy-staging" in workflow_text
    assert "workflow_dispatch:" in workflow_text
    assert "workflow_run:" in workflow_text
    assert "Frontend CI" in workflow_text
    assert "/api/v1/health" in workflow_text

    required_secrets = [
        "RENDER_API_KEY",
        "RENDER_STAGING_SERVICE_ID",
        "RENDER_STAGING_DEPLOY_HOOK_URL",
        "STAGING_BACKEND_URL",
        "VERCEL_TOKEN",
        "VERCEL_ORG_ID",
        "VERCEL_STAGING_PROJECT_ID",
    ]
    for secret in required_secrets:
        assert secret in workflow_text, f"Missing required staging workflow secret reference: {secret}"
