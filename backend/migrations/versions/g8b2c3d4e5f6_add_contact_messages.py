"""add contact messages

Revision ID: g8b2c3d4e5f6
Revises: f7a1b2c3d4e5
Create Date: 2026-08-13 17:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "g8b2c3d4e5f6"
down_revision = "f7a1b2c3d4e5"
branch_labels = None
depends_on = None


def _table_exists(bind, name: str) -> bool:
    return inspect(bind).has_table(name)


def _pg_type_exists(bind, name: str) -> bool:
    return bool(
        bind.execute(
            sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = :name)"),
            {"name": name},
        ).scalar()
    )


def upgrade():
    bind = op.get_bind()

    if not _pg_type_exists(bind, "contact_message_status_enum"):
        op.execute(
            "CREATE TYPE contact_message_status_enum AS ENUM "
            "('open', 'in_progress', 'resolved', 'spam')"
        )

    if _table_exists(bind, "contact_messages"):
        return

    status = postgresql.ENUM(
        "open",
        "in_progress",
        "resolved",
        "spam",
        name="contact_message_status_enum",
        create_type=False,
    )

    op.create_table(
        "contact_messages",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", status, nullable=False, server_default="open"),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("company_id", sa.BigInteger(), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("admin_reply", sa.Text(), nullable=True),
        sa.Column("handled_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("handled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["handled_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contact_messages_email", "contact_messages", ["email"])
    op.create_index("ix_contact_messages_status", "contact_messages", ["status"])
    op.create_index("ix_contact_messages_user_id", "contact_messages", ["user_id"])
    op.create_index("ix_contact_messages_company_id", "contact_messages", ["company_id"])
    op.create_index("ix_contact_messages_created_at", "contact_messages", ["created_at"])
    op.create_index("ix_contact_messages_updated_at", "contact_messages", ["updated_at"])


def downgrade():
    bind = op.get_bind()
    if _table_exists(bind, "contact_messages"):
        op.drop_table("contact_messages")
    if _pg_type_exists(bind, "contact_message_status_enum"):
        op.execute("DROP TYPE contact_message_status_enum")
