# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from pathlib import Path


def test_persona_dashboard_exists_and_references_persona_metrics():
    repo_root = Path(__file__).resolve().parents[2]
    dashboard_path = repo_root / "backend" / "ops" / "grafana" / "dashboards" / "scholarform-persona-kpis.json"

    assert dashboard_path.exists(), "Persona KPI dashboard must exist"
    dashboard = dashboard_path.read_text(encoding="utf-8")

    assert "persona_events_total" in dashboard
    assert "persona_operation_duration_seconds" in dashboard
    assert "ScholarForm Persona KPIs" in dashboard
