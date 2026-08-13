"""add password reset fields and material feedback replies

Revision ID: f7a1b2c3d4e5
Revises: a1b2c3d4e567
Create Date: 2026-08-13 15:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "f7a1b2c3d4e5"
down_revision = "a1b2c3d4e567"
branch_labels = None
depends_on = None


def _table_exists(bind, name: str) -> bool:
    return inspect(bind).has_table(name)


def _column_exists(bind, table: str, column: str) -> bool:
    insp = inspect(bind)
    if not insp.has_table(table):
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def _index_exists(bind, name: str) -> bool:
    return bool(
        bind.execute(
            sa.text("SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = :name)"),
            {"name": name},
        ).scalar()
    )


def upgrade():
    bind = op.get_bind()

    if _table_exists(bind, "users"):
        if not _column_exists(bind, "users", "password_reset_token_hash"):
            op.add_column(
                "users",
                sa.Column("password_reset_token_hash", sa.String(length=255), nullable=True),
            )
        if not _column_exists(bind, "users", "password_reset_expires_at"):
            op.add_column(
                "users",
                sa.Column("password_reset_expires_at", sa.DateTime(timezone=True), nullable=True),
            )
        if not _index_exists(bind, "ix_users_password_reset_token_hash"):
            op.create_index(
                "ix_users_password_reset_token_hash",
                "users",
                ["password_reset_token_hash"],
                unique=False,
            )

    if not _table_exists(bind, "edu_material_feedback_replies"):
        op.create_table(
            "edu_material_feedback_replies",
            sa.Column("id", sa.BigInteger(), nullable=False),
            sa.Column("company_id", sa.BigInteger(), nullable=False),
            sa.Column("feedback_id", sa.BigInteger(), nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["feedback_id"], ["edu_material_feedback.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_edu_material_feedback_replies_company_id",
            "edu_material_feedback_replies",
            ["company_id"],
            unique=False,
        )
        op.create_index(
            "ix_edu_material_feedback_replies_feedback_id",
            "edu_material_feedback_replies",
            ["feedback_id"],
            unique=False,
        )
        op.create_index(
            "ix_edu_material_feedback_replies_user_id",
            "edu_material_feedback_replies",
            ["user_id"],
            unique=False,
        )
        op.create_index(
            "ix_feedback_replies_company_feedback",
            "edu_material_feedback_replies",
            ["company_id", "feedback_id"],
            unique=False,
        )
        op.create_index(
            "ix_edu_material_feedback_replies_created_at",
            "edu_material_feedback_replies",
            ["created_at"],
            unique=False,
        )
        op.create_index(
            "ix_edu_material_feedback_replies_updated_at",
            "edu_material_feedback_replies",
            ["updated_at"],
            unique=False,
        )

        # Backfill legacy admin_reply into the replies table (best-effort, idempotent).
        op.execute(
            sa.text(
                """
                INSERT INTO edu_material_feedback_replies (
                    company_id, feedback_id, user_id, message, created_at, updated_at
                )
                SELECT
                    f.company_id,
                    f.id,
                    COALESCE(f.resolved_by_user_id, f.user_id),
                    f.admin_reply,
                    COALESCE(f.updated_at, f.created_at, now()),
                    COALESCE(f.updated_at, f.created_at, now())
                FROM edu_material_feedback f
                WHERE f.admin_reply IS NOT NULL
                  AND TRIM(f.admin_reply) <> ''
                  AND NOT EXISTS (
                      SELECT 1
                      FROM edu_material_feedback_replies r
                      WHERE r.feedback_id = f.id
                        AND r.message = f.admin_reply
                  )
                """
            )
        )


def downgrade():
    bind = op.get_bind()

    if _table_exists(bind, "edu_material_feedback_replies"):
        op.drop_table("edu_material_feedback_replies")

    if _table_exists(bind, "users"):
        if _index_exists(bind, "ix_users_password_reset_token_hash"):
            op.drop_index("ix_users_password_reset_token_hash", table_name="users")
        if _column_exists(bind, "users", "password_reset_expires_at"):
            op.drop_column("users", "password_reset_expires_at")
        if _column_exists(bind, "users", "password_reset_token_hash"):
            op.drop_column("users", "password_reset_token_hash")
