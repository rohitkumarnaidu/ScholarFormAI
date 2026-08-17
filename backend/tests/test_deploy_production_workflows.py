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
