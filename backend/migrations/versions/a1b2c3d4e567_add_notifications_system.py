"""add notifications system

Revision ID: a1b2c3d4e567
Revises: e6f3a8b2c901
Create Date: 2026-07-13 14:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "a1b2c3d4e567"
down_revision = "e6f3a8b2c901"
branch_labels = None
depends_on = None


def _table_exists(bind, name: str) -> bool:
    return inspect(bind).has_table(name)


def _index_exists(bind, name: str) -> bool:
    return bool(
        bind.execute(
            sa.text("SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = :name)"),
            {"name": name},
        ).scalar()
    )


def upgrade():
    bind = op.get_bind()

    if not _table_exists(bind, "notification_batches"):
        op.create_table(
            "notification_batches",
            sa.Column("id", sa.BigInteger(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("company_id", sa.BigInteger(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("event_type", sa.String(length=50), nullable=False),
            sa.Column("channels_json", sa.String(length=120), nullable=False),
            sa.Column("material_id", sa.BigInteger(), nullable=True),
            sa.Column("created_by_user_id", sa.BigInteger(), nullable=True),
            sa.Column("recipient_count", sa.Integer(), server_default="0", nullable=False),
            sa.Column("in_app_count", sa.Integer(), server_default="0", nullable=False),
            sa.Column("email_count", sa.Integer(), server_default="0", nullable=False),
            sa.Column("push_count", sa.Integer(), server_default="0", nullable=False),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["material_id"], ["edu_materials.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _index_exists(bind, "ix_notification_batches_company_created"):
        op.create_index(
            "ix_notification_batches_company_created",
            "notification_batches",
            ["company_id", "created_at"],
        )

    if not _table_exists(bind, "user_notifications"):
        op.create_table(
            "user_notifications",
            sa.Column("id", sa.BigInteger(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("company_id", sa.BigInteger(), nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("batch_id", sa.BigInteger(), nullable=True),
            sa.Column("event_type", sa.String(length=50), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("data_json", sa.Text(), nullable=True),
            sa.Column("material_id", sa.BigInteger(), nullable=True),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["batch_id"], ["notification_batches.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _index_exists(bind, "ix_user_notifications_user_unread"):
        op.create_index(
            "ix_user_notifications_user_unread",
            "user_notifications",
            ["company_id", "user_id", "read_at"],
        )

    if not _table_exists(bind, "user_device_tokens"):
        op.create_table(
            "user_device_tokens",
            sa.Column("id", sa.BigInteger(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("company_id", sa.BigInteger(), nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("token", sa.String(length=512), nullable=False),
            sa.Column("platform", sa.String(length=20), server_default="android", nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _index_exists(bind, "ix_user_device_tokens_user_token"):
        op.create_index(
            "ix_user_device_tokens_user_token",
            "user_device_tokens",
            ["company_id", "user_id", "token"],
            unique=True,
        )

    if not _table_exists(bind, "push_outbox"):
        op.create_table(
            "push_outbox",
            sa.Column("id", sa.BigInteger(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("company_id", sa.BigInteger(), nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("device_token", sa.String(length=512), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("data_json", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
            sa.Column("tries", sa.Integer(), server_default="0", nullable=False),
            sa.Column("last_error", sa.String(length=800), nullable=True),
            sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notification_id", sa.BigInteger(), nullable=True),
            sa.Column("batch_id", sa.BigInteger(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _index_exists(bind, "ix_push_outbox_status_created"):
        op.create_index("ix_push_outbox_status_created", "push_outbox", ["status", "created_at"])


def downgrade():
    bind = op.get_bind()
    for table in ("push_outbox", "user_device_tokens", "user_notifications", "notification_batches"):
        if _table_exists(bind, table):
            op.drop_table(table)
