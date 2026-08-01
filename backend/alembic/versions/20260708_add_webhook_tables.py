"""Add webhook_subscriptions and webhook_delivery_logs tables

Revision ID: 20260708_add_webhook_tables
Revises: 20260708_add_v2_pagination_index
Create Date: 2026-07-08 00:00:00.000000
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "20260708_add_webhook_tables"
down_revision = "20260708_add_v2_pagination_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("events", JSONB(), nullable=False),
        sa.Column("secret", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_webhook_subs_user_id",
        "webhook_subscriptions",
        ["user_id"],
    )
    op.create_index(
        "idx_webhook_subs_active_events",
        "webhook_subscriptions",
        ["is_active", sa.text("events")],
        postgresql_using="gin",
    )

    op.create_table(
        "webhook_delivery_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("subscription_id", UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.Text(), nullable=False, server_default=""),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_webhook_delivery_sub_attempted",
        "webhook_delivery_logs",
        ["subscription_id", sa.text("attempted_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_webhook_delivery_sub_attempted", table_name="webhook_delivery_logs")
    op.drop_table("webhook_delivery_logs")
    op.drop_index("idx_webhook_subs_active_events", table_name="webhook_subscriptions")
    op.drop_index("idx_webhook_subs_user_id", table_name="webhook_subscriptions")
    op.drop_table("webhook_subscriptions")

__all__ = ['revision', 'down_revision', 'branch_labels', 'depends_on', 'upgrade', 'downgrade']
