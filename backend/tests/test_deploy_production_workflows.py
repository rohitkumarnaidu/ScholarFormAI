# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from pathlib import Path


def test_deploy_production_workflow_is_manual_and_health_guarded():
    repo_root = Path(__file__).resolve().parents[2]
    workflow_path = repo_root / ".github" / "workflows" / "deploy-production.yml"

    assert workflow_path.exists(), "deploy-production.yml must exist"
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert "name: deploy-production" in workflow_text
    assert "workflow_dispatch:" in workflow_text
    assert "push:" not in workflow_text
    assert "/health" in workflow_text
    assert "--connect-timeout 5" in workflow_text
    assert "--max-time 10" in workflow_text
    assert "exit 1" in workflow_text


def test_keepalive_workflow_contract_for_free_tier_reliability():
    repo_root = Path(__file__).resolve().parents[2]
    workflow_path = repo_root / ".github" / "workflows" / "keepalive-free-tier.yml"

    assert workflow_path.exists(), "keepalive-free-tier.yml must exist"
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert "name: keepalive-free-tier" in workflow_text
    assert 'cron: "*/14 * * * *"' in workflow_text
    assert "workflow_dispatch:" in workflow_text
    assert "/health" in workflow_text

    required_hf_secrets = [
        "HF_GROBID_PRIMARY_URL",
        "HF_GROBID_SHADOW_URL",
        "HF_DOCLING_PRIMARY_URL",
        "HF_DOCLING_SHADOW_URL",
        "HF_OCR_PRIMARY_URL",
        "HF_OCR_SHADOW_URL",
        "HF_DOCX_PRIMARY_URL",
        "HF_DOCX_SHADOW_URL",
    ]
    for secret in required_hf_secrets:
        assert secret in workflow_text, f"Missing keepalive secret reference: {secret}"
