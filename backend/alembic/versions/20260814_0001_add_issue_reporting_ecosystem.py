"""add issue reporting ecosystem

Revision ID: 20260814_0001
Revises: 5ab5f4f9e36d
Create Date: 2026-08-14 15:18:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260814_0001'
down_revision = '20260708_add_webhook_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the issues schema if it doesn't exist
    op.execute('CREATE SCHEMA IF NOT EXISTS issues')

    # Create issues table
    op.create_table(
        'issues',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tracking_number', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('priority', sa.String(), nullable=True),
        sa.Column('severity', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assignee_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('system_info', sa.JSON(), nullable=True),
        sa.Column('ai_category', sa.String(), nullable=True),
        sa.Column('ai_summary', sa.String(), nullable=True),
        sa.Column('ai_suggested_fix', sa.String(), nullable=True),
        sa.Column('github_issue_url', sa.String(), nullable=True),
        sa.Column('github_issue_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['assignee_id'], ['profiles.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['profiles.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='issues'
    )
    op.create_index(op.f('ix_issues_issues_id'), 'issues', ['id'], unique=False, schema='issues')
    op.create_index(op.f('ix_issues_issues_tracking_number'), 'issues', ['tracking_number'], unique=True, schema='issues')

    # Create issue_comments table
    op.create_table(
        'issue_comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('issue_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('body', sa.String(), nullable=False),
        sa.Column('is_internal', sa.Boolean(), nullable=True),
        sa.Column('is_ai_generated', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.issues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['profiles.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='issues'
    )
    op.create_index(op.f('ix_issues_issue_comments_id'), 'issue_comments', ['id'], unique=False, schema='issues')

    # Create issue_attachments table
    op.create_table(
        'issue_attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('issue_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_name', sa.String(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=False),
        sa.Column('mime_type', sa.String(), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('storage_path', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.issues.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='issues'
    )
    op.create_index(op.f('ix_issues_issue_attachments_id'), 'issue_attachments', ['id'], unique=False, schema='issues')

    # Create issue_settings table
    op.create_table(
        'issue_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('triage_model', sa.String(), nullable=True),
        sa.Column('reasoning_model', sa.String(), nullable=True),
        sa.Column('github_sync_enabled', sa.Boolean(), nullable=True),
        sa.Column('github_repo', sa.String(), nullable=True),
        sa.Column('slack_webhook_url', sa.String(), nullable=True),
        sa.Column('discord_webhook_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema='issues'
    )
    op.create_index(op.f('ix_issues_issue_settings_id'), 'issue_settings', ['id'], unique=False, schema='issues')


def downgrade() -> None:
    op.drop_index(op.f('ix_issues_issue_settings_id'), table_name='issue_settings', schema='issues')
    op.drop_table('issue_settings', schema='issues')
    op.drop_index(op.f('ix_issues_issue_attachments_id'), table_name='issue_attachments', schema='issues')
    op.drop_table('issue_attachments', schema='issues')
    op.drop_index(op.f('ix_issues_issue_comments_id'), table_name='issue_comments', schema='issues')
    op.drop_table('issue_comments', schema='issues')
    op.drop_index(op.f('ix_issues_issues_tracking_number'), table_name='issues', schema='issues')
    op.drop_index(op.f('ix_issues_issues_id'), table_name='issues', schema='issues')
    op.drop_table('issues', schema='issues')
    op.execute('DROP SCHEMA IF EXISTS issues')
