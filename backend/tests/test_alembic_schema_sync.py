# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from pathlib import Path


def test_required_risk_migrations_exist_and_chain():
    versions_dir = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    audit = versions_dir / "20260315_0001_audit_log.py"
    billing = versions_dir / "20260315_0002_users_billing.py"

    assert audit.exists(), "Missing Alembic migration for audit_log table."
    assert billing.exists(), "Missing Alembic migration for users billing fields."

    audit_text = audit.read_text(encoding="utf-8")
    billing_text = billing.read_text(encoding="utf-8")

    assert "op.create_table(" in audit_text and "\"audit_log\"" in audit_text
    assert "down_revision" in audit_text and "20260311_0001" in audit_text

    assert "\"profiles\"" in billing_text
    assert "plan_tier" in billing_text
    assert "stripe_customer_id" in billing_text
    assert "billing_status" in billing_text
    assert "down_revision" in billing_text and "20260315_0001" in billing_text
