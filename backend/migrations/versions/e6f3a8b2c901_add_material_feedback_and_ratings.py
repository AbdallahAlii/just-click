"""add material feedback and rating aggregates

Revision ID: e6f3a8b2c901
Revises: d5e1f2a3b467
Create Date: 2026-07-13 10:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "e6f3a8b2c901"
down_revision = "d5e1f2a3b467"
branch_labels = None
depends_on = None


def _pg_type_exists(bind, name: str) -> bool:
    return bool(
        bind.execute(
            sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = :name)"),
            {"name": name},
        ).scalar()
    )


def _column_exists(bind, table: str, column: str) -> bool:
    insp = inspect(bind)
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

    if not _pg_type_exists(bind, "edu_material_feedback_type_enum"):
        op.execute(
            "CREATE TYPE edu_material_feedback_type_enum AS ENUM "
            "('rating', 'comment', 'broken_file', 'clarification')"
        )

    if not _pg_type_exists(bind, "edu_material_feedback_status_enum"):
        op.execute(
            "CREATE TYPE edu_material_feedback_status_enum AS ENUM ('open', 'resolved')"
        )

    if not _column_exists(bind, "edu_materials", "rating_count"):
        op.add_column(
            "edu_materials",
            sa.Column("rating_count", sa.Integer(), server_default="0", nullable=False),
        )

    if not _column_exists(bind, "edu_materials", "rating_avg"):
        op.add_column(
            "edu_materials",
            sa.Column("rating_avg", sa.Float(), server_default="0", nullable=False),
        )

    insp = inspect(bind)
    if insp.has_table("edu_material_feedback"):
        return

    feedback_type = postgresql.ENUM(
        "rating",
        "comment",
        "broken_file",
        "clarification",
        name="edu_material_feedback_type_enum",
        create_type=False,
    )
    feedback_status = postgresql.ENUM(
        "open",
        "resolved",
        name="edu_material_feedback_status_enum",
        create_type=False,
    )

    op.create_table(
        "edu_material_feedback",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("material_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("feedback_type", feedback_type, nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", feedback_status, nullable=True),
        sa.Column("admin_reply", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "(rating IS NULL) OR (rating >= 1 AND rating <= 5)",
            name="ck_material_feedback_rating_range",
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["edu_materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    indexes = [
        ("ix_edu_material_feedback_company_id", ["company_id"], False, None),
        ("ix_edu_material_feedback_material_id", ["material_id"], False, None),
        ("ix_edu_material_feedback_user_id", ["user_id"], False, None),
        ("ix_edu_material_feedback_feedback_type", ["feedback_type"], False, None),
        ("ix_edu_material_feedback_status", ["status"], False, None),
        ("ix_material_feedback_company_material", ["company_id", "material_id"], False, None),
        ("ix_material_feedback_company_status", ["company_id", "status"], False, None),
        (
            "uq_material_feedback_one_rating",
            ["company_id", "material_id", "user_id"],
            True,
            sa.text("feedback_type = 'rating'"),
        ),
    ]

    for name, columns, unique, where in indexes:
        if _index_exists(bind, name):
            continue
        op.create_index(
            name,
            "edu_material_feedback",
            columns,
            unique=unique,
            postgresql_where=where,
        )


def downgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    if insp.has_table("edu_material_feedback"):
        for name in [
            "uq_material_feedback_one_rating",
            "ix_material_feedback_company_status",
            "ix_material_feedback_company_material",
            "ix_edu_material_feedback_status",
            "ix_edu_material_feedback_feedback_type",
            "ix_edu_material_feedback_user_id",
            "ix_edu_material_feedback_material_id",
            "ix_edu_material_feedback_company_id",
        ]:
            if _index_exists(bind, name):
                op.drop_index(name, table_name="edu_material_feedback")
        op.drop_table("edu_material_feedback")

    if _column_exists(bind, "edu_materials", "rating_avg"):
        op.drop_column("edu_materials", "rating_avg")
    if _column_exists(bind, "edu_materials", "rating_count"):
        op.drop_column("edu_materials", "rating_count")

    if _pg_type_exists(bind, "edu_material_feedback_status_enum"):
        op.execute("DROP TYPE edu_material_feedback_status_enum")
    if _pg_type_exists(bind, "edu_material_feedback_type_enum"):
        op.execute("DROP TYPE edu_material_feedback_type_enum")
