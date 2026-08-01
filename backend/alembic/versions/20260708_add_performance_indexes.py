"""add performance indexes

Revision ID: 20260708_add_performance_indexes
Revises: 20260629_0001
Create Date: 2026-07-08 00:00:00.000000
"""
import contextlib

import sqlalchemy as sa

from alembic import op

revision = "20260708_add_performance_indexes"
down_revision = "20260629_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("idx_documents_user_id", "documents", ["user_id"])
    op.create_index("idx_documents_status", "documents", ["status"])
    op.create_index("idx_documents_created_at", "documents", [sa.text("created_at DESC")])
    op.create_index("idx_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("idx_audit_log_timestamp", "audit_log", [sa.text("created_at DESC")])
    op.create_index("idx_audit_log_resource", "audit_log", ["resource_type", "resource_id"])
    op.create_index("idx_api_key_usage_key_id", "api_key_usage_log", ["key_id"])
    op.create_index("idx_api_key_usage_timestamp", "api_key_usage_log", [sa.text("timestamp DESC")])

    with contextlib.suppress(Exception):
        op.create_index(
            "idx_documents_fts",
            "documents",
            [sa.text("to_tsvector('english', COALESCE(raw_text, ''))")],
            postgresql_using="gin",
        )


def downgrade() -> None:
    op.drop_index("idx_documents_fts", table_name="documents")
    op.drop_index("idx_api_key_usage_timestamp", table_name="api_key_usage_log")
    op.drop_index("idx_api_key_usage_key_id", table_name="api_key_usage_log")
    op.drop_index("idx_audit_log_resource", table_name="audit_log")
    op.drop_index("idx_audit_log_timestamp", table_name="audit_log")
    op.drop_index("idx_audit_log_user_id", table_name="audit_log")
    op.drop_index("idx_documents_created_at", table_name="documents")
    op.drop_index("idx_documents_status", table_name="documents")
    op.drop_index("idx_documents_user_id", table_name="documents")

__all__ = ['revision', 'down_revision', 'branch_labels', 'depends_on', 'upgrade', 'downgrade']
